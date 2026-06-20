"""Mechanically extracted responsibilities from crs_dialog.py."""

import importlib
import traceback
from qgis.PyQt.QtCore import Qt, QTimer
from qgis.PyQt.QtWidgets import (
    QDialog, QHBoxLayout, QVBoxLayout, QLabel, QListWidget, QWidget, QStackedWidget
)
from qgis.core import Qgis, QgsMessageLog, QgsProject
from modules.common.ui_utils import get_dialog_stylesheet, customize_combo_boxes, is_dark_mode, set_dialog_icon, create_themed_button
from ..common.i18n import tr
from ..common.qt_compat import TextSelectableByMouse, ScrollBarAlwaysOff
from ..common.scroll_utils import wrap_widget_in_scroll


class CrsTabRegistryMixin:
    def _tab_specs(self):
        top_package = __name__.split(".")[0]
        prefix = f"{top_package}." if top_package in ["vnu2f_qlddk68"] else ""
        return [
            {
                "attr": "tab_layer",
                "title": tr("crs.sidebar.project_layers"),
                "module": ".tabs.layer_tab",
                "class": "LayerTab",
                "args": lambda: (self.iface, self),
                "kwargs": lambda: {"on_crs_changed": self._update_project_crs_status},
                "scroll": True,
            },
            {
                "attr": "tab_point",
                "title": tr("crs.sidebar.point_coords"),
                "module": ".tabs.point_tab",
                "class": "PointTab",
                "args": lambda: (self.iface, self.canvas, self),
                "scroll": True,
            },
            {
                "attr": "tab_font",
                "title": tr("crs.sidebar.font_convert"),
                "module": ".tabs.font_tab",
                "class": "FontTab",
                "args": lambda: (self.iface, self),
                "scroll": True,
            },
            {
                "attr": "tab_plot",
                "title": tr("crs.sidebar.plot_points"),
                "module": ".tabs.plot_tab",
                "class": "PlotTab",
                "args": lambda: (self.iface, self.canvas, self),
            },
            {
                "attr": "tab_map_packager",
                "title": tr("crs.sidebar.map_packager"),
                "module": ".tabs.map_packager_tab",
                "class": "MapPackagerTab",
                "args": lambda: (self.iface, self),
                "scroll": True,
            },
            {
                "attr": "tab_kml",
                "title": tr("crs.sidebar.kml"),
                "module": ".tabs.kml_tools_tab",
                "class": "KmlToolsTab",
                "args": lambda: (self.iface, self),
            },
            {
                "attr": "tab_mbtiles",
                "title": tr("crs.sidebar.mbtiles"),
                "module": ".tabs.mbtiles_tab",
                "class": "MBTilesTab",
                "args": lambda: (self.iface, self),
            },
            {
                "attr": "tab_layout",
                "title": tr("crs.sidebar.layout"),
                "module": ".tabs.map_layout_tab",
                "class": "MapLayoutTab",
                "args": lambda: (self.iface, self),
            },
            {
                "attr": "tab_dxf_advanced",
                "title": tr("crs.sidebar.dxf_advanced"),
                "module": ".tabs.dxf_advanced_tab",
                "class": "DxfAdvancedTab",
                "args": lambda: (self.iface, self),
            },
            {
                "attr": "tab_topology",
                "title": tr("crs.sidebar.topology"),
                "module": ".tabs.topology_tab",
                "class": "TopologyTab",
                "args": lambda: (self.iface, self),
            },
            {
                "attr": "tab_symbology",
                "title": tr("crs.sidebar.symbology"),
                "module": f"{prefix}cadastral_tools.ui.symbology_tab",
                "class": "SymbologyTab",
                "args": lambda: (self._plugin_state, self),
                "scroll": False,
            },
            {
                "attr": "tab_label",
                "title": tr("crs.sidebar.label"),
                "module": f"{prefix}cadastral_tools.ui.label_tab",
                "class": "LabelTab",
                "args": lambda: (self._plugin_state, self),
                "scroll": False,
            },
            {
                "attr": "tab_stats",
                "title": tr("crs.sidebar.stats"),
                "module": f"{prefix}cadastral_tools.ui.stats_tab",
                "class": "StatsTab",
                "args": lambda: (self._plugin_state, self),
                "scroll": False,
            },
            {
                "attr": "tab_report",
                "title": tr("crs.sidebar.report"),
                "module": ".tabs.report_tab",
                "class": "ReportTab",
                "args": lambda: (self.iface, self),
            },
            {
                "attr": "tab_cadastral_settings",
                "title": tr("crs.sidebar.cadastral_settings"),
                "module": f"{top_package}.cadastral_tools.ui.settings_tab",
                "class": "SettingsTab",
                "args": lambda: (self._plugin_state, self),
                "scroll": False,
            },
            {
                "attr": "tab_qa",
                "title": tr("crs.sidebar.qa_audit", default="QA & Kiểm định"),
                "module": f"{top_package}.cadastral_tools.ui.qa_tab",
                "class": "QATab",
                "args": lambda: (self._plugin_state, self),
                "scroll": False,
            },
            {
                "attr": "tab_health",
                "title": "Hệ thống & Thư viện",
                "module": ".tabs.health_tab",
                "class": "HealthTab",
                "args": lambda: (self.iface, self),
            },
        ]
