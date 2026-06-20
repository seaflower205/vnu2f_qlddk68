# -*- coding: utf-8 -*-
"""Small runtime translation helper for plugin UI text."""

from __future__ import annotations

import os

try:
    from qgis.PyQt.QtCore import QSettings
except Exception:  # noqa: BLE001 — intentional suppress
    QSettings = None


DEFAULT_LANGUAGE = "vi"
SETTINGS_KEY = "vnu2f_qlddk68/language"


TRANSLATIONS = {
    "vi": {
        "common.close": "Đóng",
        "common.reset": "Đặt lại",
        "common.help": "Trợ giúp",
        "common.warning": "Cảnh báo",
        "common.error": "Lỗi",
        "common.success": "Thành công",
        "crs.window_title": "Chuyển đổi Hệ Tọa Độ VN-2000",
        "crs.sidebar.project_layers": "Dự án & Bản vẽ",
        "crs.sidebar.point_coords": "Tọa độ điểm đo",
        "crs.sidebar.font_convert": "Chuyển đổi Font chữ",
        "crs.sidebar.plot_points": "Rải điểm tọa độ",
        "crs.sidebar.map_packager": "Đóng gói bản đồ",
        "crs.sidebar.kml": "Công cụ KML",
        "crs.sidebar.mbtiles": "Tạo MBTiles",
        "crs.sidebar.layout": "Bố cục bản đồ",
        "crs.sidebar.dxf_advanced": "DXF nâng cao",
        "crs.sidebar.topology": "Sửa lỗi ranh thửa",
        "crs.sidebar.symbology": "Ký hiệu địa chính",
        "crs.sidebar.label": "Nhãn thửa đất",
        "crs.sidebar.stats": "Thống kê đất đai",
        "crs.sidebar.cadastral_settings": "Cài đặt & CRS",
        "crs.sidebar.report": "Xuất báo cáo",

        "crs.status.unavailable": "Hệ tọa độ dự án: Không khả dụng (Ngoài môi trường QGIS)",
        "crs.status.current": "🌐 Hệ tọa độ Dự án hiện tại: {desc} ({auth})",
        "crs.status.invalid": "⚠️ Dự án hiện chưa được thiết lập Hệ tọa độ (Invalid CRS)!",
        "layer.group.project_crs": "Đặt Hệ tọa độ cho Dự án",
        "layer.group.reproject": "Chuyển đổi CRS Lớp Bản đồ và Xuất file",
        "layer.group.basemaps": "Tải nhanh bản đồ nền địa lý (Quick Basemaps)",
        "layer.label.project_crs": "Chọn Hệ tọa độ:",
        "layer.label.layer": "Chọn Lớp dữ liệu:",
        "layer.label.basemap": "Chọn bản đồ nền:",
        "layer.label.target_crs": "CRS đích chuyển đổi:",
        "layer.button.apply_project": "Áp dụng cho Dự án",
        "layer.button.export_shp": "Xuất lớp bản đồ (Shapefile)",
        "layer.button.add_basemap": "Thêm vào dự án QGIS",
        "layer.msg.invalid_crs": "Hệ tọa độ không hợp lệ: {code}",
        "layer.msg.project_applied": "Đã áp dụng Hệ tọa độ mới cho Dự án: {authid}",
        "layer.msg.basemap_added": "Đã thêm bản đồ nền '{name}' thành công.",
        "layer.msg.need_layer": "Vui lòng chọn lớp dữ liệu cần chuyển đổi.",
        "layer.msg.invalid_target_crs": "Hệ tọa độ đích không hợp lệ: {code}",
        "layer.dialog.save_shp": "Lưu file Shapefile sau chuyển đổi",
        "layer.dialog.convert_success": "Chuyển đổi thành công",
        "layer.msg.export_success": "Đã xuất file thành công sang:\n{filename}\nCRS: {authid}",
        "layer.dialog.export_error": "Lỗi xuất file",
        "layer.msg.export_error": "Mã lỗi: {code}\nChi tiết: {detail}",
        "font.group.config": "Cấu hình Chuyển đổi Font chữ",
        "font.group.log": "Kết quả xử lý",
        "font.label.source": "Nguồn dữ liệu:",
        "font.label.layer": "Lớp bản đồ:",
        "font.label.file_in": "Tệp Shapefile nguồn:",
        "font.label.file_out": "Tệp Shapefile kết quả:",
        "font.label.conversion": "Chuyển đổi bảng mã:",
        "font.label.format": "Định dạng đầu ra:",
        "font.label.target_crs": "Hệ tọa độ đích (CRS):",
        "font.option.qgis_layer": "Lớp bản đồ đang mở trong QGIS",
        "font.option.shp_file": "Tệp Shapefile (.shp) trên đĩa",
        "font.option.tcvn3_unicode": "TCVN3 (ABC) → Unicode",
        "font.option.vni_unicode": "VNI → Unicode",
        "font.option.unicode_tcvn3": "Unicode → TCVN3 (.VnTime)",
        "font.option.no_convert": "Không chuyển đổi (Chỉ xuất file / Đổi CRS)",
        "font.option.shapefile": "Shapefile (*.shp)",
        "font.option.mapinfo": "MapInfo TAB (*.tab)",
        "font.placeholder.file_in": "Đường dẫn tới file .shp đầu vào...",
        "font.placeholder.file_out": "Đường dẫn lưu file .shp kết quả...",
        "font.button.convert_export": "Chuyển đổi và Xuất",
        "font.help.title": "Trợ giúp Chuyển đổi Font",
        "font.help.body": (
            "Công cụ chuyển đổi bảng mã tiếng Việt cho các lớp bản đồ:\n\n"
            "- TCVN3 (ABC) → Unicode: Chuyển đổi thuộc tính lớp bản đồ từ TCVN3 sang Unicode dựng sẵn (UTF-8).\n"
            "- VNI → Unicode: Chuyển đổi thuộc tính lớp bản đồ từ VNI-Windows sang Unicode dựng sẵn (UTF-8).\n"
            "- Unicode → TCVN3 (.VnTime): Chuyển đổi ngược lại phục vụ bản đồ MapInfo hoặc MicroStation V7.\n\n"
            "Tính năng đặc biệt:\n"
            "- Tự động quét một lần (Positional Scan) tránh lỗi dịch lặp/dây chuyền ký tự.\n"
            "- Tự động hậu xử lý (Post-process) file MapInfo TAB để khắc phục lỗi bể font Charset Neutral."
        ),
        "font.dialog.open_shp": "Chọn file Shapefile nguồn",
        "font.dialog.save_shp": "Chọn file Shapefile kết quả",
        "font.dialog.save_result": "Lưu tệp kết quả",
        "font.msg.need_source_file": "Vui lòng chọn tệp Shapefile nguồn hợp lệ.",
        "font.msg.need_output_file": "Vui lòng chọn đường dẫn lưu tệp kết quả.",
        "font.msg.need_layer": "Vui lòng chọn lớp bản đồ cần chuyển đổi.",
        "cadastral.window_title": "Nhập CAD địa chính",
        "cadastral.title": "Nhập CAD địa chính",
        "cadastral.subtitle": "Nhập bản vẽ DWG/DGN/DXF vào QGIS; GTP/POL/SHP chỉ dùng để đồng bộ thuộc tính thửa.",
        "cadastral.group.source": "Nguồn dữ liệu",
    },
    "en": {
        "common.close": "Close",
        "common.reset": "Reset",
        "common.help": "Help",
        "common.warning": "Warning",
        "common.error": "Error",
        "common.success": "Success",
        "crs.window_title": "VN-2000 Coordinate Converter",
        "crs.sidebar.project_layers": "Project & Layers",
        "crs.sidebar.point_coords": "Point Coordinates",
        "crs.sidebar.font_convert": "Font Conversion",
        "crs.sidebar.plot_points": "Plot Coordinates",
        "crs.sidebar.map_packager": "Map Packager",
        "crs.sidebar.kml": "KML Tools",
        "crs.sidebar.mbtiles": "Create MBTiles",
        "crs.sidebar.layout": "Map Layout",
        "crs.sidebar.dxf_advanced": "Advanced DXF",
        "crs.sidebar.topology": "Fix Parcel Boundaries",
        "crs.sidebar.symbology": "Cadastral Symbology",
        "crs.sidebar.label": "Parcel Labels",
        "crs.sidebar.stats": "Land Statistics",
        "crs.sidebar.cadastral_settings": "Settings & CRS",
        "crs.sidebar.report": "Export Reports",

        "crs.status.unavailable": "Project CRS: Unavailable (outside QGIS)",
        "crs.status.current": "🌐 Current Project CRS: {desc} ({auth})",
        "crs.status.invalid": "⚠️ The project CRS is not set yet (Invalid CRS)!",
        "layer.group.project_crs": "Set Project CRS",
        "layer.group.reproject": "Reproject Map Layer and Export File",
        "layer.group.basemaps": "Load Quick Basemaps",
        "layer.label.project_crs": "Select CRS:",
        "layer.label.layer": "Select data layer:",
        "layer.label.basemap": "Select basemap:",
        "layer.button.apply_project": "Apply to Project",
        "layer.button.export_shp": "Export Map Layer (Shapefile)",
        "layer.button.add_basemap": "Add to QGIS Project",
        "layer.msg.invalid_crs": "Invalid CRS: {code}",
        "layer.msg.project_applied": "Applied new Project CRS: {authid}",
        "layer.msg.basemap_added": "Successfully added basemap '{name}'.",
        "layer.msg.need_layer": "Please select a data layer to convert.",
        "layer.msg.invalid_target_crs": "Invalid target CRS: {code}",
        "layer.dialog.save_shp": "Save converted Shapefile",
        "layer.dialog.convert_success": "Conversion Complete",
        "layer.msg.export_success": "Successfully exported to:\n{filename}\nCRS: {authid}",
        "layer.dialog.export_error": "Export Error",
        "layer.msg.export_error": "Error code: {code}\nDetails: {detail}",
        "font.group.config": "Font Conversion Settings",
        "font.group.log": "Processing Result",
        "font.label.source": "Data source:",
        "font.label.layer": "Map layer:",
        "font.label.file_in": "Source Shapefile:",
        "font.label.file_out": "Output Shapefile:",
        "font.label.conversion": "Encoding conversion:",
        "font.label.format": "Output format:",
        "font.label.target_crs": "Target CRS:",
        "font.option.qgis_layer": "Map layer opened in QGIS",
        "font.option.shp_file": "Shapefile (.shp) on disk",
        "font.option.tcvn3_unicode": "TCVN3 (ABC) → Unicode",
        "font.option.vni_unicode": "VNI → Unicode",
        "font.option.unicode_tcvn3": "Unicode → TCVN3 (.VnTime)",
        "font.option.no_convert": "No conversion (export / change CRS only)",
        "font.option.shapefile": "Shapefile (*.shp)",
        "font.option.mapinfo": "MapInfo TAB (*.tab)",
        "font.placeholder.file_in": "Path to source .shp file...",
        "font.placeholder.file_out": "Path for output .shp file...",
        "font.button.convert_export": "Convert and Export",
        "font.help.title": "Font Conversion Help",
        "font.help.body": (
            "Convert Vietnamese text encodings in map layer attributes:\n\n"
            "- TCVN3 (ABC) → Unicode: Convert TCVN3 attributes to precomposed Unicode (UTF-8).\n"
            "- VNI → Unicode: Convert VNI-Windows attributes to precomposed Unicode (UTF-8).\n"
            "- Unicode → TCVN3 (.VnTime): Convert back for MapInfo or MicroStation V7 workflows.\n\n"
            "Special behavior:\n"
            "- Single positional scan to avoid repeated/chain conversion artifacts.\n"
            "- Automatic MapInfo TAB post-process to fix Charset Neutral font issues."
        ),
        "font.dialog.open_shp": "Select source Shapefile",
        "font.dialog.save_shp": "Select output Shapefile",
        "font.dialog.save_result": "Save output file",
        "font.msg.need_source_file": "Please select a valid source Shapefile.",
        "font.msg.need_output_file": "Please choose an output file path.",
        "font.msg.need_layer": "Please select a map layer to convert.",
        "cadastral.window_title": "Import Cadastral CAD",
        "cadastral.title": "Import Cadastral CAD",
        "cadastral.subtitle": "Import DWG/DGN/DXF drawings into QGIS; GTP/POL/SHP are only used to synchronize parcel attributes.",
        "cadastral.group.source": "Data source",
    },
}


