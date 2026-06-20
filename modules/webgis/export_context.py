# -*- coding: utf-8 -*-
"""Context-layer export helpers for WebGIS."""

from qgis.core import QgsFeatureRequest, QgsJsonExporter, QgsMapLayerType, QgsProject, QgsWkbTypes
from .export_geometry import _bbox_intersects, _context_filter_rect, _context_kind, _context_label, _expand_bbox, _geometry_as_map_json, _geometry_bbox, _geometry_type_name, _is_layer_visible
from .export_style import _build_renderer_color_lookup, _context_color, _get_classify_field
from .export_utils import _json_value

CONTEXT_MAX_FEATURES = {QgsWkbTypes.PointGeometry: 700, QgsWkbTypes.LineGeometry: 500, QgsWkbTypes.PolygonGeometry: 300}
CONTEXT_SIMPLIFY_TOLERANCE = {QgsWkbTypes.PointGeometry: 0.0, QgsWkbTypes.LineGeometry: 0.5, QgsWkbTypes.PolygonGeometry: 0.35}
PARCEL_SIMPLIFY_TOLERANCE = 0.05
COORDINATE_PRECISION = 2

def _export_context_layers(launcher, parcel_layer, map_crs, bbox) -> list:
    layers = []
    for candidate in QgsProject.instance().mapLayers().values():
        if candidate.id() == parcel_layer.id():
            continue
        if candidate.type() != QgsMapLayerType.VectorLayer:
            continue
        geometry_type = QgsWkbTypes.geometryType(candidate.wkbType())
        if geometry_type not in (
            QgsWkbTypes.PointGeometry,
            QgsWkbTypes.LineGeometry,
            QgsWkbTypes.PolygonGeometry,
        ):
            continue
        if not _is_layer_visible(candidate):
            continue

        exported = _export_context_layer(launcher, candidate, map_crs, bbox)
        if exported:
            layers.append(exported)
    return layers

def _export_context_layer(launcher, layer, map_crs, bbox) -> dict | None:
    fields = list(layer.fields())
    geometry_type = QgsWkbTypes.geometryType(layer.wkbType())
    features = []
    parcel_filter = _context_filter_rect(layer, map_crs, bbox)
    max_features = CONTEXT_MAX_FEATURES.get(geometry_type, 300)
    parcel_center = ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
    candidates = []

    # Native QgsJsonExporter for fast C++ execution
    exporter = QgsJsonExporter()
    exporter.setSourceCrs(layer.crs())
    exporter.setDestinationCrs(map_crs)
    exporter.setPrecision(COORDINATE_PRECISION)

    request = QgsFeatureRequest()
    if parcel_filter:
        request.setFilterRect(parcel_filter)

    # Pre-build renderer color lookup once for all context features
    ctx_color_lookup = _build_renderer_color_lookup(layer)
    ctx_classify_field = _get_classify_field(layer)

    for feat in layer.getFeatures(request):
        geom = feat.geometry()
        if not geom or geom.isEmpty():
            continue
        try:
            geom_json = _geometry_as_map_json(
                geom,
                exporter,
                simplify_tolerance=CONTEXT_SIMPLIFY_TOLERANCE.get(geometry_type, 0.1),
                dest_crs=map_crs
            )
        except Exception:  # noqa: BLE001 — intentional suppress
            continue
        geom_bbox = _geometry_bbox(geom_json)
        if not geom_bbox or not _bbox_intersects(geom_bbox, _expand_bbox(bbox)):
            continue

        props = {}
        for field in fields:
            value = feat[field.name()]
            props[field.name()] = _json_value(value)
        props["webgis_label"] = _context_label(layer.name(), props)
        props["webgis_kind"] = _context_kind(layer.name(), props, geometry_type)
        props["webgis_color"] = _context_color(launcher, feat, props["webgis_kind"], ctx_color_lookup, ctx_classify_field)

        cx = (geom_bbox[0] + geom_bbox[2]) / 2
        cy = (geom_bbox[1] + geom_bbox[3]) / 2
        distance = ((cx - parcel_center[0]) ** 2 + (cy - parcel_center[1]) ** 2) ** 0.5
        candidates.append((distance, {
            "type": "Feature",
            "id": feat.id(),
            "properties": props,
            "geometry": geom_json,
        }))

    for idx, (_, feature) in enumerate(sorted(candidates, key=lambda item: item[0])[:max_features], start=1):
        feature["id"] = idx
        features.append(feature)

    if not features:
        return None

    return {
        "name": layer.name(),
        "geometry_type": _geometry_type_name(geometry_type),
        "kind": _context_kind(layer.name(), {}, geometry_type),
        "truncated": len(candidates) > len(features),
        "source_count": len(candidates),
        "features": features,
    }

