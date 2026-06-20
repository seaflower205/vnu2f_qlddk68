# -*- coding: utf-8 -*-
"""
Trình quản lý Xuất/Nhập (Import/Export Manager).
Thực hiện đọc/ghi các file QML, JSON và .cadprofile chứa thông tin ký hiệu và cấu hình nhãn.
"""

import json
import os
from datetime import datetime
from qgis.core import QgsMapLayer, QgsProject, QgsMessageLog, Qgis

def export_symbology_json(code_configs: list[dict], file_path: str) -> None:
    """
    Xuất bảng mã loại đất hiện tại ra file JSON.
    Format giống land_use_codes.json để có thể dùng lại hoặc chia sẻ.
    """
    output_data = {}
    for cfg in code_configs:
        code = cfg.get("code")
        if not code:
            continue
        output_data[code] = {
            "name_vi": cfg.get("name_vi", ""),
            "name_en": cfg.get("name_en", ""),
            "group": cfg.get("group", "Chưa phân nhóm"),
            "fill_color": cfg.get("fill_color", "#FFFFFF"),
            "border_color": cfg.get("border_color", "#000000"),
            "border_width_mm": cfg.get("border_width_mm", 0.26),
            "pattern": cfg.get("pattern", "solid"),
            "pattern_color": cfg.get("pattern_color"),
            "pattern_angle": cfg.get("pattern_angle"),
            "opacity": cfg.get("opacity", 1.0),
            "source": cfg.get("source", "user")
        }
        
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

def export_symbology_qml(layer, file_path: str) -> None:
    """
    Xuất renderer hiện tại của layer ra file QML chuẩn QGIS.
    Dùng layer.saveNamedStyle(file_path) — chỉ lưu phần symbology, không lưu nhãn.
    Lưu ý: gọi hàm này SAU KHI đã apply_to_layer(), không phải từ bảng UI.
    """
    if not layer:
        raise ValueError("Layer không hợp lệ.")
        
    style_category = None
    if hasattr(QgsMapLayer, 'StyleCategory') and hasattr(QgsMapLayer.StyleCategory, 'Symbology'):
        style_category = QgsMapLayer.StyleCategory.Symbology
    elif hasattr(QgsMapLayer, 'Symbology'):
        style_category = QgsMapLayer.Symbology
        
    if style_category is not None:
        success, msg = layer.saveNamedStyle(file_path, style_category)
    else:
        success, msg = layer.saveNamedStyle(file_path)
        
    if not success:
        raise RuntimeError(f"Lỗi từ QGIS: {msg}")

def export_label_json(label_config: dict, file_path: str) -> None:
    """
    Xuất cấu hình nhãn hiện tại (preset + field mapping + visual settings) ra JSON.
    Bao gồm cả custom presets người dùng đã lưu.
    """
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(label_config, f, ensure_ascii=False, indent=2)

def export_full_profile(
    code_configs: list[dict],
    label_config: dict,
    general_settings: dict,
    file_path: str
) -> None:
    """
    Đóng gói tất cả thành file .cadprofile (JSON với metadata version).
    """
    profile_data = {
        "version": "1.0",
        "created_at": datetime.now().isoformat(),
        "plugin": "cadastral_tools",
        "symbology": code_configs,
        "labels": label_config,
        "settings": general_settings
    }
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(profile_data, f, ensure_ascii=False, indent=2)

# ── IMPORT ────────────────────────────────────────────────

def import_symbology_json(file_path: str) -> list[dict]:
    """
    Đọc file JSON ký hiệu.
    Validate schema: kiểm tra các trường bắt buộc (code, fill_color, border_color).
    Với trường thiếu: điền giá trị mặc định, không raise exception.
    Trả về list[dict] để load thẳng vào QTableWidget.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    result = []
    if isinstance(data, dict):
        for code, details in data.items():
            cfg = {
                "code": code,
                "name_vi": details.get("name_vi", f"Loại đất {code}"),
                "name_en": details.get("name_en", ""),
                "group": details.get("group", "Chưa phân nhóm"),
                "fill_color": details.get("fill_color", "#FFFFFF"),
                "border_color": details.get("border_color", "#000000"),
                "border_width_mm": details.get("border_width_mm", 0.26),
                "pattern": details.get("pattern", "solid"),
                "pattern_color": details.get("pattern_color"),
                "pattern_angle": details.get("pattern_angle"),
                "opacity": details.get("opacity", 1.0),
                "source": details.get("source", "user")
            }
            result.append(cfg)
    elif isinstance(data, list):
        for item in data:
            code = item.get("code", "")
            if not code:
                continue
            cfg = {
                "code": code,
                "name_vi": item.get("name_vi", f"Loại đất {code}"),
                "name_en": item.get("name_en", ""),
                "group": item.get("group", "Chưa phân nhóm"),
                "fill_color": item.get("fill_color", "#FFFFFF"),
                "border_color": item.get("border_color", "#000000"),
                "border_width_mm": item.get("border_width_mm", 0.26),
                "pattern": item.get("pattern", "solid"),
                "pattern_color": item.get("pattern_color"),
                "pattern_angle": item.get("pattern_angle"),
                "opacity": item.get("opacity", 1.0),
                "source": item.get("source", "user")
            }
            result.append(cfg)
            
    return result

def import_symbology_qml(file_path: str, layer) -> bool:
    """
    Áp dụng file QML vào layer bằng layer.loadNamedStyle(file_path).
    Trả về True nếu thành công.
    """
    if not layer:
        return False
        
    success, msg = layer.loadNamedStyle(file_path)
    if success:
        layer.triggerRepaint()
        layer.emitStyleChanged()
        return True
    else:
        QgsMessageLog.logMessage(f"Lỗi load QML style: {msg}", "CadastralTools", Qgis.Warning)
        return False

def import_label_json(file_path: str) -> dict:
    """
    Đọc file JSON nhãn.
    Validate các trường bắt buộc (preset, font_family, base_size_pt).
    Trả về dict để load vào Label Tab.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    if not isinstance(data, dict):
        raise ValueError("Cấu trúc file cấu hình nhãn phải là JSON object.")
        
    return data

