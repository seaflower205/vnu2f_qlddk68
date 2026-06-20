use std::fs::File;
use std::io::Read;
use std::path::Path;
use serde::{Serialize, Deserialize};

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct PolRecord {
    pub index: usize,
    pub reference_id: u32,
    pub code: u32,
    pub parcel_number: u32,
    pub area: f64,
    pub owner: String,
    pub address: String,
    pub vertex_count: u32,
    pub summary_values: [f64; 6],
    pub vertices: Vec<(f64, f64)>,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct PolSummary {
    pub source_path: String,
    pub header_path: String,
    pub record_count_header: u32,
    pub map_sheet: u32,
    pub layer_text: String,
    pub records: Vec<PolRecord>,
}

// Hàm chuyển đổi TCVN3 (ABC) sang Unicode tiếng Việt.
// Bảng đối chiếu được xây dựng dựa trên danh sách ký tự chuẩn của Việt Nam.
pub fn tcvn3_to_unicode(input: &str) -> String {
    // Để giữ mã nguồn tinh gọn và dễ bảo trì, chúng ta ánh xạ trực tiếp các ký tự đặc biệt TCVN3
    // sang ký tự Unicode tương ứng.
    let mut result = String::new();
    let chars: Vec<char> = input.chars().collect();
    let mut i = 0;
    while i < chars.len() {
        // Ánh xạ 2 ký tự (in hoa có dấu phụ)
        if i + 1 < chars.len() {
            let ch1 = chars[i];
            let ch2 = chars[i + 1];
            let opt = match (ch1, ch2) {
                ('\u{00A2}', '\u{00CA}') => Some('Ấ'),
                ('\u{00A2}', '\u{00C7}') => Some('Ầ'),
                ('\u{00A2}', '\u{00C8}') => Some('Ẩ'),
                ('\u{00A2}', '\u{00C9}') => Some('Ẫ'),
                ('\u{00A2}', '\u{00CB}') => Some('Ậ'),
                ('\u{00A1}', '\u{00BE}') => Some('Ắ'),
                ('\u{00A1}', '\u{00BB}') => Some('Ằ'),
                ('\u{00A1}', '\u{00BC}') => Some('Ẳ'),
                ('\u{00A1}', '\u{00BD}') => Some('Ẵ'),
                ('\u{00A1}', '\u{00C6}') => Some('Ặ'),
                ('\u{00A3}', '\u{00D5}') => Some('Ế'),
                ('\u{00A3}', '\u{00D2}') => Some('Ề'),
                ('\u{00A3}', '\u{00D3}') => Some('Ể'),
                ('\u{00A3}', '\u{00D4}') => Some('Ễ'),
                ('\u{00A3}', '\u{00D6}') => Some('Ệ'),
                ('\u{00A4}', '\u{00E8}') => Some('Ố'),
                ('\u{00A4}', '\u{00E5}') => Some('Ồ'),
                ('\u{00A4}', '\u{00E6}') => Some('Ổ'),
                ('\u{00A4}', '\u{00E7}') => Some('Ỗ'),
                ('\u{00A4}', '\u{00E9}') => Some('Ộ'),
                ('\u{00A5}', '\u{00ED}') => Some('Ớ'),
                ('\u{00A5}', '\u{00EA}') => Some('Ờ'),
                ('\u{00A5}', '\u{00EB}') => Some('Ở'),
                ('\u{00A5}', '\u{00EC}') => Some('Ỡ'),
                ('\u{00A5}', '\u{00EE}') => Some('Ợ'),
                ('\u{00A6}', '\u{00F8}') => Some('Ứ'),
                ('\u{00A6}', '\u{00F5}') => Some('Ừ'),
                ('\u{00A6}', '\u{00F6}') => Some('Ử'),
                ('\u{00A6}', '\u{00F7}') => Some('Ữ'),
                ('\u{00A6}', '\u{00F9}') => Some('Ự'),
                _ => None,
            };
            if let Some(unicode_ch) = opt {
                result.push(unicode_ch);
                i += 2;
                continue;
            }
        }

        // Ánh xạ 1 ký tự
        let ch = chars[i];
        let mapped = match ch {
            '\u{00B5}' => 'à',
            '\u{00B8}' => 'á',
            '\u{00A2}' => 'Â', // Trường hợp đứng riêng
            '\u{00B7}' => 'ã',
            '\u{00CC}' => 'è',
            '\u{00D0}' => 'é',
            '\u{00A3}' => 'Ê',
            '\u{00D7}' => 'ì',
            '\u{00DD}' => 'í',
            '\u{00DF}' => 'ò',
            '\u{00E3}' => 'ó',
            '\u{00A4}' => 'Ô',
            '\u{00E2}' => 'õ',
            '\u{00EF}' => 'ù',
            '\u{00F3}' => 'ú',
            '\u{00FD}' => 'ý',
            '\u{00A9}' => 'â',
            '\u{00AA}' => 'ê',
            '\u{00AB}' => 'ô',
            '\u{00A1}' => 'Ă',
            '\u{00A8}' => 'ă',
            '\u{00A7}' => 'Đ',
            '\u{00AE}' => 'đ',
            '\u{00DC}' => 'ĩ',
            '\u{00F2}' => 'ũ',
            '\u{00AC}' => 'ơ',
            '\u{00AD}' => 'ư',
            '\u{00B9}' => 'ạ',
            '\u{00B6}' => 'ả',
            '\u{00CA}' => 'ấ',
            '\u{00C7}' => 'ầ',
            '\u{00C8}' => 'ẩ',
            '\u{00C9}' => 'ẫ',
            '\u{00CB}' => 'ậ',
            '\u{00BE}' => 'ắ',
            '\u{00BB}' => 'ằ',
            '\u{00BC}' => 'ẳ',
            '\u{00BD}' => 'ẵ',
            '\u{00C6}' => 'ặ',
            '\u{00D1}' => 'ẹ',
            '\u{00CE}' => 'ẻ',
            '\u{00CF}' => 'ẽ',
            '\u{00D5}' => 'ế',
            '\u{00D2}' => 'ề',
            '\u{00D3}' => 'ể',
            '\u{00D4}' => 'ễ',
            '\u{00D6}' => 'ệ',
            '\u{00D8}' => 'ỉ',
            '\u{00DE}' => 'ị',
            '\u{00E4}' => 'ọ',
            '\u{00E1}' => 'ỏ',
            '\u{00E8}' => 'ố',
            '\u{00E5}' => 'ồ',
            '\u{00E6}' => 'ổ',
            '\u{00E7}' => 'ỗ',
            '\u{00E9}' => 'ộ',
            '\u{00ED}' => 'ớ',
            '\u{00EA}' => 'ờ',
            '\u{00EB}' => 'ở',
            '\u{00EC}' => 'ỡ',
            '\u{00EE}' => 'ợ',
            '\u{00F4}' => 'ụ',
            '\u{00F1}' => 'ủ',
            '\u{00F8}' => 'ứ',
            '\u{00F5}' => 'ừ',
            '\u{00F6}' => 'ử',
            '\u{00F7}' => 'ữ',
            '\u{00F9}' => 'ự',
            '\u{00FA}' => 'ỳ',
            '\u{00FE}' => 'ỵ',
            '\u{00FB}' => 'ỷ',
            '\u{00FC}' => 'ỹ',
            _ => ch,
        };
        result.push(mapped);
        i += 1;
    }
    result
}

// Giải mã chuỗi bytes TCVN3 thành String Unicode
fn decode_tcvn3_field(raw: &[u8]) -> String {
    let chunks: Vec<&[u8]> = raw.split(|&b| b == 0).filter(|c| !c.is_empty()).collect();
    if chunks.is_empty() {
        return String::new();
    }
    let longest_chunk = chunks.iter().max_by_key(|c| c.len()).unwrap();
    let s: String = longest_chunk.iter().map(|&b| b as char).collect();
    tcvn3_to_unicode(&s).trim().to_string()
}

/// Đọc và phân tích cú pháp tệp nhị phân .pol
pub fn parse_pol_file<P: AsRef<Path>>(path: P) -> Result<PolSummary, Box<dyn std::error::Error>> {
    let mut file = File::open(&path)?;
    let mut data = Vec::new();
    file.read_to_end(&mut data)?;

    if data.len() < 76 {
        return Err("Kích thước tệp .pol quá nhỏ (nhỏ hơn 76 bytes header).".into());
    }

    // Đọc thông tin header
    let header_path_bytes = &data[0..32];
    let header_path = String::from_utf8_lossy(
        header_path_bytes.split(|&b| b == 0).next().unwrap_or(b"")
    ).into_owned();

    let mut count_buf = [0u8; 4];
    count_buf.copy_from_slice(&data[40..44]);
    let record_count_header = u32::from_le_bytes(count_buf);

    let mut sheet_buf = [0u8; 4];
    sheet_buf.copy_from_slice(&data[44..48]);
    let map_sheet = u32::from_le_bytes(sheet_buf);

    let layer_text_bytes = &data[52..64];
    let layer_text = String::from_utf8_lossy(
        layer_text_bytes.split(|&b| b == 0).next().unwrap_or(b"")
    ).into_owned();

    let mut records = Vec::new();
    let mut offset = 76;
    let data_len = data.len();

    while offset + 248 <= data_len {
        let rec_data = &data[offset..];
        
        let mut id_buf = [0u8; 4];
        id_buf.copy_from_slice(&rec_data[0..4]);
        let reference_id = u32::from_le_bytes(id_buf);

        let mut code_buf = [0u8; 4];
        code_buf.copy_from_slice(&rec_data[4..8]);
        let code = u32::from_le_bytes(code_buf);

        let mut parcel_buf = [0u8; 4];
        parcel_buf.copy_from_slice(&rec_data[8..12]);
        let parcel_number = u32::from_le_bytes(parcel_buf);

        let mut summary_values = [0.0; 6];
        for k in 0..6 {
            let mut val_buf = [0u8; 4];
            let start = 24 + k * 4;
            val_buf.copy_from_slice(&rec_data[start..start+4]);
            summary_values[k] = (u32::from_le_bytes(val_buf) as f64) / 1000.0;
        }

        let mut area_buf = [0u8; 8];
        area_buf.copy_from_slice(&rec_data[48..56]);
        let area = f64::from_le_bytes(area_buf);

        let owner = decode_tcvn3_field(&rec_data[108..156]);
        let address = decode_tcvn3_field(&rec_data[156..240]);

        let mut v_count_buf = [0u8; 4];
        v_count_buf.copy_from_slice(&rec_data[240..244]);
        let vertex_count = u32::from_le_bytes(v_count_buf);

        if parcel_number > 100000 || area > 1e10 || vertex_count > 100000 {
            break;
        }

        let mut vertices = Vec::new();
        let vertex_offset = offset + 248;
        if vertex_offset + (vertex_count as usize) * 16 > data_len {
            break;
        }

        for k in 0..(vertex_count as usize) {
            let v_start = vertex_offset + k * 16;
            let mut vx_buf = [0u8; 8];
            vx_buf.copy_from_slice(&data[v_start..v_start+8]);
            let vx = f64::from_le_bytes(vx_buf);

            let mut vy_buf = [0u8; 8];
            vy_buf.copy_from_slice(&data[v_start+8..v_start+16]);
            let vy = f64::from_le_bytes(vy_buf);

            vertices.push((vx, vy));
        }

        records.push(PolRecord {
            index: records.len() + 1,
            reference_id,
            code,
            parcel_number,
            area,
            owner,
            address,
            vertex_count,
            summary_values,
            vertices,
        });

        offset += 248 + (vertex_count as usize) * 16;
    }

    Ok(PolSummary {
        source_path: path.as_ref().to_string_lossy().into_owned(),
        header_path,
        record_count_header,
        map_sheet,
        layer_text,
        records,
    })
}
