# -*- coding: utf-8 -*-
"""Compatibility facade orchestrating cadastral synchronization."""
from __future__ import annotations
from .cad_reader import find_cad_path
from .layer_runtime import add_generated_layer, remove_previous_generated_layers
from .sync_layers import _create_aux_layer, _create_parcel_layer, _make_aux_feature, _make_parcel_feature
from .sync_matching import _best_match, _index_record, _make_sync_index, _match_sync, _read_cad_features
from .sync_models import ImportIssue, SyncImportResult
from .sync_sources import _fetch_gtp_records, _load_gtp_records, _load_pol_records, _load_shp_records, _load_xml_records
from .sync_utils import *  # compatibility re-exports
from .texts import cadastral_text as tx

def import_cadastral_group(
    group,
    crs_authid: str,
    project=None,
    *,
    convert_legacy_text: bool = False,
    add_to_project: bool = True,
    is_canceled_cb=None,
) -> SyncImportResult:
    """Create normalized QGIS layers from CAD and sync GTP/POL/SHP attributes.

    DWG/DGN/DXF are the only geometry import sources. GTP, POL and SHP are loaded
    only as synchronization sources for parcel number, map sheet, owner,
    address and area fields.
    """
    from qgis.core import QgsProject

    result = SyncImportResult()
    project = project or QgsProject.instance()
    if not group:
        result.issues.append(ImportIssue("error", tx("sync.error.no_group")))
        return result

    cad_path = find_cad_path(group)
    if not cad_path:
        result.issues.append(
            ImportIssue(
                "error",
                tx("sync.error.no_cad"),
                tx("sync.error.no_cad.detail"),
            )
        )
        return result
    
    source_key = group.stem
    remove_previous_generated_layers(
        project,
        source_key,
        ("sync_parcel", "sync_cad_line", "sync_cad_point"),
        (
            f"KG_ThuaDat_import_{group.display_name}",
            f"KG_CAD_line_{group.display_name}",
            f"KG_CAD_point_{group.display_name}",
        ),
    )

    if is_canceled_cb and is_canceled_cb():
        return result
    gtp_records = _load_gtp_records(group, result)
    if is_canceled_cb and is_canceled_cb():
        return result
    pol_records = _load_pol_records(group, result)
    if is_canceled_cb and is_canceled_cb():
        return result
    shp_records = _load_shp_records(group, result, convert_legacy_text)
    if is_canceled_cb and is_canceled_cb():
        return result
    xml_records = _load_xml_records(group, result)
    if is_canceled_cb and is_canceled_cb():
        return result
    sync_index = _make_sync_index(gtp_records, pol_records, shp_records, xml_records)

    parcel_candidates, cad_aux = _read_cad_features(
        cad_path,
        crs_authid,
        result,
        convert_legacy_text,
    )

    if parcel_candidates:
        parcel_layer = _create_parcel_layer(group.display_name, crs_authid)
        parcel_features = []
        for candidate in parcel_candidates:
            if is_canceled_cb and is_canceled_cb():
                result.issues.append(ImportIssue("warning", "Tác vụ bị hủy bởi người dùng."))
                break
            sync = _match_sync(candidate, sync_index)
            feature = _make_parcel_feature(parcel_layer, candidate, sync)
            parcel_features.append(feature)
            if sync.get("gtp"):
                result.matched_gtp += 1
            if sync.get("pol"):
                result.matched_pol += 1
            if sync.get("shp"):
                result.matched_shp += 1
            if sync.get("xml"):
                result.matched_xml += 1
            if not sync.get("gtp") and not sync.get("pol") and not sync.get("shp") and not sync.get("xml"):
                result.unmatched += 1

        provider = parcel_layer.dataProvider()
        provider.addFeatures(parcel_features)
        if add_to_project:
            add_generated_layer(project, parcel_layer, source_key, "sync_parcel", len(parcel_features))
        else:
            from .layer_runtime import prepare_generated_layer
            prepare_generated_layer(parcel_layer, source_key, "sync_parcel", len(parcel_features))
            result.output_layers.append(parcel_layer)
        result.output_layer_names.append(parcel_layer.name())
        result.feature_counts["parcel"] = len(parcel_features)
    else:
        result.issues.append(
            ImportIssue(
                "warning",
                tx("sync.warning.no_parcel_polygon"),
                tx("sync.warning.no_parcel_polygon.detail"),
            )
        )

    for key in ("line", "point"):
        features = cad_aux.get(key, [])
        if not features:
            continue
        layer = _create_aux_layer(group.display_name, crs_authid, key)
        output = []
        for candidate in features:
            output.append(_make_aux_feature(layer, candidate))
        provider = layer.dataProvider()
        provider.addFeatures(output)
        if add_to_project:
            add_generated_layer(project, layer, source_key, f"sync_cad_{key}", len(output))
        else:
            from .layer_runtime import prepare_generated_layer
            prepare_generated_layer(layer, source_key, f"sync_cad_{key}", len(output))
            result.output_layers.append(layer)
        result.output_layer_names.append(layer.name())
        result.feature_counts[key] = len(output)

    return result
