# -*- coding: utf-8 -*-
"""Compatibility facade for CAD import services."""
from __future__ import annotations
import os

from .cad_blocks import flatten_entities
from .cad_models import (
    CAD_EXTENSIONS, CadImportIssue, CadImportResult, CadSourceLayerSummary,
    find_cad_path, is_dgn_v8,
)
from .cad_ogr import (
    _append_layer_summary, _create_output_layer, _first_attribute,
    _import_cad_via_ogr, _make_output_fields, _parse_sublayer,
    collect_feature_attributes, geometry_bucket, open_cad_source_layers,
)
from .cad_rust import _import_cad_via_rust_engine
from .texts import cadastral_text as tx


def import_cad_to_memory_layers(cad_path: str, crs_authid: str, project=None, add_to_project: bool = True, is_canceled_cb=None) -> CadImportResult:
    """Read DWG/DXF/DGN through the supported native adapter or OGR."""
    extension = os.path.splitext(cad_path)[1].lower()
    if extension in (".dwg", ".dxf"):
        return _import_cad_via_rust_engine(cad_path, crs_authid, project, add_to_project=add_to_project, is_canceled_cb=is_canceled_cb)
    if extension == ".dgn":
        if is_dgn_v8(cad_path):
            return _import_dgn_v8_native(cad_path, crs_authid, project, add_to_project=add_to_project)
        return _import_cad_via_ogr(cad_path, crs_authid, project, add_to_project=add_to_project, is_canceled_cb=is_canceled_cb)
    result = CadImportResult(cad_path=cad_path, cad_format=extension.lstrip(".").upper(), crs_authid=crs_authid)
    result.issues.append(CadImportIssue("error", tx("cad.error.unsupported_format", extension=extension)))
    return result


def _import_dgn_v8_native(cad_path: str, crs_authid: str, project=None, add_to_project: bool = True) -> CadImportResult:
    """Import DGN V8 with the native parser."""
    from .dgn_reader import import_dgn_v8_native
    return import_dgn_v8_native(cad_path, crs_authid, project)
