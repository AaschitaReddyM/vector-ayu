"""
H3 Spatial Ingestion (Spec §3, §4 — Uber H3 Hexagonal Ingestion).

Converts floating-point (lat, lon) coordinates into H3 hexagonal cell IDs at
Resolution 7 or 8 (Resolution 7 ≈ 5.16 km² avg, Resolution 8 ≈ 0.74 km²),
and builds a key-value index from H3 cell → list of ZIP codes whose centroid
falls in that cell.

This replaces costly geometric polygon-intersection lookups with O(1)
key-value matching as called out in spec §4 (Core Technical Features) and
unblocks the downstream pipeline tiers (Exposure Attenuation, TFT input).

Usage
-----
    from pre_build.spatial.h3_ingestion import (
        coord_to_cell, build_zip_index, resolve_coordinate,
    )

    cell = coord_to_cell(32.7876, -96.7989, resolution=7)
    index = build_zip_index(resolution=7)
    hit = resolve_coordinate(32.7876, -96.7989, index, resolution=7)
    # → ResolutionHit(h3_cell="87...", zips=["75201", ...], nearest_zip="75201")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import asin, cos, radians, sin, sqrt
from typing import Iterable

import h3

from .texas_zip_centroids import TEXAS_ZIP_CENTROIDS

# Default H3 resolution per spec §2 step 2 (Resolution 7/8).
DEFAULT_RESOLUTION = 7


# ── Core coordinate → cell ─────────────────────────────────────────────────

def coord_to_cell(lat: float, lon: float, resolution: int = DEFAULT_RESOLUTION) -> str:
    """Hash a (lat, lon) into an H3 cell ID string at the given resolution."""
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        raise ValueError(f"coordinate out of range: ({lat}, {lon})")
    if not (0 <= resolution <= 15):
        raise ValueError(f"invalid H3 resolution: {resolution}")
    return h3.latlng_to_cell(lat, lon, resolution)


def cell_to_center(cell: str) -> tuple[float, float]:
    """Return the (lat, lon) of the centroid of an H3 cell."""
    return h3.cell_to_latlng(cell)


def cell_neighbors(cell: str, k: int = 1) -> list[str]:
    """k-ring neighbors of a cell — useful for spatial smoothing of exposure."""
    return list(h3.grid_disk(cell, k))


# ── ZIP index ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ZipRecord:
    zip_code: str
    lat: float
    lon: float
    city: str


@dataclass
class H3ZipIndex:
    """Forward and reverse index between H3 cells and Texas ZIPs."""
    resolution: int
    cell_to_zips: dict[str, list[ZipRecord]] = field(default_factory=dict)
    zip_to_cell: dict[str, str] = field(default_factory=dict)

    def cells(self) -> Iterable[str]:
        return self.cell_to_zips.keys()

    def zips(self) -> Iterable[str]:
        return self.zip_to_cell.keys()

    def __len__(self) -> int:
        return len(self.zip_to_cell)


def build_zip_index(resolution: int = DEFAULT_RESOLUTION) -> H3ZipIndex:
    """Materialize the Texas ZIP ↔ H3 cell index from the static centroid table."""
    idx = H3ZipIndex(resolution=resolution)
    for zip_code, lat, lon, city in TEXAS_ZIP_CENTROIDS:
        cell = coord_to_cell(lat, lon, resolution)
        rec = ZipRecord(zip_code=zip_code, lat=lat, lon=lon, city=city)
        idx.cell_to_zips.setdefault(cell, []).append(rec)
        idx.zip_to_cell[zip_code] = cell
    return idx


# ── Resolution lookup ──────────────────────────────────────────────────────

@dataclass
class ResolutionHit:
    """Result of resolving a coordinate against the ZIP index."""
    h3_cell: str
    zips: list[str]
    nearest_zip: str | None
    nearest_distance_km: float | None


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = radians(lat1), radians(lat2)
    dp, dl = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
    return 2 * r * asin(sqrt(a))


def resolve_coordinate(
    lat: float,
    lon: float,
    index: H3ZipIndex,
    *,
    resolution: int | None = None,
    k_ring_fallback: int = 2,
) -> ResolutionHit:
    """
    Look up a coordinate in the ZIP index.

    Strategy:
      1. Hash to its H3 cell — if that cell holds any ZIPs, return them.
      2. Otherwise expand outward via k-ring up to ``k_ring_fallback`` rings.
      3. If still no hit, return ``nearest_zip=None`` so callers can route the
         patient to Track B (manual triage, spec §7).
    """
    res = resolution if resolution is not None else index.resolution
    cell = coord_to_cell(lat, lon, res)

    hits = list(index.cell_to_zips.get(cell, []))
    if not hits:
        for k in range(1, k_ring_fallback + 1):
            for neighbor in cell_neighbors(cell, k):
                hits.extend(index.cell_to_zips.get(neighbor, []))
            if hits:
                break

    if not hits:
        return ResolutionHit(h3_cell=cell, zips=[], nearest_zip=None, nearest_distance_km=None)

    # Pick the geometrically nearest ZIP centroid among collected hits.
    nearest = min(hits, key=lambda r: _haversine_km(lat, lon, r.lat, r.lon))
    return ResolutionHit(
        h3_cell=cell,
        zips=[r.zip_code for r in hits],
        nearest_zip=nearest.zip_code,
        nearest_distance_km=_haversine_km(lat, lon, nearest.lat, nearest.lon),
    )


# ── CLI smoke test ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Building H3 ZIP index at resolution {DEFAULT_RESOLUTION}...")
    idx = build_zip_index()
    print(f"  indexed {len(idx)} Texas ZIPs across {len(idx.cell_to_zips)} H3 cells")

    samples = [
        ("Reunion Tower (Dallas)", 32.7755, -96.8089),
        ("AT&T Stadium (Arlington)", 32.7473, -97.0945),
        ("Texas Medical Center (Houston)", 29.7100, -95.3970),
        ("UT Tower (Austin)", 30.2862, -97.7394),
        ("Middle of nowhere (West Texas)", 31.0, -102.0),
    ]
    for label, lat, lon in samples:
        hit = resolve_coordinate(lat, lon, idx)
        print(
            f"  {label:38s} -> cell={hit.h3_cell} "
            f"nearest_zip={hit.nearest_zip} "
            f"(~{hit.nearest_distance_km:.2f} km)"
            if hit.nearest_zip
            else f"  {label:38s} -> cell={hit.h3_cell} (no nearby ZIP — route to Track B)"
        )
