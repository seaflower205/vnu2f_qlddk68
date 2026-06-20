use std::collections::HashMap;
use std::fs::File;
use std::io::{Read, Write};
use std::path::Path;

const PAGE_SIZE: usize = 4096;

/// Giải mã file GTP thành SQLite bằng phép toán XOR theo trang (4096 bytes).
/// Hàm này được tối ưu hóa hiệu năng và ghi chú chi tiết sơ đồ nhị phân.
pub fn decode_gtp<P1: AsRef<Path>, P2: AsRef<Path>>(
    input_path: P1,
    output_path: P2,
) -> Result<(), Box<dyn std::error::Error>> {
    // 1. Đọc toàn bộ nội dung tệp tin đầu vào vào bộ nhớ
    let mut file = File::open(input_path)?;
    let mut data = Vec::new();
    file.read_to_end(&mut data)?;

    let len = data.len();
    if len == 0 || len % PAGE_SIZE != 0 {
        return Err(format!(
            "Kích thước file gtp không hợp lệ: {} bytes (phải là bội số của {}).",
            len, PAGE_SIZE
        )
        .into());
    }

    // 2. Tìm trang lặp lại nhiều nhất (Mask Page)
    // Tệp GTP bị obfuscate bằng cách XOR với một trang mặt nạ cố định.
    // Vì SQLite có nhiều trang trống (chỉ chứa byte 0), các trang này sau khi XOR
    // sẽ giống hệt trang mặt nạ ban đầu. Do đó, trang xuất hiện nhiều nhất chính là Mask Page.
    let num_pages = len / PAGE_SIZE;
    let mut page_counts = HashMap::new();
    for i in 0..num_pages {
        let page = &data[i * PAGE_SIZE..(i + 1) * PAGE_SIZE];
        *page_counts.entry(page).or_insert(0) += 1;
    }

    // Lấy trang có tần suất xuất hiện cao nhất
    let (&mask_page, &count) = page_counts
        .iter()
        .max_by_key(|&(_, count)| count)
        .ok_or("Không tìm thấy trang mặt nạ hợp lệ trong file GTP.")?;

    if count < 2 {
        return Err("File GTP không chứa trang mặt nạ (có thể file không được mã hóa hoặc bị hỏng).".into());
    }

    // 3. Khởi tạo mảng mẫu của một trang SQLite trống (Leaf Node)
    // SQLite định nghĩa trang trống (leaf node) có byte 0x0D ở offset 0 và 0x10 ở offset 5.
    // Các byte khác bằng 0x00. Chúng ta cần XOR ngược với cấu trúc này để khôi phục chính xác.
    let mut empty_sqlite_leaf = [0u8; PAGE_SIZE];
    empty_sqlite_leaf[0] = 0x0D;
    empty_sqlite_leaf[5] = 0x10;

    // 4. Thực hiện giải mã XOR tối ưu hóa
    // Công thức khôi phục: Byte_SQLite = Byte_Mã_Hóa ^ Byte_Mặt_Nạ ^ Byte_Mẫu_Trống_SQLite
    let mut decoded = vec![0u8; len];
    for i in 0..num_pages {
        let offset = i * PAGE_SIZE;
        let page = &data[offset..offset + PAGE_SIZE];
        let decoded_page = &mut decoded[offset..offset + PAGE_SIZE];
        
        for j in 0..PAGE_SIZE {
            decoded_page[j] = page[j] ^ mask_page[j] ^ empty_sqlite_leaf[j];
        }
    }

    // 5. Kiểm tra tính hợp lệ của Header SQLite sau khi giải mã
    // Tệp SQLite hợp lệ phải bắt đầu bằng chuỗi "SQLite format 3\0"
    if !decoded.starts_with(b"SQLite format 3\0") {
        return Err("Giải mã thất bại: Kết quả không có Header của SQLite format 3.".into());
    }

    // 6. Ghi kết quả ra tệp tin SQLite đích
    let mut out_file = File::create(output_path)?;
    out_file.write_all(&decoded)?;

    Ok(())
}
