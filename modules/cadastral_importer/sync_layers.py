# -*- coding: utf-8 -*-
"""QGIS memory-layer and feature factories for synchronized imports."""
from __future__ import annotations
import json

from .sync_utils import _first_present, _safe_float, _safe_int, _text


def _create_parcel_layer(name: str, crs_authid: str):
    from qgis.PyQt.QtCore import QVariant
    from qgis.core import QgsField, QgsFields, QgsVectorLayer

    uri = f"Polygon?crs={crs_authid}" if crs_authid else "Polygon"
    layer = QgsVectorLayer(uri, f"KG_ThuaDat_import_{name}", "memory")
    fields = QgsFields()
    for field_name, field_type in (
        ("source", QVariant.String),
        ("source_fid", QVariant.String),
        ("thuaDatId", QVariant.LongLong),
        ("soHieuToBanDo", QVariant.Int),
        ("soThuTuThua", QVariant.Int),
        ("dienTich", QVariant.Double),
        ("dienTichGtp", QVariant.Double),
        ("dienTichShp", QVariant.Double),
        ("dienTichPol", QVariant.Double),
        ("dienTichXml", QVariant.Double),
        ("loaiDat", QVariant.String),
        ("tenChu", QVariant.String),
        ("diaChi", QVariant.String),
        ("matchStatus", QVariant.String),
        ("syncSource", QVariant.String),
        ("cadLevel", QVariant.String),
        ("rawAttrs", QVariant.String),
    ):
        fields.append(QgsField(field_name, field_type))
    provider = layer.dataProvider()
    provider.addAttributes(fields)
    layer.updateFields()
    return layer


def _make_parcel_feature(layer, candidate, sync):
    from qgis.core import QgsFeature, QgsGeometry

    gtp = sync.get("gtp") or {}
    pol = sync.get("pol") or {}
    shp = sync.get("shp") or {}
    xml = sync.get("xml") or {}
    sheet = _first_present(candidate.get("sheet"), gtp.get("soHieuToBanDo"), shp.get("sheet"), pol.get("sheet"), xml.get("sheet"))
    parcel = _first_present(candidate.get("parcel"), gtp.get("soThuTuThua"), shp.get("parcel"), pol.get("parcel"), xml.get("parcel"))
    area = _first_present(candidate.get("area"), gtp.get("dienTich"), shp.get("area"), pol.get("area"), xml.get("area"))
    status_parts = []
    if gtp:
        status_parts.append("GTP")
    if shp:
        status_parts.append("SHP")
    if pol:
        status_parts.append("POL")
    if xml:
        status_parts.append("XML")
    match_status = "+".join(status_parts) if status_parts else "unmatched"

    feature = QgsFeature(layer.fields())
    feature.setGeometry(QgsGeometry(candidate["geometry"]))
    feature.setAttributes(
        [
            candidate.get("source", ""),
            str(candidate.get("source_fid", "")),
            _safe_int(_first_present(candidate.get("thuaDatId"), gtp.get("thuaDatId"), shp.get("thuaDatId"))),
            _safe_int(sheet),
            _safe_int(parcel),
            _safe_float(area),
            _safe_float(gtp.get("dienTich")),
            _safe_float(shp.get("area")),
            _safe_float(pol.get("area")),
            _safe_float(xml.get("dienTich")),
            _text(_first_present(gtp.get("loaiDat"), shp.get("land_use"), xml.get("loai_dat"), candidate.get("land_use"))),
            _text(_first_present(gtp.get("tenChu"), shp.get("owner"), pol.get("owner"), xml.get("chu_su_dung"), candidate.get("owner"))),
            _text(_first_present(gtp.get("diaChi"), shp.get("address"), pol.get("address"), xml.get("dia_chi"), candidate.get("address"))),
            match_status,
            match_status if match_status != "unmatched" else "",
            _text(candidate.get("cad_level")),
            json.dumps(candidate.get("attrs", {}), ensure_ascii=False),
        ]
    )
    return feature


def _create_aux_layer(name: str, crs_authid: str, key: str):
    from qgis.PyQt.QtCore import QVariant
    from qgis.core import QgsField, QgsFields, QgsVectorLayer

    geom_name = "LineString" if key == "line" else "Point"
    uri = f"{geom_name}?crs={crs_authid}" if crs_authid else geom_name
    layer = QgsVectorLayer(uri, f"KG_CAD_{key}_{name}", "memory")
    fields = QgsFields()
    for field_name, field_type in (
        ("source", QVariant.String),
        ("source_layer", QVariant.String),
        ("source_fid", QVariant.String),
        ("cadLevel", QVariant.String),
        ("cadText", QVariant.String),
        ("rawAttrs", QVariant.String),
    ):
        fields.append(QgsField(field_name, field_type))
    provider = layer.dataProvider()
    provider.addAttributes(fields)
    layer.updateFields()
    return layer


def _make_aux_feature(layer, candidate):
    from qgis.core import QgsFeature, QgsGeometry

    feature = QgsFeature(layer.fields())
    feature.setGeometry(QgsGeometry(candidate["geometry"]))
    feature.setAttributes(
        [
            candidate.get("source", ""),
            candidate.get("source_layer", ""),
            str(candidate.get("source_fid", "")),
            _text(candidate.get("cad_level")),
            _text(candidate.get("cad_text")),
            json.dumps(candidate.get("attrs", {}), ensure_ascii=False),
        ]
    )
    return feature


