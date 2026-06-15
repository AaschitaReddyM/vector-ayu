"""
Static Texas ZIP centroid table for the Buildathon demo.

Per spec §9.1.2, the pre-build framework only needs a *local static database
matching hexagons to Texas ZIP codes* — not all ~2.6k Texas ZIPs. This file
ships a representative slice covering the Dallas-Fort Worth metroplex plus
the other top Texas metros so demo data can resolve real lat/lon to a known
ZIP with an H3 cell.

For production, swap this for a join against the USPS / Census TIGER ZCTA
centroid file (one row per ZCTA, ~33k US-wide).

Coordinates are approximate ZCTA centroids (WGS-84, lat, lon).
"""

# (zip, lat, lon, city)
TEXAS_ZIP_CENTROIDS: list[tuple[str, float, float, str]] = [
    # Dallas
    ("75201", 32.7876, -96.7989, "Dallas"),
    ("75202", 32.7787, -96.8054, "Dallas"),
    ("75204", 32.8019, -96.7867, "Dallas"),
    ("75205", 32.8400, -96.7800, "Dallas"),
    ("75206", 32.8338, -96.7700, "Dallas"),
    ("75218", 32.8410, -96.7100, "Dallas"),
    ("75219", 32.8126, -96.8089, "Dallas"),
    ("75225", 32.8700, -96.7900, "Dallas"),
    ("75230", 32.9100, -96.7800, "Dallas"),
    ("75240", 32.9300, -96.7700, "Dallas"),
    # Fort Worth
    ("76102", 32.7544, -97.3307, "Fort Worth"),
    ("76104", 32.7250, -97.3200, "Fort Worth"),
    ("76107", 32.7400, -97.3700, "Fort Worth"),
    ("76109", 32.7100, -97.3700, "Fort Worth"),
    ("76116", 32.7300, -97.4400, "Fort Worth"),
    # Plano / Frisco / Allen
    ("75024", 33.0764, -96.8016, "Plano"),
    ("75034", 33.1500, -96.8400, "Frisco"),
    ("75093", 33.0500, -96.8200, "Plano"),
    ("75002", 33.1100, -96.6700, "Allen"),
    # Arlington / Irving
    ("76011", 32.7600, -97.0900, "Arlington"),
    ("75038", 32.8700, -96.9700, "Irving"),
    ("75061", 32.8200, -96.9500, "Irving"),
    # Houston
    ("77002", 29.7589, -95.3677, "Houston"),
    ("77004", 29.7270, -95.3700, "Houston"),
    ("77006", 29.7400, -95.3900, "Houston"),
    ("77019", 29.7500, -95.4100, "Houston"),
    ("77024", 29.7700, -95.5100, "Houston"),
    ("77056", 29.7400, -95.4700, "Houston"),
    ("77081", 29.7100, -95.4900, "Houston"),
    # Austin
    ("78701", 30.2711, -97.7437, "Austin"),
    ("78702", 30.2620, -97.7160, "Austin"),
    ("78703", 30.2900, -97.7700, "Austin"),
    ("78704", 30.2400, -97.7700, "Austin"),
    ("78705", 30.2900, -97.7300, "Austin"),
    # San Antonio
    ("78201", 29.4675, -98.5300, "San Antonio"),
    ("78205", 29.4252, -98.4861, "San Antonio"),
    ("78209", 29.4700, -98.4500, "San Antonio"),
    ("78216", 29.5200, -98.4900, "San Antonio"),
    # El Paso
    ("79901", 31.7619, -106.4850, "El Paso"),
    ("79912", 31.8400, -106.5500, "El Paso"),
    # Corpus Christi
    ("78401", 27.8006, -97.3964, "Corpus Christi"),
    # Lubbock
    ("79401", 33.5779, -101.8552, "Lubbock"),
    # McAllen
    ("78501", 26.2034, -98.2300, "McAllen"),
]
