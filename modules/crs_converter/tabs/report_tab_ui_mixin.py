"""Mechanically extracted responsibilities from report_tab.py."""

import os
from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QComboBox, QMessageBox, QTableWidget,
    QTableWidgetItem, QLineEdit, QFileDialog
)
from qgis.core import (
    QgsMapLayerProxyModel
)
from qgis.gui import QgsMapLayerComboBox
from ...common.qt_compat import HeaderStretch, ItemIsEnabled, ItemIsSelectable
from ...common.scroll_utils import make_scroll_area
from modules.common.ui_utils import (
    create_themed_button,
    create_centered_panel,
    create_form_group,
    create_growing_form,
    tune_form_controls,
)
from ...common.i18n import tr
from ...common.dep_installer import is_installed
from ...report_generator.field_mapper import auto_detect_mapping
from .tab_text import tab_text


def tx(key, **kwargs):
    return tab_text("report", key, **kwargs)


class ReportTabUiMixin:
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)
        
        # Kiểm tra dependency openpyxl
        self.deps_ok = self._deps_ready()
        
        scroll, scroll_widget, scroll_layout = make_scroll_area(self, spacing=14, margins=(0, 0, 0, 0))
        
        panel, panel_layout = create_centered_panel(scroll_widget, scroll_layout, panel_spacing=14)
        
        # 0. Warning Label nếu thiếu thư viện openpyxl
        if not self.deps_ok:
            self.lbl_warn = QLabel(
                tx("warning.missing_deps"),
                scroll_widget
            )
            self.lbl_warn.setStyleSheet(
                "background-color: #fef2f2; border: 1px solid #fca5a5; "
                "color: #991b1b; padding: 12px; border-radius: 6px; font-weight: bold;"
            )
            self.lbl_warn.setWordWrap(True)
            panel_layout.addWidget(self.lbl_warn)
            
        # ----------------- 1. Chọn nguồn dữ liệu & Loại báo cáo -----------------
        self.grp_source, layout_source = create_form_group(
            tx("group.source"), self, minimum_height=180
        )
        form_src = create_growing_form()
        
        self.cmb_poly_layer = QgsMapLayerComboBox(self.grp_source)
        self.cmb_poly_layer.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.cmb_poly_layer.layerChanged.connect(self._on_layer_changed)
        form_src.addRow(tx("label.layer"), self.cmb_poly_layer)
        
        self.cmb_report_type = QComboBox(self.grp_source)
        self.cmb_report_type.addItem(tx("option.so_dia_chinh"), "so_dia_chinh")
        self.cmb_report_type.addItem(tx("option.so_cap_gcn"), "so_cap_gcn")
        self.cmb_report_type.addItem(tx("option.so_muc_ke"), "so_muc_ke")
        form_src.addRow(tx("label.report_type"), self.cmb_report_type)
        
        layout_source.addLayout(form_src)
        panel_layout.addWidget(self.grp_source)
        
        # ----------------- 2. Ánh xạ trường dữ liệu -----------------
        self.grp_mapping, layout_mapping = create_form_group(
            tx("group.mapping"), self, minimum_height=220
        )
        
        self.tbl_mapping = QTableWidget(self.grp_mapping)
        self.tbl_mapping.setColumnCount(2)
        self.tbl_mapping.setHorizontalHeaderLabels(tx("table.mapping"))
        self.tbl_mapping.horizontalHeader().setSectionResizeMode(HeaderStretch)
        self.tbl_mapping.setMinimumHeight(160)
        layout_mapping.addWidget(self.tbl_mapping)
        
        panel_layout.addWidget(self.grp_mapping)
        
        # ----------------- 3. Thông tin hành chính bổ sung -----------------
        self.grp_info, layout_info = create_form_group(
            tx("group.info"), self, minimum_height=220
        )
        form_info = create_growing_form()
        
        self.txt_xa = QLineEdit(self.grp_info)
        self.txt_xa.setPlaceholderText(tx("placeholder.xa"))
        form_info.addRow(tx("label.xa"), self.txt_xa)
        
        self.txt_huyen = QLineEdit(self.grp_info)
        self.txt_huyen.setPlaceholderText(tx("placeholder.huyen"))
        form_info.addRow(tx("label.huyen"), self.txt_huyen)
        
        self.txt_tinh = QLineEdit(self.grp_info)
        self.txt_tinh.setPlaceholderText(tx("placeholder.tinh"))
        form_info.addRow(tx("label.tinh"), self.txt_tinh)
        
        self.txt_nguoi_lap = QLineEdit(self.grp_info)
        self.txt_nguoi_lap.setPlaceholderText(tx("placeholder.nguoi_lap"))
        form_info.addRow(tx("label.nguoi_lap"), self.txt_nguoi_lap)
        
        layout_info.addLayout(form_info)
        panel_layout.addWidget(self.grp_info)
        
        # ----------------- Nút xuất báo cáo -----------------
        self.btn_export = create_themed_button(tx("button.export"), theme="success", parent=scroll_widget)
        self.btn_export.clicked.connect(self._on_export_report)
        scroll_layout.addWidget(self.btn_export)
        
        self._set_dependency_controls(self.deps_ok)
            
        layout.addWidget(scroll)
        
        # Cập nhật cấu hình form
        tune_form_controls(self)
        
        # Tự động nạp cấu hình ban đầu
        self._on_layer_changed()
