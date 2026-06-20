# -*- coding: utf-8 -*-
from qgis.PyQt.QtCore import Qt

class SymbologyInlineEditor:
    """
    Xử lý sự kiện chỉnh sửa trực tiếp trên ô (Inline Edit) của bảng Symbology,
    đặc biệt là đồng bộ giá trị khi người dùng chọn nhiều hàng cùng lúc.
    """
    def __init__(self, table_widget):
        self.table = table_widget
        self._updating_multi_selection = False
        self._last_multi_selection = set()

    def on_item_changed(self, item):
        """Đồng bộ giá trị khi thuộc tính ký hiệu của thửa đất thay đổi trong vùng chọn nhiều dòng."""
        if getattr(self, "_updating_multi_selection", False):
            return
            
        col = item.column()
        if col not in (3, 4, 5, 6, 7):
            return
            
        row = item.row()
        selected_rows = getattr(self, "_last_multi_selection", set())
        if not selected_rows or row not in selected_rows:
            selected_ranges = self.table.selectedRanges()
            selected_rows = set()
            for r_range in selected_ranges:
                for r_idx in range(r_range.topRow(), r_range.bottomRow() + 1):
                    selected_rows.add(r_idx)
                    
        if row not in selected_rows:
            return
            
        self._updating_multi_selection = True
        self.table.blockSignals(True)
        try:
            if col in (3, 4):
                color_val = item.data(Qt.ItemDataRole.UserRole)
                for r in selected_rows:
                    if r == row:
                        continue
                    target_item = self.table.item(r, col)
                    if target_item:
                        target_item.setData(Qt.ItemDataRole.UserRole, color_val)
            else:
                text_val = item.text()
                for r in selected_rows:
                    if r == row:
                        continue
                    target_item = self.table.item(r, col)
                    if target_item:
                        target_item.setText(text_val)
        finally:
            self.table.blockSignals(False)
            self._updating_multi_selection = False
            self.table.viewport().update()

    def on_selection_changed(self):
        """Theo dõi vùng chọn nhiều dòng khi người dùng bôi đen trước khi bắt đầu edit."""
        selected_ranges = self.table.selectedRanges()
        rows = set()
        for r_range in selected_ranges:
            for r_idx in range(r_range.topRow(), r_range.bottomRow() + 1):
                rows.add(r_idx)
                
        if len(rows) > 1:
            self._last_multi_selection = rows
        elif len(rows) == 1:
            if not self._last_multi_selection or list(rows)[0] not in self._last_multi_selection:
                self._last_multi_selection = set()
        else:
            self._last_multi_selection = set()
