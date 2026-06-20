# -*- coding: utf-8 -*-
"""
from ..common.common_utils import log_critical, log_warning

Module đọc dữ liệu hình học, text, hatch và thuộc tính từ tệp DXF (DXF Reader).
"""

from ..common.common_utils import log_warning
from .dxf_block_extractor import extract_block_attributes
from shapely.geometry import Point, LineString, Polygon

def read_dxf_data(filepath):
    import ezdxf
    """
    Đọc tệp DXF và phân tích hình học, nhãn chữ, block.
    
    Args:
        filepath (str): Đường dẫn đến tệp tin .dxf.
        
    Returns:
        dict: Chứa các phần tử đã phân loại:
            {
                'polylines': list of dict,
                'texts': list of dict,
                'blocks': list of dict
            }
    """
    results = {
        "polylines": [],
        "texts": [],
        "blocks": []
    }
    
    try:
        doc = ezdxf.readfile(filepath)
        msp = doc.modelspace()
    except Exception as e:
        log_warning(f"Lỗi khi đọc file DXF {filepath}: {e}")
        return results
        
    # 1. Trích xuất Block Attributes
    results["blocks"] = extract_block_attributes(doc)
    
    # 2. Quét các đối tượng hình học ranh và text trong Model Space
    for entity in msp:
        etype = entity.dxftype()
        layer = entity.dxf.layer
        
        # A. Xử lý đường Polyline / LwPolyline (Ranh thửa)
        if etype in ("LWPOLYLINE", "POLYLINE"):
            try:
                # Lấy các điểm đỉnh của polyline
                points = [(p[0], p[1]) for p in entity.get_points()]
                if len(points) < 2:
                    continue
                    
                is_closed = entity.is_closed
                
                # Tạo Shapely Geometry
                if is_closed and len(points) >= 3:
                    # Nếu khép kín, thử tạo đa giác
                    geom = Polygon(points)
                else:
                    geom = LineString(points)
                    
                results["polylines"].append({
                    "geometry": geom,
                    "layer": layer,
                    "type": etype,
                    "is_closed": is_closed
                })
            except Exception as e:  # noqa: BLE001
                import traceback
                log_warning(f"[_parse_LWPOLYLINE] Lỗi bị bỏ qua: {e}\n{traceback.format_exc()}")
                
        # B. Xử lý đường thẳng đơn lẻ (LINE)
        elif etype == "LINE":
            try:
                p_start = (entity.dxf.start.x, entity.dxf.start.y)
                p_end = (entity.dxf.end.x, entity.dxf.end.y)
                geom = LineString([p_start, p_end])
                results["polylines"].append({
                    "geometry": geom,
                    "layer": layer,
                    "type": etype,
                    "is_closed": False
                })
            except Exception as e:  # noqa: BLE001
                import traceback
                log_warning(f"[_parse_LINE] Lỗi bị bỏ qua: {e}\n{traceback.format_exc()}")
                
        # C. Xử lý nhãn chữ (TEXT / MTEXT)
        elif etype in ("TEXT", "MTEXT"):
            try:
                text_val = entity.dxf.text.strip()
                if not text_val:
                    continue
                    
                # MTEXT có thể chứa mã định dạng, làm sạch đơn giản
                if etype == "MTEXT":
                    # Loại bỏ các ký tự định dạng kiểu \\A1; hoặc \\P...
                    import re
                    text_val = re.sub(r"\\[A-Za-z0-9]+;", "", text_val)
                    text_val = text_val.replace("\\P", "\n").strip()
                    
                from modules.dxf_engine.tcvn3_decoder import decode_tcvn3
                text_val = decode_tcvn3(text_val)
                
                insert_pt = entity.dxf.insert
                geom = Point(insert_pt.x, insert_pt.y)
                
                results["texts"].append({
                    "geometry": geom,
                    "text": text_val,
                    "layer": layer,
                    "type": etype
                })
            except Exception as e:  # noqa: BLE001
                import traceback
                log_warning(f"[_parse_TEXT] Lỗi bị bỏ qua: {e}\n{traceback.format_exc()}")
                
    return results

def match_parcels_with_attributes(polygons, blocks, texts):
    """
    Ghép các đa giác thửa đất với thông tin thuộc tính tìm thấy trong tệp DXF
    dựa trên quan hệ chứa đựng không gian.
    
    Args:
        polygons (list): Danh sách các đối tượng shapely Polygon.
        blocks (list): Dữ liệu các block reference trích xuất từ DXF.
        texts (list): Dữ liệu các nhãn chữ trích xuất từ DXF.
        
    Returns:
        list: Danh sách thửa đất hoàn chỉnh (geometry + attributes).
    """
    from shapely.geometry import Point
    parcels = []
    
    for poly in polygons:
        attrs = {}
        
        # 1. Tìm các block nằm bên trong polygon
        for blk in blocks:
            pt = Point(blk['x'], blk['y'])
            if poly.contains(pt):
                # Copy thuộc tính từ block
                attrs.update(blk['attributes'])
                
        # 2. Tìm các nhãn chữ nằm bên trong polygon (để bổ sung)
        inside_texts = []
        for txt in texts:
            if poly.contains(txt['geometry']):
                inside_texts.append(txt['text'])
                
        if inside_texts:
            attrs["_notes_text"] = ", ".join(inside_texts)
            
            # Thử parse số thửa / loại đất từ chữ nếu block chưa có
            # Thường nhãn chữ có định dạng: "123" (số thửa) hoặc "ONT" (loại đất)
            for text in inside_texts:
                t = text.strip()
                if t.isdigit() and "SOTHUA" not in attrs:
                    attrs["SOTHUA"] = t
                elif t.isupper() and len(t) in (3, 4) and "LOAIDAT" not in attrs:
                    attrs["LOAIDAT"] = t
                    
        # Thiết lập mặc định
        if "DIENTICH" not in attrs:
            attrs["DIENTICH"] = round(poly.area, 1)
        attrs["DIENTICH_CAD"] = round(poly.area, 2)
        
        parcels.append({
            "geometry": poly,
            "attributes": attrs
        })
        
    return parcels
