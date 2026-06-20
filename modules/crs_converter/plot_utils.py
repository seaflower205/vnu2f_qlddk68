# -*- coding: utf-8 -*-
"""
Tiện ích phân tích tệp số liệu tọa độ (Excel, CSV/Text, GPX)
phục vụ chức năng rải điểm bản vẽ.
"""

import os
import re
import xml.etree.ElementTree as ET
import pandas as pd
import unicodedata


def strip_accents(text):
    """Bỏ dấu tiếng Việt để so khớp từ khóa chính xác."""
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize('NFD', text)
    return ''.join(c for c in text if unicodedata.category(c) != 'Mn').lower()


def list_excel_sheets(file_path):
    import pandas as pd
    """Trả về danh sách các Sheet trong tệp Excel."""
    try:
        xls = pd.ExcelFile(file_path)
        return xls.sheet_names
    except Exception as e:  # noqa: BLE001 — intentional suppress
        raise Exception(f"Không thể đọc danh sách Sheet từ Excel: {e}")


def parse_coordinate_file(file_path, file_type=None, delimiter=',', has_header=True, sheet_name=None):
    """
    Phân tích tệp tọa độ và trả về:
    - columns: Danh sách tên cột (chuỗi).
    - preview_rows: 5 dòng đầu tiên dưới dạng danh sách các list giá trị.
    - all_data: Danh sách các dict đại diện cho toàn bộ các dòng dữ liệu.
    """
    if not file_type:
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ['.xlsx', '.xls']:
            file_type = 'excel'
        elif ext == '.gpx':
            file_type = 'gpx'
        else:
            file_type = 'text'

    if file_type == 'excel':
        return _parse_excel(file_path, sheet_name, has_header)
    elif file_type == 'gpx':
        return _parse_gpx(file_path)
    else:
        return _parse_text(file_path, delimiter, has_header)


def _parse_excel(file_path, sheet_name=None, has_header=True):
    try:
        # Nếu không chỉ định sheet, mặc định đọc sheet đầu tiên
        if not sheet_name:
            xls = pd.ExcelFile(file_path)
            if xls.sheet_names:
                sheet_name = xls.sheet_names[0]
            else:
                raise Exception("Tệp Excel không có sheet nào.")

        header_val = 0 if has_header else None
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=header_val)
        return _dataframe_to_result(df, has_header)
    except Exception as e:  # noqa: BLE001 — intentional suppress
        raise Exception(f"Lỗi khi đọc file Excel: {e}")


def _parse_text(file_path, delimiter=',', has_header=True):
    try:
        header_val = 0 if has_header else None
        # Xử lý ký tự phân cách khoảng trắng (whitespace)
        if delimiter == ' ':
            sep = r'\s+'
            engine = 'python'
        else:
            sep = delimiter
            engine = 'c'

        # Đọc tệp bằng pandas
        df = pd.read_csv(file_path, sep=sep, header=header_val, engine=engine)
        return _dataframe_to_result(df, has_header)
    except Exception as e:  # noqa: BLE001 — intentional suppress
        raise Exception(f"Lỗi khi đọc file văn bản: {e}")


def _parse_gpx(file_path):
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()

        # Loại bỏ namespace nếu có để dễ query
        ns = ""
        m = re.match(r'\{.*\}', root.tag)
        if m:
            ns = m.group(0)

        data = []
        # 1. Quét Waypoints <wpt>
        for wpt in root.findall(f'.//{ns}wpt'):
            lat = wpt.attrib.get('lat')
            lon = wpt.attrib.get('lon')
            name_el = wpt.find(f'{ns}name')
            ele_el = wpt.find(f'{ns}ele')
            desc_el = wpt.find(f'{ns}desc') or wpt.find(f'{ns}cmt')

            name = name_el.text if name_el is not None else f"WPT_{len(data)+1}"
            ele = float(ele_el.text) if ele_el is not None and ele_el.text else 0.0
            desc = desc_el.text if desc_el is not None else "Waypoint"

            data.append({
                'Tên điểm': name,
                'Tọa độ X (Lon)': float(lon) if lon else 0.0,
                'Tọa độ Y (Lat)': float(lat) if lat else 0.0,
                'Độ cao Z': ele,
                'Ghi chú': desc
            })

        # 2. Quét Trackpoints <trkpt>
        trk_idx = 1
        for trk in root.findall(f'.//{ns}trk'):
            trk_name_el = trk.find(f'{ns}name')
            trk_name = trk_name_el.text if trk_name_el is not None else f"Track_{trk_idx}"
            
            pt_idx = 1
            for trkpt in trk.findall(f'.//{ns}trkpt'):
                lat = trkpt.attrib.get('lat')
                lon = trkpt.attrib.get('lon')
                ele_el = trkpt.find(f'{ns}ele')
                name = f"{trk_name}_{pt_idx}"
                ele = float(ele_el.text) if ele_el is not None and ele_el.text else 0.0

                data.append({
                    'Tên điểm': name,
                    'Tọa độ X (Lon)': float(lon) if lon else 0.0,
                    'Tọa độ Y (Lat)': float(lat) if lat else 0.0,
                    'Độ cao Z': ele,
                    'Ghi chú': "Trackpoint"
                })
                pt_idx += 1
            trk_idx += 1

        if not data:
            raise Exception("Tệp GPX không chứa điểm Waypoint hoặc Trackpoint nào.")

        df = pd.DataFrame(data)
        return _dataframe_to_result(df, has_header=True)
    except Exception as e:  # noqa: BLE001 — intentional suppress
        raise Exception(f"Lỗi khi đọc file GPX: {e}")


