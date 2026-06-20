"""Mechanically extracted responsibilities from dxf_advanced_tab.py."""

import os
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QMessageBox,
    QLineEdit, QFileDialog
)
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry, QgsField, QgsFields,
    QgsMapLayerProxyModel
)
from qgis.gui import QgsMapLayerComboBox
from ...common.scroll_utils import make_scroll_area
from modules.common.ui_utils import (
    create_themed_button,
    create_centered_panel,
    create_form_group,
    create_growing_form,
    tune_form_controls
)
from ...common.i18n import tr
from ...common.dep_installer import is_installed
from ...report_generator.field_mapper import auto_detect_mapping
from .tab_text import tab_text


def tx(key, **kwargs):
    return tab_text("dxf", key, **kwargs)


class DxfAdvancedUiMixin:
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)
        
        self.deps_ok = self._deps_ready()
        
        scroll, scroll_widget, scroll_layout = make_scroll_area(self, spacing=14, margins=(0, 0, 0, 0))
        
        panel, panel_layout = create_centered_panel(scroll_widget, scroll_layout, panel_spacing=14)
        
        # 0. Warning Label nếu thiếu thư viện xử lý CAD
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
            
        # ----------------- 1. Đọc tệp DXF (Import CAD) -----------------
        self.grp_import, layout_import = create_form_group(
            tx("group.import"), self, minimum_height=180
        )
        form_imp = create_growing_form()
        
        # Đường dẫn tệp DXF nhập
        hbox_file = QHBoxLayout()
        self.txt_dxf_in = QLineEdit(self.grp_import)
        self.txt_dxf_in.setPlaceholderText(tx("placeholder.input"))
        self.btn_browse_in = create_themed_button(tx("button.browse"), theme="primary", parent=self.grp_import)
        self.btn_browse_in.setObjectName("btn_browse")
        self.btn_browse_in.clicked.connect(self._on_browse_in)
        hbox_file.addWidget(self.txt_dxf_in)
        hbox_file.addWidget(self.btn_browse_in)
        form_imp.addRow(tx("label.input"), hbox_file)
        
        layout_import.addLayout(form_imp)
        
        self.btn_import = create_themed_button(tx("button.import"), theme="success", parent=self.grp_import)
        self.btn_import.clicked.connect(self._on_import_dxf)
        layout_import.addWidget(self.btn_import)
        
        panel_layout.addWidget(self.grp_import)
        
        # ----------------- 2. Xuất bản vẽ DXF (Export CAD) -----------------
        self.grp_export, layout_export = create_form_group(
            tx("group.export"), self, minimum_height=250
        )
        form_exp = create_growing_form()
        
        self.cmb_poly_layer = QgsMapLayerComboBox(self.grp_export)
        self.cmb_poly_layer.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.cmb_poly_layer.layerChanged.connect(self._on_layer_changed)
        form_exp.addRow(tx("label.layer"), self.cmb_poly_layer)
        
        # Khung ánh xạ trường khi xuất
        self.cmb_f_sothua = QComboBox(self.grp_export)
        self.cmb_f_soto = QComboBox(self.grp_export)
        self.cmb_f_loaidat = QComboBox(self.grp_export)
        self.cmb_f_dientich = QComboBox(self.grp_export)
        
        form_exp.addRow(tx("label.sothua"), self.cmb_f_sothua)
        form_exp.addRow(tx("label.soto"), self.cmb_f_soto)
        form_exp.addRow(tx("label.loaidat"), self.cmb_f_loaidat)
        form_exp.addRow(tx("label.dientich"), self.cmb_f_dientich)
        
        layout_export.addLayout(form_exp)
        
        self.btn_export = create_themed_button(tx("button.export"), theme="primary", parent=self.grp_export)
        self.btn_export.clicked.connect(self._on_export_dxf)
        layout_export.addWidget(self.btn_export)
        
        panel_layout.addWidget(self.grp_export)
        
        self._set_dependency_controls(self.deps_ok)
            
        layout.addWidget(scroll)
        
        tune_form_controls(self)
        self._on_layer_changed()
