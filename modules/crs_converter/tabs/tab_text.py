# -*- coding: utf-8 -*-
"""Runtime text dictionaries for CRS converter tabs.

The tab classes should focus on UI wiring and workflow coordination. User-facing
copy lives here so Vietnamese strings can be reviewed, translated, or renamed
without touching processing code.
"""

from __future__ import annotations


TEXT = {
    "dxf": {
        "warning.missing_deps": (
            "CẢNH BÁO: Tính năng DXF nâng cao yêu cầu thư viện 'ezdxf' và 'shapely'.\n"
            "Hệ thống sẽ cố gắng cài đặt thư viện còn thiếu trong luồng nền.\n"
            "Vui lòng đợi vài giây rồi chuyển tab để cập nhật, hoặc khởi động lại QGIS."
        ),
        "group.import": "1. Nhập bản vẽ địa chính từ tệp CAD DXF",
        "placeholder.input": "Đường dẫn đến file .dxf...",
        "button.browse": "Duyệt tệp",
        "label.input": "Chọn tệp DXF nguồn:",
        "button.import": "Đọc hình học & Nhập thửa đất QGIS",
        "group.export": "2. Xuất lớp thửa đất QGIS ra bản vẽ CAD DXF",
        "label.layer": "Chọn lớp thửa đất (Polygon):",
        "label.sothua": "Trường Số thửa (SOTHUA):",
        "label.soto": "Trường Số tờ (SOTO):",
        "label.loaidat": "Trường Loại đất (LOAIDAT):",
        "label.dientich": "Trường Diện tích (DIENTICH):",
        "button.export": "Xuất lớp thửa ra CAD DXF",
        "dialog.open": "Chọn bản vẽ CAD DXF",
        "dialog.save": "Lưu bản vẽ CAD DXF",
        "missing.import": "Cần cài ezdxf và shapely trước khi đọc DXF nâng cao.",
        "missing.export": "Cần cài ezdxf và shapely trước khi xuất DXF nâng cao.",
        "warn.need_file": "Vui lòng chọn đường dẫn tệp DXF nguồn hợp lệ.",
        "warn.no_polygons": (
            "Không tìm thấy đa giác khép kín (Polygon) nào trong tệp DXF để nhập làm thửa đất.\n"
            "Hãy sử dụng Tab 'Sửa lỗi ranh thửa' để làm sạch và đóng vùng trước nếu bản vẽ chỉ chứa các đường line rời rạc."
        ),
        "success.import": (
            "Đã nhập dữ liệu địa chính thành công từ tệp DXF!\n"
            "- Số thửa đất (đa giác khép kín): {parcel_count}\n"
            "- Số chữ nhãn quét được: {text_count}\n"
            "- Số block ký hiệu quét được: {block_count}\n"
            "Lớp thửa đất mới '{layer_name}' đã được hiển thị trên QGIS."
        ),
        "warn.need_layer": "Vui lòng chọn lớp thửa đất để xuất.",
        "warn.need_sothua": "Trường Số thửa bắt buộc phải được chọn ánh xạ.",
        "warn.empty_layer": "Lớp đang chọn rỗng.",
        "success.export_title": "Xuất thành công",
        "success.export": "Đã xuất thành công {feature_count} thửa đất sang tệp tin CAD:\n{path}",
        "error.export": "Không thể xuất bản vẽ DXF. Vui lòng kiểm tra quyền ghi tệp.",
    },
    "topology": {
        "warning.missing_deps": (
            "CẢNH BÁO: Tính năng sửa lỗi ranh thửa yêu cầu thư viện 'shapely'.\n"
            "Hệ thống sẽ cố gắng cài đặt thư viện còn thiếu trong luồng nền.\n"
            "Vui lòng đợi vài giây rồi chuyển tab để cập nhật, hoặc khởi động lại QGIS."
        ),
        "group.step1": "Bước 1: Làm sạch ranh thửa (Snap & Cắt đường thừa)",
        "label.line_layer": "Chọn lớp đường ranh (CAD/Line):",
        "label.snap": "Dung sai Snap:",
        "label.dangle": "Ngưỡng đường treo (dangle):",
        "label.params": "Cấu hình sai số:",
        "button.clean": "Chạy làm sạch ranh",
        "group.step2": "Bước 2: Tạo thửa đất (Polygonize & Spatial Join)",
        "label.clean_layer": "Chọn lớp ranh đã sạch:",
        "label.label_layer": "Chọn lớp điểm nhãn/chữ (Tùy chọn):",
        "button.polygonize": "Khép vùng thửa đất",
        "group.step3": "Bước 3: Kiểm định chất lượng & Sửa lỗi hình học",
        "label.polygon_layer": "Chọn lớp thửa đất kiểm tra:",
        "button.validate": "Kiểm tra lỗi topo",
        "button.repair": "Tự động sửa lỗi hình học",
        "table.errors": ["Thửa A ID", "Thửa B ID", "Diện tích chồng đè (m²)"],
        "missing.deps": "Cần cài shapely trước khi dùng công cụ sửa lỗi ranh thửa.",
        "warn.need_line": "Vui lòng chọn lớp đường ranh nguồn.",
        "error.no_lines": "Lớp nguồn không có hình học LineString hợp lệ.",
        "success.clean": (
            "Đã làm sạch ranh thửa thành công!\n"
            "- Số đoạn ban đầu: {before_count}\n"
            "- Số đoạn sau khi xử lý: {after_count}\n"
            "Lớp kết quả '{layer_name}' đã được nạp vào QGIS."
        ),
        "warn.need_clean_line": "Vui lòng chọn lớp ranh đã làm sạch ở bước 1.",
        "error.empty_lines": "Lớp ranh rỗng.",
        "error.no_polygons": "Không thể khép vùng đa giác nào từ các đường ranh hiện tại. Hãy kiểm tra lại dung sai snap ở bước 1.",
        "success.polygonize": (
            "Khép vùng và gán nhãn thành công!\n"
            "- Đã tạo ra {polygon_count} thửa đất mới.\n"
            "Lớp kết quả '{layer_name}' đã được hiển thị trên QGIS."
        ),
        "warn.need_polygon": "Vui lòng chọn lớp thửa đất để kiểm tra.",
        "error.no_valid_polygon": "Lớp thửa đất không có hình học hợp lệ.",
        "success.no_overlap": "Chúc mừng! Không phát hiện lỗi chồng đè topo nào.",
        "warn.overlap": (
            "Phát hiện {error_count} vị trí chồng đè hình học giữa các thửa!\n"
            "Đã tạo thêm lớp lỗi '{layer_name}' màu đỏ để bạn dễ dàng zoom đến kiểm tra."
        ),
        "warn.need_repair_layer": "Vui lòng chọn lớp thửa đất cần sửa hình học.",
        "success.repair": (
            "Đã quét và sửa lỗi hoàn tất:\n"
            "- Tìm thấy {invalid_count} thửa bị lỗi tự giao cắt/hở vòng.\n"
            "- Đã sửa tự động thành công: {repaired_count} thửa."
        ),
        "success.no_repair": "Tất cả các thửa đều hợp lệ hình học. Không cần sửa gì.",
    },
    "report": {
        "warning.missing_deps": (
            "CẢNH BÁO: Tính năng Xuất báo cáo Excel yêu cầu thư viện 'openpyxl'.\n"
            "Hệ thống đang tự động cài đặt thư viện này trong luồng nền.\n"
            "Vui lòng đợi vài giây rồi chuyển tab để cập nhật, hoặc khởi động lại QGIS."
        ),
        "field.sothua": "Số hiệu thửa đất (SOTHUA)",
        "field.soto": "Số hiệu tờ bản đồ (SOTO)",
        "field.loaidat": "Mục đích sử dụng / Loại đất (LOAIDAT)",
        "field.tenchu": "Tên chủ sử dụng / Chủ sở hữu (TENCHU)",
        "field.dientich": "Diện tích thửa đất (DIENTICH)",
        "group.source": "1. Chọn lớp thửa đất và Mẫu biểu báo cáo",
        "label.layer": "Chọn lớp thửa đất (Polygon):",
        "option.so_dia_chinh": "Sổ địa chính (Mẫu 01/ĐK)",
        "option.so_cap_gcn": "Sổ cấp Giấy chứng nhận (Mẫu 02/ĐK)",
        "option.so_muc_ke": "Sổ mục kê đất đai (Phụ lục 15)",
        "label.report_type": "Chọn loại báo cáo Excel:",
        "group.mapping": "2. Ánh xạ trường dữ liệu (QGIS Layer ↔ Cột Excel)",
        "table.mapping": ["Cột Excel cần ghi", "Trường dữ liệu QGIS tương ứng"],
        "group.info": "3. Thông tin hành chính & Ký duyệt",
        "placeholder.xa": "Ví dụ: Phường Bến Nghé",
        "label.xa": "Xã/Phường/Thị trấn:",
        "placeholder.huyen": "Ví dụ: Quận 1",
        "label.huyen": "Quận/Huyện/Thành phố:",
        "placeholder.tinh": "Ví dụ: TP. Hồ Chí Minh",
        "label.tinh": "Tỉnh/Thành phố trực thuộc:",
        "placeholder.nguoi_lap": "Họ và tên người lập biểu",
        "label.nguoi_lap": "Người lập biểu:",
        "button.export": "Xuất báo cáo Excel địa chính",
        "missing.deps": "Cần cài openpyxl trước khi xuất báo cáo Excel.",
        "warn.need_layer": "Vui lòng chọn lớp thửa đất để xuất.",
        "warn.need_required_fields": "Các trường Số thửa và Diện tích bắt buộc phải được ánh xạ.",
        "error.no_template": "Không tìm thấy tệp mẫu biểu Excel tại:\n{path}",
        "dialog.save": "Lưu báo cáo Excel",
        "warn.empty_layer": "Lớp đang chọn không chứa dòng dữ liệu nào.",
        "success.export": "Đã xuất báo cáo thành công ra file:\n{path}",
        "error.write": "Không thể ghi dữ liệu ra tệp Excel. Vui lòng kiểm tra quyền ghi hoặc xem log chi tiết.",
    },
    "health": {
        "title": "Hệ thống & Thư viện",
        "label.network": "Trạng thái mạng:",
        "label.manifest": "Phiên bản Manifest:",
        "status.online": "Trực tuyến (Có Internet)",
        "status.offline": "Ngoại tuyến (Không có Internet)",
        "col.name": "Thư viện",
        "col.required": "Yêu cầu",
        "col.status": "Trạng thái",
        "col.version": "Phiên bản",
        "col.path": "Đường dẫn",
        "core": "Bắt buộc (Core)",
        "optional": "Tùy chọn (Optional)",
        "installed": "Đã cài đặt",
        "missing": "Chưa cài đặt",
        "btn.install": "Cài đặt / Cập nhật",
        "btn.check": "Kiểm tra hệ thống",
        "log.title": "Nhật ký cài đặt & hệ thống:",
    },
}


def tab_text(section: str, key: str, **kwargs):
    value = TEXT.get(section, {}).get(key, key)
    if kwargs and isinstance(value, str):
        return value.format(**kwargs)
    return value
