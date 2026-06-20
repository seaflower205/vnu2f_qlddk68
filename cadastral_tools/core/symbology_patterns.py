"""Fill-pattern builders extracted from :mod:`symbology_manager`."""
from __future__ import annotations

import os

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor
from qgis.core import (
    QgsFillSymbol,
    QgsLinePatternFillSymbolLayer,
    QgsMarkerSymbol,
    QgsPointPatternFillSymbolLayer,
    QgsSimpleFillSymbolLayer,
)


def parse_config_colors(config: dict) -> tuple:
    opacity = float(config.get("opacity", 1.0))
    fill_color = QColor(config.get("fill_color", "#FFFFFF"))
    border_color = QColor(config.get("border_color", "#000000"))
    pattern_color = QColor(config.get("pattern_color") or border_color.name())
    for color in (fill_color, border_color, pattern_color):
        color.setAlphaF(opacity)
    return fill_color, border_color, pattern_color, opacity


def qt_brush_style(name: str):
    namespace = getattr(Qt, "BrushStyle", None)
    return getattr(namespace, name) if namespace is not None else getattr(Qt, name)


def create_background_layer(pattern: str, fill_color: QColor):
    layer = QgsSimpleFillSymbolLayer()
    layer.setFillColor(fill_color)
    layer.setStrokeColor(QColor(0, 0, 0, 0))
    layer.setStrokeWidth(0.0)
    if pattern == "no_brush":
        layer.setFillColor(QColor(0, 0, 0, 0))
        layer.setBrushStyle(qt_brush_style("NoBrush"))
    else:
        layer.setBrushStyle(qt_brush_style("SolidPattern"))
    return layer


def _svg_pattern(plugin_dir: str, fill_color: QColor) -> list:
    try:
        from qgis.core import QgsSVGFillSymbolLayer
        layer = QgsSVGFillSymbolLayer()
        path = os.path.join(plugin_dir, "icon_cad.svg")
        if os.path.exists(path):
            layer.setSvgFilePath(path)
        layer.setSvgWidth(6.0)
        return [layer]
    except Exception:  # noqa: BLE001
        layer = QgsSimpleFillSymbolLayer()
        layer.setFillColor(fill_color)
        return [layer]


def _raster_pattern(plugin_dir: str) -> list:
    try:
        try:
            from qgis.core import QgsRasterImageFillSymbolLayer
            layer = QgsRasterImageFillSymbolLayer()
        except ImportError:
            from qgis.core import QgsRasterFillSymbolLayer
            layer = QgsRasterFillSymbolLayer()
        path = os.path.join(plugin_dir, "icon.png")
        if os.path.exists(path):
            layer.setImageFilePath(path)
        return [layer]
    except Exception:  # noqa: BLE001
        return []


def _geometry_generator(fill_color, border_color, border_width) -> list:
    try:
        from qgis.core import QgsGeometryGeneratorSymbolLayer
        layer = QgsGeometryGeneratorSymbolLayer.create(
            {"geometryModifier": "$geometry", "symbolType": "Fill"}
        )
        if layer is not None:
            layer.setSubSymbol(QgsFillSymbol.createSimple({
                "color": fill_color.name(),
                "outline_color": border_color.name(),
                "outline_width": str(border_width),
            }))
            return [layer]
    except Exception:  # noqa: BLE001
        pass
    return []


def _marker_fill(class_name: str, pattern_color: QColor) -> list:
    try:
        from qgis import core
        layer = getattr(core, class_name)()
        marker = QgsMarkerSymbol.createSimple({
            "name": "circle", "color": pattern_color.name(),
            "size": "1.0", "outline_style": "no",
        })
        layer.setSubSymbol(marker)
        return [layer]
    except Exception:  # noqa: BLE001
        return []


def _centroid_fill(pattern_color: QColor, border_color: QColor) -> list:
    try:
        from qgis.core import QgsCentroidFillSymbolLayer
        layer = QgsCentroidFillSymbolLayer()
        layer.setSubSymbol(QgsMarkerSymbol.createSimple({
            "name": "circle", "color": pattern_color.name(), "size": "2.0",
            "outline_color": border_color.name(), "outline_width": "0.2",
        }))
        return [layer]
    except Exception:  # noqa: BLE001
        return []


