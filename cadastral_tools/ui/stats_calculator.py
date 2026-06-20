# -*- coding: utf-8 -*-
from qgis.PyQt.QtGui import QColor, QBrush
from qgis.PyQt.QtWidgets import QTableWidgetItem

class StatsCalculator:
    """Manages table rendering and sorting logic for statistics data."""
    
    @staticmethod
    def sort_data(stats_data, logical_index, sort_asc):
        """Sắp xếp dữ liệu thống kê."""
        if not stats_data:
            return stats_data
            
        keys = ["code", "name_vi", "count", "area_m2", "area_ha", "percentage"]
        sort_key = keys[logical_index]
        stats_data.sort(key=lambda x: x[sort_key], reverse=not sort_asc)
        return stats_data

    @staticmethod
    def rebuild_table(table_widget, stats_data):
        """Xây dựng dữ liệu hiển thị lên QTableWidget từ stats_data."""
        table_widget.setRowCount(0)
        
        if not stats_data:
            return
            
        total_count = 0
        total_area_m2 = 0.0
        
        for data in stats_data:
            row = table_widget.rowCount()
            table_widget.insertRow(row)
            
            # 0. Mã loại đất kèm màu sắc
            item_code = QTableWidgetItem(data["code"])
            item_code.setBackground(QColor(data["color"]))
            
            # Chọn màu chữ tương phản dựa trên màu nền để người dùng dễ đọc nhãn
            rgb = QColor(data["color"])
            brightness = (rgb.red() * 299 + rgb.green() * 587 + rgb.blue() * 114) / 1000
            if brightness < 128:
                item_code.setForeground(QBrush(QColor("#ffffff")))
            else:
                item_code.setForeground(QBrush(QColor("#000000")))
            
            table_widget.setItem(row, 0, item_code)
            
            # 1. Tên loại đất
            table_widget.setItem(row, 1, QTableWidgetItem(data["name_vi"]))
            
            # 2. Số thửa
            table_widget.setItem(row, 2, QTableWidgetItem(f"{data['count']:,}"))
            
            # 3. Tổng diện tích (m²)
            table_widget.setItem(row, 3, QTableWidgetItem(f"{data['area_m2']:,.1f}"))
            
            # 4. Tổng diện tích (ha)
            table_widget.setItem(row, 4, QTableWidgetItem(f"{data['area_ha']:,.4f}"))
            
            # 5. Tỷ lệ (%)
            table_widget.setItem(row, 5, QTableWidgetItem(f"{data['percentage']:.2f}%"))
            
            total_count += data["count"]
            total_area_m2 += data["area_m2"]
            
        # Thêm dòng tổng cộng dưới cùng
        row_total = table_widget.rowCount()
        table_widget.insertRow(row_total)
        
        bold_font = table_widget.font()
        bold_font.setBold(True)
        
        item_total_lbl = QTableWidgetItem("TỔNG CỘNG")
        item_total_lbl.setFont(bold_font)
        table_widget.setItem(row_total, 0, item_total_lbl)
        table_widget.setItem(row_total, 1, QTableWidgetItem(""))
        
        item_tot_cnt = QTableWidgetItem(f"{total_count:,}")
        item_tot_cnt.setFont(bold_font)
        table_widget.setItem(row_total, 2, item_tot_cnt)
        
        item_tot_m2 = QTableWidgetItem(f"{total_area_m2:,.1f}")
        item_tot_m2.setFont(bold_font)
        table_widget.setItem(row_total, 3, item_tot_m2)
        
        item_tot_ha = QTableWidgetItem(f"{total_area_m2 / 10000.0:,.4f}")
        item_tot_ha.setFont(bold_font)
        table_widget.setItem(row_total, 4, item_tot_ha)
        
        item_tot_pct = QTableWidgetItem("100.00%")
        item_tot_pct.setFont(bold_font)
        table_widget.setItem(row_total, 5, item_tot_pct)
        
        # Đánh dấu nền màu dòng tổng cộng khác biệt nhẹ
        bg_col = QColor("#27272a") if table_widget.palette().color(table_widget.backgroundRole()).value() < 128 else QColor("#f4f4f5")
        for col in range(6):
            table_widget.item(row_total, col).setBackground(bg_col)
