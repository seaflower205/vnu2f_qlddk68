# -*- coding: utf-8 -*-
"""Source discovery and import workflow for the cadastral import dialog."""

from __future__ import annotations

import os
import time

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QFileDialog, QMessageBox

from ..common.qt_compat import MessageBoxNo, MessageBoxYes
from ..common.settings_manager import load_setting, save_setting
from .cad_reader import find_cad_path
from .file_scanner import CadastralFileScanner
from .import_service import ImportCallbacks
from .texts import cadastral_text as tx


class CadastralImportWorkflowMixin:
    """Coordinate source selection, previews, and background imports."""

    def _choose_file(self):
        start_dir = self.txt_path.text() or load_setting(
            "vnu2f_qlddk68", "last_working_dir", ""
        )
        path, _ = QFileDialog.getOpenFileName(
            self, tx("dialog.open_file"), start_dir, tx("dialog.open_file_filter")
        )
        if path:
            self.txt_path.setText(path)
            save_setting("vnu2f_qlddk68", "last_working_dir", os.path.dirname(path))
            self._scan()

    def _choose_folder(self):
        start_dir = self.txt_path.text() or load_setting(
            "vnu2f_qlddk68", "last_working_dir", ""
        )
        path = QFileDialog.getExistingDirectory(self, tx("dialog.open_folder"), start_dir)
        if path:
            self.txt_path.setText(path)
            save_setting("vnu2f_qlddk68", "last_working_dir", path)
            self._scan()

    def _scan(self):
        path = self.txt_path.text().strip()
        if not path:
            QMessageBox.warning(self, tx("warn.missing_path.title"), tx("warn.missing_path.body"))
            return
        if not os.path.exists(path):
            QMessageBox.warning(self, tx("warn.path_missing.title"), tx("warn.path_missing.body"))
            return

        now = time.time()
        if path == self._last_scanned_path and now - self._last_scan_time < 1.0:
            return
        self._last_scanned_path = path
        self._last_scan_time = now
        self._set_loading_state(True, "Đang quét nguồn dữ liệu...")
        self.scanner = CadastralFileScanner(path, self)

        def on_finished(groups, primary):
            if not self._dialog_alive:
                return
            self._set_loading_state(False)
            self.groups = groups
            self.cmb_group.blockSignals(True)
            self.cmb_group.clear()
            for group in groups:
                self.cmb_group.addItem(self._group_label(group), group)
            self.cmb_group.setCurrentIndex(groups.index(primary) if primary else -1)
            self.cmb_group.blockSignals(False)
            self._set_current_group(primary)
            file_count = sum(len(group.files) for group in groups)
            cad_count = sum(1 for group in groups if find_cad_path(group))
            sync_count = sum(
                1
                for group in groups
                if group.get(".gtp") or group.get(".pol") or group.get(".shp")
            )
            self._log(tx("log.scan", group_count=len(groups), file_count=file_count,
                         cad_count=cad_count, sync_count=sync_count))
            self.scanner = None

        def on_error(exc):
            if not self._dialog_alive:
                return
            self._set_loading_state(False)
            self._show_error(tx("error.scan"), exc)
            self.scanner = None

        connection_type = getattr(Qt, "ConnectionType", None)
        queued = connection_type.QueuedConnection if connection_type else Qt.QueuedConnection
        self.scanner.finished_scan.connect(on_finished, queued)
        self.scanner.error_scan.connect(on_error, queued)
        self.scanner.start()

    def _on_group_changed(self, index: int):
        if index >= 0:
            self._set_current_group(self.cmb_group.itemData(index))

    def _set_current_group(self, group):
        self._cleanup_decoded_gtp()
        self.current_group = group
        self.gtp_summary = self.pol_summary = None
        self.cad_result = self.sync_result = None
        self._cad_loaded = self._gtp_loaded = self._pol_loaded = False
        for table in (self.tbl_cad, self.tbl_gtp, self.tbl_pol, self.tbl_import):
            self.table_mapper.clear_table(table)
        self.ui.update_discovery_card()
        self.btn_import_sync.setText("NHẬP VÀO QGIS")
        self.btn_import_sync.setEnabled(group is not None)
        if self.btn_accordion.isChecked():
            self._load_active_tab_preview()

    def _update_discovery_card(self):
        self.ui.update_discovery_card()

    def _get_callbacks(self) -> ImportCallbacks:
        signals = self.import_signals
        return ImportCallbacks(
            on_log=signals.log.emit, on_progress=signals.progress.emit,
            on_warning=signals.warning.emit, on_error=signals.error.emit,
            on_loading=signals.loading.emit, on_cad_loaded=signals.cad_loaded.emit,
            on_gtp_loaded=signals.gtp_loaded.emit, on_pol_loaded=signals.pol_loaded.emit,
            on_sync_loaded=signals.sync_loaded.emit,
        )

    def _on_cad_loaded(self, cad_result):
        if not self._dialog_alive:
            return
        self.cad_result = cad_result
        self._cad_loaded = True
        self._refresh_cad_table()
        counts = cad_result.feature_counts
        self._log(tx("log.cad_preview", point=counts.get("point", 0),
                     line=counts.get("line", 0), polygon=counts.get("polygon", 0),
                     skipped=cad_result.skipped_features))
        self._log_issues(cad_result.issues)

    def _on_gtp_loaded(self, gtp_summary):
        if not self._dialog_alive:
            return
        self.gtp_summary = gtp_summary
        self._gtp_loaded = True
        decoded = gtp_summary.decoded
        self._log(tx("log.gtp_preview", page_count=decoded.page_count,
                     mask_count=decoded.mask_page_count, integrity=decoded.integrity))
        self._refresh_gtp_table()

    def _on_pol_loaded(self, pol_summary):
        if not self._dialog_alive:
            return
        self.pol_summary = pol_summary
        self._pol_loaded = True
        self._log(tx("log.pol_preview", record_count=len(pol_summary.records),
                     header_count=pol_summary.record_count_header, map_sheet=pol_summary.map_sheet))
        self._refresh_pol_table()

    def _on_sync_loaded(self, sync_result):
        if not self._dialog_alive:
            return
        self.sync_result = sync_result
        self._refresh_import_table()
        counts = sync_result.feature_counts
        self._log(tx("log.import_sync", parcel=counts.get("parcel", 0),
                     line=counts.get("line", 0), point=counts.get("point", 0),
                     matched_gtp=sync_result.matched_gtp, matched_shp=sync_result.matched_shp,
                     matched_pol=sync_result.matched_pol, unmatched=sync_result.unmatched))
        self._log_issues(sync_result.issues)
        self.zone_c.setCurrentIndex(1)
        self.btn_import_sync.setText("NHẬP LẠI")

    def _log_issues(self, issues):
        for issue in issues:
            detail = f" — {issue.detail}" if issue.detail else ""
            self._log(f"[{issue.level}] {issue.message}{detail}")

    def _read_cad(self):
        cad_path = find_cad_path(self.current_group)
        crs_authid = self.cmb_cad_crs.currentData() or ""
        self.current_task = self.coordinator.read_cad(cad_path, crs_authid, self._get_callbacks())

    def _read_gtp(self):
        gtp_path = self.current_group.get(".gtp") if self.current_group else None
        try:
            self._cleanup_decoded_gtp()
        except Exception:
            pass
        self.current_task = self.coordinator.read_gtp(gtp_path, self._get_callbacks())

    def _read_pol(self):
        pol_path = self.current_group.get(".pol") if self.current_group else None
        self.current_task = self.coordinator.read_pol(pol_path, self._get_callbacks())

    def _import_sync(self):
        crs_authid = self.cmb_cad_crs.currentData() or ""
        convert_legacy_text = False
        if self.current_group and self.current_group.get(".shp"):
            answer = QMessageBox.question(
                self, tx("question.shp_text.title"), tx("question.shp_text.body"),
                MessageBoxYes | MessageBoxNo, MessageBoxYes
            )
            convert_legacy_text = answer == MessageBoxYes
        self.current_task = self.coordinator.import_sync(
            self.current_group, crs_authid, convert_legacy_text, self._get_callbacks()
        )
