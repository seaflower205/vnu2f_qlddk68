# -*- coding: utf-8 -*-
"""Context-menu coordinator for the symbology table."""

from qgis.PyQt.QtWidgets import QMenu


class SymbologyContextMenuHandler:
    def __init__(self, table, bulk_editor, mapper, owner):
        self.table = table
        self.bulk_editor = bulk_editor
        self.mapper = mapper
        self.owner = owner

    def show_context_menu(self, pos):
        rows = self._selected_rows()
        menu = QMenu(self.owner)

        bulk_actions = {}
        if len(rows) > 1:
            bulk = menu.addMenu(f"Chỉnh sửa {len(rows)} dòng đã chọn")
            bulk_actions = {
                bulk.addAction("Sửa màu nền..."): self.bulk_editor.edit_fill_color,
                bulk.addAction("Sửa màu viền..."): self.bulk_editor.edit_border_color,
                bulk.addAction("Sửa kiểu fill..."): self._edit_pattern,
                bulk.addAction("Sửa nét viền..."): self.bulk_editor.edit_border_width,
                bulk.addAction("Sửa độ mờ..."): self.bulk_editor.edit_opacity,
            }
            menu.addSeparator()

        add_above = menu.addAction("Thêm phía trên")
        add_below = menu.addAction("Thêm phía dưới")
        delete_row = menu.addAction("Xóa hàng")
        menu.addSeparator()
        reset_defaults = menu.addAction("Reset về mặc định")

        action = menu.exec_(self.table.viewport().mapToGlobal(pos))
        if action in bulk_actions:
            bulk_actions[action](rows)
            return

        row = self.table.currentRow()
        if action == add_above:
            self.mapper.add_row_at(row if row >= 0 else 0)
        elif action == add_below:
            self.mapper.add_row_at(row + 1 if row >= 0 else self.table.rowCount())
        elif action == delete_row and row >= 0:
            self.mapper.delete_row_at(row)
        elif action == reset_defaults:
            self.owner.reset_to_defaults()

    def _selected_rows(self):
        rows = set()
        for selected_range in self.table.selectedRanges():
            rows.update(range(selected_range.topRow(), selected_range.bottomRow() + 1))
        return sorted(rows)

    def _edit_pattern(self, rows):
        self.bulk_editor.edit_pattern(rows, self.owner.current_pattern_map)
