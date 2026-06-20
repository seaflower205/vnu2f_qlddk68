# -*- coding: utf-8 -*-
"""XML exchange data connector for Vietnamese cadastral information."""

import os
import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass

@dataclass
class XmlExchangeSummary:
    source_path: str
    parcel_count: int
    records: list[dict]
    mapping_used: dict

def get_mapping_config_path() -> str:
    """Return path to xml_field_mapping.json config file."""
    plugin_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(plugin_root, "config", "xml_field_mapping.json")

def load_mapping_config() -> dict:
    """Load XML field mapping configuration."""
    config_path = get_mapping_config_path()
    default_config = {
        "parcel_tag": "ThuaDat",
        "fields": {
            "so_hieu_to_ban_do": "soHieuToBanDo",
            "so_thu_tu_thua": "soThuTuThua",
            "dien_tich": "dienTich",
            "chu_su_dung": "hoTen",
            "dia_chi": "diaChi",
            "loai_dat": "loaiMucDichSuDungKiemKeId"
        }
    }
    if not os.path.exists(config_path):
        return default_config
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001 — intentional suppress
        return default_config

def parse_exchange_xml(xml_path: str, is_canceled_cb=None) -> XmlExchangeSummary:
    """Parse cadastral data from an XML file dynamically based on mapping config."""
    config = load_mapping_config()
    parcel_tag = config.get("parcel_tag", "ThuaDat")
    fields_map = config.get("fields", {})

    if not os.path.exists(xml_path):
        raise FileNotFoundError(f"Không tìm thấy tệp XML: {xml_path}")

    # Parse XML document
    tree = ET.parse(xml_path)
    root = tree.getroot()

    records = []
    
    # Tìm kiếm các nút thửa đất (hỗ trợ cả tìm kiếm đệ quy toàn bộ tree)
    parcels = root.findall(f".//{parcel_tag}")
    if not parcels and root.tag == parcel_tag:
        parcels = [root]

    for idx, p_node in enumerate(parcels):
        if is_canceled_cb and is_canceled_cb():
            raise RuntimeError("Tác vụ bị hủy bởi người dùng.")

        record = {"index": idx + 1}
        
        # Trích xuất dữ liệu dựa theo ánh xạ cấu hình
        for internal_key, xml_tag in fields_map.items():
            # Thử lấy attribute trước
            val = p_node.get(xml_tag)
            if val is None:
                # Thử tìm thẻ con
                child = p_node.find(xml_tag)
                if child is not None:
                    val = child.text
            
            # Lưu giá trị
            record[internal_key] = val.strip() if val else ""

        # Trích xuất tọa độ HinhHoc nếu có
        hinh_hoc_node = p_node.find("HinhHoc")
        if hinh_hoc_node is not None:
            diems = []
            for diem_node in hinh_hoc_node.findall("Diem"):
                x_val = diem_node.get("x")
                y_val = diem_node.get("y")
                if x_val is not None and y_val is not None:
                    try:
                        diems.append({"x": float(x_val), "y": float(y_val)})
                    except ValueError:
                        pass
            record["hinh_hoc"] = diems

        # Chuẩn hóa kiểu dữ liệu
        try:
            record["so_hieu_to_ban_do"] = int(record.get("so_hieu_to_ban_do") or 0)
        except ValueError:
            record["so_hieu_to_ban_do"] = 0
            
        try:
            record["so_thu_tu_thua"] = int(record.get("so_thu_tu_thua") or 0)
        except ValueError:
            record["so_thu_tu_thua"] = 0

        try:
            record["dien_tich"] = float(record.get("dien_tich") or 0.0)
        except ValueError:
            record["dien_tich"] = 0.0

        records.append(record)

    return XmlExchangeSummary(
        source_path=xml_path,
        parcel_count=len(records),
        records=records,
        mapping_used=config
    )

