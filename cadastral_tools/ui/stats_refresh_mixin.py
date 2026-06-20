"""Mechanically extracted responsibilities from stats_tab.py."""

from qgis.PyQt.QtCore import QTimer
from qgis.PyQt.QtWidgets import QWidget
from qgis.core import QgsApplication, QgsMapLayerType, QgsProject, Qgis
from qgis.utils import iface
from ..core import stats_manager as stats_mgr
from .stats_calculator import StatsCalculator
from .stats_exporter import StatsExporter
from .stats_tab_ui import StatsTabUi


class StatsRefreshMixin:
    def _on_layer_changed(self):
        """Đồng bộ khi Layer thay đổi trên Dropdown."""
        self.cbo_field_code.blockSignals(True)
        self.cbo_field_area.blockSignals(True)
        self.cbo_field_code.clear()
        self.cbo_field_area.clear()
        
        self.cbo_field_area.addItem("--- Tính từ hình học (mặc định) ---", "")

        layer_id = self.cbo_layer.currentData()
        if not layer_id:
            self.cbo_field_code.blockSignals(False)
            self.cbo_field_area.blockSignals(False)
            return
            
        layer = QgsProject.instance().mapLayer(layer_id)
        if not layer:
            self.cbo_field_code.blockSignals(False)
            self.cbo_field_area.blockSignals(False)
            return

        # Đẩy layer đang chọn sang shared state
        self.plugin_state.active_layer_id = layer_id
        
        # Lấy danh sách các trường để điền vào dropdown
        suggested_code_idx = 0
        suggested_area_idx = 0
        
        for idx, field in enumerate(layer.fields()):
            f_name = field.name()
            f_name_upper = f_name.upper()
            
            self.cbo_field_code.addItem(f_name)
            self.cbo_field_area.addItem(f_name, f_name)
            
            if f_name_upper in ["LOAIDAT", "MA_DAT", "LOAI_DAT", "LOAIDAT_TT25"]:
                suggested_code_idx = idx
            if f_name_upper in ["DIENTICH", "DIEN_TICH", "DT", "AREA"]:
                suggested_area_idx = idx + 1 # +1 do mục "Tính từ hình học" ở đầu

        self.cbo_field_code.blockSignals(False)
        self.cbo_field_area.blockSignals(False)

        if self.cbo_field_code.count() > 0:
            self.cbo_field_code.setCurrentIndex(suggested_code_idx)
            self.plugin_state.code_field = self.cbo_field_code.currentText()
            
        if self.cbo_field_area.count() > 0:
            self.cbo_field_area.setCurrentIndex(suggested_area_idx)
            self.plugin_state.area_field = self.cbo_field_area.currentData()

        self._toggle_auto_update_connections()
        self.trigger_refresh()
    def _start_refresh_task(self):
        """Chụp dữ liệu layer một lần rồi khởi động QgsTask."""
        if not self.isVisible():
            self._refresh_pending = True
            return

        layer_id = self.cbo_layer.currentData()
        code_field = self.cbo_field_code.currentText()
        area_field = self.cbo_field_area.currentData()
        
        if not layer_id or not code_field:
            self.table.setRowCount(0)
            return

        layer = QgsProject.instance().mapLayer(layer_id)
        if not layer or layer.type() != QgsMapLayerType.VectorLayer:
            self.table.setRowCount(0)
            return

        if self.current_task:
            self._refresh_pending = True
            self.current_task.cancel()
            return

        # Hiển thị progress bar và vô hiệu hóa nút Làm mới
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.btn_refresh.setEnabled(False)

        # Tạo và đăng ký QgsTask
        self.current_task = stats_mgr.ComputeStatsTask(
            "Tính toán thống kê địa chính ngầm",
            layer,
            code_field,
            area_field,
            callback=self._on_task_completed
        )
        
        QgsApplication.taskManager().addTask(self.current_task)
