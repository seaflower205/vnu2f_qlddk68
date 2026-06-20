# -*- coding: utf-8 -*-
"""Geometry helpers for overview maps."""


def expanded_extent(rect, margin_percent):
    from qgis.core import QgsRectangle
    result = QgsRectangle(rect)
    result.grow(max(result.width() * margin_percent / 100.0, result.height() * margin_percent / 100.0, 1e-9))
    return result


def extent_is_broader(context, main):
    if context is None or main is None or context.isEmpty() or main.isEmpty():
        return False
    contains = (context.xMinimum() <= main.xMinimum() and context.yMinimum() <= main.yMinimum()
                and context.xMaximum() >= main.xMaximum() and context.yMaximum() >= main.yMaximum())
    return contains and (context.width() > main.width() * 1.05 or context.height() > main.height() * 1.05)
