# -*- coding: utf-8 -*-
"""Attribute source loaders for cadastral synchronization."""
from __future__ import annotations
import os
import sqlite3
import tempfile

from .cad_reader import collect_feature_attributes
from .gtp_reader import decode_and_summarize
from .pol_reader import parse_pol
from .sync_models import ImportIssue, SyncImportResult
from .sync_utils import (
    _append_unique, _convert_attrs_tcvn3, _first_float, _first_int,
    _first_present, _first_text, _safe_float, _safe_int, _text,
)
from .texts import cadastral_text as tx

def _load_xml_records(group, result: SyncImportResult) -> list[dict[str, object]]:
    path = group.get(".xml") if group else None
    if not path:
        return []
    try:
        from .xml_exchange_connector import parse_exchange_xml
        summary = parse_exchange_xml(path)
    except Exception as exc:  # noqa: BLE001 — intentional suppress
        result.issues.append(ImportIssue("warning", f"Không thể nạp tệp XML: {exc}"))
        return []

    records = []
    for record in summary.records:
        records.append(
            {
                "source": "XML",
                "sheet": record.get("so_hieu_to_ban_do"),
                "parcel": record.get("so_thu_tu_thua"),
                "area": record.get("dien_tich"),
                "owner": record.get("chu_su_dung"),
                "address": record.get("dia_chi"),
                "land_use": record.get("loai_dat"),
                "attrs": record,
            }
        )
    return records


def _load_gtp_records(group, result: SyncImportResult) -> list[dict[str, object]]:
    path = group.get(".gtp") if group else None
    if not path:
        return []
    try:
        summary = decode_and_summarize(path)
        sqlite_path = summary.decoded.sqlite_path
        try:
            return _fetch_gtp_records(sqlite_path)
        finally:
            if (
                sqlite_path.endswith("_gtp_decoded.sqlite")
                and os.path.dirname(sqlite_path) == tempfile.gettempdir()
                and os.path.exists(sqlite_path)
            ):
                try:
                    os.remove(sqlite_path)
                except OSError:
                    pass
    except Exception as exc:  # noqa: BLE001 — intentional suppress
        result.issues.append(ImportIssue("warning", tx("sync.warning.gtp_failed"), str(exc)))
        return []


def _fetch_gtp_records(sqlite_path: str) -> list[dict[str, object]]:
    query = """
        SELECT
            td.thuaDatId,
            td.soHieuToBanDo,
            td.soThuTuThua,
            td.dienTich,
            td.dienTichPhapLy,
            td.mucDichSuDungGhep,
            td.TamX,
            td.TamY,
            td.geom,
            dt.nguoiId,
            n.hoTen,
            n.diaChi,
            dm.loaiMucDichSuDungKiemKeId,
            dm.dienTich AS dienTichMucDich
        FROM ThuaDat td
        LEFT JOIN DangKyThua dt
            ON dt.thuaDatId = td.thuaDatId
            AND (dt.trangThai = 1 OR dt.trangThai = '1' OR dt.trangThai IS NULL)
        LEFT JOIN Nguoi n
            ON n.nguoiId = dt.nguoiId
        LEFT JOIN DaMucDichSuDung dm
            ON dm.daMucDichSuDungId = dt.daMucDichSuDungId
        ORDER BY td.thuaDatId, dt.nguoiId
    """
    records: dict[int, dict[str, object]] = {}
    with sqlite3.connect(sqlite_path) as connection:
        connection.row_factory = sqlite3.Row
        for row in connection.execute(query):
            thua_id = _safe_int(row["thuaDatId"])
            if thua_id is None:
                continue
            record = records.setdefault(
                thua_id,
                {
                    "thuaDatId": thua_id,
                    "soHieuToBanDo": _safe_int(row["soHieuToBanDo"]),
                    "soThuTuThua": _safe_int(row["soThuTuThua"]),
                    "dienTich": _safe_float(row["dienTich"]),
                    "dienTichPhapLy": _safe_float(row["dienTichPhapLy"]),
                    "loaiDat": _text(row["mucDichSuDungGhep"]),
                    "TamX": _safe_float(row["TamX"]),
                    "TamY": _safe_float(row["TamY"]),
                    "geom": row["geom"],
                    "owners": [],
                    "addresses": [],
                    "landUses": [],
                },
            )
            _append_unique(record["owners"], _text(row["hoTen"]))
            _append_unique(record["addresses"], _text(row["diaChi"]))
            _append_unique(record["landUses"], _text(row["loaiMucDichSuDungKiemKeId"]))

    for record in records.values():
        record["tenChu"] = "; ".join(record.pop("owners"))
        record["diaChi"] = "; ".join(record.pop("addresses"))
        if not record.get("loaiDat"):
            record["loaiDat"] = "; ".join(record.pop("landUses"))
        else:
            record.pop("landUses", None)
    return list(records.values())


def _load_pol_records(group, result: SyncImportResult) -> list[dict[str, object]]:
    path = group.get(".pol") if group else None
    if not path:
        return []
    try:
        summary = parse_pol(path)
    except Exception as exc:  # noqa: BLE001 — intentional suppress
        result.issues.append(ImportIssue("warning", tx("sync.warning.pol_failed"), str(exc)))
        return []

    records = []
    for record in summary.records:
        records.append(
            {
                "source": "POL",
                "sheet": summary.map_sheet,
                "parcel": record.parcel_number,
                "area": record.area,
                "owner": record.owner,
                "address": record.address,
                "reference_id": record.reference_id,
                "code": record.code,
                "vertices": getattr(record, "vertices", ()),
            }
        )
    return records


def _load_shp_records(
    group,
    result: SyncImportResult,
    convert_legacy_text: bool = False,
) -> list[dict[str, object]]:
    path = group.get(".shp") if group else None
    if not path:
        return []

    from qgis.core import QgsVectorLayer

    layer = QgsVectorLayer(path, os.path.splitext(os.path.basename(path))[0], "ogr")
    if not layer.isValid():
        result.issues.append(ImportIssue("warning", tx("sync.warning.shp_failed"), path))
        return []

    records = []
    for feature in layer.getFeatures():
        attrs = collect_feature_attributes(feature)
        if convert_legacy_text:
            attrs = _convert_attrs_tcvn3(attrs)

        geometry = feature.geometry()
        geometry_area = None
        if geometry is not None and not geometry.isEmpty():
            try:
                geometry_area = geometry.area()
            except Exception:  # noqa: BLE001 — intentional suppress
                geometry_area = None

        records.append(
            {
                "source": "SHP",
                "source_path": path,
                "source_fid": int(feature.id()),
                "thuaDatId": _first_int(attrs, ("thuaDatId", "THUADATID", "THUAID", "ID")),
                "sheet": _first_int(attrs, ("soHieuToBanDo", "SHBANDO", "SHTOBD", "SOTO", "TOBD", "SOBANDO")),
                "parcel": _first_int(attrs, ("soThuTuThua", "SHTHUA", "SOTHUA", "SO_THUA", "THUA", "THUAID")),
                "area": _first_present(
                    _first_float(attrs, ("DIENTICH", "DIENTICHPL", "DTICH", "AREA", "Shape_Area")),
                    geometry_area,
                ),
                "owner": _first_text(attrs, ("TENCHU", "HOTEN", "HO_TEN", "OWNER", "CHU")),
                "address": _first_text(attrs, ("DIACHI", "DIA_CHI", "ADDRESS")),
                "land_use": _first_text(attrs, ("KHLOAIDAT", "MALOAIDAT", "LOAIDAT", "MDSD")),
                "attrs": attrs,
            }
        )
    return records


