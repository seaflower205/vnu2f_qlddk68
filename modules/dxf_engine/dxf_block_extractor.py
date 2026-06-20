# -*- coding: utf-8 -*-
"""
Module trích xuất thuộc tính của đối tượng Block Reference (INSERT) từ tệp DXF.
"""

def extract_block_attributes(doc):
    """
    Quét toàn bộ không gian bản vẽ (Model Space) và trích xuất thuộc tính
    từ tất cả các đối tượng Block Reference (INSERT).
    
    Args:
        doc (ezdxf.document.Drawing): Đối tượng Drawing đọc từ ezdxf.
        
    Returns:
        list: Danh sách các Block dữ liệu tìm thấy, mỗi block dạng:
            {
                'name': str (tên Block),
                'x': float,
                'y': float,
                'attributes': dict (thẻ tag -> giá trị text),
                'xdata': dict (dữ liệu mở rộng đính kèm)
            }
    """
    blocks_data = []
    try:
        msp = doc.modelspace()
    except Exception as e:  # noqa: BLE001
        import traceback
        from ..common.common_utils import log_warning
        log_warning(f"[extract_block_attributes] Lỗi bị bỏ qua: {e}\n{traceback.format_exc()}")
        return []
        
    for entity in msp.query("INSERT"):
        try:
            block_name = entity.dxf.name
            insert_pt = entity.dxf.insert
            
            # 1. Trích xuất các thuộc tính đính kèm (ATTRIB)
            attrs = {}
            if entity.has_attribs:
                for attrib in entity.attribs:
                    tag = attrib.dxf.tag.upper()
                    val = attrib.dxf.text.strip()
                    attrs[tag] = val
                    
            # 2. Trích xuất dữ liệu mở rộng XData nếu có
            xdata = {}
            if entity.xdata:
                for appid, data_list in entity.xdata:
                    # Lấy các giá trị thô từ danh sách (mã code, giá trị)
                    xdata[appid] = [val for _, val in data_list]
                    
            blocks_data.append({
                'name': block_name,
                'x': insert_pt.x,
                'y': insert_pt.y,
                'attributes': attrs,
                'xdata': xdata
            })
        except Exception as e:  # noqa: BLE001
            import traceback
            from ..common.common_utils import log_warning
            log_warning(f"[extract_block_attributes loop] Lỗi bị bỏ qua: {e}\n{traceback.format_exc()}")
            
    return blocks_data
