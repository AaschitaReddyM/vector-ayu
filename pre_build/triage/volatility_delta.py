"""
Climate Volatility Delta (Spec §4 — 72-Hour Provider Triage Dashboard).

The spec defines the sort key as "the explicit increase in crisis risk
driven by oncoming weather anomalies". We operationalize this as the
forward 72-hour predicted risk minus the patient's stable baseline risk:

    Δ = max(0, P_72h − P_baseline) · severity_amplifier(climate_anomaly)

We clip negatives to zero — "things got better" doesn't earn dashboard
real-estate.
"""

from __future__ import annotations

import numpy as np


def climate_volatility_delta(
    forecast_risk: np.ndarray,
    baseline_risk: np.ndarray,
    anomaly_z: np.ndarray | float = 0.0,
    amplifier_slope: float = 0.25,
) -> np.ndarray:
    """
    Δ = clip( forecast_risk − baseline_risk, 0, ∞ ) × (1 + amplifier_slope · max(0, anomaly_z))

    Parameters
    ----------
    forecast_risk : np.ndarray
        Per-patient probability from the TFT for the 72-hour horizon, in [0, 1].
    baseline_risk : np.ndarray
        Per-patient stable-state probability (e.g. last-30-day median).
    anomaly_z : np.ndarray | float
        Z-score of the upcoming climate anomaly (e.g. PM2.5 vs seasonal
        normal). Negative values are treated as zero — "below normal"
        does not amplify risk.
    amplifier_slope : float
        Per-unit-of-z amplification. 0.25 means a +2σ heat anomaly
        amplifies the delta by 50%.

    Returns
    -------
    np.ndarray of shape ``forecast_risk.shape``
    """
    forecast_risk = np.asarray(forecast_risk, dtype=np.float32)
    baseline_risk = np.asarray(baseline_risk, dtype=np.float32)
    raw = np.clip(forecast_risk - baseline_risk, 0.0, None)
    z = np.maximum(0.0, np.asarray(anomaly_z, dtype=np.float32))
    amplifier = 1.0 + amplifier_slope * z
    return raw * amplifier


def aggregate_head_deltas(
    head_deltas: dict[str, np.ndarray],
    weights: dict[str, float] | None = None,
) -> np.ndarray:
    """
    Combine per-head deltas into a single sort key for the dashboard.

    Default weights match the multi-task loss priorities (cardio worst).
    """
    weights = weights or {"cardiovascular": 0.5, "respiratory": 0.3, "metabolic": 0.2}
    total = None
    for head, w in weights.items():
        if head not in head_deltas:
            continue
        d = np.asarray(head_deltas[head], dtype=np.float32) * w
        total = d if total is None else total + d
    if total is None:
        raise ValueError("no head deltas supplied")
    return total


if __name__ == "__main__":
    rng = np.random.default_rng(0)
    baseline = rng.uniform(0.05, 0.15, 8)
    forecast = baseline + rng.uniform(-0.05, 0.30, 8)
    anomaly = rng.normal(2.0, 0.5, 8)   # mild heat wave
    deltas = climate_volatility_delta(forecast, baseline, anomaly)
    print(f"  baseline : {np.round(baseline, 3).tolist()}")
    print(f"  forecast : {np.round(forecast, 3).tolist()}")
    print(f"  anomaly  : {np.round(anomaly, 2).tolist()}")
    print(f"  Δ        : {np.round(deltas, 3).tolist()}")