def current_language() -> str:
    env_lang = os.environ.get("VNU2F_LANG")
    if env_lang:
        return env_lang if env_lang in TRANSLATIONS else DEFAULT_LANGUAGE
    if QSettings:
        value = QSettings().value(SETTINGS_KEY, DEFAULT_LANGUAGE)
        return value if value in TRANSLATIONS else DEFAULT_LANGUAGE
    return DEFAULT_LANGUAGE



def tr(key: str, **kwargs) -> str:
    language = current_language()
    text = TRANSLATIONS.get(language, {}).get(key)
    if text is None:
        text = TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text


_translator = None


def install_qt_translator():
    """Nạp file .qm tương ứng ngôn ngữ hiện tại vào QApplication.
    Gọi hàm này 1 lần khi plugin khởi động (initGui).
    Mô hình Hybrid: Dict-based tr() vẫn là runtime chính.
    """
    global _translator
    lang = current_language()
    qm_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "i18n", f"{lang}.qm"
    )
    if not os.path.isfile(qm_path):
        return False
    try:
        from qgis.PyQt.QtCore import QTranslator, QCoreApplication
        _translator = QTranslator()
        if _translator.load(qm_path):
            QCoreApplication.installTranslator(_translator)
            return True
    except Exception:
        pass
    return False
