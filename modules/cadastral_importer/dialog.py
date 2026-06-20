# -*- coding: utf-8 -*-
"""Dialog controller for cadastral import preview and validation."""

from __future__ import annotations

from qgis.PyQt.QtCore import QObject, pyqtSignal
from qgis.PyQt.QtWidgets import QDialog, QMessageBox

from modules.common.ui_utils import (
    customize_combo_boxes,
    get_dialog_stylesheet,
    set_dialog_icon,
)
from .cad_models import CadImportResult
from .dialog_lifecycle import CadastralImportLifecycleMixin
from .dialog_ui import CadastralImportDialogUi
from .dialog_workflow import CadastralImportWorkflowMixin
from .dossier import SourceGroup
from .gtp_reader import GtpSummary
from .import_service import CadastralImportCoordinator
from .pol_reader import PolSummary
from .sync_models import SyncImportResult
from .table_mapper import CadastralTableMapper
from .texts import cadastral_text as tx


class ImportUiSignals(QObject):
    """Marshal worker callbacks onto the dialog's Qt thread."""

    log = pyqtSignal(str)
    progress = pyqtSignal(int, str)
    warning = pyqtSignal(str, str)
    error = pyqtSignal(str, object)
    loading = pyqtSignal(bool, str)
    cad_loaded = pyqtSignal(object)
    gtp_loaded = pyqtSignal(object)
    pol_loaded = pyqtSignal(object)
    sync_loaded = pyqtSignal(object)


class CadastralImportDialog(
    CadastralImportWorkflowMixin,
    CadastralImportLifecycleMixin,
    QDialog,
):
    """Compose the cadastral import view, workflow, and lifecycle helpers."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dialog_alive = True
        self.setObjectName("cadastralImportDialog")
        self.setWindowTitle(tx("window_title"))
        self.resize(1180, 800)
        self.setMinimumSize(1040, 780)
        set_dialog_icon(self, "icon_cad.svg")

        self.groups: list[SourceGroup] = []
        self.current_group: SourceGroup | None = None
        self.gtp_summary: GtpSummary | None = None
        self.pol_summary: PolSummary | None = None
        self.cad_result: CadImportResult | None = None
        self.sync_result: SyncImportResult | None = None
        self.current_task = None
        self.scanner = None
        self._cad_loaded = False
        self._gtp_loaded = False
        self._pol_loaded = False
        self._last_scanned_path = ""
        self._last_scan_time = 0.0

        self.import_signals = ImportUiSignals()
        self.import_signals.log.connect(self._log)
        self.import_signals.warning.connect(
            lambda title, body: QMessageBox.warning(self, tx(title), tx(body))
        )
        self.import_signals.error.connect(
            lambda title, exc: self._show_error(tx(title), exc)
        )
        self.import_signals.loading.connect(self._set_loading_state)
        self.import_signals.cad_loaded.connect(self._on_cad_loaded)
        self.import_signals.gtp_loaded.connect(self._on_gtp_loaded)
        self.import_signals.pol_loaded.connect(self._on_pol_loaded)
        self.import_signals.sync_loaded.connect(self._on_sync_loaded)

        self.ui = CadastralImportDialogUi(self)
        self.table_mapper = CadastralTableMapper()
        self.coordinator = CadastralImportCoordinator()
        self.ui.setup_ui()
        customize_combo_boxes(self)
        self.setStyleSheet(get_dialog_stylesheet() + self.ui._dialog_stylesheet())
        self._load_settings()
