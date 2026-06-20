# Kiểm tra an toàn trước khi sửa module

Trước khi copy thay đổi vào QGIS hoặc đóng gói plugin, chạy:

```powershell
C:\Python314\python.exe tools\check_plugin.py
```

Hoặc:

```powershell
powershell -ExecutionPolicy Bypass -File tools\check_plugin.ps1
```

Bộ kiểm tra này áp dụng cho toàn bộ plugin, không chỉ WebGIS:

- Kiểm tra file runtime bắt buộc của plugin.
- Kiểm tra `metadata.txt`.
- Kiểm tra bảng màu `config/land_types.json`.
- Kiểm tra cú pháp toàn bộ Python trong plugin.
- Kiểm tra cú pháp `webgis_demo/app.js`.
- Kiểm tra `index.html` có đủ ID mà `app.js` đang dùng.
- Kiểm tra asset WebGIS có cache-busting query `?v=...`.
- Kiểm tra schema SQL cơ bản.
- Cảnh báo nếu có `webgis_demo/data/parcels.geojson` trong source.

Nguyên tắc làm việc:

1. Sửa trong source trước, không sửa trực tiếp trong QGIS profile.
2. Chạy `tools\check_plugin.py`.
3. Chỉ copy/cài plugin khi guard báo `PASSED`.
4. Không commit hoặc đóng gói `__pycache__`, `.pyc`, file log, file tạm, hoặc `webgis_demo/data/parcels.geojson`.
5. Khi sửa WebGIS UI, luôn đổi version query trong `index.html`, ví dụ `app.js?v=...`, để trình duyệt không dùng cache cũ.
6. Khi thay đổi cấu trúc mã nguồn lớn (thêm/xóa file, thay đổi xuất khẩu hàm/class, thay đổi luồng xử lý hoặc thêm tính năng mới), bắt buộc phải cập nhật thông tin tương ứng vào các đồ thị cache tĩnh tại `cache/code_knowledge_graph.json` và `cache/control_agentic_graph.json`.

## Danh sách các tệp kiểm thử chính (Main Test Files)

Dưới đây là mô tả của các tệp kiểm thử trong thư mục `tests/`:

*   `tests/test_xml_exchange.py`: Kiểm thử bộ phân tích cú pháp XML địa chính (`parse_exchange_xml`), xuất khẩu XML địa chính (`export_to_exchange_xml`), kiểm tra sai số diện tích pháp lý (`check_area_tolerance`), và so khớp đồng bộ chỉ mục thửa đất (`_make_sync_index`).
*   `tests/test_cadastral_importer.py`: Kiểm thử chức năng quét hồ sơ, đọc tệp CAD thô bằng OGR, và phân tích các tệp tin .gtp, .pol.
*   `tests/test_crs_converter.py`: Kiểm thử chuyển đổi hệ tọa độ VN-2000 3 độ/6 độ, chuyển đổi DMS và chuyển mã font tiếng Việt (TCVN3, VNI sang Unicode).
*   `tests/test_smoke.py`: Kiểm thử tích hợp cơ bản (Smoke test) khởi động plugin.
*   `tests/test_ui_stress.py`: Kiểm thử ứng suất thao tác đổi tab nhanh trên giao diện để tránh crash Qt.
*   `tests/test_webgis.py` & `test_webgis_e2e.py`: Kiểm thử máy chủ WebGIS, kiểm tra xác thực cookie và API.


