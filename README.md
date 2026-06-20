<div align="center">
  <img src="icon.png" alt="VNU2F QLDDK68 Logo" width="120" />

  # VNU2F QLDDK68
  **Bộ công cụ Trắc địa - Địa chính Việt Nam Toàn diện cho QGIS 4.0+**

  [![Release](https://github.com/seaflower205/vnu2f_qlddk68/actions/workflows/release.yml/badge.svg)](https://github.com/seaflower205/vnu2f_qlddk68/actions/workflows/release.yml)
  [![Tests](https://github.com/seaflower205/vnu2f_qlddk68/actions/workflows/tests.yml/badge.svg)](https://github.com/seaflower205/vnu2f_qlddk68/actions/workflows/tests.yml)
  [![QGIS Version](https://img.shields.io/badge/QGIS-4.0%2B-green.svg)](https://qgis.org/)
  [![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org/)
  [![License](https://img.shields.io/badge/License-GPL%20v3-orange.svg)](https://opensource.org/licenses/GPL-3.0)

</div>

---

## 🌟 Giới thiệu

**VNU2F QLDDK68** là một plugin mã nguồn mở được phát triển riêng cho phần mềm QGIS, tối ưu hóa toàn diện cho các tác vụ chuyên ngành Trắc địa và Quản lý đất đai tại Việt Nam.

Với mục tiêu tự động hóa và nâng cao độ chính xác, plugin cung cấp đầy đủ các tính năng từ chuyển đổi hệ tọa độ VN-2000, xử lý lỗi hình học (topology), đến xuất báo cáo địa chính chuẩn Thông tư mới nhất của Bộ TN&MT, và tích hợp WebGIS 3D tiên tiến.

---

## 🚀 Tính năng nổi bật

### 🗺️ Xử lý Không gian & Tọa độ
- **Chuyển đổi VN-2000:** Chuyển đổi linh hoạt giữa hệ tọa độ WGS-84 và hệ tọa độ VN-2000 nội bộ các tỉnh thành (chuẩn 7 tham số).
- **Rải điểm tọa độ:** Hỗ trợ đọc tọa độ từ file văn bản/Excel và vẽ điểm/đường ranh giới lên bản đồ nhanh chóng.
- **Sửa lỗi hình học (Topology):** Tự động phát hiện và sửa các lỗi ranh thửa, tự động khép vùng (sử dụng thư viện `shapely`).

### 📐 Nhập/Xuất Dữ liệu Địa chính
- **Import đa định dạng:** Hỗ trợ nhập liệu đồng bộ từ các tệp `SHP`, `POL`, `GTP`, `CAD` (`DXF`, `DWG`, `DGN`).
- **DXF Nâng cao:** Đọc và ghi bản vẽ CAD DXF nâng cao, bảo toàn và trích xuất hoàn chỉnh **Block Attributes** cùng **XData** (sử dụng thư viện `ezdxf`).
- **Chuyển mã Font:** Tự động phát hiện và hỏi chuyển đổi font chữ tiếng Việt từ `TCVN3` / `VNI` sang `Unicode` chuẩn khi nhập dữ liệu.

### 📊 Báo cáo & Thống kê
- **Xuất Excel Chuẩn Thông tư:** Tự động trích xuất thông tin không gian và thuộc tính thửa đất, xuất ra biểu mẫu Excel chuẩn Thông tư `10/2024/TT-BTNMT` và `08/2024/TT-BTNMT` của Bộ TN&MT (sử dụng thư viện `openpyxl`).
- **Biểu đồ & Thống kê:** Phân tích cơ cấu loại đất, thống kê diện tích tự động.

### 🌐 WebGIS Tích hợp
- **WebGIS Demo & 3D:** Khởi tạo nhanh máy chủ WebGIS cục bộ để trực quan hóa dữ liệu không gian dưới dạng 2D/3D.
- **Đo đạc & Tìm kiếm:** Tích hợp công cụ đo đạc địa chí, tìm kiếm địa chỉ Nominatim Việt Nam, và reverse geocoding địa chỉ từ tọa độ.
- **Đồng bộ hóa:** WebGIS tự động trích xuất dữ liệu từ lớp polygon đang được chọn trên QGIS để hiển thị tức thì.

---

## 💻 Yêu cầu hệ thống

- **Hệ điều hành:** Windows 10/11, macOS, hoặc Linux.
- **Phần mềm:** QGIS phiên bản **4.0** trở lên.
- **Python:** Python 3.10+.
- **Thư viện phụ thuộc chính:** `shapely`, `ezdxf`, `openpyxl`. (Plugin sẽ tự động cài đặt các thư viện thiếu thông qua giao diện QGIS).

---

## 🛠️ Hướng dẫn Cài đặt

### Cách 1: Cài đặt từ file ZIP (Khuyên dùng)
1. Truy cập trang [Releases](https://github.com/seaflower205/vnu2f_qlddk68/releases).
2. Tải về file `vnu2f_qlddk68.zip` của phiên bản mới nhất.
3. Mở phần mềm QGIS.
4. Trên thanh menu, chọn **Plugins** -> **Manage and Install Plugins...**
5. Chuyển sang tab **Install from ZIP**, chọn đường dẫn tới file `vnu2f_qlddk68.zip` vừa tải.
6. Nhấn **Install Plugin** và khởi động lại QGIS nếu được yêu cầu.

### Cách 2: Cài đặt thủ công cho Nhà phát triển (Developer)
1. Clone kho lưu trữ này về thư mục plugins của QGIS:
   ```bash
   # Windows (Đường dẫn thường gặp)
   cd %APPDATA%\QGIS\QGIS3\profiles\default\python\plugins
   git clone https://github.com/seaflower205/vnu2f_qlddk68.git
   ```
2. Khởi động lại QGIS và bật plugin `VNU2F QLDDK68` trong Plugin Manager.

---

## 📖 Hướng dẫn sử dụng nhanh

1. **Thanh công cụ (Toolbar):** Sau khi cài đặt, bạn sẽ thấy các biểu tượng công cụ của plugin xuất hiện trên thanh công cụ QGIS.
2. **Thanh Menu:** Truy cập `Plugins` -> `VNU2F QLDDK68` để mở bảng điều khiển chính.
3. Các module được chia tab rõ ràng:
   - **Cơ sở dữ liệu / Import:** Quản lý nhập file CAD, SHP.
   - **Công cụ VN-2000:** Xử lý chuyển hệ tọa độ, chuyển đổi font.
   - **Biên tập hình học:** Bắt lỗi topology, dọn dẹp layer thừa.
   - **Báo cáo:** Thiết lập và kết xuất Excel biểu mẫu địa chính.
   - **WebGIS:** Khởi chạy server và mở ứng dụng WebGIS ngay trên trình duyệt.

---

## 👨‍💻 Phát triển & Đóng góp

Dự án là mã nguồn mở, chúng tôi luôn hoan nghênh các đóng góp từ cộng đồng (Issues, Pull Requests).

Để đóng gói bản release tự động:
Dự án sử dụng GitHub Actions, bạn có thể trigger workflow **"Package and Release Plugin"** tại tab [Actions](https://github.com/seaflower205/vnu2f_qlddk68/actions) để tự động xuất ra file `.zip` phát hành.

---

## 📜 Giấy phép (License)

Dự án được phân phối dưới giấy phép [GNU GPLv3](https://opensource.org/licenses/GPL-3.0). Mọi sửa đổi và phân phối lại mã nguồn phải tuân thủ điều khoản của giấy phép này.

---
<div align="center">
  <i>Được phát triển với niềm đam mê GIS bởi cộng đồng VNU2F.</i>
</div>
