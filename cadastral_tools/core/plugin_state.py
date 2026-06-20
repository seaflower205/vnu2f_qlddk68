# -*- coding: utf-8 -*-
"""
Trạng thái dùng chung của plugin (Shared Plugin State).
Giúp đồng bộ hóa lớp dữ liệu và trường thuộc tính đang chọn giữa các tab.
"""

from qgis.PyQt.QtCore import QObject, pyqtSignal

class PluginStateSignals(QObject):
    # Tín hiệu phát ra khi có bất kỳ thay đổi nào
    state_changed = pyqtSignal()
    # Tín hiệu phát ra khi thay đổi Layer hoạt động
    layer_changed = pyqtSignal(str)
    # Tín hiệu phát ra khi thay đổi trường Mã loại đất
    code_field_changed = pyqtSignal(str)
    # Tín hiệu phát ra khi thay đổi trường Diện tích
    area_field_changed = pyqtSignal(str)

class PluginState:
    """Quản lý trạng thái và cấu hình dùng chung giữa các tab của plugin."""
    
    def __init__(self):
        self.signals = PluginStateSignals()
        self._active_layer_id = ""
        self._code_field = ""
        self._area_field = ""
        self._active_preset = "Địa chính chuẩn"
        self._layer_cache = None
        
        try:
            from qgis.core import QgsProject
            QgsProject.instance().layersAdded.connect(self.invalidate_layer_cache)
            QgsProject.instance().layersRemoved.connect(self.invalidate_layer_cache)
        except Exception:
            pass

    @property
    def active_layer_id(self) -> str:
        return self._active_layer_id

    @active_layer_id.setter
    def active_layer_id(self, val: str):
        if self._active_layer_id != val:
            self._active_layer_id = val
            self.signals.layer_changed.emit(val)
            self.signals.state_changed.emit()

    @property
    def code_field(self) -> str:
        return self._code_field

    @code_field.setter
    def code_field(self, val: str):
        if self._code_field != val:
            self._code_field = val
            self.signals.code_field_changed.emit(val)
            self.signals.state_changed.emit()

    @property
    def area_field(self) -> str:
        return self._area_field

    @area_field.setter
    def area_field(self, val: str):
        if self._area_field != val:
            self._area_field = val
            self.signals.area_field_changed.emit(val)
            self.signals.state_changed.emit()

    @property
    def active_preset(self) -> str:
        return self._active_preset

    @active_preset.setter
    def active_preset(self, val: str):
        if self._active_preset != val:
            self._active_preset = val
            self.signals.state_changed.emit()

    def invalidate_layer_cache(self, *args):
        self._layer_cache = None

    def get_project_layers(self) -> dict:
        """Cached access to QgsProject mapLayers to avoid repeated C++ boundary calls."""
        if self._layer_cache is None:
            try:
                from qgis.core import QgsProject
                self._layer_cache = QgsProject.instance().mapLayers().copy()
            except Exception:
                self._layer_cache = {}
        return self._layer_cache
