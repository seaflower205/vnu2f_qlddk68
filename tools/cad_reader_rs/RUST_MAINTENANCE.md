# Hướng Dẫn Bảo Trì Động Cơ Rust (Rust Core Engine Maintenance Guide)

Tài liệu này cung cấp toàn bộ chỉ dẫn, cấu trúc nhị phân và quy trình biên dịch/bảo trì cho công cụ dòng lệnh **cad_reader** (được viết bằng Rust). Bộ công cụ này đóng vai trò xử lý các tác vụ hiệu năng cao cho QGIS Plugin `vnu2f_qlddk68`.

---

## 1. Cấu Trúc Mã Nguồn (Project Structure)

Dự án Rust nằm tại thư mục `tools/cad_reader_rs/` và được tổ chức như sau:

- **`src/main.rs`**: Điểm khởi đầu của chương trình. Chịu trách nhiệm phân phối lệnh phụ (Subcommands) và xử lý tương thích ngược khi nhận đầu vào là các file `.dwg/.dxf/.dgn/.pol/.gtp` trực tiếp.
- **`src/dgn.rs`**: Giải mã định dạng tệp bản vẽ nhị phân MicroStation DGN V8 (đọc OLE, giải nén zlib, phân tích các Element Type 3, 4, 6, 17 và quy đổi tọa độ thực tế).
- **`src/gtp.rs`**: Giải mã tệp thuộc tính gCadas `.gtp` bằng thuật toán XOR mảng byte (slice XOR) tốc độ cao.
- **`src/pol.rs`**: Phân tích tệp hồ sơ nhị phân FAMIS `.pol` và tích hợp bộ dịch ký tự TCVN3 (ABC) sang Unicode tiếng Việt.
- **`src/topology.rs`**: Xử lý gán nhãn thuộc tính thửa đất từ điểm đo không gian thông qua cây R-Tree tối ưu hóa ($O(N \log N)$).

---

## 2. Sơ Đồ Định Dạng Nhị Phân & Byte Offset

### 2.1 Cấu trúc tệp DGN V8 (Compound File Binary Format)
Tệp DGN V8 thực chất là một container OLE chứa nhiều stream dữ liệu nhị phân. Các stream chính bao gồm:
- **`_Dgn~Mh` (Model Header)**: Lưu trữ các tham số tỷ lệ và gốc tọa độ.
  - Vị trí `scale` (f64 - 8 bytes): Offset **4196** (đọc từ stream giải nén).
  - Vị trí `go_x` (f64 - 8 bytes): Offset **4212**.
  - Vị trí `go_y` (f64 - 8 bytes): Offset **4220**.
  - Vị trí `go_z` (f64 - 8 bytes): Offset **4228**.
- **`_Dgn^G_...` (Graphic Data)**: Chứa danh sách các đối tượng hình học. Các đối tượng được nén bằng thuật toán zlib Deflate (signature bắt đầu bằng `0x78`).
  - Đầu mỗi element chứa 4 byte `type_flags` (`el_type = type_flags & 0xFF`) và 4 byte `length_words` (`el_size = 4 + length_words * 2`).
  - Level ID nằm tại offset **12**, Element ID nằm tại offset **16**.
  - **Type 3 (Line)**: Tọa độ bắt đầu (X, Y) ở offset **104, 112**; Tọa độ kết thúc ở offset **120, 128**.
  - **Type 4 (LineString)**: Số lượng đỉnh (u32) ở offset **104**; Danh sách tọa độ (mỗi điểm 16 bytes: X f64, Y f64) bắt đầu từ offset **112**.
  - **Type 6 (Shape/Polygon)**: Tương tự như LineString nhưng tự động khép kín điểm đầu và điểm cuối để dựng vùng.
  - **Type 17 (Text)**: Tọa độ điểm chèn ở offset **152, 160**; Độ dài chuỗi (u32) ở offset **110**; Byte dữ liệu ký tự bắt đầu từ offset **170**.

