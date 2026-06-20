# -*- coding: utf-8 -*-
"""
Tab 4: Rải điểm tọa độ
"""
import os
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QTableWidget,
    QTableWidgetItem,
    QGridLayout,
    QMessageBox,
    QFileDialog,
    QPushButton
)
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsProject,
    QgsVectorLayer,
    QgsCoordinateTransform,
    QgsFeature,
    QgsField,
    QgsPointXY,
    QgsGeometry,
    QgsMapLayerProxyModel
)
from qgis.gui import QgsMapLayerComboBox

from ...common.vn2000_data import populate_crs_combo
from modules.common.ui_utils import create_themed_button, create_file_browser_row
from ...common.qt_compat import (
    MessageBoxNo,
    MessageBoxYes,
    NoEditTriggers,
    SizePolicyExpanding,
    SizePolicyFixed,
)
from ...common.scroll_utils import make_scroll_area
from ..plot_utils import parse_coordinate_file, list_excel_sheets, suggest_column_mappings
from .plot_tab_ui_mixin import PlotTabUiMixin
from .plot_execution_mixin import PlotExecutionMixin

class PlotTab(PlotExecutionMixin, PlotTabUiMixin, QWidget):
    def __init__(self, iface, canvas, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.canvas = canvas
        self.parent_dialog = parent
        self._plot_columns = []
        self._plot_all_data = []
        self._build_ui()



    def _on_plot_browse_clicked(self):
        filters = "Tất cả file hỗ trợ (*.xlsx *.xls *.csv *.txt *.dat *.gpx);;Excel (*.xlsx *.xls);;Văn bản (*.csv *.txt *.dat);;GPX (*.gpx)"
        path, _ = QFileDialog.getOpenFileName(self, "Chọn tệp tọa độ nguồn", "", filters)
        if path:
            self.txt_plot_file.setText(path)
            self._load_plot_file(path)

    def _on_plot_file_config_changed(self):
        self._update_plot_preview_and_mapping()

    def _on_plot_sheet_changed(self):
        self._update_plot_preview_and_mapping()

    def _on_plot_target_type_changed(self, index):
        is_existing = (index == 1)
        self.lbl_plot_target_layer.setVisible(is_existing)
        self.cmb_plot_target_layer.setVisible(is_existing)

    def _on_connect_lines_changed(self, state):
        self.chk_close_polygon.setEnabled(state == 2)

    def _load_plot_file(self, path):
        if not path or not os.path.exists(path):
            return

        ext = os.path.splitext(path)[1].lower()

        # Reset các control
        self.cmb_plot_sheet.blockSignals(True)
        self.cmb_plot_sheet.clear()

        is_excel = ext in ['.xlsx', '.xls']
        is_gpx = ext == '.gpx'
        is_txt = not is_excel and not is_gpx

        self.lbl_delim.setVisible(is_txt)
        self.cmb_plot_delim.setVisible(is_txt)
        self.chk_plot_header.setVisible(not is_gpx)

        self.lbl_sheet.setVisible(is_excel)
        self.cmb_plot_sheet.setVisible(is_excel)

        if is_excel:
            try:
                sheets = list_excel_sheets(path)
                self.cmb_plot_sheet.addItems(sheets)
            except Exception as e:  # noqa: BLE001 — intentional suppress
                QMessageBox.warning(self, "Lỗi đọc Excel", str(e))
                self.cmb_plot_sheet.blockSignals(False)
                return

        self.cmb_plot_sheet.blockSignals(False)
        self._update_plot_preview_and_mapping()

    def _update_plot_preview_and_mapping(self):
        path = self.txt_plot_file.text().strip()
        if not path or not os.path.exists(path):
            return

        ext = os.path.splitext(path)[1].lower()
        delim = self.cmb_plot_delim.currentData()
        has_header = self.chk_plot_header.isChecked()
        sheet_name = self.cmb_plot_sheet.currentText() if ext in ['.xlsx', '.xls'] else None

        try:
            file_type = 'excel' if ext in ['.xlsx', '.xls'] else ('gpx' if ext == '.gpx' else 'text')
            columns, preview_rows, all_data = parse_coordinate_file(
                path, file_type=file_type, delimiter=delim, has_header=has_header, sheet_name=sheet_name
            )

            self._plot_columns = columns
            self._plot_all_data = all_data

            # Cập nhật QTableWidget
            self.tbl_plot_preview.clear()
            self.tbl_plot_preview.setColumnCount(len(columns))
            self.tbl_plot_preview.setHorizontalHeaderLabels(columns)

            self.tbl_plot_preview.setRowCount(len(preview_rows))
            for r_idx, row in enumerate(preview_rows):
                for c_idx, val in enumerate(row):
                    self.tbl_plot_preview.setItem(r_idx, c_idx, QTableWidgetItem(str(val)))

            self.tbl_plot_preview.resizeColumnsToContents()

            # Cập nhật Comboboxes mapping
            self.cmb_col_name.blockSignals(True)
            self.cmb_col_x.blockSignals(True)
            self.cmb_col_y.blockSignals(True)
            self.cmb_col_z.blockSignals(True)
            self.cmb_col_note.blockSignals(True)

            self.cmb_col_name.clear()
            self.cmb_col_x.clear()
            self.cmb_col_y.clear()
            self.cmb_col_z.clear()
            self.cmb_col_note.clear()

            self.cmb_col_z.addItem("--- Không chọn ---", "")
            self.cmb_col_note.addItem("--- Không chọn ---", "")

            for col in columns:
                self.cmb_col_name.addItem(col, col)
                self.cmb_col_x.addItem(col, col)
                self.cmb_col_y.addItem(col, col)
                self.cmb_col_z.addItem(col, col)
                self.cmb_col_note.addItem(col, col)

            suggested = suggest_column_mappings(columns)

            if suggested['name']:
                self.cmb_col_name.setCurrentText(suggested['name'])
            if suggested['x']:
                self.cmb_col_x.setCurrentText(suggested['x'])
            if suggested['y']:
                self.cmb_col_y.setCurrentText(suggested['y'])
            if suggested['z']:
                self.cmb_col_z.setCurrentText(suggested['z'])
            else:
                self.cmb_col_z.setCurrentIndex(0)
            if suggested['note']:
                self.cmb_col_note.setCurrentText(suggested['note'])
            else:
                self.cmb_col_note.setCurrentIndex(0)

            self.cmb_col_name.blockSignals(False)
            self.cmb_col_x.blockSignals(False)
            self.cmb_col_y.blockSignals(False)
            self.cmb_col_z.blockSignals(False)
            self.cmb_col_note.blockSignals(False)

            if ext == '.gpx':
                idx = self.cmb_plot_src_crs.findData("EPSG:4326")
                if idx >= 0:
                    self.cmb_plot_src_crs.setCurrentIndex(idx)

        except Exception as e:  # noqa: BLE001 — intentional suppress
            QMessageBox.critical(self, "Lỗi đọc tệp dữ liệu", f"Không thể phân tích tệp:\n{e}")



    def reset(self):
        """Reset các trường cấu hình rải điểm."""
        self.txt_plot_file.clear()
        self.chk_plot_header.setChecked(True)
        self.cmb_plot_delim.setCurrentIndex(0)
        self.cmb_plot_sheet.clear()
        self.cmb_plot_sheet.setVisible(False)
        self.lbl_sheet.setVisible(False)
        
        self.tbl_plot_preview.clear()
        self.tbl_plot_preview.setRowCount(0)
        self.tbl_plot_preview.setColumnCount(0)
        
        self.cmb_col_name.clear()
        self.cmb_col_x.clear()
        self.cmb_col_y.clear()
        self.cmb_col_z.clear()
        self.cmb_col_note.clear()
        self.cmb_plot_src_crs.setCurrentIndex(0)
        
        self.cmb_plot_target_type.setCurrentIndex(0)
        self.chk_label_name.setChecked(True)
        self.chk_label_z.setChecked(False)
        self.cmb_label_color.setCurrentIndex(0)
        self.chk_connect_lines.setChecked(False)
        self.chk_close_polygon.setChecked(False)
        self.chk_close_polygon.setEnabled(False)
