# -*- coding: utf-8 -*-
"""Settings-tab controller."""
import os

from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.QtWidgets import QWidget
from qgis.core import QgsProject

from .settings_actions import SettingsActionsMixin
from .settings_profiles import SettingsProfileMixin
from .settings_tab_ui import setup_settings_ui


class SettingsTab(SettingsActionsMixin, SettingsProfileMixin, QWidget):
    """Tab cấu hình CRS, tính toán diện tích và tiện ích Layout bản in mẫu."""

    def __init__(self, plugin_state, parent=None):
        super().__init__(parent)
        self.plugin_state = plugin_state
        self.plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._setup_ui()
        self._connect_signals()
        self.load_persisted_settings()
        self.plugin_state.signals.layer_changed.connect(self._on_shared_layer_changed)
        self.plugin_state.signals.state_changed.connect(self.save_persisted_settings)

    def _setup_ui(self):
        setup_settings_ui(self)

    def _connect_signals(self):
        self.btn_reproject.clicked.connect(self.open_reproject_dialog)
        self.btn_calc_area.clicked.connect(self.recalculate_area)
        self.btn_create_layout.clicked.connect(self.create_default_print_layout)
        self.btn_import_profile.clicked.connect(self._on_import_profile)
        self.btn_export_profile.clicked.connect(self._on_export_profile)
        self.cbo_area_field.currentIndexChanged.connect(self._on_area_field_changed)

    def load_persisted_settings(self):
        settings = QSettings()
        stored = {
            "active_layer_id": settings.value("cadastral_tools/last_layer_id", ""),
            "code_field": settings.value("cadastral_tools/last_code_field", ""),
            "area_field": settings.value("cadastral_tools/last_area_field", ""),
            "active_preset": settings.value(
                "cadastral_tools/last_preset", "Địa chính chuẩn"
            ),
        }
        for name, value in stored.items():
            if value:
                setattr(self.plugin_state, name, value)
        self.populate_fields()
        self.check_layer_crs_status()

    def save_persisted_settings(self):
        settings = QSettings()
        settings.setValue("cadastral_tools/last_layer_id", self.plugin_state.active_layer_id)
        settings.setValue("cadastral_tools/last_code_field", self.plugin_state.code_field)
        settings.setValue("cadastral_tools/last_area_field", self.plugin_state.area_field)
        settings.setValue("cadastral_tools/last_preset", self.plugin_state.active_preset)

    def populate_fields(self):
        self.cbo_area_field.blockSignals(True)
        self.cbo_area_field.clear()
        self.cbo_area_field.addItem("Tạo trường mới: DIENTICH", "__NEW__")
        layer = QgsProject.instance().mapLayer(self.plugin_state.active_layer_id)
        suggested = 0
        if layer:
            for index, field in enumerate(layer.fields()):
                name = field.name()
                self.cbo_area_field.addItem(name, name)
                if name.upper() in {"DIENTICH", "DIEN_TICH", "DT", "AREA"}:
                    suggested = index + 1
                if self.plugin_state.area_field == name:
                    suggested = index + 1
        self.cbo_area_field.blockSignals(False)
        self.cbo_area_field.setCurrentIndex(suggested)

    def _on_area_field_changed(self):
        value = self.cbo_area_field.currentData()
        if value != "__NEW__":
            self.plugin_state.area_field = value

    def _on_shared_layer_changed(self, layer_id):
        self.populate_fields()
        self.check_layer_crs_status()

    def get_current_settings(self) -> dict:
        return {
            "active_layer_id": self.plugin_state.active_layer_id,
            "code_field": self.plugin_state.code_field,
            "area_field": self.plugin_state.area_field,
            "active_preset": self.plugin_state.active_preset,
            "unit": "ha" if self.rad_ha.isChecked() else "m2",
        }
