use std::env;
use std::fs::File;
use std::io::Write;
use std::path::Path;
use acadrust::DxfReader;
use acadrust::io::dwg::DwgReader;

mod dgn;
mod gtp;
mod pol;
mod topology;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        print_usage();
        std::process::exit(1);
    }

    let cmd_or_path = &args[1];

    // 1. Phân phối các lệnh CLI đặc thù (Subcommands)
    match cmd_or_path.as_str() {
        "dgn-parse" => {
            if args.len() < 3 {
                eprintln!("Sử dụng: cad_reader dgn-parse <input_dgn> [output_json]");
                std::process::exit(1);
            }
            let input = &args[2];
            let doc = dgn::parse_dgn_file(input)?;
            let json_str = serde_json::to_string_pretty(&doc)?;
            if args.len() > 3 {
                let output = &args[3];
                let mut file = File::create(output)?;
                file.write_all(json_str.as_bytes())?;
            } else {
                println!("{}", json_str);
            }
            return Ok(());
        }
        "gtp-decode" => {
            if args.len() < 4 {
                eprintln!("Sử dụng: cad_reader gtp-decode <input_gtp> <output_sqlite>");
                std::process::exit(1);
            }
            let input = &args[2];
            let output = &args[3];
            gtp::decode_gtp(input, output)?;
            eprintln!("Giải mã GTP thành công!");
            return Ok(());
        }
        "pol-parse" => {
            if args.len() < 3 {
                eprintln!("Sử dụng: cad_reader pol-parse <input_pol> [output_json]");
                std::process::exit(1);
            }
            let input = &args[2];
            let doc = pol::parse_pol_file(input)?;
            let json_str = serde_json::to_string_pretty(&doc)?;
            if args.len() > 3 {
                let output = &args[3];
                let mut file = File::create(output)?;
                file.write_all(json_str.as_bytes())?;
            } else {
                println!("{}", json_str);
            }
            return Ok(());
        }
        "topology-join" => {
            let mut poly_path = "";
            let mut label_path = "";
            let mut out_path = "";
            let mut i = 2;
            while i < args.len() {
                match args[i].as_str() {
                    "--polygons" => {
                        if i + 1 < args.len() {
                            poly_path = &args[i + 1];
                            i += 2;
                        } else {
                            return Err("Thiếu giá trị cho --polygons".into());
                        }
                    }
                    "--labels" => {
                        if i + 1 < args.len() {
                            label_path = &args[i + 1];
                            i += 2;
                        } else {
                            return Err("Thiếu giá trị cho --labels".into());
                        }
                    }
                    "--output" => {
                        if i + 1 < args.len() {
                            out_path = &args[i + 1];
                            i += 2;
                        } else {
                            return Err("Thiếu giá trị cho --output".into());
                        }
                    }
                    _ => {
                        return Err(format!("Tham số không hợp lệ: {}", args[i]).into());
                    }
                }
            }
            if poly_path.is_empty() || label_path.is_empty() || out_path.is_empty() {
                return Err("Yêu cầu đầy đủ tham số --polygons, --labels và --output".into());
            }
            topology::run_topology_join(poly_path, label_path, out_path)?;
            eprintln!("Gán thuộc tính topo thửa đất thành công!");
            return Ok(());
        }
        _ => {}
    }

    // 2. Chế độ tương thích ngược (Backward Compatibility / Fallback)
    // Nếu tham số thứ nhất là một đường dẫn file, tự động nhận diện phần mở rộng để xử lý.
    let path = Path::new(cmd_or_path);
    let ext = path.extension()
        .and_then(|s| s.to_str())
        .map(|s| s.to_lowercase());

    match ext.as_deref() {
        Some("dgn") => {
            eprintln!("Tự động nhận diện định dạng DGN...");
            let doc = dgn::parse_dgn_file(cmd_or_path)?;
            let json_str = serde_json::to_string(&doc)?;
            write_or_print_json(&args, &json_str)?;
        }
        Some("pol") => {
            eprintln!("Tự động nhận diện định dạng POL...");
            let doc = pol::parse_pol_file(cmd_or_path)?;
            let json_str = serde_json::to_string(&doc)?;
            write_or_print_json(&args, &json_str)?;
        }
        Some("gtp") => {
            eprintln!("Tự động nhận diện định dạng GTP...");
            if args.len() < 3 {
                return Err("Chế độ tự động giải mã GTP yêu cầu tệp đích đầu ra làm tham số thứ 2.".into());
            }
            gtp::decode_gtp(cmd_or_path, &args[2])?;
        }
        Some("dxf") => {
            eprintln!("Tự động nhận diện định dạng DXF...");
            let reader = DxfReader::from_file(cmd_or_path)?;
            let doc = reader.read()?;
            let json_str = serde_json::to_string(&doc)?;
            write_or_print_json(&args, &json_str)?;
        }
        Some("dwg") => {
            eprintln!("Tự động nhận diện định dạng DWG...");
            let mut reader = DwgReader::from_file(cmd_or_path)?;
            let doc = reader.read()?;
            let json_str = serde_json::to_string(&doc)?;
            write_or_print_json(&args, &json_str)?;
        }
        _ => {
            return Err(format!("Không hỗ trợ định dạng tệp tin: {:?}", ext).into());
        }
    }

    Ok(())
}

fn write_or_print_json(args: &[String], json_str: &str) -> Result<(), Box<dyn std::error::Error>> {
    if args.len() > 2 {
        let output_path = &args[2];
        eprintln!("Đang ghi kết quả JSON ra file: {}", output_path);
        let mut file = File::create(output_path)?;
        file.write_all(json_str.as_bytes())?;
    } else {
        println!("{}", json_str);
    }
    eprintln!("Thành công!");
    Ok(())
}

fn print_usage() {
    eprintln!("=== Bộ công cụ tối ưu hóa địa chính (Rust Core CLI) ===");
    eprintln!("Cách dùng phổ thông (Tự nhận diện định dạng):");
    eprintln!("  cad_reader <file_đầu_vào> [file_json_đầu_ra]");
    eprintln!("Các lệnh phụ chuyên dụng:");
    eprintln!("  cad_reader dgn-parse <input_dgn> [output_json]");
    eprintln!("  cad_reader gtp-decode <input_gtp> <output_sqlite>");
    eprintln!("  cad_reader pol-parse <input_pol> [output_json]");
    eprintln!("  cad_reader topology-join --polygons <poly_json> --labels <label_json> --output <out_json>");
}
