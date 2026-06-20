# -*- coding: utf-8 -*-
"""Geometry conversion helpers for WebGIS exports."""

import json
from qgis.core import QgsCoordinateTransform, QgsCoordinateTransformContext, QgsGeometry, QgsProject, QgsRectangle, QgsWkbTypes
from .export_utils import _first_value, _iter_points

def _context_filter_rect(layer, map_crs, bbox) -> QgsRectangle | None:
    expanded = _expand_bbox(bbox)
    rect = QgsRectangle(expanded[0], expanded[1], expanded[2], expanded[3])
    if layer.crs() == map_crs:
        return rect
    try:
        transform = QgsCoordinateTransform(map_crs, layer.crs(), QgsCoordinateTransformContext())
        return transform.transformBoundingBox(rect)
    except Exception:  # noqa: BLE001 — intentional suppress
        return None

def _expand_bbox(bbox) -> list[float]:
    width = max(bbox[2] - bbox[0], 1)
    height = max(bbox[3] - bbox[1], 1)
    diagonal = (width * width + height * height) ** 0.5
    buffer_m = max(300.0, min(2500.0, diagonal * 0.35))
    return [bbox[0] - buffer_m, bbox[1] - buffer_m, bbox[2] + buffer_m, bbox[3] + buffer_m]

def _geometry_bbox(geometry) -> list[float] | None:
    bbox = [float("inf"), float("inf"), float("-inf"), float("-inf")]
    for x, y in _iter_points(geometry):
        bbox[0] = min(bbox[0], x)
        bbox[1] = min(bbox[1], y)
        bbox[2] = max(bbox[2], x)
        bbox[3] = max(bbox[3], y)
    return None if bbox[0] == float("inf") else bbox

def _bbox_intersects(a, b) -> bool:
    return not (a[2] < b[0] or a[0] > b[2] or a[3] < b[1] or a[1] > b[3])

def _geometry_as_map_json(geometry, exporter, simplify_tolerance=0.0, dest_crs=None) -> dict:
    """Use C++ native QgsJsonExporter to perform projection, simplification, and rounding."""
    mapped = QgsGeometry(geometry)

    # 1. Reproject to destination CRS first if source is different (safely handles units swap for simplification)
    src_crs = exporter.sourceCrs()
    has_transformed = False
    if dest_crs and dest_crs.isValid() and src_crs.isValid() and dest_crs != src_crs:
        try:
            transform = QgsCoordinateTransform(src_crs, dest_crs, QgsCoordinateTransformContext())
            mapped.transform(transform)
            has_transformed = True
        except Exception:  # noqa: BLE001 — intentional suppress
            pass

    # 2. Simplify in destination CRS (meters) rather than source (which might be degrees)
    if simplify_tolerance > 0.0:
        actual_tolerance = simplify_tolerance
        if not has_transformed and src_crs.isValid() and src_crs.isGeographic():
            # Approx 1 degree = 111,320 meters
            actual_tolerance = simplify_tolerance / 111320.0
        mapped = mapped.simplify(actual_tolerance)

    # 3. Export to JSON (using exporter with source set to dest_crs if already transformed)
    orig_source = exporter.sourceCrs()
    if has_transformed:
        exporter.setSourceCrs(dest_crs)
    try:
        if hasattr(exporter, "exportGeometry"):
            try:
                return json.loads(exporter.exportGeometry(mapped))
            except Exception:  # noqa: BLE001 — intentional suppress
                pass
        geom_dict = json.loads(mapped.asJson())
        precision = exporter.precision()
        if precision >= 0:
            _round_coordinates(geom_dict.get("coordinates"), precision)
        return geom_dict
    finally:
        if has_transformed:
            exporter.setSourceCrs(orig_source)

def _round_coordinates(coords, precision):
    if not isinstance(coords, list):
        return
    if len(coords) == 0:
        return
    if isinstance(coords[0], (int, float)):
        for i in range(len(coords)):
            coords[i] = round(coords[i], precision)
    else:
        for item in coords:
            _round_coordinates(item, precision)

