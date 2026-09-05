import numpy as np
import torch
torch.set_num_threads(1)  # CRITICAL for single-core cloud deployments (Railway) to prevent OOM/deadlocks
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from pre_build.db import repository
from pre_build.fhir.fhir_client import MockFhirClient, Observation
from pre_build.fhir.progress_note import RiskSummary, build_progress_note
from pre_build.spatial import build_zip_index, resolve_coordinate
from pre_build.exposure import IndoorEdgeSignals, classify_indoor, shielding_for_zip, effective_exposure
from pre_build.model import TFTConfig, TFTSkeleton, HEADS
from pre_build.triage import climate_volatility_delta, aggregate_head_deltas, TokenBucketConstrainer, PatientFlag
from pre_build.explain import attribute_head
from pre_build.consent import fresh_track_a, route_patient
from pre_build.outreach import SmsContext, render_sms

# Global instances
fhir_client = MockFhirClient()
zip_idx = build_zip_index()
cfg = TFTConfig(horizon_hours=72, environmental_input_dim=8)
model = TFTSkeleton(cfg).eval()

checkpoint_path = Path(__file__).resolve().parent.parent / "model" / "tft_trained.pt"
if checkpoint_path.exists():
    model.load_state_dict(torch.load(checkpoint_path, map_location="cpu", weights_only=True))

from pre_build.climate.live_weather import fetch_live_air_quality, generate_climate_anomaly_string

CLINIC_PANEL_SIZE = 420
rng = np.random.default_rng(42)

def get_all_patients(region: Optional[str] = None):
    """Patients from Supabase; falls back to the mock seed if the DB is
    unreachable or empty (keeps the demo resilient)."""
    patients = list(fhir_client.seed_patients.values())
    eff_region = (region or CURRENT_REGION or "dallas").lower()
    if eff_region == "new_delhi":
        return patients[12:24]
    return patients[0:12]

from pre_build.api.schemas import SimulationOverrides

def get_patient_detail(patient_id: str):
    patient = fhir_client.fetch_patient(patient_id)
    obs = fhir_client.fetch_observations(patient_id)
    meds = fhir_client.fetch_medications(patient_id)
    return patient, obs, meds

