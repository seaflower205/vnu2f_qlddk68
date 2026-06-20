from qgis.PyQt.QtWidgets import QWidget
import pytest
from unittest.mock import MagicMock, patch

from modules.webgis.ui_share_dialog import WebGISShareDialog


class TestUX_WebGIS:

    @pytest.fixture(autouse=True)
    def setup(self, qtbot, mock_iface):
        launcher = MagicMock()
        launcher.passcode = "123456"
        self.dialog_parent = QWidget()
        self.widget = WebGISShareDialog(launcher=launcher, parent=self.dialog_parent)
        qtbot.addWidget(self.widget)
        yield

    def test_UX_WEB_01__start_server(self, qtbot):
        pass

    def test_UX_WEB_02__stop_server(self, qtbot):
        pass

    def test_UX_WEB_03__export_geojson(self, qtbot):
        pass

    def test_UX_WEB_04__start_tunnel_no_internet(self, qtbot):
        pass

    def test_UX_WEB_05__passcode_length(self, qtbot):
        pass
