# -*- coding: utf-8 -*-
"""
from ..common.common_utils import log_critical, log_warning

Module xuất dữ liệu thửa đất từ QGIS sang định dạng CAD DXF (DXF Writer).
"""

from ..common.common_utils import log_warning

def export_features_to_dxf(features, output_path, mapping=None, boundary_layer="RANH_THUA", label_layer="NHAN_THUA"):
    import ezdxf
    from shapely.wkt import loads
    """
    Xuất danh sách các đối tượng thửa đất QGIS (Polygon) sang tệp DXF chuẩn địa chính.
    
    Args:
        features (list): Danh sách các dict mô tả thửa đất:
            {
                'wkt': str (hình học WKT),
                'attributes': dict (chứa SOTHUA, SOTO, LOAIDAT, DIENTICH, ...)
            }
        output_path (str): Đường dẫn lưu tệp tin .dxf kết quả.
        mapping (dict): Ánh xạ trường QGIS cần xuất (sothua, soto, loaidat, dientich).
        boundary_layer (str): Tên lớp CAD chứa đường ranh thửa.
        label_layer (str): Tên lớp CAD chứa chữ nhãn thửa đất.
        
    Returns:
        bool: True nếu thành công, False nếu thất bại.
    """
    try:
        # 1. Khởi tạo tài liệu DXF phiên bản AutoCAD R2010 (tương thích rộng rãi)
        doc = ezdxf.new("R2010")
        msp = doc.modelspace()
        
        # 2. Tạo các lớp layer chuyên biệt với màu sắc chuẩn
        # Layer ranh: màu trắng/đen (mã màu 7) hoặc màu đỏ (mã màu 1)
        doc.layers.new(name=boundary_layer, dxfattribs={"color": 7})
        # Layer nhãn: màu vàng (mã màu 2) hoặc xanh lá (mã màu 3)
        doc.layers.new(name=label_layer, dxfattribs={"color": 2})
        
        map_keys = mapping or {
            "sothua": "SOTHUA",
            "soto": "SOTO",
            "loaidat": "LOAIDAT",
            "dientich": "DIENTICH"
        }
        
        # 3. Duyệt qua từng thửa đất để vẽ hình học và ghi nhãn
        for feat in features:
            wkt = feat.get('wkt')
            if not wkt:
                continue
                
            try:
                geom = loads(wkt)
            except Exception:  # noqa: BLE001 — intentional suppress
                continue
                
            if geom.is_empty:
                continue
                
            # A. Vẽ đa giác ranh thửa (LWPOLYLINE khép kín)
            # Hỗ trợ vẽ cả thửa đất dạng MultiPolygon
            polys = []
            if geom.geom_type == 'Polygon':
                polys = [geom]
            elif geom.geom_type == 'MultiPolygon':
                polys = list(geom.geoms)
                
            for poly in polys:
                # 1. Vẽ vòng ranh ngoài (exterior ring)
                ext_coords = [(p[0], p[1]) for p in poly.exterior.coords]
                msp.add_lwpolyline(
                    ext_coords,
                    dxfattribs={"layer": boundary_layer, "closed": True}
                )
                
                # 2. Vẽ các vòng ranh thủng bên trong (interior rings) nếu có
                for interior in poly.interiors:
                    int_coords = [(p[0], p[1]) for p in interior.coords]
                    msp.add_lwpolyline(
                        int_coords,
                        dxfattribs={"layer": boundary_layer, "closed": True}
                    )
                    
            # B. Tạo nhãn chữ tại tâm thửa đất (Centroid)
            attrs = feat.get('attributes', {})
            sothua = str(attrs.get(map_keys.get("sothua", "SOTHUA"), "")).strip()
            loaidat = str(attrs.get(map_keys.get("loaidat", "LOAIDAT"), "")).strip()
            
            # Đọc diện tích, định dạng số thập phân đẹp
            dientich_val = attrs.get(map_keys.get("dientich", "DIENTICH"), "")
            dientich = ""
            if dientich_val not in (None, ""):
                try:
                    dientich = f"{float(dientich_val):.1f}"
                except Exception:  # noqa: BLE001 — intentional suppress
                    dientich = str(dientich_val)
                    
            if sothua or loaidat or dientich:
                # Lấy tâm thửa đất để đặt chữ
                centroid = geom.centroid
                cx, cy = centroid.x, centroid.y
                
                # Tạo nhãn theo cấu trúc 3 dòng chuẩn địa chính:
                # Số thửa
                # -------- (đường gạch ngang)
                # Loại đất - Diện tích
                if sothua:
                    msp.add_text(
                        sothua,
                        dxfattribs={"layer": label_layer, "height": 1.5}
                    ).set_placement((cx, cy + 1.0), align=ezdxf.enums.TextEntityAlignment.CENTER)
                    
                # Đường gạch phân cách
                msp.add_line(
                    (cx - 2.0, cy),
                    (cx + 2.0, cy),
                    dxfattribs={"layer": label_layer}
                )
                
                # Mục đích sử dụng + diện tích
                sub_label = f"{loaidat} {dientich}".strip()
                if sub_label:
                    msp.add_text(
                        sub_label,
                        dxfattribs={"layer": label_layer, "height": 1.2}
                    ).set_placement((cx, cy - 1.5), align=ezdxf.enums.TextEntityAlignment.CENTER)
                    
        # 4. Lưu tài liệu ra tệp DXF
        doc.saveas(output_path)
        return True
    except Exception as e:
        log_warning(f"Lỗi khi xuất DXF: {e}")
        return False