def export_to_exchange_xml(layers, output_path: str, is_canceled_cb=None) -> bool:
    """Export parcel vector layers to XML format using the mapping config."""
    config = load_mapping_config()
    parcel_tag = config.get("parcel_tag", "ThuaDat")
    fields_map = config.get("fields", {})

    root = ET.Element("CadastralData")
    
    exported = 0
    for layer in layers:
        if is_canceled_cb and is_canceled_cb():
            raise RuntimeError("Tác vụ bị hủy bởi người dùng.")

        for feature in layer.getFeatures():
            if is_canceled_cb and is_canceled_cb():
                raise RuntimeError("Tác vụ bị hủy bởi người dùng.")
                
            p_node = ET.SubElement(root, parcel_tag)
            
            # Map dữ liệu từ layer attributes sang XML
            attrs = {field.name().lower(): feature.attribute(field.name()) for field in feature.fields()}
            
            for internal_key, xml_tag in fields_map.items():
                # Tìm trường khớp trong layer attributes
                # Ví dụ: internal_key = "so_thu_tu_thua"
                val = ""
                # Thử tìm theo tên key gốc, tên lowercase, hoặc các từ đồng nghĩa
                lookup_keys = [internal_key, internal_key.lower()]
                if internal_key == "so_hieu_to_ban_do":
                    lookup_keys.extend(["tobando", "so_to", "to_ban_do"])
                elif internal_key == "so_thu_tu_thua":
                    lookup_keys.extend(["sothua", "so_thua", "thu_tu_thua"])
                elif internal_key == "dien_tich":
                    lookup_keys.extend(["dientich", "area", "dientichphaply"])
                elif internal_key == "chu_su_dung":
                    lookup_keys.extend(["tenchu", "chu_su_dung", "chusu_dung", "owner"])
                elif internal_key == "dia_chi":
                    lookup_keys.extend(["diachi", "dia_chi", "address"])
                elif internal_key == "loai_dat":
                    lookup_keys.extend(["loaidat", "ma_loai_dat", "loai_dat", "mucdich", "loaidat_ri"])

                for k in lookup_keys:
                    if k in attrs:
                        val = attrs[k]
                        break
                        
                val_str = "" if val is None else str(val)
                # Ghi dưới dạng thẻ con
                child = ET.SubElement(p_node, xml_tag)
                child.text = val_str
            
            # Xuất hình học của thửa đất
            geom = feature.geometry()
            if geom and not geom.isEmpty():
                geom_node = ET.SubElement(p_node, "HinhHoc")
                points = []
                if geom.isMultipart():
                    try:
                        poly = geom.asMultiPolygon()
                        if poly and len(poly) > 0 and len(poly[0]) > 0:
                            points = [(p.x(), p.y()) for p in poly[0][0]]
                    except Exception:  # noqa: BLE001 — intentional suppress
                        pass
                else:
                    try:
                        poly = geom.asPolygon()
                        if poly and len(poly) > 0:
                            points = [(p.x(), p.y()) for p in poly[0]]
                    except Exception:  # noqa: BLE001 — intentional suppress
                        pass
                if not points:
                    try:
                        points = [(v.x(), v.y()) for v in geom.vertices()]
                    except Exception:  # noqa: BLE001 — intentional suppress
                        pass
                
                for x, y in points:
                    ET.SubElement(geom_node, "Diem", x=f"{x:.4f}", y=f"{y:.4f}")
            
            exported += 1

    # Ghi file XML định dạng thụt lề đẹp
    try:
        from xml.dom import minidom
        xml_str = ET.tostring(root, encoding="utf-8")
        parsed_str = minidom.parseString(xml_str)
        pretty_xml = parsed_str.toprettyxml(indent="  ", encoding="utf-8")
        
        with open(output_path, "wb") as f:
            f.write(pretty_xml)
        return True
    except Exception:  # noqa: BLE001 — intentional suppress
        # Fallback ghi trực tiếp nếu lỗi minidom
        tree = ET.ElementTree(root)
        tree.write(output_path, encoding="utf-8", xml_declaration=True)
        return True
