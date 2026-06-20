# -*- coding: utf-8 -*-
"""User-facing text for the cadastral CAD importer dialog."""

from __future__ import annotations

TEXT = {
    "window_title": "Nhập CAD địa chính",
    "title": "Nhập CAD địa chính",
    "subtitle": "Nhập bản vẽ DWG/DGN/DXF vào QGIS; GTP/POL/SHP chỉ dùng để đồng bộ thuộc tính thửa.",
    "group.source": "Nguồn dữ liệu",
    "placeholder.path": "Chọn file CAD .dwg/.dgn/.dxf hoặc thư mục kèm .gtp/.pol/.shp...",
    "label.path": "Đường dẫn",
    "label.group": "Bộ file",
    "label.cad_crs": "CRS CAD",
    "label.log": "Nhật ký xử lý",
    "button.file": "File",
    "button.folder": "Thư mục",
    "button.scan": "Quét CAD",
    "button.read_cad": "Đọc CAD",
    "button.read_gtp": "Xem GTP sync",
    "button.read_pol": "Xem POL sync",
    "button.refresh": "Làm mới preview",
    "button.import_sync": "Nhập CAD + đồng bộ",
    "button.close": "Đóng",
    "tab.files": "File",
    "tab.cad": "CAD nhập",
    "tab.gtp": "GTP đồng bộ",
    "tab.pol": "POL đồng bộ",
    "tab.import": "Kết quả",
    "log.placeholder": "Nhật ký xử lý sẽ hiển thị ở đây sau khi quét CAD hoặc đồng bộ dữ liệu.",
    "crs.current": "CRS dự án hiện tại — {authid} {description}",
    "crs.fallback_description": "WGS 84",
    "dialog.open_file": "Chọn file CAD địa chính",
    "dialog.open_file_filter": "CAD địa chính (*.dwg *.dgn *.dxf);;Dữ liệu đồng bộ (*.gtp *.pol *.shp);;Tất cả (*.*)",
    "dialog.open_folder": "Chọn thư mục CAD và dữ liệu đồng bộ",
    "warn.missing_path.title": "Thiếu đường dẫn",
    "warn.missing_path.body": "Bạn cần chọn file hoặc thư mục trước.",
    "warn.path_missing.title": "Không tồn tại",
    "warn.path_missing.body": "Đường dẫn đã chọn không tồn tại.",
    "warn.missing_cad.title": "Thiếu CAD",
    "warn.missing_cad.body": "Bộ file hiện tại không có .dxf, .dgn hoặc .dwg.",
    "warn.missing_cad_for_import.body": (
        "Bạn cần chọn bộ có file .dwg, .dgn hoặc .dxf để nhập. "
        "GTP/POL/SHP chỉ dùng để đồng bộ thuộc tính."
    ),
    "warn.missing_crs.title": "Thiếu CRS",
    "warn.missing_crs.body": "Bạn cần chọn CRS nguồn cho file CAD.",
    "warn.missing_crs_import.body": "Bạn cần chọn CRS nguồn cho dữ liệu import.",
    "warn.missing_gtp.title": "Thiếu GTP",
    "warn.missing_gtp.body": "Bộ file hiện tại không có .gtp để đồng bộ.",
    "warn.missing_pol.title": "Thiếu POL",
    "warn.missing_pol.body": "Bộ file hiện tại không có .pol để đồng bộ.",
    "warn.missing_group.title": "Thiếu bộ file",
    "warn.missing_group.body": "Bạn cần quét và chọn một bộ file trước khi import.",
    "question.shp_text.title": "Dịch thuộc tính SHP?",
    "question.shp_text.body": (
        "Bộ file có Shapefile đồng bộ. Nếu DBF còn font TCVN3/ABC, "
        "bạn có muốn dịch các cột chữ sang Unicode trong lớp import không?\n\n"
        "File gốc sẽ không bị sửa."
    ),
    "error.scan": "Lỗi quét hồ sơ",
    "error.read_cad": "Lỗi đọc CAD",
    "error.read_gtp": "Lỗi đọc GTP",
    "error.read_pol": "Lỗi đọc POL",
    "error.import_sync": "Lỗi nhập CAD + đồng bộ",
    "log.scan": (
        "Đã quét {group_count} bộ, {file_count} file; "
        "{cad_count} bộ có CAD để nhập, {sync_count} bộ có GTP/POL/SHP để đồng bộ."
    ),
    "log.cad_preview": (
        "Nhập CAD preview: point={point}, line={line}, polygon={polygon}, skipped={skipped}."
    ),
    "log.gtp_preview": "GTP decode ok: {page_count} page, mask lặp {mask_count} lần, integrity={integrity}.",
    "log.pol_preview": "POL đọc được {record_count} record; header={header_count}, tờ={map_sheet}.",
    "log.import_sync": (
        "Nhập CAD + đồng bộ: thửa={parcel}, line={line}, point={point}, "
        "khớp GTP={matched_gtp}, khớp SHP={matched_shp}, khớp POL={matched_pol}, "
        "chưa khớp={unmatched}."
    ),
    "table.files.headers": ["", "Bộ file", "Đuôi", "Vai trò", "Tên file", "Thư mục", "Trạng thái"],
    "status.empty": "Rỗng",
    "status.missing": "Thiếu",
    "status.selected": "Đang chọn",
    "group.label.cad": "CAD:",
    "group.label.sync": "Sync:",
    "group.label.other": "Khác:",
    "role.cad": "CAD nhập",
    "role.sync": "Đồng bộ",
    "role.sidecar": "Phụ trợ",
    "cad.error.unsupported_format": "Không hỗ trợ định dạng {extension}",
    "cad.error.file_missing": "File CAD không tồn tại",
    "cad.error.ogr_unreadable": "QGIS/OGR không đọc được file {cad_format}",
    "cad.error.ogr_unreadable.detail": (
        "DWG/DGN V8 có thể cần driver; với DWG nên chuyển sang DXF bằng ODA File Converter rồi import DXF."
    ),
    "cad.warning.no_output_geometry": "Đọc được CAD nhưng không có geometry point/line/polygon để tạo layer.",
    "cad.error.invalid_layer": "Layer không hợp lệ",
    "sync.error.no_group": "Chưa chọn bộ file để import.",
    "sync.error.no_cad": "Bộ file chưa có CAD để nhập.",
    "sync.error.no_cad.detail": "Chọn file .dwg, .dgn hoặc .dxf; GTP/POL/SHP chỉ dùng để đồng bộ thuộc tính.",
    "sync.warning.no_parcel_polygon": "Không tìm thấy polygon thửa trong CAD.",
    "sync.warning.no_parcel_polygon.detail": (
        "GTP/POL/SHP đã được đọc làm dữ liệu đồng bộ nhưng không được dùng để dựng hình học."
    ),
    "sync.warning.gtp_failed": "Không đồng bộ được GTP",
    "sync.warning.pol_failed": "Không đồng bộ được POL",
    "sync.warning.shp_failed": "Không đồng bộ được SHP",
    "sync.warning.cad_failed": "Không đọc được CAD",
    "gtp.error.invalid_size": "Kích thước file không chia hết cho {page_size} byte",
    "gtp.error.mask_missing": "Không tìm thấy page lặp để decode GTP",
    "gtp.error.sqlite_header_missing": "File GTP sau decode không có header SQLite",
    "pol.error.too_short": "File POL quá ngắn",
    "pol.error.parser_stopped": "Parser POL dừng tại byte {offset}, file dài {size} byte",
}


def cadastral_text(key: str, **kwargs):
    """Return a translated cadastral importer text entry."""
    value = TEXT.get(key, key)
    if isinstance(value, str) and kwargs:
        return value.format(**kwargs)
    return value
