# -*- coding: utf-8 -*-
"""Helpers shared by map packaging workflows."""

import os
from qgis.PyQt.QtCore import QDir
from qgis.core import QgsLayoutItemPicture, QgsProviderRegistry, QgsSymbolLayerUtils

_cached_stock_svgs = None


def _get_stock_svgs():
    global _cached_stock_svgs
    if _cached_stock_svgs is None:
        _cached_stock_svgs = [QDir(path).canonicalPath() for path in QgsSymbolLayerUtils.listSvgFiles()]
    return _cached_stock_svgs


def _symbol_layers_from_symbol(symbol):
    layers = []
    for layer in symbol.symbolLayers():
        if layer.subSymbol():
            layers.extend(_symbol_layers_from_symbol(layer.subSymbol()))
        layers.append(layer)
    return layers


def _get_path(layer):
    for getter in ("path", "svgFilePath", "imageFilePath"):
        try:
            return getattr(layer, getter)()
        except AttributeError:
            continue
    return None


def _set_path(layer, new_path):
    for setter in ("setPath", "setSvgFilePath", "setImageFilePath"):
        try:
            getattr(layer, setter)(new_path)
            return
        except AttributeError:
            continue


def _collect_symbol_paths(project, context):
    result, stock = {}, _get_stock_svgs()
    for layer in project.mapLayers().values():
        try:
            symbols = layer.renderer().symbols(context)
        except AttributeError:
            continue
        for symbol in symbols:
            for symbol_layer in _symbol_layers_from_symbol(symbol):
                raw = _get_path(symbol_layer)
                path = QDir(raw).canonicalPath() if raw else ""
                if path and os.path.exists(path) and path not in stock:
                    result[symbol_layer] = path
    for layout in project.layoutManager().printLayouts():
        model = layout.itemsModel()
        for row in range(model.rowCount()):
            item = model.itemFromIndex(model.index(row, 0))
            if isinstance(item, QgsLayoutItemPicture):
                candidates = [(item, item.picturePath())]
            else:
                try:
                    candidates = [(layer, _get_path(layer)) for layer in _symbol_layers_from_symbol(item.symbol())]
                except AttributeError:
                    continue
            for target, raw in candidates:
                path = QDir(raw).canonicalPath() if raw else ""
                if path and os.path.exists(path) and path not in stock:
                    result[target] = path
    return result


def _is_in_dir(parent, child):
    parent, child = os.path.abspath(parent), os.path.abspath(child)
    try:
        return os.path.commonpath([parent, child]) == parent
    except ValueError:
        return False


def _get_source_info(layer):
    provider = layer.dataProvider()
    if provider is None:
        return None
    parts = QgsProviderRegistry.instance().decodeUri(provider.name(), layer.source())
    path = QDir(parts.get("path", "")).canonicalPath()
    return (path, parts.get("layerName"), None) if path else None
