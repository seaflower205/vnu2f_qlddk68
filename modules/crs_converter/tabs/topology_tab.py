# -*- coding: utf-8 -*-
"""
Giao diện phân hệ Sửa lỗi ranh thửa & Khép vùng tự động (Topology Wizard Tab).
"""

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
from .topology_helpers import get_shapely as _get_shapely, tx
from .topology_ui_mixin import TopologyUiMixin
from .topology_build_mixin import TopologyBuildMixin
from .topology_validate_mixin import TopologyValidateMixin


class TopologyTab(TopologyValidateMixin, TopologyBuildMixin, TopologyUiMixin, QWidget):
    """Giao diện Wizard sửa lỗi ranh thửa và đóng vùng địa chính."""

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.parent_dialog = parent
        
        # Biến lưu trữ kết quả trung gian
        self.cleaned_layer = None
        self.polygon_layer = None
        self.lbl_warn = None
        self.deps_ok = self._deps_ready()
        
        self._build_ui()


    def _deps_ready(self):
        return is_installed("shapely")

    def showEvent(self, event):
        super().showEvent(event)
        now_ok = self._deps_ready()
        if now_ok != self.deps_ok:
            self.deps_ok = now_ok
            self._set_dependency_controls(now_ok)

    def _set_dependency_controls(self, enabled: bool):
        for widget in (
            self.btn_clean,
            self.btn_polygonize,
            self.btn_validate,
            self.btn_repair,
        ):
            widget.setEnabled(enabled)
        if self.lbl_warn:
            self.lbl_warn.setVisible(not enabled)

    def _require_deps(self):
        if self._deps_ready():
            return True
        QMessageBox.warning(self, tr("common.warning"), tx("missing.deps"))
        return False





    def reset(self):
        """Đặt lại các combobox."""
        self.cmb_line_layer.setCurrentIndex(0)
        self.cmb_clean_line_layer.setCurrentIndex(0)
        self.cmb_label_layer.setCurrentIndex(0)
        self.cmb_polygon_layer.setCurrentIndex(0)
        self.tbl_errors.setRowCount(0)
