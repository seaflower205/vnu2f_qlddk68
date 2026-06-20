# -*- coding: utf-8 -*-
"""Import/export workflow extracted from the Symbology controller."""

import os

from qgis.PyQt.QtWidgets import QFileDialog, QMessageBox
from qgis.core import QgsProject, Qgis
from qgis.utils import iface

from ...core import import_export_manager as ie_mgr


class SymbologyImportExportHandler:
    def __init__(self, owner):
        self.owner = owner

    def open_import(self):
        self._open_dialog(1)

    def open_export(self):
        self._open_dialog(0)

    def export_qml(self):
        layer = self.owner.selected_layer()
        if not layer:
            QMessageBox.warning(
                self.owner,
                "Cảnh báo",
                "Vui lòng chọn một layer ranh thửa đang hoạt động.",
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self.owner,
            "Xuất style QML",
            "",
            "QGIS Style File (*.qml)",
        )
        if not file_path:
            return

        try:
            self.owner.apply_symbology()
            ie_mgr.export_symbology_qml(layer, file_path)
            if iface:
                iface.messageBar().pushMessage(
                    "Thành công",
                    f"Đã xuất ký hiệu màu sắc ra file QML: {os.path.basename(file_path)}",
                    level=Qgis.Success,
                    duration=5,
                )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self.owner, "Lỗi", f"Không thể xuất file QML: {exc}")

    def _open_dialog(self, active_tab_index):
        from ..import_export_dialog import ImportExportDialog

        dialog = ImportExportDialog(
            active_layer=self.owner.selected_layer(),
            parent=self.owner.window(),
        )
        dialog.tabs.setCurrentIndex(active_tab_index)
        dialog.config_imported.connect(self.handle_imported_config)
        dialog.exec_()

    def handle_imported_config(self, config_info):
        config_type = config_info.get("type")
        if config_type == "symbology_json":
            current = self.owner.get_current_code_configs()
            merged = ie_mgr.merge_symbology_configs(
                current,
                config_info.get("data", []),
                config_info.get("merge_mode", "merge"),
            )
            self.owner.load_code_configs_to_table(merged)
        elif config_type == "symbology_qml":
            self.owner._on_scan_layer_codes()
        elif config_type == "profile":
            symbology = config_info.get("data", {}).get("symbology", [])
            if symbology:
                self.owner.load_code_configs_to_table(symbology)