def _is_layer_visible(layer) -> bool:
    try:
        node = QgsProject.instance().layerTreeRoot().findLayer(layer.id())
        if not node:
            return False
        for method_name in ("itemVisibilityCheckedRecursive", "isVisible", "itemVisibilityChecked"):
            method = getattr(node, method_name, None)
            if method and not method():
                return False
        return True
    except Exception:  # noqa: BLE001 — intentional suppress
        return True

def _geometry_type_name(geometry_type) -> str:
    if geometry_type == QgsWkbTypes.PointGeometry:
        return "point"
    if geometry_type == QgsWkbTypes.LineGeometry:
        return "line"
    if geometry_type == QgsWkbTypes.PolygonGeometry:
        return "polygon"
    return "unknown"

def _context_label(layer_name, props) -> str:
    value = _first_value(props, [
        "name", "ten", "TEN", "TEN_DIADANH", "DIADANH", "LABEL", "label",
        "TEN_DUONG", "DUONG", "TRUONG", "TEN_TRUONG", "TENQUAN", "TEN_QUAN",
    ])
    return str(value or layer_name or "").strip()

def _context_kind(layer_name, props, geometry_type) -> str:
    text = " ".join(str(v or "") for v in [layer_name, *props.values()]).lower()
    replacements = {
        "đ": "d", "á": "a", "à": "a", "ả": "a", "ã": "a", "ạ": "a",
        "ă": "a", "ắ": "a", "ằ": "a", "ẳ": "a", "ẵ": "a", "ặ": "a",
        "â": "a", "ấ": "a", "ầ": "a", "ẩ": "a", "ẫ": "a", "ậ": "a",
        "é": "e", "è": "e", "ẻ": "e", "ẽ": "e", "ẹ": "e",
        "ê": "e", "ế": "e", "ề": "e", "ể": "e", "ễ": "e", "ệ": "e",
        "í": "i", "ì": "i", "ỉ": "i", "ĩ": "i", "ị": "i",
        "ó": "o", "ò": "o", "ỏ": "o", "õ": "o", "ọ": "o",
        "ô": "o", "ố": "o", "ồ": "o", "ổ": "o", "ỗ": "o", "ộ": "o",
        "ơ": "o", "ớ": "o", "ờ": "o", "ở": "o", "ỡ": "o", "ợ": "o",
        "ú": "u", "ù": "u", "ủ": "u", "ũ": "u", "ụ": "u",
        "ư": "u", "ứ": "u", "ừ": "u", "ử": "u", "ữ": "u", "ự": "u",
        "ý": "y", "ỳ": "y", "ỷ": "y", "ỹ": "y", "ỵ": "y",
    }
    normalized = "".join(replacements.get(ch, ch) for ch in text)
    if any(key in normalized for key in ("cafe", "ca phe", "coffee")):
        return "cafe"
    if any(key in normalized for key in ("truong", "school", "mau giao", "tieu hoc", "thcs", "thpt")):
        return "school"
    if any(key in normalized for key in ("quan an", "nha hang", "restaurant", "food", "an uong")):
        return "food"
    if any(key in normalized for key in ("song", "kenh", "suoi", "thuy", "ho nuoc", "mat nuoc", "water", "river", "canal")):
        return "water"
    if any(key in normalized for key in ("duong", "road", "street", "tuyen")):
        return "road"
    if any(key in normalized for key in ("dia danh", "thon", "ap ", "xa ", "phuong", "thi tran", "place")):
        return "place"
    if geometry_type == QgsWkbTypes.PointGeometry:
        return "point"
    if geometry_type == QgsWkbTypes.LineGeometry:
        return "line"
    if geometry_type == QgsWkbTypes.PolygonGeometry:
        return "area"
    return "context"
