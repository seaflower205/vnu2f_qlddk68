# -*- coding: utf-8 -*-
"""
Dữ liệu hệ tọa độ VN-2000 tập trung.

Gom danh sách 63 tỉnh/thành, câu lệnh SQL fallback, và hàm populate
QComboBox vào **một nơi duy nhất** để tránh trùng lặp giữa crs_dialog.py
và crs_utils.py.
"""



# ═══════════════════════════════════════════════════════════════════════
# CÁC HỆ TỌA ĐỘ TIÊU CHUẨN (EPSG)
# ═══════════════════════════════════════════════════════════════════════
STANDARD_CRS = [
    ("WGS 84 (Lat/Lon) [EPSG:4326]", "EPSG:4326"),
    ("WGS 84 / UTM 48N [EPSG:32648]", "EPSG:32648"),
    ("WGS 84 / UTM 49N [EPSG:32649]", "EPSG:32649"),
    ("VN-2000 / UTM 48N [EPSG:3405]", "EPSG:3405"),
    ("VN-2000 / UTM 49N [EPSG:3406]", "EPSG:3406"),
    ("HN-72 / Hà Nội 3° [USER:900101]", "USER:900101"),
    ("HN-72 / UTM 48N [USER:900102]", "USER:900102"),
    ("HN-72 / UTM 49N [USER:900103]", "USER:900103"),
]


# ═══════════════════════════════════════════════════════════════════════
# DANH SÁCH 63 TỈNH THÀNH — VN-2000 CUSTOM 7 THAM SỐ
# ═══════════════════════════════════════════════════════════════════════
VN2000_PROVINCES = [
    ("Hà Nội (KTT 105.00)", "USER:100001"),
    ("Hà Giang (KTT 105.50)", "USER:100002"),
    ("Cao Bằng (KTT 105.75)", "USER:100004"),
    ("Bắc Kạn (KTT 106.50)", "USER:100006"),
    ("Tuyên Quang (KTT 106.00)", "USER:100008"),
    ("Lào Cai (KTT 104.75)", "USER:100010"),
    ("Điện Biên (KTT 103.00)", "USER:100011"),
    ("Lai Châu (KTT 103.00)", "USER:100012"),
    ("Sơn La (KTT 104.00)", "USER:100014"),
    ("Yên Bái (KTT 104.75)", "USER:100015"),
    ("Hoà Bình (KTT 106.00)", "USER:100017"),
    ("Thái Nguyên (KTT 106.50)", "USER:100019"),
    ("Lạng Sơn (KTT 107.25)", "USER:100020"),
    ("Quảng Ninh (KTT 107.75)", "USER:100022"),
    ("Bắc Giang (KTT 107.00)", "USER:100024"),
    ("Phú Thọ (KTT 104.75)", "USER:100025"),
    ("Vĩnh Phúc (KTT 105.00)", "USER:100026"),
    ("Bắc Ninh (KTT 105.50)", "USER:100027"),
    ("Hải Dương (KTT 105.50)", "USER:100030"),
    ("Hải Phòng (KTT 105.75)", "USER:100031"),
    ("Hưng Yên (KTT 105.50)", "USER:100033"),
    ("Thái Bình (KTT 105.50)", "USER:100034"),
    ("Hà Nam (KTT 105.00)", "USER:100035"),
    ("Nam Định (KTT 105.50)", "USER:100036"),
    ("Ninh Bình (KTT 105.00)", "USER:100037"),
    ("Thanh Hóa (KTT 105.00)", "USER:100038"),
    ("Nghệ An (KTT 104.75)", "USER:100040"),
    ("Hà Tĩnh (KTT 105.50)", "USER:100042"),
    ("Quảng Bình (KTT 106.00)", "USER:100044"),
    ("Quảng Trị (KTT 106.25)", "USER:100045"),
    ("Thừa Thiên Huế (KTT 107.00)", "USER:100046"),
    ("Đà Nẵng (KTT 107.75)", "USER:100048"),
    ("Quảng Nam (KTT 107.75)", "USER:100049"),
    ("Quảng Ngãi (KTT 108.00)", "USER:100051"),
    ("Bình Định (KTT 108.25)", "USER:100052"),
    ("Phú Yên (KTT 108.50)", "USER:100054"),
    ("Khánh Hòa (KTT 108.25)", "USER:100056"),
    ("Ninh Thuận (KTT 108.25)", "USER:100058"),
    ("Bình Thuận (KTT 108.50)", "USER:100060"),
    ("Kon Tum (KTT 107.50)", "USER:100062"),
    ("Gia Lai (KTT 108.50)", "USER:100064"),
    ("Đắk Lắk (KTT 108.50)", "USER:100066"),
    ("Đắk Nông (KTT 108.50)", "USER:100067"),
    ("Lâm Đồng (KTT 107.75)", "USER:100068"),
    ("Bình Phước (KTT 106.25)", "USER:100070"),
    ("Tây Ninh (KTT 105.50)", "USER:100072"),
    ("Bình Dương (KTT 105.75)", "USER:100074"),
    ("Đồng Nai (KTT 107.75)", "USER:100075"),
    ("Bà Rịa - Vũng Tàu (KTT 107.75)", "USER:100077"),
    ("Hồ Chí Minh (KTT 105.75)", "USER:100079"),
    ("Long An (KTT 105.75)", "USER:100080"),
    ("Tiền Giang (KTT 105.75)", "USER:100082"),
    ("Bến Tre (KTT 105.75)", "USER:100083"),
    ("Trà Vinh (KTT 105.50)", "USER:100084"),
    ("Vĩnh Long (KTT 105.50)", "USER:100086"),
    ("Đồng Tháp (KTT 105.00)", "USER:100087"),
    ("An Giang (KTT 104.75)", "USER:100089"),
    ("Kiên Giang (KTT 104.50)", "USER:100091"),
    ("Cần Thơ (KTT 105.00)", "USER:100092"),
    ("Hậu Giang (KTT 105.00)", "USER:100093"),
    ("Sóc Trăng (KTT 105.50)", "USER:100094"),
    ("Bạc Liêu (KTT 105.00)", "USER:100095"),
    ("Cà Mau (KTT 104.50)", "USER:100096"),
]