def import_full_profile(file_path: str) -> dict:
    """
    Đọc file .cadprofile.
    Kiểm tra version compatibility.
    Nếu version không khớp: hiện QgsMessageBar warning nhưng vẫn import phần compatible.
    Trả về dict với keys: 'symbology', 'labels', 'settings'.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    if not isinstance(data, dict):
        raise ValueError("File profile không hợp lệ.")
        
    version = data.get("version", "1.0")
    if version != "1.0":
        QgsMessageLog.logMessage(
            f"Phiên bản cấu hình {version} không khớp với phiên bản hiện tại (1.0).", 
            "CadastralTools", 
            Qgis.Warning
        )
        
    return {
        "symbology": data.get("symbology", []),
        "labels": data.get("labels", {}),
        "settings": data.get("settings", {}),
        "version_warning": version != "1.0"
    }

def detect_format(file_path: str) -> str:
    """
    Nhận dạng định dạng từ extension + nội dung file.
    Trả về: 'symbology_json' | 'symbology_qml' | 'label_json' | 'profile' | 'unknown'
    """
    if not os.path.exists(file_path):
        return "unknown"
        
    _, ext = os.path.splitext(file_path.lower())
    if ext == ".qml":
        return "symbology_qml"
    elif ext == ".cadprofile":
        return "profile"
    elif ext == ".json":
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = json.load(f)
            
            if isinstance(content, dict):
                if "plugin" in content and content.get("plugin") == "cadastral_tools":
                    return "profile"
                if any(isinstance(v, dict) and "expression_template" in v for v in content.values()):
                    return "label_json"
                if any(isinstance(v, dict) and ("fill_color" in v or "border_color" in v) for v in content.values()):
                    return "symbology_json"
            elif isinstance(content, list):
                if any(isinstance(item, dict) and "code" in item for item in content):
                    return "symbology_json"
                    
            return "symbology_json"
        except Exception:  # noqa: BLE001 — intentional suppress
            return "unknown"
            
    return "unknown"

def merge_symbology_configs(
    current_configs: list[dict],
    imported_configs: list[dict],
    mode: str
) -> list[dict]:
    """
    Thực hiện gộp bảng mã ký hiệu theo 3 chế độ:
    - 'merge': Gộp (giữ mã hiện tại, thêm mã mới)
    - 'replace': Thay thế hoàn toàn
    - 'update_existing': Chỉ cập nhật các mã đã tồn tại ở bảng hiện tại
    """
    if mode == "replace":
        return imported_configs

    current_dict = {cfg["code"]: cfg for cfg in current_configs}
    imported_dict = {cfg["code"]: cfg for cfg in imported_configs}

    if mode == "merge":
        for code, imported_cfg in imported_dict.items():
            if code not in current_dict:
                current_dict[code] = imported_cfg
                
    elif mode == "update_existing":
        for code, imported_cfg in imported_dict.items():
            if code in current_dict:
                current_dict[code].update({
                    "fill_color": imported_cfg.get("fill_color", current_dict[code]["fill_color"]),
                    "border_color": imported_cfg.get("border_color", current_dict[code]["border_color"]),
                    "border_width_mm": imported_cfg.get("border_width_mm", current_dict[code]["border_width_mm"]),
                    "pattern": imported_cfg.get("pattern", current_dict[code]["pattern"]),
                    "pattern_color": imported_cfg.get("pattern_color", current_dict[code]["pattern_color"]),
                    "opacity": imported_cfg.get("opacity", current_dict[code]["opacity"]),
                    "name_vi": imported_cfg.get("name_vi", current_dict[code]["name_vi"]),
                })

    return list(current_dict.values())
