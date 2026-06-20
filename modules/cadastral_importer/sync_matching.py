# -*- coding: utf-8 -*-
"""CAD candidate extraction and synchronization matching."""
from __future__ import annotations

from .cad_reader import collect_feature_attributes, geometry_bucket, open_cad_source_layers
from .sync_models import ImportIssue, SyncImportResult
from .sync_utils import (
    _convert_attrs_tcvn3, _first_float, _first_int, _first_text,
    _safe_float, _safe_int, _sheet_parcel,
)
from .texts import cadastral_text as tx

def _make_sync_index(gtp_records, pol_records, shp_records, xml_records=None):
    if xml_records is None:
        xml_records = []
    index = {
        "gtp_by_id": {},
        "gtp_by_sheet_parcel": {},
        "gtp_by_parcel": {},
        "pol_by_sheet_parcel": {},
        "pol_by_parcel": {},
        "shp_by_id": {},
        "shp_by_sheet_parcel": {},
        "shp_by_parcel": {},
        "xml_by_sheet_parcel": {},
        "xml_by_parcel": {},
    }
    for record in gtp_records:
        thua_id = _safe_int(record.get("thuaDatId"))
        if thua_id is not None:
            index["gtp_by_id"][thua_id] = record
        _index_record(index["gtp_by_sheet_parcel"], _sheet_parcel(record.get("soHieuToBanDo"), record.get("soThuTuThua")), record)
        _index_record(index["gtp_by_parcel"], _safe_int(record.get("soThuTuThua")), record)

    for record in pol_records:
        _index_record(index["pol_by_sheet_parcel"], _sheet_parcel(record.get("sheet"), record.get("parcel")), record)
        _index_record(index["pol_by_parcel"], _safe_int(record.get("parcel")), record)

    for record in shp_records:
        thua_id = _safe_int(record.get("thuaDatId"))
        if thua_id is not None:
            index["shp_by_id"][thua_id] = record
        _index_record(index["shp_by_sheet_parcel"], _sheet_parcel(record.get("sheet"), record.get("parcel")), record)
        _index_record(index["shp_by_parcel"], _safe_int(record.get("parcel")), record)

    for record in xml_records:
        _index_record(index["xml_by_sheet_parcel"], _sheet_parcel(record.get("sheet"), record.get("parcel")), record)
        _index_record(index["xml_by_parcel"], _safe_int(record.get("parcel")), record)
    return index


def _index_record(mapping, key, record):
    if key is None:
        return
    mapping.setdefault(key, []).append(record)


def _read_cad_features(
    path: str,
    crs_authid: str,
    result: SyncImportResult,
    convert_legacy_text: bool = False,
):
    from qgis.core import QgsVectorLayer, QgsWkbTypes

    source_layers = open_cad_source_layers(path, QgsVectorLayer, QgsWkbTypes)
    valid_layers = [item for item in source_layers if item.valid and item.layer is not None]
    if not valid_layers:
        result.issues.append(ImportIssue("warning", tx("sync.warning.cad_failed"), path))
        return [], {"line": [], "point": []}

    parcels = []
    aux = {"line": [], "point": []}
    for source in valid_layers:
        for feature in source.layer.getFeatures():
            geometry = feature.geometry()
            if geometry is None or geometry.isEmpty():
                continue
            key = geometry_bucket(geometry, QgsWkbTypes)
            attrs = collect_feature_attributes(feature)
            if convert_legacy_text:
                attrs = _convert_attrs_tcvn3(attrs)
            candidate = {
                "source": "CAD",
                "source_path": path,
                "source_fid": int(feature.id()),
                "source_layer": source.name,
                "geometry": geometry,
                "attrs": attrs,
                "sheet": _first_int(attrs, ("soHieuToBanDo", "SHBANDO", "SHTOBD", "SOTO", "TOBD")),
                "parcel": _first_int(attrs, ("soThuTuThua", "SHTHUA", "SOTHUA", "SO_THUA", "THUA", "Text", "OGR_TEXT")),
                "area": _first_float(attrs, ("DIENTICH", "DTICH", "AREA")),
                "cad_level": _first_text(attrs, ("Layer", "LAYER", "Level", "LEVEL", "LevelName")),
                "cad_text": _first_text(attrs, ("Text", "TEXT", "TextString", "OGR_TEXT", "Label")),
            }
            if key == "polygon":
                parcels.append(candidate)
            elif key in aux:
                aux[key].append(candidate)
    return parcels, aux


def _match_sync(candidate, index):
    sync = {"gtp": None, "pol": None, "shp": None, "xml": None}
    thua_id = _safe_int(candidate.get("thuaDatId"))
    if thua_id is not None:
        sync["gtp"] = index["gtp_by_id"].get(thua_id)
        sync["shp"] = index["shp_by_id"].get(thua_id)

    sheet_key = _sheet_parcel(candidate.get("sheet"), candidate.get("parcel"))
    area = _safe_float(candidate.get("area"))
    if not sync["gtp"]:
        sync["gtp"] = _best_match(index["gtp_by_sheet_parcel"].get(sheet_key, []), area)
    if not sync["gtp"]:
        sync["gtp"] = _best_match(index["gtp_by_parcel"].get(_safe_int(candidate.get("parcel")), []), area)

    if not sync["shp"]:
        sync["shp"] = _best_match(index["shp_by_sheet_parcel"].get(sheet_key, []), area)
    if not sync["shp"]:
        sync["shp"] = _best_match(index["shp_by_parcel"].get(_safe_int(candidate.get("parcel")), []), area)

    sync["pol"] = _best_match(index["pol_by_sheet_parcel"].get(sheet_key, []), area)
    if not sync["pol"]:
        sync["pol"] = _best_match(index["pol_by_parcel"].get(_safe_int(candidate.get("parcel")), []), area)

    if "xml_by_sheet_parcel" in index:
        sync["xml"] = _best_match(index["xml_by_sheet_parcel"].get(sheet_key, []), area)
        if not sync["xml"]:
            sync["xml"] = _best_match(index["xml_by_parcel"].get(_safe_int(candidate.get("parcel")), []), area)
    return sync


def _best_match(records, area):
    if not records:
        return None
    if len(records) == 1 or area is None:
        return records[0] if len(records) == 1 else None

    scored = []
    for record in records:
        record_area = _safe_float(record.get("dienTich", record.get("area")))
        if record_area is None:
            continue
        scored.append((abs(record_area - area), record))
    if not scored:
        return None
    scored.sort(key=lambda item: item[0])
    return scored[0][1] if scored[0][0] <= max(1.0, area * 0.005) else None


