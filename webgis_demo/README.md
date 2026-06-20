# WebGIS quản lý thửa đất

WebGIS này được mở từ nút **Mở WebGIS quản lý thửa đất** trong plugin QGIS.

Khi bấm nút, plugin sẽ lấy **layer polygon đang chọn trong bảng Layers của QGIS**, xuất tạm sang
`data\parcels.geojson`, rồi mở trang WebGIS bằng dữ liệu vừa xuất.

Plugin không đóng gói sẵn dữ liệu thửa mặc định. File `data\parcels.geojson`
chỉ được tạo khi bạn mở WebGIS từ một layer polygon trong QGIS.

## Chức năng hiện có

- Hiển thị layer thửa đất polygon đang chọn trong QGIS.
- Kéo bản đồ, cuộn chuột để phóng to/thu nhỏ.
- Tìm kiếm theo số tờ, số thửa, chủ sử dụng, địa chỉ, loại đất.
- Click thửa hoặc kết quả tìm kiếm để xem thuộc tính.
- Thống kê nhanh tổng số thửa, tổng diện tích, số loại đất và diện tích theo loại.

## Nguyên tắc triển khai

- Nguồn dữ liệu phải được chọn tường minh từ danh sách layer polygon trong QGIS.
- Mỗi lần mở WebGIS, plugin xóa dữ liệu xuất cũ rồi tạo lại `data\parcels.geojson`.
- GeoJSON xuất ra kèm metadata: tên layer, nguồn layer, CRS, số lượng thửa và thống kê loại đất.
- WebGIS không đóng gói sẵn dataset thửa mặc định để tránh nhầm dữ liệu nghiên cứu/demo với dữ liệu người dùng.
- Web client chỉ đọc dữ liệu vừa xuất, không tự thay đổi dữ liệu gốc trong QGIS.

## Cách dùng trong QGIS

1. Mở project QGIS và nạp layer ranh thửa dạng polygon.
2. Bấm nút **Mở WebGIS quản lý thửa đất** trên toolbar/menu plugin.
3. Chọn đúng layer polygon trong hộp thoại **Chọn layer WebGIS**.
4. Trình duyệt sẽ mở WebGIS nội bộ tại `http://127.0.0.1:<port>/`.

Nếu chưa chọn layer polygon, plugin sẽ báo yêu cầu chọn layer trước.

## Chạy thử ngoài QGIS

Trước khi chạy thử ngoài QGIS, cần có file `data\parcels.geojson` do plugin xuất
hoặc tự tạo bằng script chuyển đổi bên dưới.

Từ thư mục `webgis_demo`:

```powershell
C:\Python314\python.exe -m http.server 8765 --bind 127.0.0.1
```

Sau đó mở:

```text
http://127.0.0.1:8765/
```

## Tạo lại dữ liệu GeoJSON mẫu

```powershell
C:\Python314\python.exe tools\convert_shp_to_geojson.py
```

File sinh ra:

```text
data\parcels.geojson
```
