# -*- coding: utf-8 -*-
"""Bulk editing operations for selected symbology rows."""

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import QColorDialog, QInputDialog

from .table_mapper import Col


class SymbologyBulkEditor:
    def __init__(self, table, parent=None):
        self.table = table
        self.parent = parent or table

    def edit_fill_color(self, rows):
        self._edit_color(rows, Col.FILL_COLOR, "Chọn màu nền")

    def edit_border_color(self, rows):
        self._edit_color(rows, Col.BORDER_COLOR, "Chọn màu viền")

    def _edit_color(self, rows, column, title):
        current = self.table.item(rows[0], column)
        initial = current.data(Qt.ItemDataRole.UserRole) if current else "#FFFFFF"
        color = QColorDialog.getColor(QColor(initial or "#FFFFFF"), self.parent, title)
        if color.isValid():
            self._set_rows(rows, column, role_value=color.name())

    def edit_border_width(self, rows):
        value, accepted = QInputDialog.getDouble(
            self.parent,
            "Nét viền",
            "Độ rộng (mm):",
            0.26,
            0.0,
            20.0,
            2,
        )
        if accepted:
            self._set_rows(rows, Col.BORDER_WIDTH, text=f"{value:.2f}")

    def edit_opacity(self, rows):
        value, accepted = QInputDialog.getInt(
            self.parent,
            "Độ mờ",
            "Độ mờ (%):",
            100,
            0,
            100,
        )
        if accepted:
            self._set_rows(rows, Col.OPACITY, text=f"{value}%")

    def edit_pattern(self, rows, pattern_map):
        labels = list(pattern_map)
        value, accepted = QInputDialog.getItem(
            self.parent,
            "Kiểu fill",
            "Chọn kiểu fill:",
            labels,
            0,
            False,
        )
        if accepted:
            self._set_rows(rows, Col.PATTERN, text=value)

    def _set_rows(self, rows, column, *, text=None, role_value=None):
        self.table.blockSignals(True)
        try:
            for row in rows:
                item = self.table.item(row, column)
                if not item:
                    continue
                if text is not None:
                    item.setText(text)
                if role_value is not None:
                    item.setData(Qt.ItemDataRole.UserRole, role_value)
        finally:
            self.table.blockSignals(False)
            self.table.viewport().update()
