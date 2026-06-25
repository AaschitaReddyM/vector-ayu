import numpy as np
import torch
from pathlib import Path
from datetime import datetime, timezone

from pre_build.db import repository
from pre_build.fhir.fhir_client import MockFhirClient
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

CLINIC_PANEL_SIZE = 420
CLIMATE_ANOMALY = "high ozone and PM2.5 from a wildfire plume drifting south"
rng = np.random.default_rng(42)

def get_all_patients():
    """Patients from Supabase; falls back to the mock seed if the DB is
    unreachable or empty (keeps the demo resilient)."""
    try:
        patients = repository.fetch_patients()
        if patients:
            return patients
    except Exception as exc:  # pragma: no cover - demo resilience
        print(f"[services] Supabase patient read failed, using mock: {exc}")
    return list(fhir_client.seed_patients.values())

def get_patient_detail(patient_id: str):
    patient = fhir_client.fetch_patient(patient_id)
    obs = fhir_client.fetch_observations(patient_id)
    meds = fhir_client.fetch_medications(patient_id)
    return patient, obs, meds

def run_patient_pipeline(patient_id: str):
    patient, _, _ = get_patient_detail(patient_id)
    
    # S2 Spatiotemporal
    home_lat, home_lon = 32.8410, -96.7100
    hit = resolve_coordinate(home_lat, home_lon, zip_idx)
    
    # S3 Exposure
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
    combined = float(aggregate_head_deltas({h: np.array([deltas[h]]) for h in HEADS})[0])
    top_head = max(deltas, key=deltas.get)
    
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
    
    # S7 Outreach
    consent = fresh_track_a(patient.id, signed_at=datetime.now(timezone.utc), policy_version="v3.2")
    plan = route_patient(consent)
    outreach_message = f"Send 48h proactive {plan.outreach_channel.replace('_', ' ')} regarding {CLIMATE_ANOMALY}."
    note = build_progress_note(
        summary=RiskSummary(patient_id=patient.id, head=top_head, volatility_delta=combined, forecast_probability=probs[top_head], horizon_hours=72, top_drivers=driver_strings),
        recommendations=[outreach_message],
        clinician_id="PR-7791"
    )

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
        "top_drivers": driver_strings,
        "triage_rank": rank,
        "outreach_track": plan.track.value,
        "fhir_note_id": note["id"]
    }

def get_triage_queue():
    constrainer = TokenBucketConstrainer(panel_size=CLINIC_PANEL_SIZE, top_fraction=0.05)
    flags = [PatientFlag(patient_id=f"PT-{i:04d}", volatility_delta=float(rng.uniform(0, 0.4)), risk_total=float(rng.uniform(0, 1)), head="respiratory") for i in range(1, CLINIC_PANEL_SIZE)]
    flags.sort(key=lambda x: x.volatility_delta, reverse=True)
    decision = constrainer.constrain(flags)
    return decision
