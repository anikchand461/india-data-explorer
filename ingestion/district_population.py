"""
2020 population for each of NFHS-5's 707 districts, by summing the
WorldPop 1 km gridded population (2020, UN-adjusted) over the NFHS-5
district boundaries in data/geo/nfhs5_districts.geojson.

Census 2011 district counts don't fit: NFHS-5 has 707 districts drawn
on 2019-21 boundaries, Census 2011 has 640, and about 70 districts were
created in between. Summing a population grid over the survey's own
polygons gives every district a figure on exactly the boundaries the
maps use.

The oral cancer model uses these to share a state's projected cases
between its districts, and for district cases per 100,000. Grid cells
are counted when their centre falls inside a district. At 1 km that
misses much of the smallest island and city territories (Lakshadweep
keeps a third of its people), so for the units in SMALL_UNITS every
cell touching the district is counted instead.

Source: WorldPop (2020), Global 1km Population, UN-adjusted, India.
https://hub.worldpop.org/geodata/summary?id=24742

Output: data/reference/oral_cancer/district_population_2020.csv
"""

import csv
import io
import json
from pathlib import Path

import numpy as np
import rasterio
import requests
from rasterio.mask import mask
from shapely.geometry import mapping, shape

ROOT = Path(__file__).resolve().parent.parent

GEOJSON = ROOT / "data" / "geo" / "nfhs5_districts.geojson"

OUT_PATH = (
    ROOT / "data" / "reference" / "oral_cancer"
    / "district_population_2020.csv"
)

# Too small or fragmented for centre-of-cell counting at 1 km.
SMALL_UNITS = {
    "Lakshadweep", "Andaman & Nicobar Islands", "Chandigarh",
}

WORLDPOP_URL = (
    "https://data.worldpop.org/GIS/Population/Global_2000_2020_1km_UNadj/"
    "2020/IND/ind_ppp_2020_1km_Aggregated_UNadj.tif"
)


def run():

    print("  WorldPop 2020 1 km grid (India, UN-adjusted)")

    response = requests.get(
        WORLDPOP_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=300
    )
    response.raise_for_status()

    features = json.loads(GEOJSON.read_text())["features"]

    rows = []

    with rasterio.MemoryFile(io.BytesIO(response.content)) as memory:
        with memory.open() as grid:

            nodata = grid.nodata

            # Whole-raster total, to check the polygons cover India.
            full = grid.read(1)
            grid_total = float(full[full != nodata].sum())

            for feature in features:

                geometry = shape(feature["geometry"])

                cells, _ = mask(
                    grid, [mapping(geometry)], crop=True, filled=True,
                    all_touched=(
                        feature["properties"]["state"] in SMALL_UNITS
                    ),
                )

                values = cells[0]
                population = float(values[values != nodata].sum())

                rows.append({
                    "district_id": feature["properties"]["district_id"],
                    "state": feature["properties"]["state"],
                    "district": feature["properties"]["district"],
                    "population_2020": int(round(population)),
                })

    total = sum(r["population_2020"] for r in rows)
    empty = [r["district_id"] for r in rows if r["population_2020"] == 0]

    if empty:
        raise ValueError(f"Districts with no population: {empty}")

    # India's UN-adjusted 2020 total is about 1.38 billion. The NFHS-5
    # boundaries leave out a little coast and disputed territory.
    if not 0.95 < total / grid_total < 1.02:
        raise ValueError(
            f"Districts sum to {total:,}, grid holds {grid_total:,.0f}"
        )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(OUT_PATH, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    print(
        f"✓ District population: {len(rows)} districts, {total:,} people "
        f"({total / grid_total:.1%} of the grid) -> {OUT_PATH.name}"
    )


if __name__ == "__main__":
    run()
