# -*- coding: utf-8 -*-
from qgis.PyQt.QtCore import QTimer
from qgis.PyQt.QtWidgets import QWidget
from qgis.core import QgsApplication, QgsMapLayerType, QgsProject, Qgis
from qgis.utils import iface

from ..core import stats_manager as stats_mgr
from .stats_calculator import StatsCalculator
from .stats_exporter import StatsExporter
from .stats_tab_ui import StatsTabUi
from .stats_refresh_mixin import StatsRefreshMixin

class StatsTab(StatsRefreshMixin, QWidget):
    """Tab tổng hợp số liệu diện tích và thống kê cơ cấu đất đai."""

    def __init__(self, plugin_state, parent=None):
        super().__init__(parent)
        self.plugin_state = plugin_state
        self.stats_data = []
        self.sort_column = 3
        self.sort_asc = False
        self.current_task = None
        self._connected_layer = None
        self._refresh_pending = False
        self._closing = False
        
        self.ui = StatsTabUi()
        self.ui.setup_ui(self)
        for name in (
            "cbo_layer", "cbo_field_code", "cbo_field_area",
            "chk_auto_update", "progress_bar", "txt_search", "table",
            "btn_refresh", "btn_csv", "btn_excel",
        ):
            setattr(self, name, getattr(self.ui, name))

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(180)
        self._refresh_timer.timeout.connect(self._start_refresh_task)
        self._connect_signals()
        
        # Field/layer signals may request several refreshes during setup. The
        # single-shot timer coalesces them into one feature snapshot.
        self.populate_layers()
        self.trigger_refresh()
        
        self.plugin_state.signals.layer_changed.connect(self._on_shared_layer_changed)
        self.plugin_state.signals.code_field_changed.connect(self._on_shared_field_changed)
        self.plugin_state.signals.area_field_changed.connect(self._on_shared_area_changed)

    def _connect_signals(self):
        self.cbo_layer.currentIndexChanged.connect(self._on_layer_changed)
        self.cbo_field_code.currentIndexChanged.connect(self._on_field_code_changed)
        self.cbo_field_area.currentIndexChanged.connect(self._on_field_area_changed)
        self.btn_refresh.clicked.connect(self.trigger_refresh)
        self.txt_search.textChanged.connect(self._on_search_text_changed)
        
        self.btn_csv.clicked.connect(self.export_csv)
        self.btn_excel.clicked.connect(self.export_excel)
        
        self.chk_auto_update.stateChanged.connect(self._toggle_auto_update_connections)
        self.table.horizontalHeader().sectionClicked.connect(self._on_header_clicked)

        QgsProject.instance().layersAdded.connect(self.populate_layers)
        QgsProject.instance().layersRemoved.connect(self.populate_layers)

    def populate_layers(self):
        """Nạp các Vector Polygon Layer."""
        try:
            from vnu2f_qlddk68.modules.common.ui_utils import populate_layers_to_combo
        except ImportError:
            from modules.common.ui_utils import populate_layers_to_combo
        populate_layers_to_combo(
            self.cbo_layer, 
            polygon_only=True, 
            active_layer_id=self.plugin_state.active_layer_id
        )
        if self.cbo_layer.count() == 0:
            self._on_layer_changed()



    def _on_search_text_changed(self, text):
        """Lọc các hàng trong bảng dựa trên từ khóa tìm kiếm (Mã hoặc Tên loại đất)."""
        q = text.strip().lower()
        for row in range(self.table.rowCount()):
            item_code = self.table.item(row, 0)
            item_name = self.table.item(row, 1)
            
            code_text = item_code.text().lower() if item_code else ""
            name_text = item_name.text().lower() if item_name else ""
            
            if not q or q in code_text or q in name_text:
                self.table.setRowHidden(row, False)
            else:
                self.table.setRowHidden(row, True)

    def _on_field_code_changed(self):
        f_name = self.cbo_field_code.currentText()
        if f_name:
            self.plugin_state.code_field = f_name
            self.trigger_refresh()

    def _on_field_area_changed(self):
        f_name = self.cbo_field_area.currentData()
        self.plugin_state.area_field = f_name
        self.trigger_refresh()

    def _on_shared_layer_changed(self, layer_id):
        idx = self.cbo_layer.findData(layer_id)
        if idx != -1 and idx != self.cbo_layer.currentIndex():
            self.cbo_layer.blockSignals(True)
            self.cbo_layer.setCurrentIndex(idx)
            self.cbo_layer.blockSignals(False)
            self._on_layer_changed()

    def _on_shared_field_changed(self, field_name):
        idx = self.cbo_field_code.findText(field_name)
        if idx != -1 and idx != self.cbo_field_code.currentIndex():
            self.cbo_field_code.blockSignals(True)
            self.cbo_field_code.setCurrentIndex(idx)
            self.cbo_field_code.blockSignals(False)
            self.trigger_refresh()

    def _on_shared_area_changed(self, field_name):
        idx = self.cbo_field_area.findData(field_name)
        if idx != -1 and idx != self.cbo_field_area.currentIndex():
            self.cbo_field_area.blockSignals(True)
            self.cbo_field_area.setCurrentIndex(idx)
            self.cbo_field_area.blockSignals(False)
            self.trigger_refresh()

    def _toggle_auto_update_connections(self):
        """Bật/tắt các tín hiệu cập nhật tự động khi dữ liệu layer thay đổi."""
        # Ngắt kết nối cũ nếu có
        if self._connected_layer:
            try:
                self._connected_layer.editingStopped.disconnect(self.trigger_refresh)
                self._connected_layer.featureAdded.disconnect(self.trigger_refresh)
                self._connected_layer.featuresDeleted.disconnect(self.trigger_refresh)
                self._connected_layer.geometryChanged.disconnect(self.trigger_refresh)
            except Exception:  # noqa: BLE001 — intentional suppress
                pass
            self._connected_layer = None

        if not self.chk_auto_update.isChecked():
            return

        layer_id = self.cbo_layer.currentData()
        if not layer_id:
            return

        layer = QgsProject.instance().mapLayer(layer_id)
        if layer:
            self._connected_layer = layer
            layer.editingStopped.connect(self.trigger_refresh)
            layer.featureAdded.connect(self.trigger_refresh)
            layer.featuresDeleted.connect(self.trigger_refresh)
            layer.geometryChanged.connect(self.trigger_refresh)

    def trigger_refresh(self):
        """Gộp các yêu cầu refresh dồn dập thành một lần tính."""
        if not self._closing:
            self._refresh_timer.start()


    def _on_task_completed(self, success, result, exception):
        """Hàm callback khi Task chạy ngầm hoàn thành."""
        self.btn_refresh.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.current_task = None

        if self._closing:
            return
        if self._refresh_pending:
            self._refresh_pending = False
            self._refresh_timer.start()
            return

        if not success:
            err = str(exception) if exception else "Lỗi không xác định."
            if iface:
                iface.messageBar().pushMessage(
                    "Thống kê", f"Lỗi tính toán thống kê: {err}",
                    level=Qgis.Critical, duration=5
                )
            return

        self.stats_data = result
        self.rebuild_table()

    def _on_header_clicked(self, logical_index):
        """Sắp xếp dữ liệu thống kê khi click vào header cột (không làm lộn xộn dòng TỔNG CỘNG)."""
        if logical_index == self.sort_column:
            # Đảo chiều nếu click lại cột cũ
            self.sort_asc = not self.sort_asc
        else:
            self.sort_column = logical_index
            self.sort_asc = True
            
        StatsCalculator.sort_data(self.stats_data, logical_index, self.sort_asc)
        self.rebuild_table()

    def rebuild_table(self):
        """Hiển thị dữ liệu đã tính bằng component chuyên trách."""
        StatsCalculator.rebuild_table(self.table, self.stats_data)

    def export_csv(self):
        """Ủy quyền xuất CSV cho component chuyên trách."""
        StatsExporter.export_csv(self.stats_data, self)

    def export_excel(self):
        """Ủy quyền xuất Excel cho component chuyên trách."""
        StatsExporter.export_excel(self.stats_data, self)

    def hideEvent(self, event):
        """Ngắt auto-update nhưng để task nền hoàn tất khi đổi tab."""
        if self._connected_layer:
            try:
                self._connected_layer.editingStopped.disconnect(self.trigger_refresh)
                self._connected_layer.featureAdded.disconnect(self.trigger_refresh)
                self._connected_layer.featuresDeleted.disconnect(self.trigger_refresh)
                self._connected_layer.geometryChanged.disconnect(self.trigger_refresh)
            except Exception:  # noqa: BLE001 — intentional suppress
                pass
            self._connected_layer = None
        if event:
            super().hideEvent(event)

    def showEvent(self, event):
        """Kết nối lại tín hiệu mà không tính lại dữ liệu đã có."""
        if event:
            super().showEvent(event)
        self._toggle_auto_update_connections()
        if (not self.stats_data or self._refresh_pending) and not self.current_task:
            self._refresh_pending = False
            self.trigger_refresh()

    def cleanup(self):
        """Dọn dẹp tài nguyên khi đóng hộp thoại."""
        self._closing = True
        self._refresh_timer.stop()
        if self.current_task:
            self.current_task.cancel()
            self.current_task = None
        self.hideEvent(None)
        
        # Ngắt kết nối shared state signals
        try:
            self.plugin_state.signals.layer_changed.disconnect(self._on_shared_layer_changed)
        except Exception:  # noqa: BLE001 — intentional suppress
            pass
        try:
            self.plugin_state.signals.code_field_changed.disconnect(self._on_shared_field_changed)
        except Exception:  # noqa: BLE001 — intentional suppress
            pass
        try:
            self.plugin_state.signals.area_field_changed.disconnect(self._on_shared_area_changed)
        except Exception:  # noqa: BLE001 — intentional suppress
            pass