def _replacement_layer(pattern: str, fill_color: QColor):
    try:
        if pattern == "gradient":
            from qgis.core import QgsGradientFillSymbolLayer
            layer = QgsGradientFillSymbolLayer()
            second = QColor(255, 255, 255, 255)
        else:
            from qgis.core import QgsShapeburstFillSymbolLayer
            layer = QgsShapeburstFillSymbolLayer()
            second = QColor(255, 255, 255, 0)
        layer.setColor(fill_color)
        layer.setColor2(second)
        return layer
    except Exception:  # noqa: BLE001
        return None


def _line_pattern(angle: float, color: QColor, width: float = 0.18):
    layer = QgsLinePatternFillSymbolLayer()
    layer.setLineAngle(angle)
    layer.setDistance(3.0)
    layer.setLineWidth(width)
    layer.setColor(color)
    return layer


def create_pattern_layers(
    pattern: str, fill_color: QColor, border_color: QColor,
    pattern_color: QColor, border_width: float, plugin_dir: str,
) -> tuple[list, object]:
    if pattern in {"solid", "simple", "no_brush"}:
        if pattern == "no_brush":
            return [], None
        layer = QgsSimpleFillSymbolLayer()
        layer.setFillColor(pattern_color)
        layer.setStrokeColor(QColor(0, 0, 0, 0))
        layer.setStrokeWidth(0.0)
        layer.setBrushStyle(qt_brush_style("NoBrush"))
        return [layer], None
    dense_styles = {
        "dense_1": "Dense1Pattern", "dense_2": "Dense2Pattern",
        "dense_3": "Dense3Pattern", "dense_4": "Dense4Pattern",
        "dense_5": "Dense5Pattern", "dense_6": "Dense6Pattern",
        "dense_7": "Dense7Pattern", "diagonal_cross": "DiagCrossPattern",
    }
    if pattern in dense_styles:
        layer = QgsSimpleFillSymbolLayer()
        layer.setFillColor(pattern_color)
        layer.setStrokeColor(QColor(0, 0, 0, 0))
        layer.setStrokeWidth(0.0)
        layer.setBrushStyle(qt_brush_style(dense_styles[pattern]))
        return [layer], None
    if pattern == "dots":
        layer = QgsPointPatternFillSymbolLayer()
        layer.setDistanceX(3.0)
        layer.setDistanceY(3.0)
        layer.setSubSymbol(QgsMarkerSymbol.createSimple({
            "name": "circle", "color": pattern_color.name(),
            "size": "0.8", "outline_style": "no",
        }))
        return [layer], None
    angles = {"horizontal": 0.0, "vertical": 90.0,
              "diagonal_fwd": 45.0, "diagonal_bwd": 135.0}
    if pattern in angles:
        return [_line_pattern(angles[pattern], pattern_color)], None
    if pattern == "cross":
        return [_line_pattern(0.0, pattern_color),
                _line_pattern(90.0, pattern_color)], None
    if pattern == "centroid":
        return _centroid_fill(pattern_color, border_color), None
    if pattern == "geom_generator":
        return _geometry_generator(fill_color, border_color, border_width), None
    if pattern in {"gradient", "shapeburst"}:
        return [], _replacement_layer(pattern, fill_color)
    if pattern == "line_pattern":
        layer = _line_pattern(0.0, pattern_color, border_width)
        layer.setDistance(6.0)
        return [layer], None
    if pattern == "point_pattern":
        layers = _marker_fill("QgsPointPatternFillSymbolLayer", pattern_color)
        if layers:
            layers[0].setDistanceX(3.0)
            layers[0].setDistanceY(3.0)
        return layers, None
    if pattern == "random_marker":
        return _marker_fill("QgsRandomMarkerFillSymbolLayer", pattern_color), None
    if pattern == "raster_image":
        return _raster_pattern(plugin_dir), None
    if pattern == "svg":
        return _svg_pattern(plugin_dir, fill_color), None
    return [], None
