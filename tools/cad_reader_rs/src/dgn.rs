use std::fs::File;
use std::io::Read;
use std::path::Path;
use cfb::CompoundFile;
use flate2::read::ZlibDecoder;
use serde::{Serialize, Deserialize};
use crate::pol::tcvn3_to_unicode;

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct DgnElement {
    pub el_type: u8,
    pub level_id: u32,
    pub element_id: u32,
    pub geom_type: String, // "point", "line", "polygon"
    pub entity_type: String, // "TEXT", "LINE", "LINESTRING", "SHAPE"
    pub coords: Vec<(f64, f64)>,
    pub text_value: Option<String>,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct DgnDocument {
    pub scale: f64,
    pub go_x: f64,
    pub go_y: f64,
    pub go_z: f64,
    pub elements: Vec<DgnElement>,
}

// Hàm giải nén zlib stream từ mảng byte thô.
// File DGN lưu các luồng dữ liệu bị nén bằng zlib tại một byte offset thay đổi (thường bắt đầu bằng 0x78).
fn decompress_zlib_stream(raw: &[u8]) -> Option<Vec<u8>> {
    let limit = std::cmp::min(64, raw.len().saturating_sub(2));
    for offset in 0..limit {
        if raw[offset] == 0x78 && matches!(raw[offset + 1], 0x01 | 0x5E | 0x9C | 0xDA) {
            let mut decoder = ZlibDecoder::new(&raw[offset..]);
            let mut decompressed = Vec::new();
            if decoder.read_to_end(&mut decompressed).is_ok() {
                return Some(decompressed);
            }
        }
    }
    None
}

/// Đọc và phân tích bản vẽ DGN V8
pub fn parse_dgn_file<P: AsRef<Path>>(path: P) -> Result<DgnDocument, Box<dyn std::error::Error>> {
    // 1. Mở OLE container (Compound File Binary Format)
    let file = File::open(&path)?;
    let mut comp = CompoundFile::open(file)?;

    // 2. Tìm Model Header stream để đọc thông số tỷ lệ (scale) và gốc tọa độ (global origin)
    let mut scale = 1000.0;
    let mut go_x = -500_000_000.0;
    let mut go_y = -1_000_000_000.0;
    let mut go_z = 0.0;

    let mut mh_stream_name = None;
    for entry in comp.walk() {
        if entry.is_stream() {
            let path_str = entry.path().to_string_lossy()
                .replace('\\', "/")
                .trim_start_matches('/')
                .replace('/', "_");
            if path_str.starts_with("Dgn-Md_#") && path_str.ends_with("_Dgn~Mh") {
                mh_stream_name = Some(entry.path().to_path_buf());
                break;
            }
        }
    }

    if let Some(mh_path) = mh_stream_name {
        let mut raw_mh = Vec::new();
        comp.open_stream(&mh_path)?.read_to_end(&mut raw_mh)?;
        
        let decompressed_mh = decompress_zlib_stream(&raw_mh).unwrap_or(raw_mh);
        
        if decompressed_mh.len() >= 4236 {
            let mut scale_buf = [0u8; 8];
            scale_buf.copy_from_slice(&decompressed_mh[4196..4204]);
            let d_scale = f64::from_le_bytes(scale_buf);
            if d_scale > 0.0 {
                scale = d_scale;
            }

            let mut go_x_buf = [0u8; 8];
            go_x_buf.copy_from_slice(&decompressed_mh[4212..4220]);
            go_x = f64::from_le_bytes(go_x_buf);

            let mut go_y_buf = [0u8; 8];
            go_y_buf.copy_from_slice(&decompressed_mh[4220..4228]);
            go_y = f64::from_le_bytes(go_y_buf);

            let mut go_z_buf = [0u8; 8];
            go_z_buf.copy_from_slice(&decompressed_mh[4228..4236]);
            go_z = f64::from_le_bytes(go_z_buf);
        }
    }

    // 3. Tìm và đọc toàn bộ các Graphic stream chứa hình học
    let mut g_streams = Vec::new();
    for entry in comp.walk() {
        if entry.is_stream() {
            let path_str = entry.path().to_string_lossy()
                .replace('\\', "/")
                .trim_start_matches('/')
                .replace('/', "_");
            if path_str.starts_with("Dgn-Md_#") && path_str.contains("_Dgn^G_") {
                g_streams.push(entry.path().to_path_buf());
            }
        }
    }

    let mut elements = Vec::new();

    for g_path in g_streams {
        let mut raw_g = Vec::new();
        if comp.open_stream(&g_path)?.read_to_end(&mut raw_g).is_err() {
            continue;
        }

        let decompressed_g = decompress_zlib_stream(&raw_g).unwrap_or(raw_g);
        let total_size = decompressed_g.len();
        let mut offset = 4; // Bỏ qua 4 byte tiền tố không dùng

        while offset + 8 <= total_size {
            let mut flags_buf = [0u8; 4];
            flags_buf.copy_from_slice(&decompressed_g[offset..offset+4]);
            let type_flags = u32::from_le_bytes(flags_buf);
            let el_type = (type_flags & 0xFF) as u8;

            let mut len_buf = [0u8; 4];
            len_buf.copy_from_slice(&decompressed_g[offset+4..offset+8]);
            let length_words = u32::from_le_bytes(len_buf);
            let el_size = 4 + (length_words as usize) * 2;

            if el_size < 8 {
                offset += 4;
                continue;
            }

            if offset + el_size > total_size {
                break;
            }

            let el_data = &decompressed_g[offset .. offset + el_size];

            let mut level_id = 0;
            let mut element_id = 0;
            if el_data.len() >= 20 {
                let mut lvl_buf = [0u8; 4];
                lvl_buf.copy_from_slice(&el_data[12..16]);
                level_id = u32::from_le_bytes(lvl_buf);

                let mut el_id_buf = [0u8; 4];
                el_id_buf.copy_from_slice(&el_data[16..20]);
                element_id = u32::from_le_bytes(el_id_buf);
            }

            match el_type {
                17 => { // Text element
                    if el_data.len() >= 168 {
                        let mut x_buf = [0u8; 8];
                        x_buf.copy_from_slice(&el_data[152..160]);
                        let dgn_x = f64::from_le_bytes(x_buf);

                        let mut y_buf = [0u8; 8];
                        y_buf.copy_from_slice(&el_data[160..168]);
                        let dgn_y = f64::from_le_bytes(y_buf);

                        let real_x = (dgn_x - go_x) / scale;
                        let real_y = (dgn_y - go_y) / scale;

                        let mut text_len_buf = [0u8; 4];
                        text_len_buf.copy_from_slice(&el_data[110..114]);
                        let text_len = u32::from_le_bytes(text_len_buf) as usize;

                        if el_data.len() >= 170 + text_len {
                            let text_bytes = &el_data[170 .. 170 + text_len];
                            let raw_text: String = text_bytes.iter().map(|&b| b as char).collect();
                            let unicode_text = tcvn3_to_unicode(&raw_text).trim().to_string();

                            elements.push(DgnElement {
                                el_type,
                                level_id,
                                element_id,
                                geom_type: "point".to_string(),
                                entity_type: "TEXT".to_string(),
                                coords: vec![(real_x, real_y)],
                                text_value: Some(unicode_text),
                            });
                        }
                    }
                }
                3 => { // Line
                    if el_data.len() >= 136 {
                        let mut x1_buf = [0u8; 8];
                        x1_buf.copy_from_slice(&el_data[104..112]);
                        let x1 = f64::from_le_bytes(x1_buf);

                        let mut y1_buf = [0u8; 8];
                        y1_buf.copy_from_slice(&el_data[112..120]);
                        let y1 = f64::from_le_bytes(y1_buf);

                        let mut x2_buf = [0u8; 8];
                        x2_buf.copy_from_slice(&el_data[120..128]);
                        let x2 = f64::from_le_bytes(x2_buf);

                        let mut y2_buf = [0u8; 8];
                        y2_buf.copy_from_slice(&el_data[128..136]);
                        let y2 = f64::from_le_bytes(y2_buf);

                        elements.push(DgnElement {
                            el_type,
                            level_id,
                            element_id,
                            geom_type: "line".to_string(),
                            entity_type: "LINE".to_string(),
                            coords: vec![
                                ((x1 - go_x) / scale, (y1 - go_y) / scale),
                                ((x2 - go_x) / scale, (y2 - go_y) / scale),
                            ],
                            text_value: None,
                        });
                    }
                }
                4 => { // LineString
                    if el_data.len() >= 108 {
                        let mut v_count_buf = [0u8; 4];
                        v_count_buf.copy_from_slice(&el_data[104..108]);
                        let v_count = u32::from_le_bytes(v_count_buf) as usize;

                        if v_count > 0 && el_data.len() >= 112 + v_count * 16 {
                            let mut coords = Vec::new();
                            for i in 0..v_count {
                                let start = 112 + i * 16;
                                let mut x_buf = [0u8; 8];
                                x_buf.copy_from_slice(&el_data[start..start+8]);
                                let x = f64::from_le_bytes(x_buf);

                                let mut y_buf = [0u8; 8];
                                y_buf.copy_from_slice(&el_data[start+8..start+16]);
                                let y = f64::from_le_bytes(y_buf);

                                coords.push(((x - go_x) / scale, (y - go_y) / scale));
                            }
                            elements.push(DgnElement {
                                el_type,
                                level_id,
                                element_id,
                                geom_type: "line".to_string(),
                                entity_type: "LINESTRING".to_string(),
                                coords,
                                text_value: None,
                            });
                        }
                    }
                }
                6 => { // Shape (Polygon)
                    if el_data.len() >= 108 {
                        let mut v_count_buf = [0u8; 4];
                        v_count_buf.copy_from_slice(&el_data[104..108]);
                        let v_count = u32::from_le_bytes(v_count_buf) as usize;

                        if v_count > 0 && el_data.len() >= 112 + v_count * 16 {
                            let mut coords = Vec::new();
                            for i in 0..v_count {
                                let start = 112 + i * 16;
                                let mut x_buf = [0u8; 8];
                                x_buf.copy_from_slice(&el_data[start..start+8]);
                                let x = f64::from_le_bytes(x_buf);

                                let mut y_buf = [0u8; 8];
                                y_buf.copy_from_slice(&el_data[start+8..start+16]);
                                let y = f64::from_le_bytes(y_buf);

                                coords.push(((x - go_x) / scale, (y - go_y) / scale));
                            }
                            if !coords.is_empty() && coords.first() != coords.last() {
                                coords.push(coords[0]);
                            }

                            elements.push(DgnElement {
                                el_type,
                                level_id,
                                element_id,
                                geom_type: "polygon".to_string(),
                                entity_type: "SHAPE".to_string(),
                                coords,
                                text_value: None,
                            });
                        }
                    }
                }
                _ => {}
            }

            offset += el_size;
        }
    }

    Ok(DgnDocument {
        scale,
        go_x,
        go_y,
        go_z,
        elements,
    })
}
