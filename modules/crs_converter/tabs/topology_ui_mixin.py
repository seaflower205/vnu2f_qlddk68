"""Mechanically extracted responsibilities from topology_tab.py."""

from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox, QMessageBox,
    QTableWidget, QTableWidgetItem
)
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry, QgsField, QgsFields,
    QgsMapLayerProxyModel
)
from qgis.gui import QgsMapLayerComboBox
from ...common.qt_compat import HeaderStretch
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
from .tab_text import tab_text
from .topology_helpers import tx


class TopologyUiMixin:
    def _build_ui(self):
        # Layout chính của tab
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)
        
        # Panel trung tâm bọc trong ScrollArea để co giãn tốt
        scroll, scroll_widget, scroll_layout = make_scroll_area(self, spacing=14, margins=(0, 0, 0, 0))
        
        panel, panel_layout = create_centered_panel(scroll_widget, scroll_layout, panel_spacing=14)

        if not self.deps_ok:
            self.lbl_warn = QLabel(
                tx("warning.missing_deps"),
                scroll_widget,
            )
            self.lbl_warn.setStyleSheet(
                "background-color: #fef2f2; border: 1px solid #fca5a5; "
                "color: #991b1b; padding: 12px; border-radius: 6px; font-weight: bold;"
            )
            self.lbl_warn.setWordWrap(True)
            panel_layout.addWidget(self.lbl_warn)
        
        # ----------------- Bước 1: Làm sạch ranh đường -----------------
        self.grp_step1, layout_step1 = create_form_group(
            tx("group.step1"), self, minimum_height=200
        )
        form_s1 = create_growing_form()
        
        self.cmb_line_layer = QgsMapLayerComboBox(self.grp_step1)
        self.cmb_line_layer.setFilters(QgsMapLayerProxyModel.LineLayer)
        form_s1.addRow(tx("label.line_layer"), self.cmb_line_layer)
        
        # Hàng chứa thông số
        hbox_params1 = QHBoxLayout()
        self.spin_tolerance = QDoubleSpinBox(self.grp_step1)
        self.spin_tolerance.setRange(0.001, 10.0)
        self.spin_tolerance.setSingleStep(0.01)
        self.spin_tolerance.setValue(0.05)
        self.spin_tolerance.setSuffix(" m")
        hbox_params1.addWidget(QLabel(tx("label.snap")))
        hbox_params1.addWidget(self.spin_tolerance)
        
        self.spin_dangle = QDoubleSpinBox(self.grp_step1)
        self.spin_dangle.setRange(0.01, 100.0)
        self.spin_dangle.setSingleStep(0.1)
        self.spin_dangle.setValue(0.5)
        self.spin_dangle.setSuffix(" m")
        hbox_params1.addWidget(QLabel(tx("label.dangle")))
        hbox_params1.addWidget(self.spin_dangle)
        
        form_s1.addRow(tx("label.params"), hbox_params1)
        layout_step1.addLayout(form_s1)
        
        self.btn_clean = create_themed_button(tx("button.clean"), theme="primary", parent=self.grp_step1)
        self.btn_clean.clicked.connect(self._on_clean_lines)
        layout_step1.addWidget(self.btn_clean)
        
        panel_layout.addWidget(self.grp_step1)
        
        # ----------------- Bước 2: Đóng vùng & Gán nhãn -----------------
        self.grp_step2, layout_step2 = create_form_group(
            tx("group.step2"), self, minimum_height=200
        )
        form_s2 = create_growing_form()
        
        self.cmb_clean_line_layer = QgsMapLayerComboBox(self.grp_step2)
        self.cmb_clean_line_layer.setFilters(QgsMapLayerProxyModel.LineLayer)
        form_s2.addRow(tx("label.clean_layer"), self.cmb_clean_line_layer)
        
        self.cmb_label_layer = QgsMapLayerComboBox(self.grp_step2)
        self.cmb_label_layer.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.cmb_label_layer.setAllowEmptyLayer(True)
        form_s2.addRow(tx("label.label_layer"), self.cmb_label_layer)
        
        layout_step2.addLayout(form_s2)
        
        self.btn_polygonize = create_themed_button(tx("button.polygonize"), theme="success", parent=self.grp_step2)
        self.btn_polygonize.clicked.connect(self._on_polygonize)
        layout_step2.addWidget(self.btn_polygonize)
        
        panel_layout.addWidget(self.grp_step2)
        
        # ----------------- Bước 3: Kiểm định Topo -----------------
        self.grp_step3, layout_step3 = create_form_group(
            tx("group.step3"), self, minimum_height=250
        )
        form_s3 = create_growing_form()
        
        self.cmb_polygon_layer = QgsMapLayerComboBox(self.grp_step3)
        self.cmb_polygon_layer.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        form_s3.addRow(tx("label.polygon_layer"), self.cmb_polygon_layer)
        
        layout_step3.addLayout(form_s3)
        
        hbox_btns3 = QHBoxLayout()
        self.btn_validate = create_themed_button(tx("button.validate"), theme="primary", parent=self.grp_step3)
        self.btn_validate.clicked.connect(self._on_validate_topo)
        hbox_btns3.addWidget(self.btn_validate)
        
        self.btn_repair = create_themed_button(tx("button.repair"), theme="success", parent=self.grp_step3)
        self.btn_repair.clicked.connect(self._on_repair_geom)
        hbox_btns3.addWidget(self.btn_repair)
        layout_step3.addLayout(hbox_btns3)
        
        # Bảng hiển thị lỗi topo
        self.tbl_errors = QTableWidget(self.grp_step3)
        self.tbl_errors.setColumnCount(3)
        self.tbl_errors.setHorizontalHeaderLabels(tx("table.errors"))
        self.tbl_errors.horizontalHeader().setSectionResizeMode(HeaderStretch)
        self.tbl_errors.setMinimumHeight(150)
        layout_step3.addWidget(self.tbl_errors)
        
        panel_layout.addWidget(self.grp_step3)
        
        layout.addWidget(scroll)
        
        # Sắp xếp cỡ chữ và căn chỉnh
        tune_form_controls(self)
        self._set_dependency_controls(self.deps_ok)
