"""Mechanically extracted responsibilities from kml_tools_tab.py."""

import os
from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QComboBox, QCheckBox, QLineEdit, QSpinBox, QPushButton, QMessageBox,
    QTableWidget, QTableWidgetItem, QFileDialog
)
from qgis.core import QgsProject, QgsVectorLayer
from modules.common.ui_utils import (
    create_themed_button,
    create_file_browser_row,
    create_form_group as create_layout_form_group,
    create_growing_form,
    tune_form_controls,
)
from .kml_tools import KmlBuilder, KmlToShpConverter, MergeKmlBuilder
from ...common.qt_compat import HeaderStretch
from ...common.scroll_utils import make_scroll_area


class KmlToolsBuildMixin:
    def _build_shp2kml(self):
        layout = QVBoxLayout(self.tab_shp2kml)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        scroll, content, content_ly = make_scroll_area(self.tab_shp2kml, spacing=10, margins=(0, 0, 0, 0))

        # 1. Layer selection
        self.grp_kml_in, kml_in_ly = create_layout_form_group("1. Chọn lớp dữ liệu đầu vào", self)
        g_form = create_growing_form()
        self.cbo_kml_layers = QComboBox(self)
        g_form.addRow("Lớp bản đồ:", self.cbo_kml_layers)
        kml_in_ly.addLayout(g_form)
        content_ly.addWidget(self.grp_kml_in)

        # 2. Name settings
        self.grp_kml_name, kml_name_ly = create_layout_form_group("2. Thiết lập nhãn hiển thị (Name)", self)
        name_form = create_growing_form()
        self.chk_f1 = QCheckBox("Sử dụng trường 1")
        self.chk_f1.setChecked(True)
        self.cbo_name1 = QComboBox(self)
        name_form.addRow(self.chk_f1, self.cbo_name1)

        self.chk_f2 = QCheckBox("Sử dụng trường 2")
        self.cbo_name2 = QComboBox(self)
        name_form.addRow(self.chk_f2, self.cbo_name2)

        self.txt_sep = QLineEdit(" - ")
        name_form.addRow("Ký tự nối:", self.txt_sep)

        self.spn_name_size = QSpinBox()
        self.spn_name_size.setRange(8, 72)
        self.spn_name_size.setValue(12)
        name_form.addRow("Cỡ chữ nhãn:", self.spn_name_size)

        self.btn_name_color = QPushButton("#000000")
        self.btn_name_color.setMinimumHeight(38)
        self.btn_name_color.setStyleSheet("background-color: #000000; color: white;")
        self.btn_name_color.clicked.connect(lambda: self._pick_color(self.btn_name_color))
        name_form.addRow("Màu chữ:", self.btn_name_color)

        kml_name_ly.addLayout(name_form)
        content_ly.addWidget(self.grp_kml_name)

        # 3. Styling
        self.grp_kml_style, kml_style_ly = create_layout_form_group("3. Giao diện vùng (Style)", self)
        style_form = create_growing_form()
        
        self.btn_border = QPushButton("#FF0000")
        self.btn_border.setMinimumHeight(38)
        self.btn_border.setStyleSheet("background-color: #FF0000; color: white;")
        self.btn_border.clicked.connect(lambda: self._pick_color(self.btn_border))
        style_form.addRow("Màu viền:", self.btn_border)

        self.spn_border_w = QSpinBox()
        self.spn_border_w.setRange(1, 10)
        self.spn_border_w.setValue(2)
        style_form.addRow("Độ dày viền:", self.spn_border_w)

        self.btn_fill = QPushButton("#00FF00")
        self.btn_fill.setMinimumHeight(38)
        self.btn_fill.setStyleSheet("background-color: #00FF00; color: white;")
        self.btn_fill.clicked.connect(lambda: self._pick_color(self.btn_fill))
        style_form.addRow("Màu nền:", self.btn_fill)

        self.spn_opacity = QSpinBox()
        self.spn_opacity.setRange(0, 100)
        self.spn_opacity.setValue(50)
        self.spn_opacity.setSuffix(" %")
        style_form.addRow("Độ mờ nền:", self.spn_opacity)

        kml_style_ly.addLayout(style_form)
        content_ly.addWidget(self.grp_kml_style)

        # Action Button
        self.btn_export_kml = create_themed_button("Xuất KML/KMZ", theme="success", parent=self.tab_shp2kml)
        self.btn_export_kml.setObjectName("btn_success")
        self.btn_export_kml.clicked.connect(self._export_shp2kml)
        content_ly.addWidget(self.btn_export_kml)

        layout.addWidget(scroll)

        from qgis.PyQt.QtCore import QTimer
        QTimer.singleShot(0, lambda: self._load_layers_to_combo(self.cbo_kml_layers))
        self.cbo_kml_layers.currentIndexChanged.connect(self._on_layer_changed)
        QTimer.singleShot(0, self._on_layer_changed)
    def _build_kml2shp(self):
        layout = QVBoxLayout(self.tab_kml2shp)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        g_form = create_growing_form()
        
        browse_ly, self.txt_kml_in, btn_kml_browse = create_file_browser_row("Chọn file KML/KMZ...", readonly=True, parent=self.tab_kml2shp)
        btn_kml_browse.clicked.connect(self._browse_kml)
        g_form.addRow("Đường dẫn KML:", browse_ly)

        self.txt_kml_crs = QLineEdit("EPSG:4326")
        g_form.addRow("Hệ tọa độ đích:", self.txt_kml_crs)
        layout.addLayout(g_form)

        # Field table
        self.tbl_kml_fields = QTableWidget(0, 3, self.tab_kml2shp)
        self.tbl_kml_fields.setHorizontalHeaderLabels(["√", "Trường dữ liệu", "Giá trị mẫu"])
        self.tbl_kml_fields.horizontalHeader().setSectionResizeMode(HeaderStretch)
        self.tbl_kml_fields.setStyleSheet(
            "QTableWidget { border: 1px solid #27272a; gridline-color: transparent; }"
            "QTableWidget::item { border-bottom: 1px solid #27272a; height: 32px; }"
        )
        layout.addWidget(self.tbl_kml_fields)

        btn_row = QHBoxLayout()
        self.btn_scan = create_themed_button("Quét cấu trúc thuộc tính", theme=None, parent=self.tab_kml2shp)
        self.btn_scan.clicked.connect(self._scan_kml_fields)
        btn_row.addWidget(self.btn_scan)
        
        self.btn_all = create_themed_button("Chọn tất cả", theme=None, parent=self.tab_kml2shp)
        self.btn_all.clicked.connect(self._kml_all)
        btn_row.addWidget(self.btn_all)

        self.btn_none = create_themed_button("Bỏ chọn", theme=None, parent=self.tab_kml2shp)
        self.btn_none.clicked.connect(self._kml_none)
        btn_row.addWidget(self.btn_none)
        layout.addLayout(btn_row)

        self.btn_convert = create_themed_button("Chuyển sang Shapefile (SHP)", theme="primary", parent=self.tab_kml2shp)
        self.btn_convert.setObjectName("btn_primary")
        self.btn_convert.clicked.connect(self._convert_kml)
        layout.addWidget(self.btn_convert)
        layout.addStretch()
