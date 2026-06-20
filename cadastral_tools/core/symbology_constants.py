# -*- coding: utf-8 -*-
from qgis.PyQt.QtCore import Qt

# Mapping of Vietnamese legacy names and internal lowercase names to canonical English names
PATTERN_ALIASES = {
    # Vietnamese legacy names
    "Đặc": "Solid",
    "Rỗng": "No Brush",
    "Không màu nền / Rỗng": "No Brush",
    "Ngang": "Horizontal Hatch",
    "Gạch ngang": "Horizontal Hatch",
    "Dọc": "Vertical Hatch", 
    "Gạch dọc": "Vertical Hatch", 
    "Chéo phải": "Diagonal Hatch",
    "Gạch chéo": "Diagonal Hatch",
    "Chéo trái": "Backward Diagonal Hatch", 
    "Gạch chéo ngược": "Backward Diagonal Hatch", 
    "Lưới chéo": "Cross Hatch",
    "Gạch chéo đôi": "Cross Diagonal Hatch",
    "Lưới chéo (DiagCross)": "Cross Diagonal Hatch",
    "Chấm hạt": "Dense 4",
    "Mật độ chấm 1 (Dense 1)": "Dense 1",
    "Mật độ chấm 2 (Dense 2)": "Dense 2",
    "Mật độ chấm 3 (Dense 3)": "Dense 3",
    "Mật độ chấm 4 (Dense 4)": "Dense 4",
    "Mật độ chấm 5 (Dense 5)": "Dense 5",
    "Mật độ chấm 6 (Dense 6)": "Dense 6",
    "Mật độ chấm 7 (Dense 7)": "Dense 7",
    "Chấm bi": "Point Pattern Fill",

    # Internal lowercase QGIS names
    "solid": "Solid",
    "no_brush": "No Brush",
    "horizontal": "Horizontal Hatch",
    "vertical": "Vertical Hatch",
    "diagonal_fwd": "Diagonal Hatch",
    "diagonal_bwd": "Backward Diagonal Hatch",
    "cross": "Cross Hatch",
    "diagonal_cross": "Cross Diagonal Hatch",
    "dense_1": "Dense 1",
    "dense_2": "Dense 2",
    "dense_3": "Dense 3",
    "dense_4": "Dense 4",
    "dense_5": "Dense 5",
    "dense_6": "Dense 6",
    "dense_7": "Dense 7",
    "centroid": "Centroid Fill",
    "geom_generator": "Geometry Generator",
    "gradient": "Gradient Fill",
    "line_pattern": "Line Pattern Fill",
    "point_pattern": "Point Pattern Fill",
    "random_marker": "Random Marker Fill",
    "raster_image": "Raster Fill",
    "svg": "SVG Fill",
    "shapeburst": "Shapeburst Fill",
    "outline_arrow": "Outline: Arrow",
    "outline_filled": "Outline: Filled Line",
    "outline_hashed": "Outline: Hashed Line",
    "outline_interpolated": "Outline: Interpolated Line",
    "outline_linear_ref": "Outline: Linear Referencing",
    "outline_lineburst": "Outline: Lineburst",
    "outline_marker": "Outline: Marker Line",
    "outline_raster": "Outline: Raster Line",
    "outline_simple": "Outline: Simple Line"
}

def normalize_pattern_key(raw: object) -> str:
    key = str(raw or "").strip()
    return PATTERN_ALIASES.get(key, key)

def qt_pen_style(name: str):
    pen_style = getattr(Qt, "PenStyle", Qt)
    return getattr(pen_style, name)

SIMPLE_FILL_PATTERNS = {
    "Solid",
    "No Brush",
    "Dense 1",
    "Dense 2",
    "Dense 3",
    "Dense 4",
    "Dense 5",
    "Dense 6",
    "Dense 7",
    "Horizontal Hatch",
    "Vertical Hatch",
    "Cross Hatch",
    "Diagonal Hatch",
    "Backward Diagonal Hatch",
    "Cross Diagonal Hatch",
}