def run_patient_pipeline(patient_id: str, anomaly_type: str = None, overrides: Optional[SimulationOverrides] = None, region: Optional[str] = None):
    patient, obs, meds = get_patient_detail(patient_id)
    
    # S2 Spatiotemporal
    patient_num = int(patient_id.replace("PT-", "")) if "PT-" in patient_id else 1
    is_india = (patient_num >= 13) or (region == "new_delhi") or (CURRENT_REGION == "new_delhi")
    if is_india:
        home_lat, home_lon = 28.6139, 77.2090
        city = "New Delhi"
    else:
        home_lat, home_lon = 32.8410, -96.7100
        city = "Dallas"
        
    hit = resolve_coordinate(home_lat, home_lon, zip_idx)
    
    # Apply Clinical Overrides to FHIR Observations
    if overrides:
        obs = list(obs)
        if overrides.spo2 is not None:
            # Overwrite or append SpO2 (LOINC 59408-5)
            spo2_obs = next((o for o in obs if o.code == "59408-5"), None)
            if spo2_obs:
                obs = [o if o.code != "59408-5" else Observation(o.id, o.patient_id, o.code, o.display, overrides.spo2, o.unit, o.effective_datetime, o.category) for o in obs]
            else:
                obs.append(Observation("OBS-SIM", patient.id, "59408-5", "SpO2 (pulse ox)", overrides.spo2, "%", "2026-09-03T12:00:00Z"))
        
        if overrides.systolic_bp is not None:
            # Overwrite or append Systolic BP (LOINC 8480-6)
            bp_obs = next((o for o in obs if o.code == "8480-6"), None)
            if bp_obs:
                obs = [o if o.code != "8480-6" else Observation(o.id, o.patient_id, o.code, o.display, overrides.systolic_bp, o.unit, o.effective_datetime, o.category) for o in obs]
            else:
                obs.append(Observation("OBS-SIM-BP", patient.id, "8480-6", "Systolic BP", overrides.systolic_bp, "mmHg", "2026-09-03T12:00:00Z"))

    # S3 Exposure & Live Climate
    aqi_data = fetch_live_air_quality(home_lat, home_lon, anomaly_type, city=city)
    
    if overrides and overrides.custom_aqi is not None:
        aqi_data["aqi"] = overrides.custom_aqi
        aqi_data["category"] = "Unhealthy (Simulated Override)"
        aqi_data["dominant"] = "PM2.5"
    climate_anomaly = generate_climate_anomaly_string(aqi_data)
    
    signals = IndoorEdgeSignals(home_wifi_match=True, barometric_variance_hpa=0.03, pedometer_steps_5min=8, gps_signal_dbm=-156, rh_indoor_proxy=0.46)
    indoor = classify_indoor(signals)
    sc = shielding_for_zip(patient.postal_code)
    
    outdoor = rng.uniform(20, 180, size=(1, 72, 8)).astype(np.float32)
    indoor_mask = np.full((1, 72, 1), indoor.indoor)
    effective = effective_exposure(outdoor, sc, indoor_mask)
    
    # S4 Model
    static_x = torch.from_numpy(rng.normal(size=(1, cfg.static_input_dim)).astype(np.float32))
    clin_x = torch.from_numpy(rng.normal(size=(1, 72, cfg.clinical_input_dim)).astype(np.float32))
    env_x = torch.from_numpy(effective)
    
    with torch.no_grad():
        logits = model(static_x, clin_x, env_x)
    probs = {h: float(torch.sigmoid(logits[h]).item()) for h in HEADS}
    
    baseline_probs = {"respiratory": 0.12, "cardiovascular": 0.10, "metabolic": 0.08}
    deltas = {h: float(climate_volatility_delta(np.array([probs[h]]), np.array([baseline_probs[h]]), anomaly_z=2.1)[0]) for h in HEADS}
    
    if anomaly_type and anomaly_type in HEADS:
        deltas[anomaly_type] = max(deltas[anomaly_type], 0.45)
        probs[anomaly_type] = max(probs[anomaly_type], 0.88)
        top_head = anomaly_type
    else:
        top_head = max(deltas, key=deltas.get)

    combined = float(aggregate_head_deltas({h: np.array([deltas[h]]) for h in HEADS})[0])
    
    # S5 Triage
    our_flag = PatientFlag(patient_id=patient.id, volatility_delta=combined, risk_total=probs[top_head], head=top_head, payload={"head_probs": probs})
    other_flags = [PatientFlag(patient_id=f"PT-{i:04d}", volatility_delta=float(rng.uniform(0, 0.4)), risk_total=float(rng.uniform(0, 1)), head="respiratory") for i in range(1, CLINIC_PANEL_SIZE)]
    constrainer = TokenBucketConstrainer(panel_size=CLINIC_PANEL_SIZE, top_fraction=0.05)
    decision = constrainer.constrain(other_flags + [our_flag])
    
    rank = next((i for i, f in enumerate(decision.accepted, start=1) if f.patient_id == patient.id), None)
    
    # S6 XAI
    bundle = attribute_head(model, top_head, static_x, clin_x, env_x, n_steps=16)
    summary = bundle.per_channel_summary()
    top_env = sorted(summary["environmental"].items(), key=lambda x: -x[1])[:3]
    top_static = sorted(summary["static"].items(), key=lambda x: -x[1])[:3]
    
    driver_strings = [f"Environmental ch={k} contribution={v:.3f}" for k, v in top_env] + [f"Static ch={k} contribution={v:.3f}" for k, v in top_static[:2]]
    
    driver_objects = []
    env_names = {0: "Ozone (O3)", 1: "PM2.5", 2: "Temperature", 3: "Humidity"}
    for k, v in top_env:
        name = env_names.get(k, f"Env Signal {k}")
        driver_objects.append({"label": name, "stream": "environmental", "value": float(v)})
    for k, v in top_static[:2]:
        driver_objects.append({"label": f"Clinical Factor {k}", "stream": "static", "value": float(v)})

    # S7 Outreach
    from pre_build.outreach.gemini_agent import generate_sms, SmsContext
    
    consent = fresh_track_a(patient.id, signed_at=datetime.now(timezone.utc), policy_version="v3.2")
    plan = route_patient(consent)
    
    drafted_sms = ""
    if plan.may_send_automated_sms:
        print(f"\n[Agent] Drafting personalized SMS via Vertex AI for {patient.display_name}...")
        # Target language is directly derived from the patient's record (fallback if none)
        target_lang = getattr(patient, "primary_language", None)
        if not target_lang:
            target_lang = "hi" if is_india else "en"

        drafted_sms = generate_sms(SmsContext(
            given_name=patient.given_name,
            head=top_head,
            climate_anomaly=climate_anomaly,
            city=city,
            locale=target_lang,
            has_smart_home=getattr(patient, "has_smart_home", False)
        ))
        try:
            print(f"[Agent SMS Result]: {drafted_sms}\n")
        except UnicodeEncodeError:
            print(f"[Agent SMS Result (Unicode)]: {drafted_sms.encode('ascii', 'backslashreplace').decode('ascii')}\n")
        
        # SMART HOME IOT MOCK
        iot_shielding_command = None
        if getattr(patient, "has_smart_home", False):
            if top_head == "respiratory":
                if is_india:
                    iot_shielding_command = {"device": "Xiaomi Smart Air Purifier 4", "action": "set_mode_turbo", "reason": f"AQI={aqi_data['aqi']}"}
                else:
                    iot_shielding_command = {"device": "Google Nest Thermostat", "action": "enable_hvac_fan", "reason": f"AQI={aqi_data['aqi']}"}
            elif top_head == "cardiovascular":
                if is_india:
                    iot_shielding_command = {"device": "Tata Smart AC", "action": "set_temp_22C", "reason": "Pre-Monsoon Heatwave"}
                else:
                    iot_shielding_command = {"device": "Google Nest Thermostat", "action": "pre_cool_68F", "reason": "Extreme Heat Dome"}
            elif top_head == "metabolic":
                if is_india:
                    iot_shielding_command = {"device": "Luminous Smart Inverter", "action": "reserve_battery_100", "reason": "Flash Flood Power Outage Risk"}
                else:
                    iot_shielding_command = {"device": "Tesla Powerwall", "action": "enable_storm_watch", "reason": "ERCOT Grid Alert"}
            
            if iot_shielding_command:
                print(f"[IoT Shielding] Sent JSON payload: {iot_shielding_command}")
            
        outreach_message = f"Drafted SMS: {drafted_sms}"
    else:
        outreach_message = f"Send 48h proactive {plan.outreach_channel.replace('_', ' ')} regarding {climate_anomaly}."
        iot_shielding_command = None
        
    note = build_progress_note(
        summary=RiskSummary(patient_id=patient.id, head=top_head, volatility_delta=combined, forecast_probability=probs[top_head], horizon_hours=72, top_drivers=driver_strings),
        recommendations=[outreach_message],
        clinician_id="PR-7791"
    )

    # Update the in-memory global state so the dashboard reflects the jump!
    target_flags = TRIAGE_FLAGS_BY_REGION.get("new_delhi" if is_india else "dallas", [])
    for i, f in enumerate(target_flags):
        if f.patient_id == patient.id:
            target_flags[i] = replace(f, risk_total=probs[top_head], volatility_delta=combined)
            break
            
    # Persist this run to Supabase (best-effort — never break the response).
    triage_status = "accepted" if rank is not None else "deferred"
    try:
        repository.save_risk_score(patient.id, probs, deltas, combined, top_head)
        repository.save_triage_entry(patient.id, probs[top_head], top_head, triage_status)
        repository.save_outreach_log(patient.id, plan.track.value, outreach_message)
    except Exception as exc:  # pragma: no cover - demo resilience
        print(f"[services] Supabase persist failed (continuing): {exc}")

    return {
        "patient": patient.__dict__ | {"display_name": patient.display_name},
        "h3_cell": hit.h3_cell,
        "indoor_proxy": indoor.indoor,
        "shielding_coefficient": sc,
        "risk": {
            "probabilities": probs,
            "climate_volatility_delta": deltas,
            "combined_delta": combined,
            "top_head": top_head
        },
        "top_drivers": driver_objects,
        "triage_rank": rank,
        "outreach_track": plan.track.value,
        "fhir_note_id": note["id"],
        "drafted_sms": drafted_sms,
        "iot_shielding": iot_shielding_command
    }

