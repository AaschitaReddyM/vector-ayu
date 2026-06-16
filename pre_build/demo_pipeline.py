"""
End-to-end pre-build demo (Spec §2 — System Process Flowchart).

Walks one synthetic patient through every tier of the pipeline:

  1. Data Ingestion          — fetch Patient / Observation / MedicationRequest
                               via Mock FHIR client (SMART-on-FHIR ready)
  2. Spatiotemporal Graph    — hash patient ZIP → H3 cell
  3. Exposure Attenuation    — indoor edge proxy + shielding coefficient +
                               Effective Exposure = Outdoor × (1 − SC)
  4. Multi-Task TFT          — forward pass → respiratory/cardio/metabolic logits
  5. Triage Constrainer      — token-bucket gate to top 5%
  6. SMART-on-FHIR App       — render the 72-hour triage flag (printed here)
  7. Endpoint Outreach       — Dual-Track consent routes patient to
                               automated SMS (Track A) or manual call (Track B);
                               progress-note write-back generated either way.

Everything is local and offline. Drop-in replacements for §9.2 live build:
  • MockFhirClient    → live FHIR REST client at {iss}
  • Synthetic outdoor → Kafka stream from real EPA / OpenWeather APIs
  • SMS template      → MindStudio worker agent
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import torch

from pre_build.consent import fresh_track_a, fresh_track_b, route_patient
from pre_build.explain import attribute_head
from pre_build.exposure import (
    IndoorEdgeSignals,
    classify_indoor,
    effective_exposure,
    shielding_for_zip,
)
from pre_build.fhir import (
    MockFhirClient,
    RiskSummary,
    build_progress_note,
)
from pre_build.model import (
    HEADS,
    MultiTaskWeights,
    TFTConfig,
    TFTSkeleton,
)
from pre_build.outreach import SmsContext, render_sms
from pre_build.spatial import build_zip_index, resolve_coordinate
from pre_build.triage import (
    PatientFlag,
    TokenBucketConstrainer,
    aggregate_head_deltas,
    climate_volatility_delta,
)


CLIMATE_ANOMALY = "high ozone and PM2.5 from a wildfire plume drifting south"
CLINIC_PANEL_SIZE = 420


def banner(title: str) -> None:
    print(f"\n{'━' * 68}\n  {title}\n{'━' * 68}")


def run() -> None:
    # ── Stage 1: Ingest patient context from the EHR ───────────────────────
    banner("1. DATA INGESTION  (Mock FHIR — swap for live SMART OAuth at event)")
    fhir = MockFhirClient()
    patient = fhir.fetch_patient("PT-0001")
    observations = fhir.fetch_observations(patient.id)
    meds = fhir.fetch_medications(patient.id)
    print(f"  patient : {patient.display_name}  dob={patient.birth_date}  zip={patient.postal_code}")
    print(f"  obs     : {len(observations)} recent observations")
    print(f"  meds    : {[m.medication_display for m in meds]}")

    # ── Stage 2: Spatiotemporal hashing → H3 cell ──────────────────────────
    banner("2. SPATIOTEMPORAL GRAPH  (lat/lon → H3 hex)")
    zip_idx = build_zip_index()
    # Patient lives at their ZIP centroid (Track B uses billing ZIP; Track A would use live geo).
    home_lat, home_lon = 32.8410, -96.7100   # Dallas 75218 centroid
    hit = resolve_coordinate(home_lat, home_lon, zip_idx)
    print(f"  home    : ({home_lat}, {home_lon}) -> H3 cell {hit.h3_cell}")
    print(f"  matched : zip={hit.nearest_zip}  Δ={hit.nearest_distance_km:.2f} km")

    # ── Stage 3: Exposure attenuation ──────────────────────────────────────
    banner("3. EXPOSURE ATTENUATION  (indoor proxy → SC → Effective = Outdoor × (1-SC))")
    signals = IndoorEdgeSignals(
        home_wifi_match=True,
        barometric_variance_hpa=0.03,
        pedometer_steps_5min=8,
        gps_signal_dbm=-156,
        rh_indoor_proxy=0.46,
    )
    indoor = classify_indoor(signals)
    sc = shielding_for_zip(patient.postal_code)
    print(f"  indoor classifier: indoor={indoor.indoor}  conf={indoor.confidence:.2f}")
    print(f"                     reasons={indoor.reasons}")
    print(f"  shielding coef   : SC={sc:.3f}  (from ZIP {patient.postal_code} profile)")

    rng = np.random.default_rng(42)
    horizon = 72
    n_env = 8
    outdoor = rng.uniform(20, 180, size=(1, horizon, n_env)).astype(np.float32)
    indoor_mask = np.full((1, horizon, 1), indoor.indoor)
    effective = effective_exposure(outdoor, sc, indoor_mask)
    print(f"  outdoor mean PM2.5 (proxy) : {outdoor.mean():.2f}")
    print(f"  effective mean             : {effective.mean():.2f}  "
          f"(attenuation = {1 - effective.mean()/outdoor.mean():.0%})")

    # ── Stage 4: TFT multi-task forecast ───────────────────────────────────
    banner("4. MULTI-TASK DEEP AI  (TFT — respiratory / cardiovascular / metabolic)")
    cfg = TFTConfig(horizon_hours=horizon, environmental_input_dim=n_env)
    torch.manual_seed(0)
    model = TFTSkeleton(cfg).eval()
    checkpoint_path = Path(__file__).resolve().parent / "model" / "tft_trained.pt"
    if checkpoint_path.exists():
        model.load_state_dict(torch.load(checkpoint_path, map_location="cpu", weights_only=True))
        print("  ✓ loaded trained weights from tft_trained.pt")
    else:
        print("  ⚠️ using random weights (run train_tft.py to train the model)")
    static_x = torch.from_numpy(rng.normal(size=(1, cfg.static_input_dim)).astype(np.float32))
    clin_x = torch.from_numpy(rng.normal(size=(1, horizon, cfg.clinical_input_dim)).astype(np.float32))
    env_x = torch.from_numpy(effective)
    with torch.no_grad():
        logits = model(static_x, clin_x, env_x)
    probs = {h: torch.sigmoid(logits[h]).item() for h in HEADS}
    for h, p in probs.items():
        print(f"  P({h:16s} acute in next 72h) = {p:.3f}")

    # Volatility delta vs a synthetic baseline.
    baseline_probs = {"respiratory": 0.12, "cardiovascular": 0.10, "metabolic": 0.08}
    anomaly_z = 2.1
    deltas = {
        h: float(climate_volatility_delta(np.array([probs[h]]),
                                          np.array([baseline_probs[h]]),
                                          anomaly_z=anomaly_z)[0])
        for h in HEADS
    }
    combined = float(aggregate_head_deltas({h: np.array([deltas[h]]) for h in HEADS})[0])
    print(f"  Climate Volatility Δ       : "
          f"resp={deltas['respiratory']:.3f}  card={deltas['cardiovascular']:.3f}  "
          f"meta={deltas['metabolic']:.3f}  combined={combined:.3f}")

    # Identify firing head (highest delta).
    top_head = max(deltas, key=deltas.get)

    # ── Stage 5: Triage constrainer ────────────────────────────────────────
    banner("5. TRIAGE CONSTRAINER  (token-bucket — top 5% of panel)")
    other_flags = [
        PatientFlag(patient_id=f"PT-{i:04d}",
                    volatility_delta=float(rng.uniform(0, 0.4)),
                    risk_total=float(rng.uniform(0, 1)),
                    head="respiratory")
        for i in range(1, CLINIC_PANEL_SIZE)
    ]
    our_flag = PatientFlag(
        patient_id=patient.id,
        volatility_delta=combined,
        risk_total=probs[top_head],
        head=top_head,
        payload={"head_probs": probs},
    )
    constrainer = TokenBucketConstrainer(panel_size=CLINIC_PANEL_SIZE, top_fraction=0.05)
    decision = constrainer.constrain(other_flags + [our_flag])
    print(f"  panel size            : {CLINIC_PANEL_SIZE}")
    print(f"  daily token budget    : {constrainer.daily_budget()}")
    print(f"  accepted              : {decision.capacity_used}  /  deferred : {len(decision.deferred)}")
    rank = next((i for i, f in enumerate(decision.accepted, start=1) if f.patient_id == patient.id), None)
    print(f"  {patient.id} accepted? {'yes — rank #' + str(rank) if rank else 'NO (deferred)'}")

    # ── Stage 6: XAI breakdown ─────────────────────────────────────────────
    banner("6. XAI BREAKDOWN  (Integrated Gradients — top drivers for the firing head)")
    bundle = attribute_head(model, top_head, static_x, clin_x, env_x, n_steps=16)
    summary = bundle.per_channel_summary()
    top_env = sorted(summary["environmental"].items(), key=lambda x: -x[1])[:3]
    top_static = sorted(summary["static"].items(), key=lambda x: -x[1])[:3]
    print(f"  head             : {top_head}")
    print(f"  top static       : {top_static}")
    print(f"  top environmental: {top_env}")

    driver_strings = [
        f"Environmental ch={k} contribution={v:.3f}" for k, v in top_env
    ] + [
        f"Static ch={k} contribution={v:.3f}" for k, v in top_static[:2]
    ]

    # ── Stage 7: Consent routing + outreach + progress note ────────────────
    banner("7. ENDPOINT OUTREACH  (Dual-Track consent → SMS or manual + progress-note write-back)")
    consent = fresh_track_a(patient.id,
                            signed_at=datetime.now(timezone.utc),
                            policy_version="v3.2")
    plan = route_patient(consent)
    print(f"  consent track : {plan.track.value} (outreach via {plan.outreach_channel})")

    if plan.may_send_automated_sms:
        sms = render_sms(SmsContext(
            given_name=patient.given_name,
            head=top_head,
            climate_anomaly=CLIMATE_ANOMALY,
            city="Dallas",
            locale="es" if patient.primary_language == "es" else "en",
        ))
        print(f"  SMS ({len(sms)} chars): {sms}")
    else:
        print("  Track B — manual phone call queued, no automated SMS sent.")

    note = build_progress_note(
        summary=RiskSummary(
            patient_id=patient.id,
            head=top_head,
            volatility_delta=combined,
            forecast_probability=probs[top_head],
            horizon_hours=horizon,
            top_drivers=driver_strings,
        ),
        recommendations=[
            f"Send 48h proactive {plan.outreach_channel.replace('_', ' ')} regarding {CLIMATE_ANOMALY}.",
            "Re-check vitals via telehealth in 24h if symptoms emerge.",
        ],
        clinician_id="PR-7791",
    )
    print(f"  FHIR DocumentReference: id={note['id']}  type={note['type']['coding'][0]['display']}")
    print(f"  → POST {patient.id}'s preventive outreach back into the EHR chart.")

    # ── Loss sanity check (training-time) ──────────────────────────────────
    banner("✓ PIPELINE COMPLETE  (priorities α/β/γ for training)")
    w = MultiTaskWeights()
    print(f"  α={w.alpha} (respiratory)   β={w.beta} (cardiovascular)   γ={w.gamma} (metabolic)")
    print()


if __name__ == "__main__":
    run()
