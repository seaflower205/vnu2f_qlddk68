# -*- coding: utf-8 -*-
"""
Module tự động ánh xạ trường (Field Mapper) giữa QGIS Layer và cột dữ liệu Excel.
"""

def auto_detect_mapping(fields):
    """
    Tự động phân tích danh sách các trường trong QGIS layer và ánh xạ sang các thuộc tính chuẩn.
    
    Args:
        fields (QgsFields): Danh sách các trường của lớp vector.
        
    Returns:
        dict: Ánh xạ kết quả (chuẩn -> tên trường QGIS)
    """
    mapping = {
        "sothua": "",
        "soto": "",
        "loaidat": "",
        "tenchu": "",
        "dientich": ""
    }
    
    field_names = [f.name() for f in fields]
    
    for name in field_names:
        n = name.lower()
        
        # 1. Số thửa
        if any(x in n for x in ["sothua", "shthua", "sothututhua"]) or n == "thua":
            mapping["sothua"] = name
            
        # 2. Số tờ
        elif any(x in n for x in ["soto", "sotobd", "shbando", "mapsheet"]) or n == "tobd":
            mapping["soto"] = name
            
        # 3. Loại đất / MDSD
        elif any(x in n for x in ["loaidat", "maloaidat", "khloaidat", "mdsd", "loai_dat", "mdsd2003"]):
            mapping["loaidat"] = name
            
        # 4. Tên chủ sử dụng
        elif any(x in n for x in ["tenchu", "chusudung", "ten_chu", "chu_sd", "chucuoc"]):
            mapping["tenchu"] = name
            
        # 5. Diện tích
        elif any(x in n for x in ["dientich", "area", "shape_area", "dt_pl", "dientich_hp"]):
            if not mapping["dientich"] or "dientich" in n: # Ưu tiên trường có chữ dientich trực tiếp
                mapping["dientich"] = name
                
    return mapping
