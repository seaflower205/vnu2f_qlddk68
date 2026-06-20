"""Mechanically extracted functions from dgn_reader.py."""
from __future__ import annotations

import json
import os

from qgis.PyQt.QtCore import QVariant
from qgis.core import QgsFeature, QgsField, QgsFields, QgsGeometry, QgsVectorLayer, QgsPointXY

from .layer_runtime import add_generated_layer
from .cad_models import CadImportResult

def _load_dgn_json_into_layers(doc: dict, cad_path: str, crs_authid: str, project, result) -> 'CadImportResult':  # noqa: F821
    from .cad_models import CadImportIssue
    from .cad_ogr import _make_output_fields, _create_output_layer
    from .texts import cadastral_text as tx
    output_fields = _make_output_fields(QgsFields, QgsField, QVariant)
    outputs = {}
    pending_features = {}
    counts = {"point": 0, "line": 0, "polygon": 0}
    feature_index = 0

    for elem in doc.get("elements", []):
        elem.get("el_type", 0)
        level_id = elem.get("level_id", 0)
        element_id = elem.get("element_id", 0)
        geom_type = elem.get("geom_type")
        entity_type = elem.get("entity_type")
        coords = elem.get("coords", [])
        text_val = elem.get("text_value")

        if not geom_type or not coords:
            continue

        qgs_geom = None
        if geom_type == "point":
            qgs_geom = QgsGeometry.fromPointXY(QgsPointXY(coords[0][0], coords[0][1]))
            target_key = "point"
        elif geom_type == "line":
            pts = [QgsPointXY(c[0], c[1]) for c in coords]
            qgs_geom = QgsGeometry.fromPolylineXY(pts)
            target_key = "line"
        elif geom_type == "polygon":
            pts = [QgsPointXY(c[0], c[1]) for c in coords]
            qgs_geom = QgsGeometry.fromPolygonXY([pts])
            target_key = "polygon"
        else:
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

        output_feature = QgsFeature(target_layer.fields())
        output_feature.setGeometry(qgs_geom)
        output_feature.setAttributes([
            os.path.basename(cad_path),
            cad_path,
            "DGN",
            f"Level {level_id}", # source_layer
            feature_index,       # source_fid
            f"Level {level_id}", # cad_level
            text_val,            # cad_text
            "7",                 # cad_color
            "Continuous",        # cad_linetype
            f"handle_{element_id}", # cad_handle
            entity_type,         # cad_entity
            json.dumps(elem, ensure_ascii=False),
        ])
        pending_features[target_key].append(output_feature)
        counts[target_key] += 1
        feature_index += 1

    for key, layer in outputs.items():
        if counts[key] <= 0:
            continue
        layer.dataProvider().addFeatures(pending_features.get(key, []))
        add_generated_layer(project, layer, cad_path, f"cad_raw_{key}", counts[key])
        result.output_layer_names.append(layer.name())

    result.feature_counts = counts
    if not result.output_layer_names:
        result.issues.append(CadImportIssue("warning", tx("cad.warning.no_output_geometry")))
        
    return result
