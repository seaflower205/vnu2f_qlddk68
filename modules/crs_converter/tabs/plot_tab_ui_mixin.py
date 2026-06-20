"""Mechanically extracted responsibilities from plot_tab.py."""

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


class PlotTabUiMixin:
    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        scroll_area, content_widget, layout = make_scroll_area(
            self,
            spacing=10,
            margins=(14, 10, 14, 10),
            stylesheet="QScrollArea { background-color: transparent; border: none; } QScrollArea > QWidget > QWidget { background-color: transparent; }"
        )

        # 1. Cấu hình file nguồn
        self.grp_plot_file = QGroupBox("Cấu hình Tệp số liệu đầu vào", self)
        file_layout = QVBoxLayout(self.grp_plot_file)
        file_layout.setContentsMargins(18, 20, 18, 18)
        file_layout.setSpacing(10)

        row_file, self.txt_plot_file, self.btn_plot_browse = create_file_browser_row(
            placeholder="Chọn file .xlsx, .xls, .csv, .txt, .dat, .gpx...",
            readonly=True,
            parent=self.grp_plot_file
        )
        row_file.insertWidget(0, QLabel("Tệp số liệu:"))
        self.btn_plot_browse.clicked.connect(self._on_plot_browse_clicked)
        file_layout.addLayout(row_file)

        row_opts = QHBoxLayout()
        self.chk_plot_header = QCheckBox("Có dòng tiêu đề (Header)", self.grp_plot_file)
        self.chk_plot_header.setChecked(True)
        self.chk_plot_header.stateChanged.connect(self._on_plot_file_config_changed)
        row_opts.addWidget(self.chk_plot_header)

        self.lbl_delim = QLabel("Phân cách:")
        self.cmb_plot_delim = QComboBox(self.grp_plot_file)
        self.cmb_plot_delim.addItem("Dấu phẩy (,)", ",")
        self.cmb_plot_delim.addItem("Dấu chấm phẩy (;)", ";")
        self.cmb_plot_delim.addItem("Tab (\\t)", "\t")
        self.cmb_plot_delim.addItem("Khoảng trắng (Space)", " ")
        self.cmb_plot_delim.currentIndexChanged.connect(self._on_plot_file_config_changed)
        row_opts.addWidget(self.lbl_delim)
        row_opts.addWidget(self.cmb_plot_delim)

        self.lbl_sheet = QLabel("Sheet:")
        self.cmb_plot_sheet = QComboBox(self.grp_plot_file)
        self.cmb_plot_sheet.setVisible(False)
        self.lbl_sheet.setVisible(False)
        self.cmb_plot_sheet.currentIndexChanged.connect(self._on_plot_sheet_changed)
        row_opts.addWidget(self.lbl_sheet)
        row_opts.addWidget(self.cmb_plot_sheet)

        row_opts.addStretch()
        file_layout.addLayout(row_opts)
        layout.addWidget(self.grp_plot_file)

        # 2. Preview bảng dữ liệu
        self.grp_plot_preview = QGroupBox("Xem trước dữ liệu (5 dòng đầu)", self)
        prev_layout = QVBoxLayout(self.grp_plot_preview)
        prev_layout.setContentsMargins(12, 18, 12, 12)

        self.tbl_plot_preview = QTableWidget(self.grp_plot_preview)
        self.tbl_plot_preview.setRowCount(0)
        self.tbl_plot_preview.setColumnCount(0)
        self.tbl_plot_preview.setMinimumHeight(130)
        self.tbl_plot_preview.setMaximumHeight(190)
        self.tbl_plot_preview.setEditTriggers(NoEditTriggers)
        prev_layout.addWidget(self.tbl_plot_preview)
        layout.addWidget(self.grp_plot_preview)

        # 3. Ánh xạ cột & CRS
        self.grp_plot_mapping = QGroupBox("Cấu hình Ánh xạ cột & Hệ tọa độ nguồn", self)
        map_layout = QGridLayout(self.grp_plot_mapping)
        map_layout.setContentsMargins(18, 20, 18, 18)
        map_layout.setHorizontalSpacing(12)
        map_layout.setVerticalSpacing(10)
        map_layout.setColumnStretch(1, 1)
        map_layout.setColumnStretch(3, 2)

        map_layout.addWidget(QLabel("Tên/Số hiệu điểm:"), 0, 0)
        self.cmb_col_name = QComboBox(self.grp_plot_mapping)
        map_layout.addWidget(self.cmb_col_name, 0, 1)

        map_layout.addWidget(QLabel("Tọa độ X (Easting):"), 1, 0)
        self.cmb_col_x = QComboBox(self.grp_plot_mapping)
        map_layout.addWidget(self.cmb_col_x, 1, 1)

        map_layout.addWidget(QLabel("Tọa độ Y (Northing):"), 2, 0)
        self.cmb_col_y = QComboBox(self.grp_plot_mapping)
        map_layout.addWidget(self.cmb_col_y, 2, 1)

        map_layout.addWidget(QLabel("Độ cao Z (Tùy chọn):"), 0, 2)
        self.cmb_col_z = QComboBox(self.grp_plot_mapping)
        map_layout.addWidget(self.cmb_col_z, 0, 3)

        map_layout.addWidget(QLabel("Ghi chú (Tùy chọn):"), 1, 2)
        self.cmb_col_note = QComboBox(self.grp_plot_mapping)
        map_layout.addWidget(self.cmb_col_note, 1, 3)

        map_layout.addWidget(QLabel("Hệ tọa độ nguồn:"), 2, 2)
        self.cmb_plot_src_crs = QComboBox(self.grp_plot_mapping)
        self.cmb_plot_src_crs.setMinimumWidth(280)
        from qgis.PyQt.QtCore import QTimer
        QTimer.singleShot(0, lambda: populate_crs_combo(self.cmb_plot_src_crs))
        map_layout.addWidget(self.cmb_plot_src_crs, 2, 3)

        layout.addWidget(self.grp_plot_mapping)

        # 4. Tùy chọn rải điểm & nhãn
        self.grp_plot_output = QGroupBox("Cấu hình rải điểm & Vẽ nhãn", self)
        out_layout = QGridLayout(self.grp_plot_output)
        out_layout.setContentsMargins(18, 20, 18, 18)
        out_layout.setHorizontalSpacing(12)
        out_layout.setVerticalSpacing(10)
        out_layout.setColumnStretch(1, 1)
        out_layout.setColumnStretch(3, 1)

        out_layout.addWidget(QLabel("Đích đến:"), 0, 0)
        self.cmb_plot_target_type = QComboBox(self.grp_plot_output)
        self.cmb_plot_target_type.addItems([
            "Tạo lớp ảo mới (Memory Layer)",
            "Ghi trực tiếp vào lớp đang chọn"
        ])
        self.cmb_plot_target_type.currentIndexChanged.connect(self._on_plot_target_type_changed)
        out_layout.addWidget(self.cmb_plot_target_type, 0, 1)

        self.lbl_plot_target_layer = QLabel("Chọn lớp Point:")
        self.cmb_plot_target_layer = QgsMapLayerComboBox(self.grp_plot_output)
        self.cmb_plot_target_layer.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.cmb_plot_target_layer.setVisible(False)
        self.lbl_plot_target_layer.setVisible(False)
        out_layout.addWidget(self.lbl_plot_target_layer, 0, 2)
        out_layout.addWidget(self.cmb_plot_target_layer, 0, 3)

        self.chk_label_name = QCheckBox("Hiển thị nhãn tên điểm", self.grp_plot_output)
        self.chk_label_name.setChecked(True)
        out_layout.addWidget(self.chk_label_name, 1, 0)

        self.chk_label_z = QCheckBox("Hiển thị nhãn độ cao Z", self.grp_plot_output)
        out_layout.addWidget(self.chk_label_z, 1, 1)

        out_layout.addWidget(QLabel("Màu nhãn:"), 1, 2)
        self.cmb_label_color = QComboBox(self.grp_plot_output)
        self.cmb_label_color.addItem("Đỏ", "#ef4444")
        self.cmb_label_color.addItem("Xanh lá", "#16a34a")
        self.cmb_label_color.addItem("Xanh dương", "#2563eb")
        self.cmb_label_color.addItem("Vàng", "#ca8a04")
        out_layout.addWidget(self.cmb_label_color, 1, 3)

        self.chk_connect_lines = QCheckBox("Nối các điểm thành đường (LineString)", self.grp_plot_output)
        self.chk_connect_lines.stateChanged.connect(self._on_connect_lines_changed)
        out_layout.addWidget(self.chk_connect_lines, 2, 0, 1, 2)

        self.chk_close_polygon = QCheckBox("Khép góc thành vùng (Polygon)", self.grp_plot_output)
        self.chk_close_polygon.setEnabled(False)
        out_layout.addWidget(self.chk_close_polygon, 2, 2, 1, 2)

        layout.addWidget(self.grp_plot_output)

        layout.addStretch()
        main_layout.addWidget(scroll_area)

        # Nút hành động chính (Pinned at the bottom)
        btn_container = QWidget(self)
        btn_layout = QVBoxLayout(btn_container)
        btn_layout.setContentsMargins(10, 10, 10, 10)
        self.btn_plot_execute = create_themed_button("Rải điểm tọa độ", theme="success", parent=btn_container)
        self.btn_plot_execute.setMinimumHeight(44)
        self.btn_plot_execute.clicked.connect(self._on_plot_execute_clicked)
        btn_layout.addWidget(self.btn_plot_execute)
        main_layout.addWidget(btn_container)
        self._tune_control_sizes()
    def _tune_control_sizes(self):
        for label in self.findChildren(QLabel):
            label.setWordWrap(True)
            if label.text():
                label.setToolTip(label.text())

        for widget in self.findChildren((QLineEdit, QComboBox)):
            widget.setMinimumHeight(38)
            widget.setSizePolicy(SizePolicyExpanding, SizePolicyFixed)

        for button in self.findChildren(QPushButton):
            if button.text():
                button.setToolTip(button.text())
            if button.objectName() != "btn_browse" and button != self.btn_plot_execute:
                button.setMinimumHeight(38)
            button.setSizePolicy(SizePolicyExpanding, SizePolicyFixed)
