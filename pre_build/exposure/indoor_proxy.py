"""
Dynamic Hardware Proxies (Spec §3.2).

To determine a patient's active localization without compromising digital
privacy, the consumer application monitors privacy-compliant hardware
proxies on the smartphone edge:

  • Cryptographic hash of the home Wi-Fi SSID/BSSID (no SSID ever leaves
    the device — only its salted SHA-256 digest)
  • Pedometer movement over the last few minutes
  • Internal barometric-pressure sensor — flat & stable indicates a
    pressurized, climate-controlled indoor HVAC setup
  • GPS signal-strength attenuation — heavy roof attenuation = indoor

This module is the *device-side classifier*; the backend only sees the
boolean output plus a confidence score (PHI-safe by design).
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass


# ── Privacy-safe home Wi-Fi identity ───────────────────────────────────────

def home_wifi_digest(bssid: str, salt: str) -> str:
    """Return the salted SHA-256 hex digest of the home Wi-Fi BSSID.

    Only the *digest* is ever stored or transmitted. The salt is held on
    the device's secure enclave so the same BSSID maps to a different
    digest on every other phone — eliminating cross-patient correlation
    even if the digest table leaked.
    """
    return hashlib.sha256(f"{salt}:{bssid.lower()}".encode("utf-8")).hexdigest()


# ── Edge signals ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class IndoorEdgeSignals:
    home_wifi_match: bool             # current Wi-Fi digest equals stored home digest
    barometric_variance_hpa: float    # stddev of pressure samples over last 5 min
    pedometer_steps_5min: int         # cumulative steps in last 5 min
    gps_signal_dbm: float             # measured satellite SNR; outdoor ≈ −130, indoor ≈ −155
    rh_indoor_proxy: float | None = None  # optional humidity — indoor HVAC typically 40–55%


# ── Classifier ─────────────────────────────────────────────────────────────

@dataclass
class IndoorClassification:
    indoor: bool
    confidence: float    # 0–1
    reasons: list[str]


# Heuristic thresholds, tuned to ship a reasonable default. Each cue
# contributes evidence; we accumulate log-odds for a final boolean.

def classify_indoor(signals: IndoorEdgeSignals) -> IndoorClassification:
    """Combine edge cues into an indoor/outdoor classification."""
    log_odds = 0.0
    reasons: list[str] = []

    # Wi-Fi match is the single strongest cue.
    if signals.home_wifi_match:
        log_odds += 2.5
        reasons.append("home Wi-Fi digest matched")
    else:
        log_odds -= 0.5

    # Flat barometric pressure = pressurized HVAC.
    if signals.barometric_variance_hpa < 0.05:
        log_odds += 1.2
        reasons.append("flat barometric pressure (HVAC)")
    elif signals.barometric_variance_hpa > 0.25:
        log_odds -= 0.6
        reasons.append("variable barometric pressure (likely outdoors)")

    # Low GPS SNR = roof attenuation.
    if signals.gps_signal_dbm < -150:
        log_odds += 1.0
        reasons.append("GPS heavily attenuated")
    elif signals.gps_signal_dbm > -135:
        log_odds -= 1.0
        reasons.append("strong GPS signal")

    # Low recent step count is weak evidence (people sit indoors AND outdoors).
    if signals.pedometer_steps_5min < 20:
        log_odds += 0.3

    # Humidity — bounded indoor band.
    if signals.rh_indoor_proxy is not None and 0.35 <= signals.rh_indoor_proxy <= 0.60:
        log_odds += 0.4
        reasons.append("humidity within HVAC band")

    # Logistic squash to a confidence.
    confidence = 1.0 / (1.0 + math.exp(-log_odds))
    return IndoorClassification(
        indoor=log_odds >= 0,
        confidence=float(confidence),
        reasons=reasons,
    )


if __name__ == "__main__":
    cases = [
        ("home, watching TV",
         IndoorEdgeSignals(home_wifi_match=True, barometric_variance_hpa=0.02,
                           pedometer_steps_5min=4, gps_signal_dbm=-158,
                           rh_indoor_proxy=0.48)),
        ("walking in the park",
         IndoorEdgeSignals(home_wifi_match=False, barometric_variance_hpa=0.32,
                           pedometer_steps_5min=480, gps_signal_dbm=-128,
                           rh_indoor_proxy=0.65)),
        ("inside a mall (no home Wi-Fi)",
         IndoorEdgeSignals(home_wifi_match=False, barometric_variance_hpa=0.04,
                           pedometer_steps_5min=120, gps_signal_dbm=-153,
                           rh_indoor_proxy=0.45)),
    ]
    for label, sig in cases:
        c = classify_indoor(sig)
        print(f"  {label:35s}  indoor={c.indoor!s:5}  conf={c.confidence:.2f}  reasons={c.reasons}")
