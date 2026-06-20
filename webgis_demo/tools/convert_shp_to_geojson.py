# -*- coding: utf-8 -*-
"""Convert a simple Polygon Shapefile + DBF pair to GeoJSON for the WebGIS demo."""

from __future__ import annotations

import json
import os
import struct
import sys
from collections import Counter, defaultdict


DEFAULT_SOURCE_STEM = r"C:\Users\Sea Flower\Documents\baitapgis\bai5\dc2\TD_29359.1"
OUT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "parcels.geojson")
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "land_types.json")


def decode_text(raw: bytes) -> str:
    raw = raw.rstrip(b" \x00")
    if not raw:
        return ""
    for enc in ("utf-8", "cp1258", "latin-1"):
        try:
            return raw.decode(enc).strip()
        except UnicodeDecodeError:
            pass
    return raw.decode("latin-1", errors="replace").strip()


def read_dbf(path: str) -> list[dict]:
    with open(path, "rb") as f:
        data = f.read()

    record_count = struct.unpack("<I", data[4:8])[0]
    header_size = struct.unpack("<H", data[8:10])[0]
    record_size = struct.unpack("<H", data[10:12])[0]

    fields = []
    offset = 32
    field_offset = 1
    while offset < header_size - 1 and data[offset] != 0x0D:
        name = data[offset : offset + 11].split(b"\x00")[0].decode("ascii", errors="replace")
        field_type = chr(data[offset + 11])
        length = data[offset + 16]
        decimals = data[offset + 17]
        fields.append((name, field_type, length, decimals, field_offset))
        field_offset += length
        offset += 32

    rows = []
    for i in range(record_count):
        start = header_size + i * record_size
        record = data[start : start + record_size]
        if not record or record[0:1] == b"*":
            continue

        row = {}
        for name, field_type, length, decimals, field_offset in fields:
            raw = record[field_offset : field_offset + length]
            text = decode_text(raw)
            if field_type in ("N", "F"):
                if not text:
                    value = None
                else:
                    try:
                        value = float(text.replace(",", "."))
                        if decimals == 0:
                            value = int(value)
                    except ValueError:
                        value = text
            else:
                value = text
            row[name] = value
        rows.append(row)
    return rows


def read_polygon_shp(path: str) -> tuple[list[dict], list[float]]:
    with open(path, "rb") as f:
        data = f.read()

    shape_type = struct.unpack("<i", data[32:36])[0]
    if shape_type != 5:
        raise ValueError(f"Only Polygon shapefiles are supported, got shape type {shape_type}.")

    bbox = list(struct.unpack("<4d", data[36:68]))
    records = []
    offset = 100
    while offset + 8 <= len(data):
        content_words = struct.unpack(">i", data[offset + 4 : offset + 8])[0]
        content_len = content_words * 2
        content = data[offset + 8 : offset + 8 + content_len]
        offset += 8 + content_len

        if len(content) < 44:
            continue
        rec_shape_type = struct.unpack("<i", content[0:4])[0]
        if rec_shape_type == 0:
            records.append(None)
            continue
        if rec_shape_type != 5:
            raise ValueError(f"Unexpected record shape type {rec_shape_type}.")

        num_parts = struct.unpack("<i", content[36:40])[0]
        num_points = struct.unpack("<i", content[40:44])[0]
        parts_start = 44
        points_start = parts_start + num_parts * 4
        parts = list(struct.unpack(f"<{num_parts}i", content[parts_start:points_start]))
        parts.append(num_points)

        points = []
        for i in range(num_points):
            p = points_start + i * 16
            points.append(list(struct.unpack("<2d", content[p : p + 16])))

        rings = []
        for part_idx in range(num_parts):
            ring = points[parts[part_idx] : parts[part_idx + 1]]
            if ring and ring[0] != ring[-1]:
                ring.append(ring[0])
            rings.append(ring)

        records.append({"type": "Polygon", "coordinates": rings})
    return records, bbox


def as_float(value) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def load_land_type_colors() -> dict[str, str]:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except OSError:
        return {}

    colors = {}
    for code, item in data.items():
        rgb = item.get("color") if isinstance(item, dict) else None
        if isinstance(rgb, list) and len(rgb) >= 3:
            colors[str(code).upper()] = "#{:02x}{:02x}{:02x}".format(
                max(0, min(255, int(rgb[0]))),
                max(0, min(255, int(rgb[1]))),
                max(0, min(255, int(rgb[2]))),
            )
    return colors


def source_stem_from_args() -> str:
    if len(sys.argv) < 2:
        return DEFAULT_SOURCE_STEM
    path = sys.argv[1]
    return os.path.splitext(path)[0] if path.lower().endswith(".shp") else path


def main() -> None:
    source_stem = source_stem_from_args()
    land_type_colors = load_land_type_colors()
    dbf_rows = read_dbf(source_stem + ".dbf")
    geometries, bbox = read_polygon_shp(source_stem + ".shp")
    feature_count = min(len(dbf_rows), len(geometries))

    features = []
    land_counts = Counter()
    land_area = defaultdict(float)
    for idx in range(feature_count):
        geom = geometries[idx]
        props = dbf_rows[idx]
        code = str(props.get("KHLOAIDAT") or props.get("MALOAIDAT") or "Khac").strip() or "Khac"
        area_m2 = as_float(props.get("DIENTICH") or props.get("DIENTICHPL"))
        land_counts[code] += 1
        land_area[code] += area_m2
        props["land_code"] = code
        props["land_color"] = land_type_colors.get(code.upper(), "#8ab4f8")
        props["area_m2"] = area_m2
        props["parcel_label"] = f"{props.get('SHBANDO', '')}-{props.get('SHTHUA', '')}".strip("-")
        features.append(
            {
                "type": "Feature",
                "id": idx + 1,
                "properties": props,
                "geometry": geom,
            }
        )

    collection = {
        "type": "FeatureCollection",
        "name": "TD_29359_1_parcels",
        "crs": {
            "type": "name",
            "properties": {"name": "VN-2000 / UTM zone 48N, central meridian 105.5"},
        },
        "bbox": bbox,
        "metadata": {
            "source": source_stem,
            "feature_count": feature_count,
            "land_counts": dict(land_counts),
            "land_area_m2": {k: round(v, 2) for k, v in land_area.items()},
            "land_type_colors": land_type_colors,
        },
        "features": features,
    }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(collection, f, ensure_ascii=False, separators=(",", ":"))
    print(OUT_PATH)
    print(f"features={feature_count}")
    print(dict(land_counts))


if __name__ == "__main__":
    main()
