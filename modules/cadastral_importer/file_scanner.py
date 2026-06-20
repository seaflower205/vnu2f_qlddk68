# -*- coding: utf-8 -*-
from qgis.PyQt.QtCore import QThread, pyqtSignal
from .import_service import CadastralImportService

class CadastralFileScanner(QThread):
    finished_scan = pyqtSignal(list, object)
    error_scan = pyqtSignal(Exception)

    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self.path = path

    def run(self):
        try:
            groups, primary = CadastralImportService.scan_path(self.path)
            self.finished_scan.emit(groups, primary)
        except Exception as exc:
            self.error_scan.emit(exc)
