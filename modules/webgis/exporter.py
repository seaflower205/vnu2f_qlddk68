# -*- coding: utf-8 -*-
"""GeoJSON exporter and spatial processing for WebGIS."""

import json
import os
from collections import Counter, defaultdict
from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsCoordinateTransformContext, QgsFeatureRequest, QgsJsonExporter, QgsMapLayerType, QgsRectangle, QgsWkbTypes
from .export_context import CONTEXT_MAX_FEATURES, CONTEXT_SIMPLIFY_TOLERANCE, COORDINATE_PRECISION, PARCEL_SIMPLIFY_TOLERANCE, _export_context_layer, _export_context_layers
from .export_geometry import _bbox_intersects, _context_filter_rect, _context_kind, _context_label, _expand_bbox, _geometry_as_map_json, _geometry_bbox, _geometry_type_name, _is_layer_visible, _round_coordinates
from .export_style import _build_renderer_color_lookup, _clamp_color, _context_color, _feature_color, _get_classify_field, _land_color, _lookup_feature_color
from .export_utils import _extend_bbox, _first_value, _iter_points, _json_value, _numeric_value, _parcel_label, _remove_previous_export

def export_layer_to_geojson(launcher, layer) -> bool:
    """Export the given parcel polygon layer to parcels.geojson for WebGIS."""
    data_dir = os.path.join(launcher.webgis_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    out_path = os.path.join(data_dir, "parcels.geojson")
    _remove_previous_export(launcher, out_path)

    if not layer:
        launcher._push_warning("Hãy chọn một lớp thửa đất dạng polygon trong QGIS trước khi mở WebGIS.")
        return False
    if layer.type() != QgsMapLayerType.VectorLayer:
        launcher._push_warning("Layer đang chọn không phải lớp vector.")
        return False
    if QgsWkbTypes.geometryType(layer.wkbType()) != QgsWkbTypes.PolygonGeometry:
        launcher._push_warning("WebGIS thửa đất hiện cần layer polygon. Hãy chọn lớp ranh thửa trước.")
        return False

    collection = _get_geojson_data(launcher, layer)
    if not collection.get("features"):
        launcher._push_warning("Layer đang chọn không có polygon hợp lệ để đưa lên WebGIS.")
        return False

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(collection, f, ensure_ascii=False, separators=(",", ":"))

    if launcher.iface:
        launcher.iface.messageBar().pushSuccess(
            launcher.plugin_name,
            f"Đã xuất {len(collection['features'])} thửa từ layer '{layer.name()}' sang WebGIS."
        )
    return True

def _get_geojson_data(launcher, layer, bbox=None) -> dict:
    if not layer or layer.type() != QgsMapLayerType.VectorLayer:
        return {"type": "FeatureCollection", "features": []}

    features = []
    bbox_filter = None
    map_crs = QgsCoordinateReferenceSystem("EPSG:3857")

    if bbox:
        try:
            transform_back = QgsCoordinateTransform(map_crs, layer.crs(), QgsCoordinateTransformContext())
            rect_3857 = QgsRectangle(bbox[0], bbox[1], bbox[2], bbox[3])
            bbox_filter = transform_back.transformBoundingBox(rect_3857)
        except Exception:  # noqa: BLE001 — intentional suppress
            pass

    request = QgsFeatureRequest()
    if bbox_filter:
        request.setFilterRect(bbox_filter)

    max_features = 2000
    land_counts = Counter()
    land_area = defaultdict(float)
    fields = list(layer.fields())
    selected_ids = set(layer.selectedFeatureIds())

    # Native QgsJsonExporter for fast C++ reprojection, simplification, and rounding
    exporter = QgsJsonExporter()
    exporter.setSourceCrs(layer.crs())
    exporter.setDestinationCrs(map_crs)
    exporter.setPrecision(COORDINATE_PRECISION)

    # Pre-build renderer color lookup once for all features (avoids per-feature
    # symbolForFeature calls that cause C++ access-violation crashes).
    color_lookup = _build_renderer_color_lookup(layer)
    classify_field = _get_classify_field(layer)

    count = 0
    computed_bbox = [float("inf"), float("inf"), float("-inf"), float("-inf")]

    for feat in layer.getFeatures(request):
        geom = feat.geometry()
        if not geom or geom.isEmpty():
            continue

        try:
            # Export via C++ native exporter
            geom_json = _geometry_as_map_json(geom, exporter, simplify_tolerance=PARCEL_SIMPLIFY_TOLERANCE, dest_crs=map_crs)
        except Exception:  # noqa: BLE001 — intentional suppress
            continue

        props = {}
        for field in fields:
            value = feat[field.name()]
            props[field.name()] = _json_value(value)

        code = _first_value(props, ["KHLOAIDAT", "MALOAIDAT", "LOAIDAT", "MDSD", "MDSD2003"]) or "Khac"
        area_m2 = _numeric_value(_first_value(props, ["DIENTICH", "DIENTICHPL", "AREA", "Shape_Area"]))
        if area_m2 <= 0:
            try:
                area_m2 = float(geom.area())
            except Exception:  # noqa: BLE001 — intentional suppress
                area_m2 = 0.0

        props["land_code"] = str(code).strip() or "Khac"
        props["land_color"] = _feature_color(launcher, feat, props["land_code"], color_lookup, classify_field)
        props["area_m2"] = round(area_m2, 3)
        props["parcel_label"] = _parcel_label(props)
        props["qgis_selected"] = feat.id() in selected_ids

        land_counts[props["land_code"]] += 1
        land_area[props["land_code"]] += area_m2
        _extend_bbox(computed_bbox, geom_json)

        features.append({
            "type": "Feature",
            "id": feat.id(),
            "properties": props,
            "geometry": geom_json,
        })

        count += 1
        if bbox and count >= max_features:
            break

    if not features:
        return {
            "type": "FeatureCollection",
            "features": [],
            "bbox": bbox or [0, 0, 0, 0],
            "metadata": {
                "feature_count": 0
            }
        }

    if computed_bbox[0] == float("inf"):
        if bbox:
            computed_bbox = bbox
        else:
            extent = layer.extent()
            computed_bbox = [extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum()]

    crs = layer.crs()
    crs_name = crs.description() if crs and crs.isValid() else "CRS không xác định"
    crs_authid = crs.authid() if crs and crs.isValid() else ""
    source_crs_name = f"{crs_name} ({crs_authid})" if crs_authid else crs_name

    context_layers = []
    if not bbox:
        context_layers = _export_context_layers(launcher, layer, map_crs, computed_bbox)

    collection = {
        "type": "FeatureCollection",
        "name": layer.name(),
        "crs": {
            "type": "name",
            "properties": {
                "name": "WGS 84 / Pseudo-Mercator (EPSG:3857)",
            },
        },
        "bbox": [round(v, 6) for v in computed_bbox],
        "metadata": {
            "source": layer.source(),
            "layer_name": layer.name(),
            "source_crs": source_crs_name,
            "map_crs": "EPSG:3857",
            "feature_count": len(features),
            "land_counts": dict(land_counts),
            "land_area_m2": {k: round(v, 2) for k, v in land_area.items()},
            "land_type_colors": launcher.land_type_colors,
        },
        "features": features,
        "context_layers": context_layers,
    }
    return collection
