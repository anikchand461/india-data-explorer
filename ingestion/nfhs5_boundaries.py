"""
Downloads NFHS-5's own state (36) and district (707) boundaries from
the DHS Program Spatial Data Repository -- the boundaries the survey
was actually sampled and reported on (survey IA2020DHS, SVYID 541).

This replaces the 2011-Census state polygons for the oral cancer page:
with these, Telangana, Ladakh and the merged Dadra & Nagar Haveli and
Daman & Diu appear as the separate units NFHS-5/NFHS-6 report them as,
instead of being population-weighted back into 2011-era states.

Geometry is simplified server-side (maxAllowableOffset 0.01 degrees,
~1 km) to keep the district file around 1 MB.

Output:
  data/geo/nfhs5_states.geojson     properties: state
  data/geo/nfhs5_districts.geojson  properties: state, district, district_id
"""

import json
from pathlib import Path

import requests
from shapely import make_valid
from shapely.geometry import MultiPolygon, mapping, shape
from shapely.geometry.polygon import orient

from ingestion.state_names import canonical_state

QUERY_URL = (
    "https://gis.dhsprogram.com/arcgis/rest/services/Geometry/"
    "SDR_Regions/MapServer/0/query"
)

SURVEY_ID = 541  # India NFHS-5 (2019-21) in the DHS SDR

GEO_DIR = Path(__file__).resolve().parent.parent / "data" / "geo"


def fetch_level(level, timeout=300):

    response = requests.get(
        QUERY_URL,
        params={
            "where": f"SVYID={SURVEY_ID} AND LEVELRNK={level}",
            "outFields": "REGCODE,REGNAME,OTHREGNA",
            "maxAllowableOffset": 0.01,
            "geometryPrecision": 3,
            "outSR": 4326,
            "f": "geojson",
        },
        timeout=timeout,
    )

    response.raise_for_status()

    data = response.json()

    if data.get("exceededTransferLimit"):
        raise ValueError(
            "DHS SDR truncated the response -- paging would be needed."
        )

    return data


def _polygons(geom):

    if geom.geom_type == "Polygon":
        return [geom]

    if hasattr(geom, "geoms"):
        return [p for part in geom.geoms for p in _polygons(part)]

    return []  # stray lines/points left over from repair


def clockwise(geometry):
    """
    Two fixes so Plotly draws every shape:
      - Server-side simplification leaves some rings self-intersecting
        (invalid); make_valid() repairs them.
      - The DHS service returns RFC 7946 rings (exterior
        counter-clockwise), but Plotly's d3-geo renderer reads a
        counter-clockwise exterior as "everything except this shape"
        and floods the whole map. Exteriors are re-wound clockwise.
    """

    polygons = [
        orient(p, sign=-1.0)
        for p in _polygons(make_valid(shape(geometry)))
        if not p.is_empty
    ]

    if not polygons:
        raise ValueError("Geometry has no polygon area after repair")

    if len(polygons) == 1:
        return mapping(polygons[0])

    return mapping(MultiPolygon(polygons))


def build_states(raw):

    features = []

    for feature in raw["features"]:

        state = canonical_state(feature["properties"]["REGNAME"])

        if state is None:
            raise ValueError(
                f"Unknown state name {feature['properties']['REGNAME']!r}"
            )

        features.append({
            "type": "Feature",
            "id": state,
            "properties": {"state": state},
            "geometry": clockwise(feature["geometry"]),
        })

    if len(features) != 36:
        raise ValueError(f"Expected 36 states/UTs, got {len(features)}")

    return {"type": "FeatureCollection", "features": features}


def build_districts(raw):

    features = []

    for feature in raw["features"]:

        props = feature["properties"]

        state = canonical_state(props["OTHREGNA"])

        if state is None:
            raise ValueError(f"Unknown state name {props['OTHREGNA']!r}")

        # REGCODE alone is not unique nationally, so the id carries
        # the state too.
        district_id = f"{state}|{props['REGNAME']}"

        features.append({
            "type": "Feature",
            "id": district_id,
            "properties": {
                "state": state,
                "district": props["REGNAME"],
                "district_id": district_id,
            },
            "geometry": clockwise(feature["geometry"]),
        })

    if len(features) != 707:
        raise ValueError(f"Expected 707 districts, got {len(features)}")

    return {"type": "FeatureCollection", "features": features}


def write(path, collection):

    # Round-trip through shapely leaves tuples and long floats; keep
    # the 3-decimal precision the service returned.
    def rounded(value):
        if isinstance(value, float):
            return round(value, 3)
        if isinstance(value, (list, tuple)):
            return [rounded(v) for v in value]
        if isinstance(value, dict):
            return {k: rounded(v) for k, v in value.items()}
        return value

    with open(path, "w", encoding="utf-8") as file:
        json.dump(rounded(collection), file, separators=(",", ":"))


def run():

    print("Downloading NFHS-5 state boundaries from DHS SDR ...")
    states = build_states(fetch_level(1))
    write(GEO_DIR / "nfhs5_states.geojson", states)
    print(f"✓ {len(states['features'])} states/UTs")

    print("Downloading NFHS-5 district boundaries from DHS SDR ...")
    districts = build_districts(fetch_level(2))
    write(GEO_DIR / "nfhs5_districts.geojson", districts)
    print(f"✓ {len(districts['features'])} districts")


if __name__ == "__main__":
    run()
