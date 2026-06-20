# -*- coding: utf-8 -*-
"""
import traceback

Các tiện ích hệ tọa độ VN-2000 (CRS Utilities).
Chịu trách nhiệm đăng ký các phép chiếu VN-2000 chuẩn 7 tham số của 63 tỉnh/thành
vào CSDL của QGIS và cung cấp các hàm chuyển đổi tọa độ.
"""

import os
import re
import traceback
import sqlite3

from qgis.core import QgsApplication

from ..common.vn2000_data import FALLBACK_SQL_INSERTS


class Vn2000DbHelper:
    """Lớp hỗ trợ ghi nhận và kiểm tra hệ tọa độ VN-2000 trong CSDL QGIS."""

    @staticmethod
    def get_qgis_db_path():
        """Lấy đường dẫn tệp CSDL người dùng qgis.db."""
        return QgsApplication.qgisUserDatabaseFilePath()


    @classmethod
    def _parse_and_insert_query(cls, cursor, query, table_cols):
        # Extract everything inside VALUES (...)
        match = re.search(r"VALUES\s*\((.*)\)", query, re.IGNORECASE)
        if not match:
            cursor.execute(query)
            return

        vals_str = match.group(1)
        vals = []
        in_quote = False
        quote_char = ""
        current_val = []
        for char in vals_str:
            if char in ("'", '"'):
                if not in_quote:
                    in_quote = True
                    quote_char = char
                elif char == quote_char:
                    in_quote = False
            elif char == ',' and not in_quote:
                vals.append("".join(current_val).strip())
                current_val = []
                continue
            current_val.append(char)
        if current_val:
            vals.append("".join(current_val).strip())

        # Strip quotes and decode nulls
        clean_vals = []
        for v in vals:
            if v.lower() == 'null':
                clean_vals.append(None)
            elif (v.startswith("'") and v.endswith("'")) or (v.startswith('"') and v.endswith('"')):
                clean_vals.append(v[1:-1])
            else:
                clean_vals.append(v)
        
        if len(clean_vals) < 5:
            cursor.execute(query)
            return

        srs_id = int(clean_vals[0])
        description = clean_vals[1]
        projection_acronym = clean_vals[2]
        ellipsoid_acronym = clean_vals[3]
        proj_params = clean_vals[4]
        srid = clean_vals[5] if len(clean_vals) > 5 else None

        # Generate WKT if running inside QGIS environment
        wkt_str = ""
        try:
            from qgis.core import QgsCoordinateReferenceSystem
            crs_temp = QgsCoordinateReferenceSystem.fromProj(proj_params)
            if crs_temp.isValid():
                wkt_str = crs_temp.toWkt()
        except Exception:  # noqa: BLE001 — intentional suppress
            pass

        col_names = [col[1] for col in table_cols]
        
        insert_data = {
            "srs_id": srs_id,
            "description": description,
            "projection_acronym": projection_acronym,
            "ellipsoid_acronym": ellipsoid_acronym,
            "parameters": proj_params,
            "srid": srid,
            "auth_name": "USER",
            "auth_id": str(srs_id),
            "deprecated": 0
        }
        
        # Handle is_geo vs is_geographic
        if "is_geo" in col_names:
            insert_data["is_geo"] = 0
        elif "is_geographic" in col_names:
            insert_data["is_geographic"] = 0
            
        # Handle wkt vs has_flipped_axes
        if "wkt" in col_names:
            insert_data["wkt"] = wkt_str
        elif "has_flipped_axes" in col_names:
            insert_data["has_flipped_axes"] = 0

        # Build parameterized query fields present in actual database
        fields_to_insert = [col for col in col_names if col in insert_data]
        placeholders = ["?"] * len(fields_to_insert)
        values_to_insert = [insert_data[f] for f in fields_to_insert]

        sql_stmt = f"INSERT OR REPLACE INTO tbl_srs ({', '.join(fields_to_insert)}) VALUES ({', '.join(placeholders)})"
        cursor.execute(sql_stmt, values_to_insert)

    @classmethod
    def register_provinces(cls):
        """Đăng ký tham số VN-2000 63 tỉnh/thành vào qgis.db.

        Dữ liệu CRS luôn lấy từ tài nguyên tích hợp trong plugin để bản cài đặt
        chạy nhất quán trên mọi máy, không phụ thuộc đường dẫn cục bộ.
        """
        db_path = cls.get_qgis_db_path()

        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS tbl_srs (
                        srs_id INTEGER PRIMARY KEY,
                        description TEXT NOT NULL,
                        projection_acronym TEXT NOT NULL,
                        ellipsoid_acronym TEXT NOT NULL,
                        parameters TEXT NOT NULL,
                        srid INTEGER,
                        auth_name TEXT,
                        auth_id TEXT,
                        is_geo INTEGER,
                        deprecated INTEGER,
                        wkt TEXT
                    )
                """)
                cursor.execute("PRAGMA table_info(tbl_srs)")
                table_cols = cursor.fetchall()
                
                for sql in FALLBACK_SQL_INSERTS:
                    cls._parse_and_insert_query(cursor, sql, table_cols)
                conn.commit()
            return True, "Đăng ký thành công hệ tọa độ 63 tỉnh thành Việt Nam từ tài nguyên tích hợp sẵn."
        except Exception as e:
            traceback.print_exc()
            return False, f"Lỗi nghiêm trọng khi ghi nhận hệ tọa độ vào CSDL: {e}"



# ==============================================================================
# PARSING DMS & COORDINATE TRANSFORMATION
# ==============================================================================

class CoordinateTransformer:
    """Lớp xử lý toán học chuyển đổi tọa độ và định vị bản đồ."""

    @staticmethod
    def parse_dms(text):
        """Phân tích chuỗi Độ Phút Giây (DMS) thành số thập phân (Decimal Degrees).
        Hỗ trợ các định dạng: 21°14'05", 21 14 05, 21-14-05, N21d14m05s...
        """
        text = text.strip().upper()
        if not text:
            raise ValueError("Chuỗi tọa độ trống.")

        hemisphere = 1
        if text[0] in "NSEW":
            if text[0] in "SW":
                hemisphere = -1
            text = text[1:].strip()
        elif text[-1] in "NSEW":
            if text[-1] in "SW":
                hemisphere = -1
            text = text[:-1].strip()

        if "," in text and "." not in text:
            if text.count(",") == 1 and not re.search(r",\s", text):
                text = text.replace(",", ".")

        parts = re.split(r"[°º\'\"\''\"dDmMsS\s;:\-]+", text)
        parts = [p.strip() for p in parts if p.strip()]

        if len(parts) == 1:
            return float(parts[0]) * hemisphere
        elif len(parts) == 2:
            d = float(parts[0])
            m = float(parts[1])
            return hemisphere * (d + m / 60.0)
        elif len(parts) >= 3:
            d = float(parts[0])
            m = float(parts[1])
            s = float(parts[2])
            return hemisphere * (d + m / 60.0 + s / 3600.0)
        else:
            raise ValueError(f"Không thể phân tích định dạng DMS: {text}")

    @staticmethod
    def dd_to_dms(dd, is_lat=True):
        """Chuyển đổi số thập phân sang định dạng chuỗi Độ Phút Giây (DMS)."""
        direction = ""
        if is_lat:
            direction = "N" if dd >= 0 else "S"
        else:
            direction = "E" if dd >= 0 else "W"

        dd = abs(dd)
        d = int(dd)
        m = int((dd - d) * 60)
        s = (dd - d - m / 60.0) * 3600.0

        return f"{d}°{m:02d}'{s:05.2f}\"{direction}"


# FALLBACK_SQL_INSERTS is imported from modules.common.vn2000_data
