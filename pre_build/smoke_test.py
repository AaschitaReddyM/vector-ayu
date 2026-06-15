"""
End-to-end smoke test for the pre-build pipeline.

Confirms input/output dimension paths are stable across every module
(spec §3–§7). This is the "dimensions are stable" check, not a real
training run — for the narrative demo see ``demo_pipeline.py``.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import torch

from pre_build.consent import (
    ConsentTrack,
    fresh_track_a,
    fresh_track_b,
    route_patient,
)
from pre_build.explain import attribute_head
from pre_build.exposure import (
    IndoorEdgeSignals,
    ShieldingProfile,
    classify_indoor,
    compute_shielding_coefficient,
    effective_exposure,
    home_wifi_digest,
    shielding_for_zip,
)
from pre_build.fhir import (
    MockFhirClient,
    RiskSummary,
    SmartLaunchConfig,
    SmartSession,
    LaunchContext,
    build_authorize_url,
    build_progress_note,
    issue_demo_token,
)
from pre_build.model import (
    CatBoostConfig,
    CatBoostFallback,
    HEADS,
    MultiTaskLoss,
    MultiTaskWeights,
    TFTConfig,
    TFTSkeleton,
    should_use_fallback,
)
from pre_build.outreach import SmsContext, render_sms
from pre_build.spatial import build_zip_index, resolve_coordinate
from pre_build.triage import (
    PatientFlag,
    TokenBucketConstrainer,
    aggregate_head_deltas,
    climate_volatility_delta,
)


def section(title: str) -> None:
    print(f"\n{'=' * 64}\n  {title}\n{'=' * 64}")


# ── 1. Spatial ─────────────────────────────────────────────────────────────

def test_h3() -> None:
    section("1. H3 SPATIAL INGESTION")
    idx = build_zip_index()
    assert len(idx) > 30
    for label, lat, lon in [
        ("Reunion Tower",    32.7755, -96.8089),
        ("Texas Med Center", 29.7100, -95.3970),
        ("UT Tower Austin",  30.2862, -97.7394),
    ]:
        hit = resolve_coordinate(lat, lon, idx)
        assert hit.nearest_zip is not None
        print(f"  {label:18s} -> cell={hit.h3_cell}  zip={hit.nearest_zip}  d={hit.nearest_distance_km:.2f} km")
    miss = resolve_coordinate(31.0, -102.0, idx)
    assert miss.nearest_zip is None
    print(f"  off-grid coord routes to Track B (nearest_zip is None) ✓")


# ── 2. Exposure ────────────────────────────────────────────────────────────

def test_exposure() -> None:
    section("2. EXPOSURE  (Shielding Coef + Indoor proxy + Effective = Outdoor × (1-SC))")
    # Shielding for a known ZIP
    sc_high = shielding_for_zip("75205")
    sc_low = shielding_for_zip("76104")
    print(f"  SC(75205 affluent / new HVAC): {sc_high:.3f}")
    print(f"  SC(76104 older Fort Worth)   : {sc_low:.3f}")
    assert sc_high > sc_low

    # Manual profile
    prof = ShieldingProfile(tree_canopy_pct=30, building_material_score=0.8,
                            hvac_density_score=0.9, sdoh_index=0.85, year_built=2010)
    sc_manual = compute_shielding_coefficient(prof)
    assert 0 <= sc_manual <= 1

    # Indoor classifier
    indoor = classify_indoor(IndoorEdgeSignals(
        home_wifi_match=True, barometric_variance_hpa=0.02,
        pedometer_steps_5min=3, gps_signal_dbm=-158, rh_indoor_proxy=0.48))
    outdoor = classify_indoor(IndoorEdgeSignals(
        home_wifi_match=False, barometric_variance_hpa=0.40,
        pedometer_steps_5min=500, gps_signal_dbm=-128, rh_indoor_proxy=0.70))
    assert indoor.indoor and not outdoor.indoor
    print(f"  indoor cues  -> indoor={indoor.indoor} conf={indoor.confidence:.2f}")
    print(f"  outdoor cues -> indoor={outdoor.indoor} conf={outdoor.confidence:.2f}")

    # Privacy-safe Wi-Fi digest
    d1 = home_wifi_digest("aa:bb:cc:11:22:33", salt="device-salt-7")
    d2 = home_wifi_digest("aa:bb:cc:11:22:33", salt="different-salt")
    assert d1 != d2 and len(d1) == 64
    print(f"  same BSSID, different salt → different digests ✓")

    # Attenuation tensor
    rng = np.random.default_rng(0)
    outdoor_hazard = rng.uniform(20, 180, size=(2, 72, 4)).astype(np.float32)
    eff = effective_exposure(outdoor_hazard, np.array([0.85, 0.40])[:, None, None])
    attn = 1 - eff.mean(axis=(1, 2)) / outdoor_hazard.mean(axis=(1, 2))
    print(f"  attenuation observed (per patient): {attn.round(3).tolist()}")


# ── 3. TFT + loss ──────────────────────────────────────────────────────────

def test_tft_and_loss() -> None:
    section("3. TFT FORWARD + MULTI-TASK LOSS")
    cfg = TFTConfig()
    model = TFTSkeleton(cfg).eval()
    b = 8
    static_x = torch.randn(b, cfg.static_input_dim)
    clin_x = torch.randn(b, cfg.horizon_hours, cfg.clinical_input_dim)
    env_x = torch.randn(b, cfg.horizon_hours, cfg.environmental_input_dim)
    with torch.no_grad():
        logits = model(static_x, clin_x, env_x)
    for head in HEADS:
        assert logits[head].shape == (b,)
    print(f"  logits shapes ok across all heads ({b},) ✓")

    weights = MultiTaskWeights()
    loss_fn = MultiTaskLoss(weights)
    grad_logits = {h: torch.randn(b, requires_grad=True) for h in HEADS}
    targets = {h: torch.randint(0, 2, (b,)) for h in HEADS}
    out = loss_fn(grad_logits, targets)
    out["total"].backward()
    print(f"  L_total={out['total'].item():.3f}  α={weights.alpha} β={weights.beta} γ={weights.gamma}")
    print(f"  param count: {sum(p.numel() for p in model.parameters()):,}")


# ── 4. Triage ──────────────────────────────────────────────────────────────

def test_triage() -> None:
    section("4. TRIAGE  (Token-Bucket + Volatility Δ)")
    rng = np.random.default_rng(0)
    baseline = rng.uniform(0.05, 0.15, 8).astype(np.float32)
    forecast = baseline + rng.uniform(-0.05, 0.30, 8).astype(np.float32)
    deltas = climate_volatility_delta(forecast, baseline, anomaly_z=2.0)
    assert (deltas >= 0).all()
    print(f"  volatility Δ (clip ≥0): {deltas.round(3).tolist()}")

    head_deltas = {h: rng.uniform(0, 1, 5).astype(np.float32) for h in HEADS}
    combined = aggregate_head_deltas(head_deltas)
    print(f"  aggregated Δ (5 patients): {combined.round(3).tolist()}")

    flags = [
        PatientFlag(patient_id=f"PT-{i:04d}",
                    volatility_delta=float(rng.uniform(0, 1)),
                    risk_total=float(rng.uniform(0, 1)),
                    head="respiratory")
        for i in range(420)
    ]
    decision = TokenBucketConstrainer(panel_size=420, top_fraction=0.05).constrain(flags)
    assert decision.capacity_used == 21
    print(f"  panel=420 5% bucket → accepted={decision.capacity_used} deferred={len(decision.deferred)}")


# ── 5. Fallback ────────────────────────────────────────────────────────────

def test_catboost_fallback() -> None:
    section("5. CATBOOST FALLBACK")
    clean = np.random.randn(4, 72, 12)
    degraded = np.where(np.random.rand(4, 72, 12) < 0.8, np.nan, 0.0)
    assert not should_use_fallback(clean)
    assert should_use_fallback(degraded)
    print(f"  routing: clean=>TFT, NaN-degraded=>fallback ✓")

    rng = np.random.default_rng(0)
    n, t, s, c_env = 150, 72, 16, 8
    static_x = rng.normal(size=(n, s)).astype(np.float32)
    env_x = rng.normal(size=(n, t, c_env)).astype(np.float32)
    targets = {
        "respiratory":    (env_x.mean(axis=1)[:, 0] > 0).astype(np.int8),
        "cardiovascular": (static_x[:, 0] > 0).astype(np.int8),
        "metabolic":      (static_x[:, 1] - env_x.mean(axis=1)[:, 1] > 0).astype(np.int8),
    }
    fb = CatBoostFallback(CatBoostConfig(iterations=80)).fit(static_x, env_x, targets)
    proba = fb.predict_proba(static_x[:3], env_x[:3])
    for head in HEADS:
        assert proba[head].shape == (3,)
    print(f"  fit + predict ok for all heads ✓")


# ── 6. XAI ─────────────────────────────────────────────────────────────────

def test_xai() -> None:
    section("6. XAI  (Captum Integrated Gradients)")
    cfg = TFTConfig()
    model = TFTSkeleton(cfg).eval()
    static = torch.randn(2, cfg.static_input_dim)
    clin = torch.randn(2, cfg.horizon_hours, cfg.clinical_input_dim)
    env = torch.randn(2, cfg.horizon_hours, cfg.environmental_input_dim)
    bundle = attribute_head(model, "cardiovascular", static, clin, env, n_steps=16)
    assert bundle.static.shape == static.shape
    assert bundle.clinical.shape == clin.shape
    assert bundle.environmental.shape == env.shape
    summary = bundle.per_channel_summary()
    print(f"  IG convergence Δ : {[round(x, 4) for x in bundle.convergence_delta.tolist()]}")
    print(f"  top-3 environmental: {sorted(summary['environmental'].items(), key=lambda x: -x[1])[:3]}")


# ── 7. SMART-on-FHIR + client + progress note ──────────────────────────────

def test_fhir() -> None:
    section("7. FHIR  (SMART OAuth + Client + Progress Note)")
    cfg = SmartLaunchConfig(
        client_id="climahealth-dev",
        redirect_uri="https://climahealth.local/smart/callback",
    )
    sess = SmartSession()
    ctx = LaunchContext(iss="https://launch.smarthealthit.org/v/r4/fhir", launch="L-XYZ")
    state, challenge = sess.stash(ctx)
    url = build_authorize_url(
        authorize_endpoint="https://launch.smarthealthit.org/v/r4/auth/authorize",
        cfg=cfg, launch_ctx=ctx, state=state, code_challenge=challenge,
    )
    assert "code_challenge_method=S256" in url and f"state={state}" in url
    print(f"  authorize URL has PKCE + state ✓")
    token = issue_demo_token(patient="PT-0001", scope=cfg.scope)
    sess.remember(state, token)
    assert token.access_token and token.token_type == "Bearer"

    client = MockFhirClient()
    p = client.fetch_patient("PT-0001")
    obs = client.fetch_observations(p.id)
    meds = client.fetch_medications(p.id)
    assert p.id == "PT-0001" and len(obs) >= 1 and len(meds) >= 1
    print(f"  patient={p.display_name}  obs={len(obs)}  meds={len(meds)}")

    note = build_progress_note(
        summary=RiskSummary(
            patient_id=p.id, head="respiratory", volatility_delta=0.32,
            forecast_probability=0.58, horizon_hours=72,
            top_drivers=["PM2.5 forecast spike", "low SC 0.51"],
        ),
        recommendations=["Send 48h SMS in Spanish.", "Telehealth check in 24h."],
        clinician_id="PR-7791",
        approved_at=datetime.now(timezone.utc),
    )
    assert note["resourceType"] == "DocumentReference"
    assert note["subject"]["reference"] == f"Patient/{p.id}"
    print(f"  DocumentReference id={note['id'][:8]}... subject={note['subject']['reference']} ✓")


# ── 8. Consent + outreach ──────────────────────────────────────────────────

def test_consent_and_outreach() -> None:
    section("8. DUAL-TRACK CONSENT + SMS TEMPLATES")
    plan_a = route_patient(
        fresh_track_a("PT-0001", signed_at=datetime.now(timezone.utc), policy_version="v3.2"))
    plan_b = route_patient(fresh_track_b("PT-0002"))
    assert plan_a.may_send_automated_sms
    assert not plan_b.may_send_automated_sms
    assert plan_b.track is ConsentTrack.B_OPS and plan_b.triage_dashboard_visible
    print(f"  Track A → outreach={plan_a.outreach_channel}, sms_ok={plan_a.may_send_automated_sms}")
    print(f"  Track B → outreach={plan_b.outreach_channel}, sms_ok={plan_b.may_send_automated_sms}")

    for locale, head in [("en", "cardiovascular"), ("es", "respiratory"), ("en", "metabolic")]:
        sms = render_sms(SmsContext(
            given_name="Maria", head=head, climate_anomaly="a heat wave",
            city="Dallas", locale=locale,
        ))
        assert len(sms) <= 320
        print(f"  [{locale} {head:14s}] {len(sms):3d} chars OK")


if __name__ == "__main__":
    test_h3()
    test_exposure()
    test_tft_and_loss()
    test_triage()
    test_catboost_fallback()
    test_xai()
    test_fhir()
    test_consent_and_outreach()
    print("\n  ✓ ALL PRE-BUILD MODULES VERIFIED.\n")
