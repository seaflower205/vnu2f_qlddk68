# -*- coding: utf-8 -*-
"""Table rendering for cadastral previews and import results."""

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QTableWidget, QTableWidgetItem

from .gtp_reader import fetch_parcel_preview
from .pol_reader import preview_records


class CadastralTableMapper:
    def __init__(self, table_widget: QTableWidget | None = None):
        self.table = table_widget

    def refresh_cad_table(self, owner):
        if not owner.cad_result:
            return
        headers = [
            "name",
            "valid",
            "features",
            "geometry",
            "uri",
            "error",
        ]
        rows = [
            [
                source.name,
                source.valid,
                source.feature_count,
                source.geometry_type,
                source.uri,
                source.error,
            ]
            for source in owner.cad_result.source_layers
        ]
        if owner.cad_result.output_layer_names:
            rows.append(
                [
                    "Output",
                    True,
                    sum(owner.cad_result.feature_counts.values()),
                    ", ".join(owner.cad_result.output_layer_names),
                    owner.cad_result.cad_path,
                    "",
                ]
            )
        for issue in owner.cad_result.issues:
            rows.append(["Issue", issue.level, "", "", issue.message, issue.detail])
        self.fill_table(owner.tbl_cad, headers, rows)

    def refresh_gtp_table(self, owner):
        if not owner.gtp_summary:
            return
        rows = fetch_parcel_preview(owner.gtp_summary.decoded.sqlite_path, limit=800)
        headers = [
            "thuaDatId",
            "soHieuToBanDo",
            "soThuTuThua",
            "dienTich",
            "hoTen",
            "diaChi",
            "nguoiId",
            "daMucDichSuDungId",
            "loaiMucDichSuDungKiemKeId",
            "dienTichMucDich",
            "TamX",
            "TamY",
            "geomSize",
        ]
        data_rows = [[row.get(header, "") for header in headers] for row in rows]
        self.fill_table(owner.tbl_gtp, headers, data_rows)

    def refresh_pol_table(self, owner):
        if not owner.pol_summary:
            return
        rows = preview_records(owner.pol_summary, limit=800)
        headers = [
            "index",
            "parcel_number",
            "area",
            "owner",
            "address",
            "vertex_count",
            "code",
            "reference_id",
        ]
        data_rows = [[row.get(header, "") for header in headers] for row in rows]
        self.fill_table(owner.tbl_pol, headers, data_rows)
        

    def refresh_import_table(self, owner):
        if not owner.sync_result:
            return
        rows = []
        for key in ("parcel", "line", "point"):
            rows.append(
                [
                    "Layer",
                    key,
                    owner.sync_result.feature_counts.get(key, 0),
                    "",
                    "",
                ]
            )
        rows.extend(
            [
                ["Sync", "matched_gtp", owner.sync_result.matched_gtp, "", ""],
                ["Sync", "matched_shp", owner.sync_result.matched_shp, "", ""],
                ["Sync", "matched_pol", owner.sync_result.matched_pol, "", ""],
                ["Sync", "matched_xml", owner.sync_result.matched_xml, "", ""],
                ["Sync", "unmatched", owner.sync_result.unmatched, "", ""],
            ]
        )
        for layer_name in owner.sync_result.output_layer_names:
            rows.append(["Output", layer_name, "", "", ""])
        for issue in owner.sync_result.issues:
            rows.append(["Issue", issue.level, "", issue.message, issue.detail])

        # Hạn sai diện tích Circular 25/2014/TT-BTNMT
        from .tolerance_checker import check_area_tolerance
        scale = owner._get_selected_scale()
        
        # Tìm parcel layer từ output layers
        parcel_layer = None
        for layer in owner.sync_result.output_layers:
            if hasattr(layer, "name") and "ThuaDat" in layer.name():
                parcel_layer = layer
                break
        
        if parcel_layer:
            from qgis.core import NULL
            for feature in parcel_layer.getFeatures():
                geom = feature.geometry()
                if geom is None or geom.isEmpty():
                    continue
                geom_area = geom.area()
                
                # Tìm diện tích hồ sơ (GTP -> XML -> SHP -> POL)
                doc_area = None
                source_used = ""
                for field_name, source_lbl in (
                    ("dienTichGtp", "GTP"),
                    ("dienTichXml", "XML"),
                    ("dienTichShp", "SHP"),
                    ("dienTichPol", "POL")
                ):
                    idx = parcel_layer.fields().indexFromName(field_name)
                    if idx >= 0:
                        val = feature.attribute(field_name)
                        if val is not None and val != NULL and str(val) != "NULL":
                            try:
                                v_float = float(val)
                                if v_float > 0.0:
                                    doc_area = v_float
                                    source_used = source_lbl
                                    break
                            except ValueError:
                                pass
                
                if doc_area is not None:
                    res = check_area_tolerance(geom_area, doc_area, scale)
                    if res["status"] == "WARNING":
                        sheet = feature.attribute("soHieuToBanDo")
                        parcel = feature.attribute("soThuTuThua")
                        rows.append([
                            "Tolerance",
                            f"Thửa {parcel} (Tờ {sheet})",
                            source_used,
                            f"Vượt hạn sai: Thực tế {geom_area:.2f} vs {source_used} {doc_area:.2f} (Lệch {res['diff']:.2f}m², Hạn sai cho phép {res['max_tolerance']:.2f}m²)",
                            "WARNING"
                        ])

        self.fill_table(owner.tbl_import, ["type", "name", "count", "message", "detail"], rows)

    def clear_table(self, table: QTableWidget):
        table.clear()
        table.setRowCount(0)
        table.setColumnCount(0)

    def fill_table(self, table: QTableWidget, headers: list[str], rows):
        from qgis.PyQt.QtGui import QColor
        table.clear()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setRowCount(len(rows))
        for row_idx, row in enumerate(rows):
            is_warning = False
            if len(row) > 4 and row[4] == "WARNING":
                is_warning = True
            elif len(row) > 0 and row[0] == "Tolerance":
                is_warning = True

            for col_idx, value in enumerate(row):
                item = QTableWidgetItem("" if value is None else str(value))
                item.setToolTip("" if value is None else str(value))
                if isinstance(value, (int, float)):
                    align = Qt.AlignRight | Qt.AlignVCenter
                    item.setTextAlignment(align)

                if is_warning:
                    if len(row) > 0 and row[0] == "Tolerance":
                        item.setBackground(QColor(255, 230, 230))  # light red
                    else:
                        item.setBackground(QColor(255, 255, 204))  # light yellow
                table.setItem(row_idx, col_idx, item)
        table.resizeColumnsToContents()
