# -*- coding: utf-8 -*-
"""Build and apply cadastral categorized symbols."""
from __future__ import annotations

import os

from qgis.PyQt.QtGui import QColor
from qgis.core import (
    QgsCategorizedSymbolRenderer,
    QgsFillSymbol,
    QgsProject,
    QgsRendererCategory,
    QgsSimpleFillSymbolLayer,
)

from .symbology_constants import normalize_pattern_key
from .symbology_outlines import create_outline_layer
from .symbology_patterns import (
    create_background_layer,
    create_pattern_layers,
    parse_config_colors,
    qt_brush_style,
)

INTERNAL_PATTERN_MAP = {
    "Solid": "solid", "No Brush": "no_brush",
    "Horizontal Hatch": "horizontal", "Vertical Hatch": "vertical",
    "Diagonal Hatch": "diagonal_fwd",
    "Backward Diagonal Hatch": "diagonal_bwd", "Cross Hatch": "cross",
    "Cross Diagonal Hatch": "diagonal_cross", "Dense 1": "dense_1",
    "Dense 2": "dense_2", "Dense 3": "dense_3", "Dense 4": "dense_4",
    "Dense 5": "dense_5", "Dense 6": "dense_6", "Dense 7": "dense_7",
    "Centroid Fill": "centroid", "Geometry Generator": "geom_generator",
    "Gradient Fill": "gradient", "Line Pattern Fill": "line_pattern",
    "Point Pattern Fill": "point_pattern", "Random Marker Fill": "random_marker",
    "Raster Fill": "raster_image", "SVG Fill": "svg",
    "Shapeburst Fill": "shapeburst", "Outline: Arrow": "outline_arrow",
    "Outline: Filled Line": "outline_filled",
    "Outline: Hashed Line": "outline_hashed",
    "Outline: Interpolated Line": "outline_interpolated",
    "Outline: Linear Referencing": "outline_linear_ref",
    "Outline: Lineburst": "outline_lineburst",
    "Outline: Marker Line": "outline_marker",
    "Outline: Raster Line": "outline_raster",
    "Outline: Simple Line": "outline_simple",
}


def build_fill_symbol(config: dict) -> QgsFillSymbol:
    """Build a ``QgsFillSymbol`` from persisted land-code configuration."""
    fill, border, pattern_color, _opacity = parse_config_colors(config)
    pattern = INTERNAL_PATTERN_MAP.get(
        normalize_pattern_key(config.get("pattern", "Solid")), "solid"
    )
    width = float(config.get("border_width_mm", 0.26))
    plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if pattern in {"solid", "simple", "no_brush"}:
        layer = QgsSimpleFillSymbolLayer()
        layer.setFillColor(fill if pattern != "no_brush" else QColor(0, 0, 0, 0))
        layer.setStrokeColor(border)
        layer.setStrokeWidth(width)
        style = "NoBrush" if pattern == "no_brush" else "SolidPattern"
        layer.setBrushStyle(qt_brush_style(style))
        return QgsFillSymbol([layer])
    if pattern.startswith("outline_"):
        return QgsFillSymbol([
            create_outline_layer(pattern, fill, border, width, plugin_dir)
        ])
    background = create_background_layer(pattern, fill)
    background.setLocked(True)
    layers = [background]
    extras, replacement = create_pattern_layers(
        pattern, fill, border, pattern_color, width, plugin_dir
    )
    if replacement is not None:
        replacement.setLocked(True)
        layers[0] = replacement
    layers.extend(extras)
    layers.append(create_outline_layer(pattern, fill, border, width, plugin_dir))
    return QgsFillSymbol(layers)


def build_renderer(
    field_name: str, code_configs: list[dict]
) -> QgsCategorizedSymbolRenderer:
    categories = []
    for config in code_configs:
        code = config.get("code", "")
        categories.append(QgsRendererCategory(code, build_fill_symbol(config), code))
    renderer = QgsCategorizedSymbolRenderer(field_name, categories)
    renderer.setSourceSymbol(QgsFillSymbol.createSimple({
        "color": "#e2e8f0", "outline_color": "#94a3b8",
        "outline_width": "0.2",
    }))
    return renderer


def apply_to_layer(layer, field_name: str, code_configs: list[dict]) -> None:
    if not layer or not field_name:
        return
    layer.setRenderer(build_renderer(field_name, code_configs))
    layer.triggerRepaint()
    if hasattr(QgsProject.instance(), "instance"):
        layer.emitStyleChanged()