# ═══════════════════════════════════════════════════════════════════════
# CÂU LỆNH SQL FALLBACK CHO 63 TỈNH THÀNH
# (Sao chép từ file giảng viên, dùng khi ổ D không có)
# ═══════════════════════════════════════════════════════════════════════
FALLBACK_SQL_INSERTS = [
    "INSERT OR REPLACE INTO tbl_srs VALUES ('900101', 'HN-72 / Hà Nội (KTT 105.00, múi 3°)', 'tmerc', 'krass', '+proj=tmerc +lat_0=0 +lon_0=105 +k=0.9999 +x_0=500000 +y_0=0 +ellps=krass +towgs84=-191.8,-110.7,-120.5,0,0,0,0 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('900102', 'HN-72 / UTM múi 48N (KTT 105.00, múi 6°)', 'tmerc', 'krass', '+proj=utm +zone=48 +ellps=krass +towgs84=-191.8,-110.7,-120.5,0,0,0,0 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('900103', 'HN-72 / UTM múi 49N (KTT 111.00, múi 6°)', 'tmerc', 'krass', '+proj=utm +zone=49 +ellps=krass +towgs84=-191.8,-110.7,-120.5,0,0,0,0 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100001', 'Hà Nội', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=105 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100002', 'Hà Giang', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=105.50 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100004', 'Cao Bằng', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=105.75 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100006', 'Bắc Kạn', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=106.50 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100008', 'Tuyên Quang', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=106 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100010', 'Lào Cai', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=104.75 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100011', 'Điện Biên', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=103 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100012', 'Lai Châu', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=103 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100014', 'Sơn La', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=104 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100015', 'Yên Bái', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=104.75 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100017', 'Hoà Bình', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=106 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100019', 'Thái Nguyên', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=106.50 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100020', 'Lạng Sơn', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=107.25 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100022', 'Quảng Ninh', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=107.75 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100024', 'Bắc Giang', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=107.00 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100025', 'Phú Thọ', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=104.75 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100026', 'Vĩnh Phúc', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=105 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100027', 'Bắc Ninh', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=105.50 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100030', 'Hải Dương', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=105.50 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100031', 'Hải Phòng', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=105.75 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100033', 'Hưng Yên', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=105.50 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100034', 'Thái Bình', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=105.50 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100035', 'Hà Nam', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=105 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100036', 'Nam Định', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=105.50 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100037', 'Ninh Bình', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=105 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100038', 'Thanh Hóa', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=105 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100040', 'Nghệ An', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=104.75 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100042', 'Hà Tĩnh', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=105.50 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100044', 'Quảng Bình', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=106 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100045', 'Quảng Trị', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=106.25 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100046', 'Thừa Thiên Huế', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=107 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100048', 'Đà Nẵng', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=107.75 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100049', 'Quảng Nam', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=107.75 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100051', 'Quảng Ngãi', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=108 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100052', 'Bình Định', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=108.25 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100054', 'Phú Yên', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=108.50 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100056', 'Khánh Hòa', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=108.25 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100058', 'Ninh Thuận', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=108.25 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100060', 'Bình Thuận', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=108.50 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100062', 'Kon Tum', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=107.50 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100064', 'Gia Lai', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=108.50 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100066', 'Đắk Lắk', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=108.50 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100067', 'Đắk Nông', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=108.50 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100068', 'Lâm Đồng', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=107.75 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100070', 'Bình Phước', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=106.25 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100072', 'Tây Ninh', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=105.50 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100074', 'Bình Dương', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=105.75 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100075', 'Đồng Nai', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=107.75 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100077', 'Bà Rịa - Vũng Tàu', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=107.75 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100079', 'Hồ Chí Minh', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=105.75 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100080', 'Long An', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=105.75 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100082', 'Tiền Giang', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=105.75 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100083', 'Bến Tre', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=105.75 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100084', 'Trà Vinh', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=105.50 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100086', 'Vĩnh Long', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=105.50 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100087', 'Đồng Tháp', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=105 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100089', 'An Giang', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=104.75 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100091', 'Kiên Giang', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=104.50 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100092', 'Cần Thơ', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=105 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100093', 'Hậu Giang', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=105 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100094', 'Sóc Trăng', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=105.50 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100095', 'Bạc Liêu', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=105 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
    "INSERT OR REPLACE INTO tbl_srs VALUES ('100096', 'Cà Mau', 'tmerc', 'WGS84', '+proj=tmerc +lat_0=0 +lon_0=104.50 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 +towgs84=191.90441429,-39.30318279,-111.45032835,0.00928836,-0.01975479,0.00427372,0.252906278 +units=m +no_defs', null, null, null, '0', null, null)",
]


# ═══════════════════════════════════════════════════════════════════════
# HÀM TIỆN ÍCH
# ═══════════════════════════════════════════════════════════════════════

def populate_crs_combo(combo, provinces_only=False):
    """Nạp danh sách CRS vào QComboBox.

    Parameters
    ----------
    combo : QComboBox
        ComboBox cần nạp dữ liệu.
    provinces_only : bool
        Nếu ``True`` chỉ nạp 63 tỉnh VN-2000, bỏ qua các CRS tiêu chuẩn.
    """
    if not provinces_only:
        for label, code in STANDARD_CRS:
            combo.addItem(label, code)

    for prov_name, crs_code in VN2000_PROVINCES:
        if provinces_only:
            combo.addItem(prov_name, crs_code)
        else:
            combo.addItem(f"VN-2000 {prov_name}", crs_code)
