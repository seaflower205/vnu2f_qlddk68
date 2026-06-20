# -*- coding: utf-8 -*-
"""
Utility for QScrollArea helper functions.
Ensures unified scroll UI styling and proper widget parenting to avoid QGIS C++ garbage collection crashes.
"""

from qgis.PyQt.QtWidgets import QScrollArea, QWidget, QVBoxLayout
from .qt_compat import FrameNoFrame

def make_scroll_area(parent, spacing=14, margins=(0, 0, 0, 0), stylesheet=None):
    """
    Creates a pre-configured QScrollArea wrapping a QWidget container with a layout.
    Ensures the widgets are explicitly parented to prevent garbage collection crashes.
    """
    scroll = QScrollArea(parent)
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(FrameNoFrame)
    if stylesheet:
        scroll.setStyleSheet(stylesheet)

    container = QWidget(scroll)
    scroll.setWidget(container)

    container_layout = QVBoxLayout(container)
    container_layout.setContentsMargins(*margins)
    container_layout.setSpacing(spacing)

    return scroll, container, container_layout

def wrap_widget_in_scroll(widget, parent=None, stylesheet=None):
    """
    Wraps an existing widget in a pre-configured QScrollArea.
    Ensures the QScrollArea is parented to parent (or widget if parent is None).
    """
    p = parent if parent is not None else widget
    scroll = QScrollArea(p)
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(FrameNoFrame)
    if stylesheet:
        scroll.setStyleSheet(stylesheet)
    scroll.setWidget(widget)
    return scroll