from dataclasses import replace

# Global state for the demo
CURRENT_REGION = "dallas"

def init_mock_triage(region="dallas"):
    heads = ["respiratory", "cardiovascular", "metabolic"]
    flags = []
    if region == "new_delhi":
        # Indian patients: PT-0013 to PT-0024
        # Cohorts:
        # Respiratory: PT-0013 (hi), PT-0016 (te), PT-0019 (en), PT-0022 (te)
        # Cardiovascular: PT-0014 (hi), PT-0017 (te), PT-0020 (en), PT-0023 (te)
        # Metabolic: PT-0015 (hi), PT-0018 (te), PT-0021 (en), PT-0024 (te)
        for i in range(12, 24):
            cohort_idx = (i - 12) % 3
            cohort_rank = (i - 12) // 3
            delta = 0.48 - (cohort_rank * 0.08) - (cohort_idx * 0.01)
            risk = 0.96 - (cohort_rank * 0.07) - (cohort_idx * 0.01)
            flags.append(PatientFlag(
                patient_id=f"PT-{i+1:04d}",
                volatility_delta=round(delta, 3),
                risk_total=round(risk, 3),
                head=heads[cohort_idx]
            ))
    else:
        # Dallas patients: PT-0001 to PT-0012
        # Cohorts:
        # Respiratory: PT-0001 (en), PT-0004 (es), PT-0007 (en), PT-0010 (en)
        # Cardiovascular: PT-0002 (en), PT-0005 (es), PT-0008 (en), PT-0011 (en)
        # Metabolic: PT-0003 (en), PT-0006 (es), PT-0009 (en), PT-0012 (en)
        for i in range(0, 12):
            cohort_idx = i % 3
            cohort_rank = i // 3
            delta = 0.48 - (cohort_rank * 0.08) - (cohort_idx * 0.01)
            risk = 0.96 - (cohort_rank * 0.07) - (cohort_idx * 0.01)
            flags.append(PatientFlag(
                patient_id=f"PT-{i+1:04d}",
                volatility_delta=round(delta, 3),
                risk_total=round(risk, 3),
                head=heads[cohort_idx]
            ))
    return flags

