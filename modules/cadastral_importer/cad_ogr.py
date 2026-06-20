# -*- coding: utf-8 -*-
"""OGR CAD fallback and shared QGIS layer helpers."""
from __future__ import annotations
import json
import os

from .cad_models import CadImportIssue, CadImportResult, CadSourceLayerSummary
from .layer_runtime import add_generated_layer, remove_previous_generated_layers
from .texts import cadastral_text as tx

def _import_cad_via_ogr(cad_path: str, crs_authid: str, project=None, add_to_project: bool = True, is_canceled_cb=None) -> CadImportResult:
    """Load a CAD file through QGIS/OGR (legacy fallback)."""
    from qgis.PyQt.QtCore import QVariant
    from qgis.core import (
        QgsFeature,
        QgsField,
        QgsFields,
        QgsGeometry,
        QgsProject,
        QgsVectorLayer,
        QgsWkbTypes,
    )

    project = project or QgsProject.instance()
    os.path.splitext(os.path.basename(cad_path))[0]
    result = CadImportResult(
        cad_path=cad_path,
        cad_format=os.path.splitext(cad_path)[1].lstrip(".").upper(),
        crs_authid=crs_authid,
    )

    source_layers = open_cad_source_layers(cad_path, QgsVectorLayer, QgsWkbTypes)
    result.source_layers.extend(source_layers)

    valid_layers = [item for item in source_layers if item.valid and item.layer is not None]
    if not valid_layers:
        result.issues.append(
            CadImportIssue(
                "error",
                tx("cad.error.ogr_unreadable", cad_format=result.cad_format),
                tx("cad.error.ogr_unreadable.detail"),
            )
        )
        return result

    output_fields = _make_output_fields(QgsFields, QgsField, QVariant)
    outputs = {}
    pending_features = {}
    counts = {"point": 0, "line": 0, "polygon": 0}

    for source in valid_layers:
        if is_canceled_cb and is_canceled_cb():
            result.issues.append(CadImportIssue("warning", "Tác vụ bị hủy bởi người dùng."))
            break
        layer = source.layer
        processed = 0
        for feature in layer.getFeatures():
            if is_canceled_cb and is_canceled_cb():
                break
            geometry = feature.geometry()
            if geometry is None or geometry.isEmpty():
                result.skipped_features += 1
                continue

            target_key = geometry_bucket(geometry, QgsWkbTypes)
            if target_key is None:
                result.skipped_features += 1
                continue

            target_layer = outputs.get(target_key)
            if target_layer is None:
                target_layer = _create_output_layer(
                    target_key,
                    crs_authid,
                    output_fields,
                    QgsVectorLayer,
                    cad_path,
                )
                outputs[target_key] = target_layer
                pending_features[target_key] = []

            raw_attrs = collect_feature_attributes(feature)
            output_feature = QgsFeature(target_layer.fields())
            output_feature.setGeometry(QgsGeometry(geometry))
            output_feature.setAttributes(
                [
                    os.path.basename(cad_path),
                    cad_path,
                    result.cad_format,
                    source.name,
                    int(feature.id()),
                    _first_attribute(raw_attrs, ("Layer", "LAYER", "Level", "LEVEL", "LevelName")),
                    _first_attribute(raw_attrs, ("Text", "TEXT", "TextString", "OGR_TEXT", "Label")),
                    _first_attribute(raw_attrs, ("Color", "COLOR", "ColorIndex")),
                    _first_attribute(raw_attrs, ("Linetype", "LineType", "OGR_STYLE")),
                    _first_attribute(raw_attrs, ("EntityHandle", "HANDLE", "Handle")),
                    _first_attribute(raw_attrs, ("Entity", "SubClasses", "Type")),
                    json.dumps(raw_attrs, ensure_ascii=False),
                ]
            )
            pending_features[target_key].append(output_feature)
            counts[target_key] += 1
            processed += 1

        source.feature_count = processed

    for key, layer in outputs.items():
        if counts[key] <= 0:
            continue
        layer.dataProvider().addFeatures(pending_features.get(key, []))
        if add_to_project:
            add_generated_layer(project, layer, cad_path, f"cad_raw_{key}", counts[key])
        else:
            from .layer_runtime import prepare_generated_layer
            prepare_generated_layer(layer, cad_path, f"cad_raw_{key}", counts[key])
            result.output_layers.append(layer)
        result.output_layer_names.append(layer.name())

    result.feature_counts = counts
    if not result.output_layer_names and not result.output_layers:
        result.issues.append(
            CadImportIssue("warning", tx("cad.warning.no_output_geometry"))
        )
    return result