def _dataframe_to_result(df, has_header=True):
    import pandas as pd
    # Thay thế các giá trị NaN bằng None hoặc chuỗi rỗng để tránh lỗi dữ liệu
    df = df.where(pd.notnull(df), None)

    if not has_header:
        # Đổi tên cột từ số 0, 1, 2 thành Cột 1, Cột 2...
        col_names = [f"Cột {i+1}" for i in range(len(df.columns))]
        df.columns = col_names
    else:
        # Đảm bảo các cột là kiểu chuỗi
        df.columns = [str(c).strip() for c in df.columns]

    columns = list(df.columns)
    
    # Lấy 5 dòng đầu xem trước
    preview_df = df.head(5)
    preview_rows = preview_df.values.tolist()
    # Chuyển đổi mọi giá trị trong preview thành chuỗi hoặc số đẹp để hiển thị
    preview_rows = [[str(v) if v is not None else "" for v in row] for row in preview_rows]

    # Convert toàn bộ dữ liệu thành danh sách dict
    all_data = df.to_dict(orient='records')

    return columns, preview_rows, all_data


def suggest_column_mappings(columns):
    """
    Phân tích tên các cột để đưa ra gợi ý tự động cho các trường dữ liệu:
    Trả về dict: { 'name': col_or_None, 'x': col_or_None, 'y': col_or_None, 'z': col_or_None, 'note': col_or_None }
    """
    mappings = {'name': None, 'x': None, 'y': None, 'z': None, 'note': None}

    # Bỏ dấu các tên cột để dễ quét
    clean_cols = [(col, strip_accents(col)) for col in columns]

    # 1. Tìm cột Tên điểm
    for col, clean in clean_cols:
        if clean in ['ten', 'id', 'name', 'stt', 'so hieu', 'sohieu', 'diem', 'point', 'point_id', 'label', 'lbl']:
            mappings['name'] = col
            break
    if not mappings['name']:
        # Tìm theo substring
        for col, clean in clean_cols:
            if any(k in clean for k in ['ten', 'name', 'sohieu', 'so_hieu']):
                mappings['name'] = col
                break

    # 2. Tìm cột X (Easting / Longitude)
    for col, clean in clean_cols:
        if clean in ['x', 'east', 'easting', 'lon', 'lng', 'longitude', 'kinh do', 'kinh_do', 'kinhdo']:
            mappings['x'] = col
            break
    if not mappings['x']:
        for col, clean in clean_cols:
            if 'east' in clean or 'lon' in clean or 'kinh' in clean or clean == 'e':
                mappings['x'] = col
                break

    # 3. Tìm cột Y (Northing / Latitude)
    for col, clean in clean_cols:
        if clean in ['y', 'north', 'northing', 'lat', 'latitude', 'vi do', 'vi_do', 'vido']:
            mappings['y'] = col
            break
    if not mappings['y']:
        for col, clean in clean_cols:
            if 'north' in clean or 'lat' in clean or 'vi' in clean or clean == 'n':
                mappings['y'] = col
                break

    # 4. Tìm cột Z (Elevation)
    for col, clean in clean_cols:
        if clean in ['z', 'h', 'ele', 'elevation', 'cao do', 'caodo', 'cao_do', 'do cao', 'docao', 'height', 'altitude']:
            mappings['z'] = col
            break
    if not mappings['z']:
        for col, clean in clean_cols:
            if 'ele' in clean or 'cao' in clean or 'height' in clean or 'alt' in clean or clean == 'h':
                mappings['z'] = col
                break

    # 5. Tìm cột Ghi chú
    for col, clean in clean_cols:
        if clean in ['note', 'code', 'ghi chu', 'ghichu', 'ghi_chu', 'mo ta', 'mota', 'mo_ta', 'desc', 'description', 'remark', 'loai']:
            mappings['note'] = col
            break
    if not mappings['note']:
        for col, clean in clean_cols:
            if any(k in clean for k in ['note', 'code', 'ghi', 'mota', 'desc']):
                mappings['note'] = col
                break

    # Gán dự phòng mặc định nếu không khớp
    if not mappings['name'] and len(columns) > 0:
        mappings['name'] = columns[0]
    if not mappings['x'] and len(columns) > 1:
        mappings['x'] = columns[1]
    if not mappings['y'] and len(columns) > 2:
        # Nếu cột 1 là tên, cột 2 là X, cột 3 thường là Y
        mappings['y'] = columns[2]
    elif not mappings['y'] and len(columns) > 1:
        # Dự phòng cột 2 là Y nếu chỉ có 2 cột
        mappings['y'] = columns[1]

    return mappings