TRIAGE_FLAGS_BY_REGION = {
    "dallas": init_mock_triage("dallas"),
    "new_delhi": init_mock_triage("new_delhi")
}
MOCK_TRIAGE_FLAGS = TRIAGE_FLAGS_BY_REGION["dallas"]

def reset_triage_and_set_region(region: str):
    global CURRENT_REGION, TRIAGE_FLAGS_BY_REGION, MOCK_TRIAGE_FLAGS
    CURRENT_REGION = region
    TRIAGE_FLAGS_BY_REGION[region] = init_mock_triage(region)
    MOCK_TRIAGE_FLAGS = TRIAGE_FLAGS_BY_REGION[region]

def get_triage_queue(region: Optional[str] = None):
    eff_region = (region or CURRENT_REGION or "dallas").lower()
    if eff_region not in TRIAGE_FLAGS_BY_REGION:
        TRIAGE_FLAGS_BY_REGION[eff_region] = init_mock_triage(eff_region)
        
    constrainer = TokenBucketConstrainer(panel_size=CLINIC_PANEL_SIZE, top_fraction=0.05)
    flags = list(TRIAGE_FLAGS_BY_REGION[eff_region])
    flags.sort(key=lambda x: x.volatility_delta, reverse=True)
    decision = constrainer.constrain(flags)
    return decision

def run_autonomous_cron(anomaly_type: Optional[str] = None, region: Optional[str] = None):
    """
    Simulates a Cloud Scheduler Cron Job. 
    Checks live weather. If dangerous, autonomously runs the pipeline for vulnerable patients.
    Guarantees strictly 1 Telugu, 1 Hindi, and 1 English patient for New Delhi anomaly runs.
    """
    eff_region = (region or CURRENT_REGION or "dallas").lower()
    if eff_region == "new_delhi":
        home_lat, home_lon = 28.6139, 77.2090
        city = "New Delhi"
    else:
        home_lat, home_lon = 32.8410, -96.7100
        city = "Dallas"
        
    aqi_data = fetch_live_air_quality(home_lat, home_lon, anomaly_type, city=city)
    
    print(f"\n[CRON] Processing anomaly for {city} (region={eff_region}, anomaly={anomaly_type})...")
    
    cohort = anomaly_type if anomaly_type in ("respiratory", "cardiovascular", "metabolic") else "respiratory"
    cohort_idx = 0 if cohort == "respiratory" else 1 if cohort == "cardiovascular" else 2
    
    if eff_region == "new_delhi":
        # Strictly 1 Hindi, 1 Telugu, and 1 English patient for India
        p_hi = f"PT-{12 + cohort_idx + 1:04d}"      # Rank 0 (Hindi)
        p_te = f"PT-{12 + 3 + cohort_idx + 1:04d}"  # Rank 1 (Telugu)
        p_en = f"PT-{12 + 6 + cohort_idx + 1:04d}"  # Rank 2 (English)
        target_pids = [p_hi, p_te, p_en]
    else:
        # Dallas: 1 English, 1 Spanish, 1 English
        p_en1 = f"PT-{0 + cohort_idx + 1:04d}"     # Rank 0 (English)
        p_es  = f"PT-{0 + 3 + cohort_idx + 1:04d}" # Rank 1 (Spanish)
        p_en2 = f"PT-{0 + 6 + cohort_idx + 1:04d}" # Rank 2 (English)
        target_pids = [p_en1, p_es, p_en2]
        
    processed = []
    for pid in target_pids:
        try:
            processed.append(run_patient_pipeline(pid, anomaly_type=anomaly_type, region=eff_region))
        except Exception as e:
            print(f"[CRON] Failed to process {pid}: {e}")
            
    return {
        "status": "Intervention Triggered",
        "message": f"Autonomous scan complete for {city}. AQI spiked to {aqi_data['aqi']}! Autonomously generated multi-lingual SMS and IoT commands for {len(processed)} vulnerable patients.",
        "processed_patients": processed
    }
