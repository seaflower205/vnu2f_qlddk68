# -*- coding: utf-8 -*-
"""Background services and UI workflow coordination for cadastral import."""

from typing import Any, Callable

from qgis.PyQt.QtWidgets import QMessageBox
from qgis.core import QgsProject

from ..common.common_utils import run_in_background
from .cad_reader import CadImportResult, find_cad_path, import_cad_to_memory_layers
from .dossier import SourceGroup, find_primary_group, scan_sources
from .gtp_reader import GtpSummary, decode_and_summarize
from .layer_runtime import add_generated_layer
from .pol_reader import PolSummary, parse_pol
from .sync_importer import SyncImportResult, import_cadastral_group
from dataclasses import dataclass

@dataclass
class ImportCallbacks:
    on_log: Callable[[str], None] | None = None
    on_progress: Callable[[int, str], None] | None = None
    on_warning: Callable[[str, str], None] | None = None
    on_error: Callable[[str, Exception], None] | None = None
    on_loading: Callable[[bool, str], None] | None = None
    on_cad_loaded: Callable[[Any], None] | None = None
    on_gtp_loaded: Callable[[Any], None] | None = None
    on_pol_loaded: Callable[[Any], None] | None = None
    on_sync_loaded: Callable[[Any], None] | None = None


class CadastralImportService:
    """Pure entry points for scan and background processing."""

    @staticmethod
    def scan_path(path: str) -> tuple[list[SourceGroup], SourceGroup | None]:
        groups = scan_sources(path)
        return groups, find_primary_group(groups)

    @staticmethod
    def read_cad_in_background(
        cad_path: str,
        crs_authid: str,
        on_finished: Callable[[CadImportResult], None],
        on_error: Callable[[Exception], None],
    ) -> Any:
        return run_in_background(
            "Đọc bản vẽ CAD",
            import_cad_to_memory_layers,
            cad_path,
            crs_authid,
            project=None,
            add_to_project=False,
            on_finished=on_finished,
            on_error=on_error,
        )

    @staticmethod
    def read_gtp_in_background(
        gtp_path: str,
        on_finished: Callable[[GtpSummary], None],
        on_error: Callable[[Exception], None],
    ) -> Any:
        return run_in_background(
            "Đọc tệp tin GTP",
            decode_and_summarize,
            gtp_path,
            on_finished=on_finished,
            on_error=on_error,
        )

    @staticmethod
    def read_pol_in_background(
        pol_path: str,
        on_finished: Callable[[PolSummary], None],
        on_error: Callable[[Exception], None],
    ) -> Any:
        return run_in_background(
            "Đọc tệp tin POL",
            parse_pol,
            pol_path,
            on_finished=on_finished,
            on_error=on_error,
        )

    @staticmethod
    def import_sync_in_background(
        group: SourceGroup,
        crs_authid: str,
        convert_legacy_text: bool,
        on_finished: Callable[[SyncImportResult], None],
        on_error: Callable[[Exception], None],
    ) -> Any:
        return run_in_background(
            "Đồng bộ nhập dữ liệu địa chính",
            import_cadastral_group,
            group,
            crs_authid,
            project=None,
            convert_legacy_text=convert_legacy_text,
            add_to_project=False,
            on_finished=on_finished,
            on_error=on_error,
        )


