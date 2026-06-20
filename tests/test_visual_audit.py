# -*- coding: utf-8 -*-
import os
from qgis.PyQt.QtWidgets import QApplication

def test_visual_audit_dialogs(qgis_app):
    """Visual audit: capture screenshots of the plugin dialogs."""
    try:
        from modules.crs_converter.crs_dialog import CRSConverterDialog
        from modules.cadastral_importer.dialog import CadastralImportDialog
    except ImportError:
        from vnu2f_qlddk68 import CRSConverterDialog, CadastralImportDialog

    # Target directory in tests/visual_logs
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(tests_dir, "visual_logs")
    os.makedirs(output_dir, exist_ok=True)

    # 1. Audit CRS dialog
    dialog_crs = CRSConverterDialog()
    dialog_crs.show()
    QApplication.processEvents()

    crs_path = os.path.join(output_dir, "crs_dialog_audit.png")
    pixmap = dialog_crs.grab()
    pixmap.save(crs_path)
    dialog_crs.close()
    assert os.path.exists(crs_path)
    print(f"\n[VISUAL AUDIT] Saved CRS Dialog screenshot to: {crs_path}")

    # 2. Audit Cadastral dialog
    dialog_cad = CadastralImportDialog()
    dialog_cad.show()
    QApplication.processEvents()

    cad_path = os.path.join(output_dir, "cadastral_dialog_audit.png")
    pixmap = dialog_cad.grab()
    pixmap.save(cad_path)
    dialog_cad.close()
    assert os.path.exists(cad_path)
    print(f"\n[VISUAL AUDIT] Saved Cadastral Dialog screenshot to: {cad_path}")