### 2.2 Cấu trúc tệp nhị phân .pol (FAMIS)
Tệp `.pol` chứa danh sách bản ghi có kích thước biến đổi: `Header (76 bytes) + các bản ghi`.
- **Header**:
  - Offset **0-32**: Tên tệp CAD liên kết.
  - Offset **40** (u32): Số lượng bản ghi khai báo.
  - Offset **44** (u32): Số hiệu tờ bản đồ.
  - Offset **52-64**: Tên Layer.
- **Records (Mỗi bản ghi có độ dài: 248 + vertex_count * 16 bytes)**:
  - Offset **0** (u32): ID tham chiếu.
  - Offset **4** (u32): Mã loại đất.
  - Offset **8** (u32): Số thứ tự thửa đất.
  - Offset **24** (6 x u32): Các giá trị tóm tắt diện tích/pháp lý (cần chia cho 1000 để lấy giá trị thực).
  - Offset **48** (f64): Diện tích thửa đất.
  - Offset **108-156** (48 bytes): Họ tên chủ sử dụng (mã TCVN3).
  - Offset **156-240** (84 bytes): Địa chỉ thửa đất (mã TCVN3).
  - Offset **240** (u32): Số lượng đỉnh của thửa đất (`vertex_count`).
  - Offset **248** trở đi: Danh sách các đỉnh (X f64, Y f64).

---

## 3. Quy Trình Biên Dịch & Đóng Gói (Build & Deploy)

### 3.1 Cài đặt môi trường
Đảm bảo máy tính đã cài đặt Rust toolchain (thông qua `rustup`). Vì QGIS trên Windows thường sử dụng MinGW GCC, dự án này được thiết lập ghi đè để biên dịch bằng GNU toolchain để tránh phụ thuộc vào Visual Studio C++.

Lệnh chuyển đổi môi trường (đã được cấu hình tự động trong thư mục):
```bash
rustup target add x86_64-pc-windows-gnu
rustup override set stable-x86_64-pc-windows-gnu
```

### 3.2 Biên dịch tệp phát hành (Release Build)
Để biên dịch chương trình tối ưu hóa cao nhất:
```bash
cargo build --release
```
Sau khi build hoàn tất, tệp thực thi nằm tại:
`tools/cad_reader_rs/target/release/cad_reader.exe`

### 3.3 Đóng gói vào plugin
Để tích hợp vào QGIS plugin chạy runtime, copy file `cad_reader.exe` vào thư mục nhị phân của plugin:
`modules/cadastral_importer/bin/cad_reader.exe`

*(Lưu ý: Công cụ đóng gói tự động `tools/package_plugin.py` sẽ tự động quét và đưa tệp này vào gói zip nếu nó tồn tại).*

---

## 4. Cơ Chế Fallback An Toàn (Python Fallback Design)

Hệ thống được thiết kế theo nguyên lý **Chịu Lỗi Chủ Động (Fail-Safe)**:
1. Khi thực hiện import DGN/GTP hoặc xử lý topo gán nhãn, mã Python trong QGIS sẽ thử gọi CLI Rust (`cad_reader.exe`) trước tiên.
2. Nếu CLI Rust chạy thành công, QGIS sẽ đọc ngay kết quả dạng GeoJSON/SQLite cực nhanh.
3. Nếu CLI Rust thất bại (do thiếu file exe, xung đột quyền hệ thống, hoặc file đầu vào bị hỏng cấu trúc đặc biệt), Python sẽ **ghi nhận cảnh báo vào QGIS Log** và **tự động chuyển hướng xử lý sang các mô-đun Python thuần** (`dgn_reader.py`, `gtp_reader.py`, `polygonizer.py`).
4. Cơ chế này đảm bảo người dùng cuối luôn hoàn thành công việc nhập dữ liệu mà không bao giờ bị đứng luồng hoặc crash ứng dụng QGIS đột ngột.

---
*Tài liệu này là một phần của kiến trúc cốt lõi QGIS Plugin vnu2f_qlddk68.*
