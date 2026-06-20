# -*- coding: utf-8 -*-
from qgis.PyQt.QtWidgets import QTableWidgetItem, QTableWidget
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QBrush, QColor
from ...core.symbology_constants import normalize_pattern_key

class Col:
    """Định nghĩa hằng số index các cột trong bảng Symbology để tránh hardcode."""
    NO = 0
    CODE = 1
    NAME = 2
    FILL_COLOR = 3
    BORDER_COLOR = 4
    BORDER_WIDTH = 5
    PATTERN = 6
    OPACITY = 7

class SymbologyTableMapper:
    """
    Helper class chuyên trách thao tác dữ liệu với QTableWidget.
    (Data Mapping & Table Rendering)
    """
    def __init__(self, table_widget: QTableWidget):
        self.table = table_widget

    def load_code_configs_to_table(self, sorted_configs: list[dict], scanned_codes: set[str], current_pattern_map: dict):
        """Hiển thị danh sách cấu hình lên bảng QTableWidget."""
        self.table.setRowCount(0)
        self.table.blockSignals(True)
        self.table.setUpdatesEnabled(False)
        
        try:
            for idx, cfg in enumerate(sorted_configs):
                row = self.table.rowCount()
                self.table.insertRow(row)
                
                code = cfg.get("code", "").strip().upper()
                is_priority = code in scanned_codes
                
                # 0. Số thứ tự
                item_no = QTableWidgetItem(str(row + 1))
                item_no.setFlags(item_no.flags() & ~Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsUserCheckable)
                item_no.setCheckState(Qt.CheckState.Checked)
                if is_priority:
                    font = item_no.font()
                    font.setBold(True)
                    item_no.setFont(font)
                self.table.setItem(row, Col.NO, item_no)
                
                # 1. Mã loại đất
                item_code = QTableWidgetItem(code)
                if is_priority:
                    font = item_code.font()
                    font.setBold(True)
                    item_code.setFont(font)
                    item_code.setForeground(QBrush(QColor("#2563eb")))  # Màu xanh dương đậm
                self.table.setItem(row, Col.CODE, item_code)
                
                # 2. Tên tiếng Việt
                name_vi = cfg.get("name_vi", "")
                item_name = QTableWidgetItem(name_vi)
                if is_priority:
                    font = item_name.font()
                    font.setBold(True)
                    item_name.setFont(font)
                    item_name.setForeground(QBrush(QColor("#2563eb")))
                self.table.setItem(row, Col.NAME, item_name)
                
                # 3. Màu nền
                item_bg = QTableWidgetItem()
                fill_color = cfg.get("fill_color", "#FFFFFF")
                item_bg.setData(Qt.ItemDataRole.UserRole, fill_color)
                self.table.setItem(row, Col.FILL_COLOR, item_bg)
                
                # 4. Màu viền
                item_border = QTableWidgetItem()
                border_color = cfg.get("border_color", "#000000")
                item_border.setData(Qt.ItemDataRole.UserRole, border_color)
                self.table.setItem(row, Col.BORDER_COLOR, item_border)
                
                # 5. Nét viền (mm)
                border_width = float(cfg.get("border_width_mm", 0.26))
                item_width = QTableWidgetItem(f"{border_width:.2f}")
                self.table.setItem(row, Col.BORDER_WIDTH, item_width)
                
                # 6. Kiểu fill
                pat = normalize_pattern_key(cfg.get("pattern", "Solid"))
                item_pattern = QTableWidgetItem(pat)
                self.table.setItem(row, Col.PATTERN, item_pattern)
                
                # 7. Độ mờ (%)
                opacity_pct = int(cfg.get("opacity", 1.0) * 100)
                item_opacity = QTableWidgetItem(f"{opacity_pct}%")
                self.table.setItem(row, Col.OPACITY, item_opacity)

        finally:
            self.table.setUpdatesEnabled(True)
            self.table.blockSignals(False)

    def get_current_code_configs(self, current_pattern_map: dict) -> list[dict]:
        """Thu thập toàn bộ thông tin cấu hình từ bảng QTableWidget."""
        configs = []
        
        for row in range(self.table.rowCount()):
            item_check = self.table.item(row, Col.NO)
            if (
                item_check
                and hasattr(item_check, "checkState")
                and item_check.checkState() == Qt.CheckState.Unchecked
            ):
                continue
            item_code = self.table.item(row, Col.CODE)
            item_name = self.table.item(row, Col.NAME)
            item_bg = self.table.item(row, Col.FILL_COLOR)
            item_border = self.table.item(row, Col.BORDER_COLOR)
            item_width = self.table.item(row, Col.BORDER_WIDTH)
            item_pattern = self.table.item(row, Col.PATTERN)
            item_opacity = self.table.item(row, Col.OPACITY)
            
            if not item_code or not item_name:
                continue
                
            code = item_code.text().strip().upper()
            if not code:
                continue
                
            bg_color = item_bg.data(Qt.ItemDataRole.UserRole) if item_bg else "#FFFFFF"
            if not bg_color:
                bg_color = "#FFFFFF"
            border_color = item_border.data(Qt.ItemDataRole.UserRole) if item_border else "#000000"
            if not border_color:
                border_color = "#000000"
                
            try:
                width_val = float(item_width.text()) if item_width else 0.26
            except ValueError:
                width_val = 0.26
                
            pat_text = item_pattern.text() if item_pattern else "Solid"
            norm_pat = normalize_pattern_key(pat_text)
            pattern_val = current_pattern_map.get(norm_pat, "solid")
            
            try:
                opacity_str = item_opacity.text().replace("%", "").strip() if item_opacity else "100"
                opacity_val = float(opacity_str) / 100.0
            except ValueError:
                opacity_val = 1.0
                
            configs.append({
                "code": code,
                "name_vi": item_name.text().strip(),
                "fill_color": bg_color,
                "border_color": border_color,
                "border_width_mm": width_val,
                "pattern": pattern_val,
                "opacity": opacity_val
            })
            
        return configs

    def add_row_at(self, row: int):
        """Thêm một hàng trống tại vị trí mong muốn."""
        self.table.blockSignals(True)
        self.table.insertRow(row)
        
        # Set default items
        item_no = QTableWidgetItem("")
        item_no.setFlags(item_no.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, Col.NO, item_no)
        self.table.setItem(row, Col.CODE, QTableWidgetItem("MOI"))
        self.table.setItem(row, Col.NAME, QTableWidgetItem("Mô tả mới"))
        
        item_bg = QTableWidgetItem()
        item_bg.setData(Qt.ItemDataRole.UserRole, "#FFFFFF")
        self.table.setItem(row, Col.FILL_COLOR, item_bg)
        
        item_border = QTableWidgetItem()
        item_border.setData(Qt.ItemDataRole.UserRole, "#000000")
        self.table.setItem(row, Col.BORDER_COLOR, item_border)
        
        self.table.setItem(row, Col.BORDER_WIDTH, QTableWidgetItem("0.26"))
        self.table.setItem(row, Col.PATTERN, QTableWidgetItem("Solid"))
        self.table.setItem(row, Col.OPACITY, QTableWidgetItem("100%"))
        
        self.table.blockSignals(False)
        self.update_row_numbers()

    def delete_row_at(self, row: int):
        """Xóa hàng và cập nhật số thứ tự."""
        self.table.removeRow(row)
        self.update_row_numbers()

    def update_row_numbers(self):
        """Cập nhật lại toàn bộ cột số thứ tự (#)."""
        for row in range(self.table.rowCount()):
            item = self.table.item(row, Col.NO)
            if item:
                item.setText(str(row + 1))
