# -*- coding: utf-8 -*-
from qgis.PyQt.QtCore import Qt, QObject, QEvent
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import QColorDialog

class TableSelectionPreserver(QObject):
    """
    Xử lý các sự kiện click chuột trên QTableWidget,
    đặc biệt là để bảo toàn Selection khi click vào các ô màu.
    """
    def __init__(self, table, parent_tab):
        super().__init__(table)
        self.table = table
        self.parent_tab = parent_tab

    def eventFilter(self, obj, event):
        if obj == self.table.viewport():
            if event.type() == QEvent.Type.MouseButtonPress:
                pos = event.pos()
                index = self.table.indexAt(pos)
                if index.isValid():
                    col = index.column()
                    row = index.row()
                    if col in (3, 4, 5, 6, 7):
                        selected_rows = set()
                        for r_range in self.table.selectedRanges():
                            for r_idx in range(r_range.topRow(), r_range.bottomRow() + 1):
                                selected_rows.add(r_idx)
                        
                        if len(selected_rows) > 1 and row in selected_rows:
                            self.parent_tab._last_multi_selection = selected_rows
                            if col in (3, 4):
                                # Open color dialog immediately
                                item = self.table.item(row, col)
                                color_hex = item.data(Qt.ItemDataRole.UserRole) or "#FFFFFF"
                                color = QColorDialog.getColor(QColor(color_hex), self.table.window(), "Chọn màu sắc")
                                if color.isValid():
                                    self.table.blockSignals(True)
                                    for r in selected_rows:
                                        r_item = self.table.item(r, col)
                                        if r_item:
                                            r_item.setData(Qt.ItemDataRole.UserRole, color.name())
                                    self.table.blockSignals(False)
                                    self.table.itemChanged.emit(item)
                                    self.table.viewport().update()
                                return True # Consume the press event, keeping the selection!
                            else:
                                # Start editing programmatically, bypasses selection clearing
                                self.table.edit(index)
                                return True # Consume the press event!
        return super().eventFilter(obj, event)
