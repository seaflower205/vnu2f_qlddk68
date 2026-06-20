use serde::{Serialize, Deserialize};
use std::fs::File;
use std::path::Path;
use rstar::{RTree, RTreeObject, AABB};

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct InputLabel {
    pub x: f64,
    pub y: f64,
    pub attributes: serde_json::Value,
}

// Bọc cấu trúc nhãn để sử dụng với cây chỉ mục không gian R-Tree
struct LabelTreeObject {
    x: f64,
    y: f64,
    attributes: serde_json::Value,
}

impl RTreeObject for LabelTreeObject {
    type Envelope = AABB<[f64; 2]>;
    
    fn envelope(&self) -> Self::Envelope {
        AABB::from_point([self.x, self.y])
    }
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct InputPolygon {
    pub id: usize,
    pub shell: Vec<(f64, f64)>,
    pub holes: Vec<Vec<(f64, f64)>>,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct OutputParcel {
    pub id: usize,
    pub shell: Vec<(f64, f64)>,
    pub holes: Vec<Vec<(f64, f64)>>,
    pub attributes: serde_json::Value,
}

// Thuật toán Ray-Casting kiểm tra một điểm (x, y) có nằm trong chuỗi đa giác khép kín shell hay không.
// Không phụ thuộc thư viện hình học ngoài, rất dễ đọc và bảo trì.
fn point_in_polygon(x: f64, y: f64, shell: &[(f64, f64)]) -> bool {
    if shell.len() < 3 {
        return false;
    }
    let mut inside = false;
    let mut j = shell.len() - 1;
    for i in 0..shell.len() {
        if ((shell[i].1 > y) != (shell[j].1 > y))
            && (x < (shell[j].0 - shell[i].0) * (y - shell[i].1) / (shell[j].1 - shell[i].1) + shell[i].0)
        {
            inside = !inside;
        }
        j = i;
    }
    inside
}

// Kiểm tra điểm có thuộc polygon hay không (có xét tới các đảo/lỗ thủng bên trong)
fn point_in_polygon_with_holes(x: f64, y: f64, shell: &[(f64, f64)], holes: &[Vec<(f64, f64)>]) -> bool {
    if !point_in_polygon(x, y, shell) {
        return false;
    }
    for hole in holes {
        if point_in_polygon(x, y, hole) {
            return false; // Nằm vào phần lỗ thủng -> Không thuộc polygon
        }
    }
    true
}

// Công thức Gauss (Shoelace) tính diện tích đa giác phẳng
fn calculate_polygon_area(shell: &[(f64, f64)]) -> f64 {
    if shell.len() < 3 {
        return 0.0;
    }
    let mut area = 0.0;
    for i in 0..shell.len() {
        let j = (i + 1) % shell.len();
        area += shell[i].0 * shell[j].1;
        area -= shell[j].0 * shell[i].1;
    }
    (area / 2.0).abs()
}

// Tính trọng tâm đa giác (Centroid) dùng để tính khoảng cách ưu tiên khi thửa bị trùng nhãn
fn calculate_centroid(shell: &[(f64, f64)]) -> (f64, f64) {
    if shell.is_empty() {
        return (0.0, 0.0);
    }
    let mut cx = 0.0;
    let mut cy = 0.0;
    let mut area = 0.0;
    for i in 0..shell.len() {
        let j = (i + 1) % shell.len();
        let factor = shell[i].0 * shell[j].1 - shell[j].0 * shell[i].1;
        cx += (shell[i].0 + shell[j].0) * factor;
        cy += (shell[i].1 + shell[j].1) * factor;
        area += factor;
    }
    if area.abs() < 1e-9 {
        let mut sx = 0.0;
        let mut sy = 0.0;
        for p in shell {
            sx += p.0;
            sy += p.1;
        }
        return (sx / shell.len() as f64, sy / shell.len() as f64);
    }
    let factor = 3.0 * area;
    (cx / factor, cy / factor)
}

/// Thực hiện gán nhãn thuộc tính thửa đất từ nhãn điểm đo thông qua R-Tree tối ưu hóa.
pub fn run_topology_join<P1: AsRef<Path>, P2: AsRef<Path>, P3: AsRef<Path>>(
    polygons_path: P1,
    labels_path: P2,
    output_path: P3,
) -> Result<(), Box<dyn std::error::Error>> {
    // 1. Load danh sách đa giác và nhãn từ file JSON
    let poly_file = File::open(polygons_path)?;
    let polygons: Vec<InputPolygon> = serde_json::from_reader(poly_file)?;

    let label_file = File::open(labels_path)?;
    let labels: Vec<InputLabel> = serde_json::from_reader(label_file)?;

    // 2. Xây dựng chỉ mục không gian R-Tree cho các điểm nhãn
    let tree_objects: Vec<LabelTreeObject> = labels
        .into_iter()
        .map(|l| LabelTreeObject {
            x: l.x,
            y: l.y,
            attributes: l.attributes,
        })
        .collect();
    let rtree = RTree::bulk_load(tree_objects);

    // 3. Tiến hành gán nhãn cho từng đa giác
    let mut output_parcels = Vec::new();

    for poly in polygons {
        let shell = &poly.shell;
        if shell.is_empty() {
            continue;
        }

        // Tìm Bounding Box của đa giác hiện tại
        let mut min_x = f64::INFINITY;
        let mut max_x = f64::NEG_INFINITY;
        let mut min_y = f64::INFINITY;
        let mut max_y = f64::NEG_INFINITY;
        for &(x, y) in shell {
            if x < min_x { min_x = x; }
            if x > max_x { max_x = x; }
            if y < min_y { min_y = y; }
            if y > max_y { max_y = y; }
        }

        let envelope = AABB::from_corners([min_x, min_y], [max_x, max_y]);

        // Truy vấn R-Tree các điểm nhãn nằm trong Bounding Box (Độ phức tạp cực nhanh O(log N))
        let candidates = rtree.locate_in_envelope(&envelope);
        let mut matched_labels = Vec::new();

        // Lọc kỹ lại bằng thuật toán chứa điểm hình học thực tế (Point-in-Polygon)
        for cand in candidates {
            if point_in_polygon_with_holes(cand.x, cand.y, shell, &poly.holes) {
                matched_labels.push(cand);
            }
        }

        let poly_area = calculate_polygon_area(shell);
        let mut attrs = serde_json::Map::new();

        if matched_labels.len() == 1 {
            // Trường hợp tối ưu nhất: Chỉ có duy nhất 1 nhãn bên trong thửa đất
            if let Some(obj) = matched_labels[0].attributes.as_object() {
                attrs = obj.clone();
            }
        } else if matched_labels.len() > 1 {
            // Phát hiện trùng nhiều nhãn -> Lấy nhãn nằm gần trọng tâm của thửa đất nhất
            let (cx, cy) = calculate_centroid(shell);
            let mut sorted_labels = matched_labels;
            sorted_labels.sort_by(|a, b| {
                let dist_a = (a.x - cx).powi(2) + (a.y - cy).powi(2);
                let dist_b = (b.x - cx).powi(2) + (b.y - cy).powi(2);
                dist_a.partial_cmp(&dist_b).unwrap_or(std::cmp::Ordering::Equal)
            });

            if let Some(obj) = sorted_labels[0].attributes.as_object() {
                attrs = obj.clone();
            }
            attrs.insert(
                "_warning".to_string(),
                serde_json::Value::String(format!("Phát hiện trùng {} nhãn trong thửa", sorted_labels.len())),
            );
        } else {
            // Không tìm thấy nhãn nào trong thửa đất -> Gán giá trị mặc định
            attrs.insert("SOTHUA".to_string(), serde_json::Value::String("".to_string()));
            attrs.insert("SOTO".to_string(), serde_json::Value::String("".to_string()));
            attrs.insert("LOAIDAT".to_string(), serde_json::Value::String("Khac".to_string()));
            attrs.insert("TENCHU".to_string(), serde_json::Value::String("".to_string()));
            attrs.insert("DIENTICH".to_string(), serde_json::Value::Number(serde_json::Number::from_f64((poly_area * 10.0).round() / 10.0).unwrap()));
            attrs.insert(
                "_warning".to_string(),
                serde_json::Value::String("Thửa chưa gán nhãn".to_string()),
            );
        }

        // Ghi nhận diện tích tính toán thực tế từ hình học
        attrs.insert("DIENTICH_HP".to_string(), serde_json::Value::Number(serde_json::Number::from_f64((poly_area * 100.0).round() / 100.0).unwrap()));

        output_parcels.push(OutputParcel {
            id: poly.id,
            shell: poly.shell.clone(),
            holes: poly.holes.clone(),
            attributes: serde_json::Value::Object(attrs),
        });
    }

    // 4. Lưu kết quả ra file JSON đích
    let out_file = File::create(output_path)?;
    serde_json::to_writer_pretty(out_file, &output_parcels)?;

    Ok(())
}
