import pytest
from unittest.mock import MagicMock, patch

from modules.crs_converter.crs_dialog import CRSConverterDialog


class TestUX_CRS:

    @pytest.fixture(autouse=True)
    def setup(self, qtbot, mock_iface):
        self.widget = CRSConverterDialog()
        qtbot.addWidget(self.widget)
        yield

    def test_UX_CRS_01__vn2000_wgs84(self, qtbot):
        pass

    def test_UX_CRS_02__ngoai_bien(self, qtbot):
        pass

    def test_UX_CRS_03__crs_khong_hop_le(self, qtbot):
        pass
