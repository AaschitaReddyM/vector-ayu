"""
Channel-index → human-readable clinical label.

The TFT operates on opaque tensor channels (s0..s15, c0..c11, e0..e7).
The dashboard needs clinical English. This module is the authoritative
mapping; keep it in sync with whatever the live data pipeline emits.

Each list is index-aligned to the corresponding ``TFTConfig`` dim:

  static_input_dim       = 16 → STATIC_LABELS
  clinical_input_dim     = 12 → CLINICAL_LABELS
  environmental_input_dim = 8 → ENVIRONMENTAL_LABELS
"""

from __future__ import annotations

# Static (16 channels) — SDOH + demographics + comorbidities + Shielding Coef.
STATIC_LABELS: list[str] = [
    "Age decile",
    "Sex",
    "Race / ethnicity",
    "Primary language",
    "Shielding Coefficient",
    "SDOH composite index",
    "Tree canopy %",
    "HVAC density",
    "Building year (envelope)",
    "BMI",
    "COPD severity (GOLD)",
    "CHF NYHA class",
    "Diabetes A1c (last)",
    "Smoking pack-years",
    "Prior ER visits (12 mo)",
    "Medication adherence",
]

# Clinical (12 channels) — wearable + EHR vitals + labs at 1-hour cadence.
CLINICAL_LABELS: list[str] = [
    "SpO2 (pulse-ox)",
    "Heart rate",
    "Heart rate variability",
    "Systolic BP",
    "Diastolic BP",
    "Respiratory rate",
    "Body temperature",
    "CGM glucose",
    "Step count",
    "Sleep stage",
    "Inhaler actuations",
    "Skin temperature",
]

# Environmental (8 channels) — per-H3-cell ambient feed.
ENVIRONMENTAL_LABELS: list[str] = [
    "PM2.5",
    "Ozone (O₃)",
    "AQI composite",
    "Pollen index",
    "Ambient temperature",
    "Relative humidity",
    "UV index",
    "Wind speed",
]


def label_for(stream: str, channel_idx: int) -> str:
    """Look up the friendly label for a given stream + channel index."""
    table = {
        "static": STATIC_LABELS,
        "clinical": CLINICAL_LABELS,
        "environmental": ENVIRONMENTAL_LABELS,
    }.get(stream)
    if table is None:
        raise ValueError(f"unknown stream '{stream}'")
    if not 0 <= channel_idx < len(table):
        return f"{stream}[{channel_idx}]"
    return table[channel_idx]
