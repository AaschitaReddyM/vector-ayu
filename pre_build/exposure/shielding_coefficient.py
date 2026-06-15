"""
Shielding Coefficient (Spec §3.1 — Static Infrastructure Filtering).

Each patient profile is assigned an unchanging, location-specific Shielding
Coefficient (SC) ∈ [0, 1] from:

  • Census-tract Social Determinants of Health (SDOH) datasets
  • Neighborhood tree-canopy coverage
  • Building-material metadata
  • Historical regional HVAC implementation density
  • Building year (proxy for envelope tightness)

SC → 1.0 means highly insulated, modern structural resilience: outdoor
hazards are heavily attenuated indoors. SC → 0.0 means the patient lives in
older, leakier housing with poor canopy / HVAC — outdoor hazards reach them
nearly unattenuated.

For Buildathon, the formula is an explicit weighted combination of the five
inputs. In production, swap for a small gradient-boosted regressor trained
on FEMA HAZUS + Census ACS + USDA tree-canopy raster joins.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ShieldingProfile:
    """Inputs needed to compute one patient's Shielding Coefficient."""
    tree_canopy_pct: float            # 0–100, neighborhood canopy coverage
    building_material_score: float    # 0–1, modern envelope quality (brick=0.9, frame=0.4)
    hvac_density_score: float         # 0–1, fraction of census tract with central HVAC
    sdoh_index: float                 # 0–1, higher = better housing stability
    year_built: int                   # e.g. 1955–2025

    def __post_init__(self) -> None:
        if not 0 <= self.tree_canopy_pct <= 100:
            raise ValueError("tree_canopy_pct must be 0–100")
        for name in ("building_material_score", "hvac_density_score", "sdoh_index"):
            v = getattr(self, name)
            if not 0 <= v <= 1:
                raise ValueError(f"{name} must be 0–1, got {v}")
        if not 1800 <= self.year_built <= 2100:
            raise ValueError(f"year_built out of range: {self.year_built}")


# Component weights — sum to 1.0. Tuned by clinical/architectural priors:
# HVAC dominates indoor pollutant attenuation (Karner et al.); canopy and
# envelope follow; SDOH captures occupancy compliance; year_built is a
# secondary proxy for tightness.
WEIGHTS = {
    "canopy":   0.15,
    "envelope": 0.25,
    "hvac":     0.35,
    "sdoh":     0.15,
    "year":     0.10,
}


def _year_score(year_built: int) -> float:
    """Map year_built to [0, 1] — newer envelopes shield better."""
    # 1950 → 0.0,  2025 → 1.0 (linear, clipped).
    return max(0.0, min(1.0, (year_built - 1950) / 75.0))


def compute_shielding_coefficient(profile: ShieldingProfile) -> float:
    """
    Combine the five inputs into a Shielding Coefficient ∈ [0, 1].

    SC = w_c · canopy/100 + w_e · envelope + w_h · hvac + w_s · sdoh + w_y · year_score
    """
    sc = (
        WEIGHTS["canopy"]   * (profile.tree_canopy_pct / 100.0)
        + WEIGHTS["envelope"] * profile.building_material_score
        + WEIGHTS["hvac"]     * profile.hvac_density_score
        + WEIGHTS["sdoh"]     * profile.sdoh_index
        + WEIGHTS["year"]     * _year_score(profile.year_built)
    )
    return max(0.0, min(1.0, sc))


# ── Seed table — representative Texas ZIPs ─────────────────────────────────
#
# Numbers below are illustrative defaults derived from census tract priors;
# real deployments back this with the actual ACS + canopy + HAZUS joins.

ZIP_SHIELDING_DEFAULTS: dict[str, ShieldingProfile] = {
    # Affluent / high-canopy / modern-HVAC neighborhoods
    "75205": ShieldingProfile(tree_canopy_pct=38, building_material_score=0.85,
                              hvac_density_score=0.95, sdoh_index=0.90, year_built=1995),
    "75225": ShieldingProfile(tree_canopy_pct=42, building_material_score=0.88,
                              hvac_density_score=0.96, sdoh_index=0.92, year_built=2000),
    "77019": ShieldingProfile(tree_canopy_pct=35, building_material_score=0.82,
                              hvac_density_score=0.94, sdoh_index=0.88, year_built=1992),
    "78703": ShieldingProfile(tree_canopy_pct=41, building_material_score=0.80,
                              hvac_density_score=0.93, sdoh_index=0.87, year_built=1988),
    # Mixed urban core
    "75201": ShieldingProfile(tree_canopy_pct=18, building_material_score=0.75,
                              hvac_density_score=0.90, sdoh_index=0.70, year_built=2005),
    "77002": ShieldingProfile(tree_canopy_pct=16, building_material_score=0.72,
                              hvac_density_score=0.88, sdoh_index=0.68, year_built=2000),
    # Lower-shielding (older stock, lower canopy)
    "75218": ShieldingProfile(tree_canopy_pct=22, building_material_score=0.55,
                              hvac_density_score=0.70, sdoh_index=0.55, year_built=1965),
    "76104": ShieldingProfile(tree_canopy_pct=17, building_material_score=0.45,
                              hvac_density_score=0.55, sdoh_index=0.40, year_built=1958),
    "78501": ShieldingProfile(tree_canopy_pct=12, building_material_score=0.50,
                              hvac_density_score=0.60, sdoh_index=0.45, year_built=1972),
    "79401": ShieldingProfile(tree_canopy_pct=10, building_material_score=0.55,
                              hvac_density_score=0.65, sdoh_index=0.50, year_built=1970),
}


def shielding_for_zip(zip_code: str) -> float:
    """Look up the default SC for a Texas ZIP, or return a moderate prior."""
    if zip_code in ZIP_SHIELDING_DEFAULTS:
        return compute_shielding_coefficient(ZIP_SHIELDING_DEFAULTS[zip_code])
    return 0.5  # neutral prior — neither pampered nor exposed


if __name__ == "__main__":
    print(f"{'ZIP':<8}{'SC':>6}")
    for z, prof in ZIP_SHIELDING_DEFAULTS.items():
        print(f"{z:<8}{compute_shielding_coefficient(prof):>6.3f}")
