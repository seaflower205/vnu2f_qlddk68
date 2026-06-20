"""Outline symbol-layer builders."""
from qgis.PyQt.QtGui import QColor
from qgis.core import QgsApplication, QgsSimpleFillSymbolLayer


def create_simple_line(color: QColor, width: float):
    try:
        from qgis.core import QgsSimpleLineSymbolLayer
        layer = QgsSimpleLineSymbolLayer()
        layer.setColor(color)
        layer.setWidth(width)
        return layer
    except Exception:  # noqa: BLE001
        return None


def _set_symbol_layer_color(layer, fill_color: QColor, stroke_color: QColor):
    for setter, color in (
        ("setColor", fill_color), ("setFillColor", fill_color),
        ("setStrokeColor", stroke_color), ("setColor2", fill_color),
    ):
        if hasattr(layer, setter):
            try:
                getattr(layer, setter)(color)
            except Exception:  # noqa: BLE001
                pass
    if hasattr(layer, "interpolatedColor") and hasattr(layer, "setInterpolatedColor"):
        try:
            interpolated = layer.interpolatedColor()
            interpolated.setColor(fill_color)
            layer.setInterpolatedColor(interpolated)
        except Exception:  # noqa: BLE001
            pass
    if hasattr(layer, "subSymbol") and layer.subSymbol():
        symbol = layer.subSymbol()
        if hasattr(symbol, "setColor"):
            symbol.setColor(fill_color)
        for index in range(symbol.symbolLayerCount()):
            _set_symbol_layer_color(symbol.symbolLayer(index), fill_color, stroke_color)


def create_outline_layer(
    pattern: str, fill_color: QColor, border_color: QColor,
    border_width: float, plugin_dir: str,
):
    if not pattern.startswith("outline_"):
        layer = QgsSimpleFillSymbolLayer()
        layer.setFillColor(QColor(0, 0, 0, 0))
        layer.setStrokeColor(border_color)
        layer.setStrokeWidth(border_width)
        return layer
    registry_names = {
        "outline_arrow": "ArrowLine", "outline_filled": "FilledLine",
        "outline_hashed": "HashLine", "outline_interpolated": "InterpolatedLine",
        "outline_linear_ref": "LinearReferencing", "outline_lineburst": "Lineburst",
        "outline_marker": "MarkerLine", "outline_raster": "RasterLine",
        "outline_simple": "SimpleLine",
    }
    registry_name = registry_names.get(pattern, "SimpleLine")
    if registry_name == "RasterLine":
        return create_simple_line(fill_color, border_width)
    metadata = QgsApplication.symbolLayerRegistry().symbolLayerMetadata(registry_name)
    if metadata:
        props = {
            "color": fill_color.name(), "line_color": fill_color.name(),
            "fill_color": fill_color.name(), "outline_color": border_color.name(),
            "width": str(border_width), "line_width": str(border_width),
        }
        if registry_name == "SimpleLine":
            props.update(line_style="solid", joinstyle="bevel", capstyle="square")
        elif registry_name == "HashLine":
            props.update(interval="3.0", hash_length="3.0")
        elif registry_name == "MarkerLine":
            props.update(interval="3.0", placement="interval")
        layer = metadata.createSymbolLayer(props)
        if layer:
            _set_symbol_layer_color(layer, fill_color, border_color)
            for setter in ("setWidth", "setStrokeWidth"):
                if hasattr(layer, setter):
                    try:
                        getattr(layer, setter)(border_width)
                    except Exception:  # noqa: BLE001
                        pass
                    break
            return layer
    return create_simple_line(border_color, border_width)
