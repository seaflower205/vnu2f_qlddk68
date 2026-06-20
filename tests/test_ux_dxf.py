import pytest
from unittest.mock import MagicMock, patch
from qgis.PyQt.QtCore import Qt

from modules.crs_converter.tabs.dxf_advanced_tab import DxfAdvancedTab


class TestUX_DxfTab:

    @pytest.fixture(autouse=True)
    def setup(self, qtbot, mock_iface):
        self.widget = DxfAdvancedTab(iface=mock_iface)
        qtbot.addWidget(self.widget)
        yield

    def test_UX_DXF_01__import_dxf_hop_le(self, qtbot):
        pass

    def test_UX_DXF_02__import_dxf_loi(self, qtbot):
        pass

    def test_UX_DXF_03__export_layer(self, qtbot):
        pass

    def test_UX_DXF_04__tcvn3_decode(self, qtbot):
        pass

    def test_UX_DXF_05__file_rong(self, qtbot):
        pass
