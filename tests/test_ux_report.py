import pytest
from unittest.mock import MagicMock, patch
from qgis.PyQt.QtCore import Qt

from modules.crs_converter.tabs.report_tab import ReportTab


class TestUX_ReportTab:

    @pytest.fixture(autouse=True)
    def setup(self, qtbot, mock_iface):
        """Khởi tạo widget, đăng ký với qtbot"""
        self.widget = ReportTab(iface=mock_iface)
        qtbot.addWidget(self.widget)
        yield

    def test_UX_RPT_01__xuat_bao_cao(self, qtbot):
        """UX-RPT-01: Chọn layer -> nhấn Xuất -> file .xlsx tồn tại"""
        pass

    def test_UX_RPT_02__khong_chon_layer(self, qtbot):
        """UX-RPT-02: Không chọn layer -> nút Xuất disable hoặc hiện cảnh báo"""
        pass

    def test_UX_RPT_03__file_da_ton_tai(self, qtbot):
        """UX-RPT-03: File đã tồn tại -> hỏi ghi đè, không tự xóa"""
        pass

    def test_UX_RPT_04__layer_rong(self, qtbot):
        """UX-RPT-04: Layer rỗng (0 feature) -> thông báo rõ ràng"""
        pass

    def test_UX_RPT_05__xuat_xong_mo_file(self, qtbot):
        """UX-RPT-05: Xuất xong -> mở file không bị lỗi định dạng"""
        pass
