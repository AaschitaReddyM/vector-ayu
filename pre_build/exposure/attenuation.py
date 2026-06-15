"""
Core Exposure Attenuation (Spec §3.3).

    Effective Exposure = Outdoor Hazard Concentration × (1 − Shielding Coefficient)

The data ingestion pipeline intercepts the continuous climate vector before
it reaches the deep learning core. When the edge indicators confirm a
patient is indoors, this multiplier dynamically scales down the outdoor
hazard weight so the predictive layers evaluate *actual* physiological
strain — not raw outdoor numbers.

Vectorized over (batch, time, channel) so it drops in front of the TFT.
"""

from __future__ import annotations

import numpy as np


def effective_exposure(
    outdoor_hazard: np.ndarray,
    shielding_coefficient: float | np.ndarray,
    indoor_mask: np.ndarray | bool = True,
) -> np.ndarray:
    """
    Compute the attenuated exposure tensor.

    Parameters
    ----------
    outdoor_hazard : np.ndarray
        Raw outdoor concentrations. Any shape — typically (B, T, C) where
        C is the environmental-channel dim (PM2.5, ozone, …).
    shielding_coefficient : float | np.ndarray
        SC ∈ [0, 1]. Scalar (one patient) or an array broadcastable to
        ``outdoor_hazard`` (per-patient, per-time, per-channel).
    indoor_mask : np.ndarray | bool
        Per-element boolean indicating whether the patient was indoors at
        that step. ``True`` everywhere applies attenuation everywhere;
        ``False`` returns ``outdoor_hazard`` unchanged at that step
        (patient is outside → full outdoor exposure).

    Returns
    -------
    np.ndarray
        Same shape as ``outdoor_hazard``.
    """
    sc = np.asarray(shielding_coefficient, dtype=outdoor_hazard.dtype)
    if np.any(sc < 0) or np.any(sc > 1):
        raise ValueError("shielding_coefficient values must be within [0, 1]")

    attenuated = outdoor_hazard * (1.0 - sc)

    if indoor_mask is True:
        return attenuated
    if indoor_mask is False:
        return outdoor_hazard.copy()

    mask = np.asarray(indoor_mask).astype(bool)
    # Broadcast mask to outdoor shape if needed.
    mask = np.broadcast_to(mask, outdoor_hazard.shape)
    return np.where(mask, attenuated, outdoor_hazard)


if __name__ == "__main__":
    rng = np.random.default_rng(0)
    outdoor = rng.uniform(20, 180, size=(2, 72, 4))  # 2 patients, 72h, 4 channels
    sc = np.array([0.85, 0.40])[:, None, None]       # per-patient SC
    indoor = rng.random((2, 72, 1)) < 0.7            # 70% of time indoors
    eff = effective_exposure(outdoor, sc, indoor)
    print(f"  outdoor PM2.5 hourly mean : {outdoor.mean(axis=(1, 2))}")
    print(f"  effective    hourly mean : {eff.mean(axis=(1, 2))}")
    print(f"  attenuation observed     : {1 - eff.mean(axis=(1, 2)) / outdoor.mean(axis=(1, 2))}")
