# -*- coding: utf-8 -*-
from unittest.mock import patch, MagicMock

def test_settings_manager_roundtrip():
    store = {}
    mock_qs = MagicMock()
    mock_qs.setValue.side_effect = lambda k, v: store.update({k: v})
    mock_qs.value.side_effect = lambda k, default=None: store.get(k, default)

    with patch('modules.common.settings_manager.QSettings', return_value=mock_qs):
        from modules.common.settings_manager import save_setting, load_setting
        save_setting("test_feature", "my_key", "hello")
        assert load_setting("test_feature", "my_key") == "hello"

def test_table_mapper_instantiation(qgis_app):
    from modules.cadastral_importer.table_mapper import CadastralTableMapper
    from qgis.PyQt.QtWidgets import QTableWidget
    mapper = CadastralTableMapper(table_widget=QTableWidget())
    assert mapper is not None

def test_file_scanner_has_run_method():
    from modules.cadastral_importer.file_scanner import CadastralFileScanner
    assert hasattr(CadastralFileScanner, 'run'), "CadastralFileScanner must define run() to be a valid QThread"
    assert callable(CadastralFileScanner.run)
