# -*- coding: utf-8 -*-
"""Controller for cadastral label configuration."""
from __future__ import annotations

import os

from qgis.PyQt.QtCore import QTimer
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import QWidget
from qgis.core import QgsProject

from ..core.config_repository import ConfigRepository
from .label_configurator import LabelConfigurator
from .label_tab_ui import LabelTabUi


class LabelTab(QWidget):
    """Tab quản lý và cấu hình gắn nhãn thửa đất địa chính."""

    def __init__(self, plugin_state, parent=None):
        super().__init__(parent)
        self.plugin_state = plugin_state
        self.plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.presets: dict = {}
        ConfigRepository.set_plugin_dir(self.plugin_dir)
        self._setup_ui()
        self._connect_signals()
        QTimer.singleShot(0, self._deferred_init)
        self.plugin_state.signals.layer_changed.connect(self._on_shared_layer_changed)

    def _setup_ui(self):
        self._ui = LabelTabUi()
        self._ui.setup_ui(self)
        for name, value in vars(self._ui).items():
            if name != "parent":
                setattr(self, name, value)

    def _deferred_init(self):
        self._load_presets()
        self.populate_layers()
        self._on_preset_changed()

    def _connect_signals(self):
        self.cbo_layer.currentIndexChanged.connect(self._on_layer_changed)
        self.cbo_preset.currentIndexChanged.connect(self._on_preset_changed)
        for combo in (
            self.cbo_f_sothua,
            self.cbo_f_ma_dat,
            self.cbo_f_dientich,
            self.cbo_f_to_ban_do,
        ):
            combo.currentIndexChanged.connect(self._update_expression_preview)
        self.btn_apply.clicked.connect(self.apply_labels)
        self.btn_disable.clicked.connect(self.disable_labels)
        self.btn_save_preset.clicked.connect(self.save_current_as_preset)
        self.btn_import.clicked.connect(self._on_import_preset)
        self.btn_export.clicked.connect(self._on_export_preset)
        QgsProject.instance().layersAdded.connect(self.populate_layers)
        QgsProject.instance().layersRemoved.connect(self.populate_layers)

    def _load_presets(self):
        self.cbo_preset.blockSignals(True)
        self.cbo_preset.clear()
        ConfigRepository.clear_cache()
        self.presets = ConfigRepository.get_config("label_presets", {}) or {}
        for name in self.presets:
            self.cbo_preset.addItem(name)
        self.cbo_preset.blockSignals(False)

    def populate_layers(self):
        try:
            from vnu2f_qlddk68.modules.common.ui_utils import populate_layers_to_combo
        except ImportError:
            from modules.common.ui_utils import populate_layers_to_combo
        populate_layers_to_combo(
            self.cbo_layer,
            polygon_only=True,
            active_layer_id=self.plugin_state.active_layer_id,
            plugin_state=self.plugin_state,
        )
        if self.cbo_layer.count() == 0:
            self._on_layer_changed()

    @property
    def _field_combos(self):
        return (
            self.cbo_f_sothua,
            self.cbo_f_ma_dat,
            self.cbo_f_dientich,
            self.cbo_f_to_ban_do,
        )

    def _on_layer_changed(self):
        for combo in self._field_combos:
            combo.blockSignals(True)
            combo.clear()
        self.cbo_f_to_ban_do.addItem("--- Không sử dụng ---", "")
        layer_id = self.cbo_layer.currentData()
        layer = QgsProject.instance().mapLayer(layer_id) if layer_id else None
        if layer is None:
            for combo in self._field_combos:
                combo.blockSignals(False)
            return
        self.plugin_state.active_layer_id = layer_id
        suggested = [0, 0, 0, 0]
        aliases = (
            {"SOTHUA", "SO_THUA", "ST", "SH"},
            {"LOAIDAT", "MA_DAT", "LOAI_DAT", "LOAIDAT_TT25"},
            {"DIENTICH", "DIEN_TICH", "DT", "AREA"},
            {"SOTO", "SO_TO", "TO_BD", "TOBANDO"},
        )
        for index, field in enumerate(layer.fields()):
            name = field.name()
            self.cbo_f_sothua.addItem(name)
            self.cbo_f_ma_dat.addItem(name)
            self.cbo_f_dientich.addItem(name)
            self.cbo_f_to_ban_do.addItem(name, name)
            for position, candidates in enumerate(aliases):
                if name.upper() in candidates:
                    suggested[position] = index + (1 if position == 3 else 0)
        for combo in self._field_combos:
            combo.blockSignals(False)
        if self.cbo_f_sothua.count():
            for combo, index in zip(self._field_combos, suggested):
                combo.setCurrentIndex(index)
        self._update_expression_preview()

    def _on_shared_layer_changed(self, layer_id):
        index = self.cbo_layer.findData(layer_id)
        if index != -1 and index != self.cbo_layer.currentIndex():
            self.cbo_layer.blockSignals(True)
            self.cbo_layer.setCurrentIndex(index)
            self.cbo_layer.blockSignals(False)
            self._on_layer_changed()

    def _on_preset_changed(self):
        config = self.presets.get(self.cbo_preset.currentText())
        if not config:
            return
        controls = (
            self.cbo_font,
            self.sp_font_size,
            self.chk_buffer,
            self.sp_buffer_size,
            self.cbo_scale_limit,
            self.cbo_placement,
            self.chk_conflict,
        )
        for control in controls:
            control.blockSignals(True)
        font = config.get("font_family", "Arial")
        if self.cbo_font.findText(font) < 0:
            self.cbo_font.addItem(font)
        self.cbo_font.setCurrentText(font)
        self.sp_font_size.setValue(int(config.get("font_size_pt", 9)))
        self.btn_color.color = QColor(config.get("color", "#000000"))
        self.chk_buffer.setChecked(config.get("buffer_enabled", True))
        self.btn_buffer_color.color = QColor(config.get("buffer_color", "#FFFFFF"))
        self.sp_buffer_size.setValue(float(config.get("buffer_size", 1.0)))
        scale_index = self.cbo_scale_limit.findData(config.get("scale_limit", 2000))
        if scale_index != -1:
            self.cbo_scale_limit.setCurrentIndex(scale_index)
        placement_index = self.cbo_placement.findData(config.get("placement_mode", 4))
        if placement_index != -1:
            self.cbo_placement.setCurrentIndex(placement_index)
        self.chk_conflict.setChecked(config.get("conflict_resolution", True))
        for control in controls:
            control.blockSignals(False)
        self._update_expression_preview()

    def _update_expression_preview(self):
        config = self.presets.get(self.cbo_preset.currentText())
        if not config:
            return
        parcel = self.cbo_f_sothua.currentText()
        land_code = self.cbo_f_ma_dat.currentText()
        area = self.cbo_f_dientich.currentText()
        sheet = self.cbo_f_to_ban_do.currentData()
        if not parcel or not land_code or not area:
            self.txt_expr_preview.setPlainText(
                "--- Thiết lập thiếu trường thuộc tính cần thiết ---"
            )
            return
        expression = (
            config.get("expression_template", "")
            .replace("{sothua}", f'"{parcel}"')
            .replace("{ma_dat}", f'"{land_code}"')
            .replace("{dientich}", f'"{area}"')
        )
        if sheet:
            expression = expression.replace("{to_ban_do}", f'"{sheet}"')
        else:
            expression = expression.replace(
                "\\nTờ: ' || coalesce({to_ban_do}, '')", ""
            ).replace("coalesce({to_ban_do}, '')", "''")
        self.txt_expr_preview.setPlainText(expression)

    def get_current_label_config(self) -> dict:
        return LabelConfigurator.get_current_label_config(self)

    def apply_labels(self):
        LabelConfigurator.apply_labels(self.cbo_layer.currentData(), self)

    def disable_labels(self):
        LabelConfigurator.disable_labels(self.cbo_layer.currentData())

    def save_current_as_preset(self):
        saved, name = LabelConfigurator.save_current_as_preset(
            self, self, self.presets
        )
        if saved:
            self._load_presets()
            self.cbo_preset.setCurrentText(name)

    def _on_import_preset(self):
        if LabelConfigurator.import_preset(self, self.presets):
            self._load_presets()

    def _on_export_preset(self):
        LabelConfigurator.export_preset(self, self.presets)
