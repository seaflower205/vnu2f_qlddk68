"""Profile import/export actions for ``SettingsTab``."""
import os

from qgis.PyQt.QtWidgets import QFileDialog, QMessageBox
from qgis.core import Qgis
from qgis.utils import iface

from ..core import import_export_manager as ie_mgr


class SettingsProfileMixin:
    def _on_import_profile(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Nhập profile plugin", "", "Profile địa chính (*.cadprofile)"
        )
        if not path:
            return
        try:
            profile = ie_mgr.import_full_profile(path)
            settings = profile.get("settings", {})
            for key in ("active_preset", "code_field", "area_field", "active_layer_id"):
                if key in settings:
                    setattr(self.plugin_state, key, settings[key])
            panel = self.parent()
            if panel and hasattr(panel, "tab_symbology") and "symbology" in profile:
                panel.tab_symbology.load_code_configs_to_table(profile["symbology"])
            if panel and hasattr(panel, "tab_labels") and "labels" in profile:
                panel.tab_labels.presets.update(profile["labels"])
                panel.tab_labels._load_presets()
            self.populate_fields()
            self.check_layer_crs_status()
            if iface:
                iface.messageBar().pushMessage(
                    "Nhập profile", "Đã nạp toàn bộ profile cấu hình địa chính thành công.",
                    level=Qgis.Success, duration=5,
                )
        except Exception as error:  # noqa: BLE001
            QMessageBox.critical(self, "Lỗi", f"Không thể nạp profile: {error}")

    def _on_export_profile(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Xuất profile plugin", "", "Profile địa chính (*.cadprofile)"
        )
        if not path:
            return
        try:
            panel = self.parent()
            symbology = (
                panel.tab_symbology.get_current_code_configs()
                if panel and hasattr(panel, "tab_symbology") else []
            )
            labels = (
                panel.tab_labels.presets
                if panel and hasattr(panel, "tab_labels") else {}
            )
            ie_mgr.export_full_profile(
                code_configs=symbology, label_config=labels,
                general_settings=self.get_current_settings(), file_path=path,
            )
            if iface:
                iface.messageBar().pushMessage(
                    "Xuất profile", f"Đã xuất cấu hình trọn bộ .cadprofile thành công ra:\n{os.path.basename(path)}",
                    level=Qgis.Success, duration=5,
                )
        except Exception as error:  # noqa: BLE001
            QMessageBox.critical(self, "Lỗi", f"Không thể xuất profile: {error}")