def open_cad_source_layers(cad_path, QgsVectorLayer, QgsWkbTypes):
    base_name = os.path.splitext(os.path.basename(cad_path))[0]

    direct = QgsVectorLayer(cad_path, base_name, "ogr")
    if not direct.isValid():
        summaries = []
        _append_layer_summary(summaries, set(), direct, cad_path, base_name, QgsWkbTypes)
        return summaries

    try:
        sublayers = direct.dataProvider().subLayers()
    except Exception:  # noqa: BLE001 — intentional suppress
        sublayers = []

    if not sublayers:
        summaries = []
        _append_layer_summary(summaries, set(), direct, cad_path, base_name, QgsWkbTypes)
        return summaries

    summaries = []
    seen_uris = set()
    for sublayer in sublayers:
        layer_id, layer_name = _parse_sublayer(sublayer)
        candidates = []
        if layer_name:
            candidates.append((f"{cad_path}|layername={layer_name}", layer_name))
        if layer_id:
            candidates.append((f"{cad_path}|layerid={layer_id}", layer_name or f"layer_{layer_id}"))

        for uri, name in candidates:
            if uri in seen_uris:
                continue
            layer = QgsVectorLayer(uri, name, "ogr")
            _append_layer_summary(summaries, seen_uris, layer, uri, name, QgsWkbTypes)
            if layer.isValid():
                break

    valid_sublayers = [summary for summary in summaries if summary.valid and summary.layer is not None]
    if valid_sublayers:
        return summaries

    fallback = []
    _append_layer_summary(fallback, set(), direct, cad_path, base_name, QgsWkbTypes)
    return fallback


def _append_layer_summary(summaries, seen_uris, layer, uri, name, QgsWkbTypes):
    if uri in seen_uris:
        return
    seen_uris.add(uri)
    valid = layer.isValid()
    error = "" if valid else tx("cad.error.invalid_layer")
    geometry_type = ""
    if valid:
        geometry_type = QgsWkbTypes.displayString(layer.wkbType())

    summary = CadSourceLayerSummary(
        name=name,
        uri=uri,
        valid=valid,
        geometry_type=geometry_type,
        error=error,
        layer=layer if valid else None,
    )
    summaries.append(summary)


def _parse_sublayer(sublayer: str) -> tuple[str, str]:
    parts = sublayer.split("!!::!!")
    if len(parts) >= 2:
        return parts[0], parts[1]
    return "", sublayer


def _make_output_fields(QgsFields, QgsField, QVariant):
    fields = QgsFields()
    for name in (
        "source_file",
        "source_path",
        "cad_format",
        "source_layer",
        "source_fid",
        "cad_level",
        "cad_text",
        "cad_color",
        "cad_linetype",
        "cad_handle",
        "cad_entity",
        "raw_attrs",
    ):
        field_type = QVariant.LongLong if name == "source_fid" else QVariant.String
        fields.append(QgsField(name, field_type))
    return fields


def _create_output_layer(key, crs_authid, fields, QgsVectorLayer, source_path=None):
    geometry_name = {
        "point": "Point",
        "line": "LineString",
        "polygon": "Polygon",
    }[key]
    uri = f"{geometry_name}?crs={crs_authid}" if crs_authid else geometry_name
    suffix = ""
    if source_path:
        suffix = "_" + os.path.splitext(os.path.basename(source_path))[0]
    layer = QgsVectorLayer(uri, f"cad_raw_{key}{suffix}", "memory")
    provider = layer.dataProvider()
    provider.addAttributes(fields)
    layer.updateFields()
    return layer


def geometry_bucket(geometry, QgsWkbTypes) -> str | None:
    geometry_type = QgsWkbTypes.geometryType(geometry.wkbType())
    if geometry_type == QgsWkbTypes.PointGeometry:
        return "point"
    if geometry_type == QgsWkbTypes.LineGeometry:
        return "line"
    if geometry_type == QgsWkbTypes.PolygonGeometry:
        return "polygon"
    return None


def collect_feature_attributes(feature) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for qgs_field in feature.fields():
        name = qgs_field.name()
        value = feature.attribute(name)
        attrs[name] = "" if value is None else str(value)
    return attrs


def _first_attribute(attrs: dict[str, str], names: tuple[str, ...]) -> str:
    lower_map = {key.lower(): value for key, value in attrs.items()}
    for name in names:
        value = lower_map.get(name.lower())
        if value:
            return value
    return ""


_open_source_layers = open_cad_source_layers
_geometry_bucket = geometry_bucket
_collect_attributes = collect_feature_attributes