class CadastralImportCoordinator:
    """Own background workflows while the dialog remains a thin controller."""

    def read_cad(self, cad_path: str, crs_authid: str, callbacks: ImportCallbacks):
        if not cad_path:
            if callbacks.on_warning:
                callbacks.on_warning("warn.missing_cad.title", "warn.missing_cad.body")
            return

        if not crs_authid:
            if callbacks.on_warning:
                callbacks.on_warning("warn.missing_crs.title", "warn.missing_crs.body")
            return

        if callbacks.on_loading:
            callbacks.on_loading(True, "Đang đọc bản vẽ CAD...")

        def on_finished(cad_result):
            if callbacks.on_loading:
                callbacks.on_loading(False, "")
            
            # Thêm các layer đã sinh vào project từ main thread
            project = QgsProject.instance()
            for layer in cad_result.output_layers:
                kind = layer.customProperty("vnu2f_qlddk68/kind", "")
                add_generated_layer(project, layer, cad_result.cad_path, kind, layer.featureCount())
                
            if callbacks.on_cad_loaded:
                callbacks.on_cad_loaded(cad_result)

        def on_error(exc):
            if callbacks.on_loading:
                callbacks.on_loading(False, "")
            if callbacks.on_error:
                callbacks.on_error("error.read_cad", exc)

        return CadastralImportService.read_cad_in_background(
            cad_path,
            crs_authid,
            on_finished,
            on_error,
        )

    def read_gtp(self, gtp_path: str, callbacks: ImportCallbacks):
        if not gtp_path:
            if callbacks.on_warning:
                callbacks.on_warning("warn.missing_gtp.title", "warn.missing_gtp.body")
            return

        if callbacks.on_loading:
            callbacks.on_loading(True, "Đang giải mã và phân tích file GTP...")

        def on_finished(gtp_summary):
            if callbacks.on_loading:
                callbacks.on_loading(False, "")
            if callbacks.on_gtp_loaded:
                callbacks.on_gtp_loaded(gtp_summary)

        def on_error(exc):
            if callbacks.on_loading:
                callbacks.on_loading(False, "")
            if callbacks.on_error:
                callbacks.on_error("error.read_gtp", exc)

        return CadastralImportService.read_gtp_in_background(
            gtp_path,
            on_finished,
            on_error,
        )

    def read_pol(self, pol_path: str, callbacks: ImportCallbacks):
        if not pol_path:
            if callbacks.on_warning:
                callbacks.on_warning("warn.missing_pol.title", "warn.missing_pol.body")
            return
            
        if callbacks.on_loading:
            callbacks.on_loading(True, "Đang phân tích tệp tin POL...")

        def on_finished(pol_summary):
            if callbacks.on_loading:
                callbacks.on_loading(False, "")
            if callbacks.on_pol_loaded:
                callbacks.on_pol_loaded(pol_summary)

        def on_error(exc):
            if callbacks.on_loading:
                callbacks.on_loading(False, "")
            if callbacks.on_error:
                callbacks.on_error("error.read_pol", exc)

        return CadastralImportService.read_pol_in_background(
            pol_path,
            on_finished,
            on_error,
        )

    def import_sync(self, group: SourceGroup, crs_authid: str, convert_legacy_text: bool, callbacks: ImportCallbacks):
        if not group:
            if callbacks.on_warning:
                callbacks.on_warning("warn.missing_group.title", "warn.missing_group.body")
            return
        if not find_cad_path(group):
            if callbacks.on_warning:
                callbacks.on_warning("warn.missing_cad.title", "warn.missing_cad_for_import.body")
            return

        if not crs_authid:
            if callbacks.on_warning:
                callbacks.on_warning("warn.missing_crs.title", "warn.missing_crs_import.body")
            return

        if callbacks.on_loading:
            callbacks.on_loading(True, "Đang xử lý đồng bộ và nhập dữ liệu...")

        def on_finished(sync_result):
            if callbacks.on_loading:
                callbacks.on_loading(False, "")
            
            # Thêm các layer đồng bộ vào project từ main thread
            project = QgsProject.instance()
            source_key = group.stem
            for layer in sync_result.output_layers:
                kind = layer.customProperty("vnu2f_qlddk68/kind", "")
                add_generated_layer(project, layer, source_key, kind, layer.featureCount())

            if callbacks.on_sync_loaded:
                callbacks.on_sync_loaded(sync_result)

        def on_error(exc):
            if callbacks.on_loading:
                callbacks.on_loading(False, "")
            if callbacks.on_error:
                callbacks.on_error("error.import_sync", exc)

        return CadastralImportService.import_sync_in_background(
            group,
            crs_authid,
            convert_legacy_text,
            on_finished,
            on_error,
        )

