# -*- coding: utf-8 -*-
"""Value and bounding-box helpers for WebGIS exports."""

import os
from qgis.core import Qgis, QgsMessageLog

def _remove_previous_export(launcher, path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as exc:
        QgsMessageLog.logMessage(
            f"Không xóa được dữ liệu WebGIS cũ '{path}': {exc}",
            launcher.plugin_name,
            Qgis.Warning,
        )

def _json_value(value):
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    try:
        if value.isNull():
            return None
    except Exception:  # noqa: BLE001 — intentional suppress
        pass
    try:
        return value.toString()
    except Exception:  # noqa: BLE001 — intentional suppress
        return str(value)

def _first_value(props, names):
    lower_map = {key.lower(): key for key in props.keys()}
    for name in names:
        key = lower_map.get(name.lower())
        if key is not None and props.get(key) not in (None, ""):
            return props.get(key)
    return None

def _numeric_value(value) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return 0.0

def _parcel_label(props) -> str:
    sheet = _first_value(props, ["SHBANDO", "SOTO", "SOTOBD", "TOBD", "MAPSHEET"])
    parcel = _first_value(props, ["SHTHUA", "SOTHUA", "THUA", "SOTHUTUTHUA"])
    if sheet not in (None, "") and parcel not in (None, ""):
        return f"{sheet}-{parcel}"
    if parcel not in (None, ""):
        return str(parcel)
    thua_id = _first_value(props, ["THUAID", "ID"])
    return str(thua_id or "")

def _iter_points(geometry):
    coords = geometry.get("coordinates", [])
    stack = [coords]
    while stack:
        item = stack.pop()
        if not isinstance(item, list):
            continue
        if len(item) >= 2 and not isinstance(item[0], list) and not isinstance(item[1], list):
            try:
                yield float(item[0]), float(item[1])
            except (TypeError, ValueError):
                pass
            continue
        stack.extend(item)

def _extend_bbox(bbox, geometry):
    for x, y in _iter_points(geometry):
        bbox[0] = min(bbox[0], x)
        bbox[1] = min(bbox[1], y)
        bbox[2] = max(bbox[2], x)
        bbox[3] = max(bbox[3], y)
