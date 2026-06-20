# -*- coding: utf-8 -*-
"""
Widget nút chọn màu (Color Swatch Button).
Hiển thị màu hiện tại và mở hộp thoại chọn màu QColorDialog khi click.
"""

from qgis.PyQt.QtWidgets import QPushButton, QColorDialog
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import pyqtSignal

class ColorSwatchButton(QPushButton):
    """Nút bấm thể hiện màu sắc, khi click sẽ mở QColorDialog chọn màu mới."""
    
    color_changed = pyqtSignal(QColor)

    def __init__(self, color_val="#FFFFFF", parent=None):
        super().__init__(parent)
        self.setObjectName("colorSwatchButton")
        self.setFixedWidth(40)
        self.setFixedHeight(24)
        self.setFlat(True)
        
        if isinstance(color_val, str):
            self._color = QColor(color_val)
        else:
            self._color = color_val

        self.clicked.connect(self._on_clicked)
        self.update_style()

    @property
    def color(self) -> QColor:
        return self._color

    @color.setter
    def color(self, val):
        if isinstance(val, str):
            self._color = QColor(val)
        else:
            self._color = val
        self.update_style()
        self.color_changed.emit(self._color)

    def hex_color(self) -> str:
        return self._color.name()

    def _on_clicked(self):
        new_color = QColorDialog.getColor(self._color, self, "Chọn màu sắc")
        if new_color.isValid():
            self.color = new_color

    def update_style(self):
        hex_val = self._color.name()
        # Đảm bảo viền mỏng bo góc nhẹ và chỉ áp dụng cho chính nút này, tránh cascade sang QColorDialog
        self.setStyleSheet(f"""
            QPushButton#colorSwatchButton {{
                background-color: {hex_val};
                border: 1px solid #71717a;
                border-radius: 4px;
            }}
            QPushButton#colorSwatchButton:hover {{
                border: 1.5px solid #18181b;
            }}
        """)
