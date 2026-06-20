import pytest
from unittest.mock import MagicMock, patch

from modules.crs_converter.tabs.font_tab import FontTab


class TestUX_FontTab:

    @pytest.fixture(autouse=True)
    def setup(self, qtbot, mock_iface):
        self.widget = FontTab(iface=mock_iface)
        qtbot.addWidget(self.widget)
        yield

    def test_UX_FONT_01__tcvn3_to_unicode(self, qtbot):
        pass

    def test_UX_FONT_02__input_rong(self, qtbot):
        pass

    def test_UX_FONT_03__input_unicode(self, qtbot):
        pass
