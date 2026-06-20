# -*- coding: utf-8 -*-
"""
QStyledItemDelegate for cadastral symbology table.
Optimizes performance by drawing swatches with QPainter and lazy-creating editors on double-click.
"""

from qgis.PyQt.QtCore import Qt, QRect, QRectF, QEvent
from qgis.PyQt.QtGui import QColor, QBrush, QPen, QPainter
from qgis.PyQt.QtWidgets import (
    QStyledItemDelegate, QStyle, QColorDialog, QDoubleSpinBox, QSpinBox, QComboBox
)

from ..core.symbology_constants import normalize_pattern_key

class SymbologyDelegate(QStyledItemDelegate):
    def __init__(self, parent=None, patterns_provider=None):
        super().__init__(parent)
        self.patterns_provider = patterns_provider or (lambda: [])

    def _patterns(self) -> list:
        return list(self.patterns_provider())

    def paint(self, painter, option, index):
        if index.column() in (3, 4):
            # Draw standard cell background (selection highlight, hover, etc.)
            option.widget.style().drawControl(
                QStyle.ControlElement.CE_ItemViewItem, option, painter, option.widget
            )

            # Retrieve color hex
            color_hex = index.data(Qt.ItemDataRole.UserRole) or "#FFFFFF"
            color = QColor(color_hex)

            # Swatch rectangle dimensions (40x18), centered
            rect = option.rect
            w, h = 40, 18
            x = rect.x() + (rect.width() - w) // 2
            y = rect.y() + (rect.height() - h) // 2
            swatch_rect = QRect(x, y, w, h)

            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # Fill color
            painter.setBrush(QBrush(color))

            # Border color based on theme
            is_dark = option.palette.window().color().lightness() < 128
            border_color = QColor("#71717a")  # zinc-400
            
            # Bold border if hovered or selected
            if option.state & QStyle.StateFlag.State_Selected:
                border_color = QColor("#fafafa") if is_dark else QColor("#18181b")
            elif option.state & QStyle.StateFlag.State_MouseOver:
                border_color = QColor("#d4d4d8") if is_dark else QColor("#3f3f46")

            painter.setPen(QPen(border_color, 1.0, Qt.PenStyle.SolidLine))

            # Draw rounded swatch
            painter.drawRoundedRect(QRectF(swatch_rect), 4.0, 4.0)

            painter.restore()
        else:
            super().paint(painter, option, index)

    def editorEvent(self, event, model, option, index):
        # Open QColorDialog on mouse release for Column 3 and 4
        if index.column() in (3, 4) and event.type() == QEvent.Type.MouseButtonRelease:
            color_hex = index.data(Qt.ItemDataRole.UserRole) or "#FFFFFF"
            color = QColor(color_hex)

            # Use option.widget as parent
            parent_widget = option.widget
            new_color = QColorDialog.getColor(color, parent_widget, "Chọn màu sắc")
            if new_color.isValid():
                model.setData(index, new_color.name(), Qt.ItemDataRole.UserRole)
                # Force update
                model.dataChanged.emit(index, index)
                return True
        return super().editorEvent(event, model, option, index)

    def createEditor(self, parent, option, index):
        col = index.column()
        if col == 5:
            # Border width spinbox
            editor = QDoubleSpinBox(parent)
            editor.setFrame(False)
            editor.setRange(0.0, 5.0)
            editor.setSingleStep(0.1)
            editor.setDecimals(2)
            return editor
        elif col == 6:
            # Pattern combobox
            editor = QComboBox(parent)
            editor.setFrame(False)
            editor.addItems(self._patterns())
            editor.view().setMinimumWidth(200)
            return editor
        elif col == 7:
            # Opacity spinbox
            editor = QSpinBox(parent)
            editor.setFrame(False)
            editor.setRange(0, 100)
            editor.setSuffix(" %")
            return editor
        return None

    def setEditorData(self, editor, index):
        col = index.column()
        val = index.data(Qt.ItemDataRole.EditRole or Qt.ItemDataRole.DisplayRole)
        if col == 5:
            try:
                editor.setValue(float(val or 0.26))
            except ValueError:
                editor.setValue(0.26)
        elif col == 6:
            if isinstance(editor, QComboBox):
                value = normalize_pattern_key(val)
                i = editor.findText(value)
                if i >= 0:
                    editor.setCurrentIndex(i)
                else:
                    editor.addItem(value)
                    editor.setCurrentIndex(editor.findText(value))
            else:
                editor.setCurrentText(str(val or "Solid"))
        elif col == 7:
            try:
                # Strip '%' if present
                clean_val = str(val).replace("%", "").strip()
                editor.setValue(int(clean_val or 100))
            except ValueError:
                editor.setValue(100)

    def setModelData(self, editor, model, index):
        col = index.column()
        if col == 5:
            model.setData(index, f"{editor.value():.2f}", Qt.ItemDataRole.EditRole)
        elif col == 6:
            text = editor.currentText() if isinstance(editor, QComboBox) else editor.text()
            model.setData(index, normalize_pattern_key(text), Qt.ItemDataRole.EditRole)
        elif col == 7:
            model.setData(index, f"{editor.value()}%", Qt.ItemDataRole.EditRole)
