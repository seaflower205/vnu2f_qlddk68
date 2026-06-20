# -*- coding: utf-8 -*-
"""Presentation state and lifecycle helpers for the cadastral import dialog."""

from __future__ import annotations

import os
import traceback

from qgis.PyQt.QtWidgets import QMessageBox
from qgis.core import QgsProject

from ..common.settings_manager import load_setting, save_setting
from ..common.vn2000_data import populate_crs_combo
from .texts import cadastral_text as tx


class CadastralImportLifecycleMixin:
    """Maintain settings, table presentation, and dialog lifecycle."""

    def _populate_cad_crs_combo(self):
        self.cmb_cad_crs.clear()
        try:
            current_crs = QgsProject.instance().crs()
            current_authid = current_crs.authid()
            current_desc = current_crs.description()
        except Exception:  # noqa: BLE001 — intentional suppress
            current_authid = "EPSG:4326"
            current_desc = tx("crs.fallback_description")
        self.cmb_cad_crs.addItem(
            tx("crs.current", authid=current_authid, description=current_desc),
            current_authid,
        )
        populate_crs_combo(self.cmb_cad_crs)

    def _refresh_cad_table(self):
        self.table_mapper.refresh_cad_table(self)

    def _refresh_gtp_table(self):
        self.table_mapper.refresh_gtp_table(self)

    def _refresh_pol_table(self):
        self.table_mapper.refresh_pol_table(self)

    def _refresh_import_table(self):
        self.table_mapper.refresh_import_table(self)

    def _get_selected_scale(self) -> int:
        try:
            return int(self.cmb_map_scale.currentText().split(":")[-1])
        except Exception:  # noqa: BLE001 — intentional suppress
            return 1000

    def _load_settings(self):
        last_dir = load_setting("vnu2f_qlddk68", "last_working_dir", "")
        if last_dir and os.path.exists(last_dir):
            self.txt_path.setText(last_dir)
            self._scan()

        last_scale = load_setting("vnu2f_qlddk68", "map_scale", "1:1000")
        scale_index = self.cmb_map_scale.findText(last_scale)
        if scale_index >= 0:
            self.cmb_map_scale.setCurrentIndex(scale_index)

        last_crs = load_setting("vnu2f_qlddk68", "cad_crs", "")
        if last_crs:
            crs_index = self.cmb_cad_crs.findData(last_crs)
            if crs_index < 0:
                crs_index = self.cmb_cad_crs.findText(last_crs)
            if crs_index >= 0:
                self.cmb_cad_crs.setCurrentIndex(crs_index)

    def _save_settings(self):
        path = self.txt_path.text().strip()
        if os.path.isdir(path):
            save_setting("vnu2f_qlddk68", "last_working_dir", path)
        elif os.path.isfile(path):
            save_setting("vnu2f_qlddk68", "last_working_dir", os.path.dirname(path))
        save_setting("vnu2f_qlddk68", "map_scale", self.cmb_map_scale.currentText())
        crs_value = self.cmb_cad_crs.currentData() or self.cmb_cad_crs.currentText()
        if crs_value:
            save_setting("vnu2f_qlddk68", "cad_crs", crs_value)

    def _group_label(self, group) -> str:
        cad = [ext for ext in (".dwg", ".dgn", ".dxf") if group.get(ext)]
        sync = [ext for ext in (".gtp", ".pol", ".shp") if group.get(ext)]
        other = sorted(ext for ext in group.files if ext not in set(cad + sync))
        parts = []
        if cad:
            parts.append(f"{tx('group.label.cad')} {', '.join(cad)}")
        if sync:
            parts.append(f"{tx('group.label.sync')} {', '.join(sync)}")
        if other:
            parts.append(f"{tx('group.label.other')} {', '.join(other)}")
        return f"{group.display_name} ({' | '.join(parts)})"

    def _log(self, message: str):
        self.txt_log.append(message)

    def _show_error(self, title: str, exc: Exception):
        self._log(f"{title}: {exc}")
        self._log(traceback.format_exc())
        QMessageBox.critical(self, title, str(exc))

    def _cleanup_decoded_gtp(self):
        if not self.gtp_summary:
            return
        sqlite_path = self.gtp_summary.decoded.sqlite_path
        if sqlite_path.endswith("_gtp_decoded.sqlite") and os.path.exists(sqlite_path):
            try:
                os.remove(sqlite_path)
            except OSError:
                pass

    def _set_loading_state(self, enabled: bool, message: str = ""):
        if enabled:
            self.progress_container.show()
            self.lbl_progress.setText(message)
            self.progress_bar.setRange(0, 0)
            self.btn_cancel.setEnabled(True)
            widgets = (self.btn_import_sync, self.txt_path, self.cmb_group,
                       self.cmb_cad_crs, self.cmb_map_scale, self.btn_file,
                       self.btn_folder, self.btn_accordion)
            for widget in widgets:
                widget.setEnabled(False)
        else:
            self.progress_container.hide()
            widgets = (self.txt_path, self.cmb_group, self.cmb_cad_crs,
                       self.cmb_map_scale, self.btn_file, self.btn_folder,
                       self.btn_accordion)
            for widget in widgets:
                widget.setEnabled(True)
            self.btn_import_sync.setEnabled(self.current_group is not None)
            self.current_task = None

    def _cancel_current_task(self):
        if self.current_task:
            self._log("Người dùng yêu cầu hủy tác vụ...")
            self.current_task.cancel()
            self.btn_cancel.setEnabled(False)

    def closeEvent(self, event):
        self._dialog_alive = False
        if self.current_task:
            self.current_task.cancel()
        if self.scanner and self.scanner.isRunning():
            self.scanner.requestInterruption()
            self.scanner.wait(1000)
        self._save_settings()
        self._cleanup_decoded_gtp()
        super().closeEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path:
                self.txt_path.setText(path)
                event.acceptProposedAction()
                self._scan()
        else:
            super().dropEvent(event)

    def _check_hn72_warning(self):
        text = self.cmb_cad_crs.currentText()
        data = self.cmb_cad_crs.currentData()
        is_hn72 = bool(text and ("HN-72" in text or "HN72" in text))
        if data and isinstance(data, str) and data.startswith("USER:9001"):
            is_hn72 = True
        self.lbl_warning_hn72.setVisible(is_hn72)

    def _toggle_accordion(self, checked: bool):
        if checked:
            self.btn_accordion.setText("▼ Ẩn chi tiết dữ liệu thô")
            self.preview_widget.show()
            self._load_active_tab_preview()
        else:
            self.btn_accordion.setText("▶ Xem chi tiết dữ liệu thô")
            self.preview_widget.hide()

    def _on_tab_changed(self, index: int):
        if self.btn_accordion.isChecked():
            self._load_active_tab_preview()

    def _load_active_tab_preview(self):
        if not self.current_group:
            return
        index = self.tabs.currentIndex()
        if index == 0 and not self._cad_loaded:
            self._read_cad()
        elif index == 1 and not self._gtp_loaded:
            self._read_gtp()
        elif index == 2 and not self._pol_loaded:
            self._read_pol()
