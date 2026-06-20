# -*- coding: utf-8 -*-
"""
Giao diện Tab Ký hiệu (Symbology Tab).
Cho phép biên tập trực quan bảng phân loại màu sắc, đường viền, hoa văn loại đất và áp dụng lên layer.
"""

import json
import os

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QMessageBox, QWidget
from qgis.core import QgsProject, Qgis
from qgis.utils import iface

from ..core import symbology_manager as sym_mgr
from .symbology.bulk_editor import SymbologyBulkEditor
from .symbology.context_menu import SymbologyContextMenuHandler
from .symbology.import_export import SymbologyImportExportHandler
from .symbology.inline_editor import SymbologyInlineEditor
from .symbology.selection_preserver import TableSelectionPreserver
from .symbology.tab_ui import SymbologyTabUi
from .symbology.table_mapper import SymbologyTableMapper
from .symbology.scanner_applier import ScannerApplier
from .symbology.config import ConfigLoader

from ..core.symbology_constants import PATTERN_ALIASES, normalize_pattern_key
from .symbology_actions_mixin import SymbologyActionsMixin

PATTERN_MAP = {
    "Solid": "solid",
    "No Brush": "no_brush",
    "Horizontal Hatch": "horizontal",
    "Vertical Hatch": "vertical",
    "Diagonal Hatch": "diagonal_fwd",
    "Backward Diagonal Hatch": "diagonal_bwd",
    "Cross Hatch": "cross",
    "Cross Diagonal Hatch": "diagonal_cross",
    "Dense 1": "dense_1",
    "Dense 2": "dense_2",
    "Dense 3": "dense_3",
    "Dense 4": "dense_4",
    "Dense 5": "dense_5",
    "Dense 6": "dense_6",
    "Dense 7": "dense_7",
    "Centroid Fill": "centroid",
    "Geometry Generator": "geom_generator",
    "Gradient Fill": "gradient",
    "Line Pattern Fill": "line_pattern",
    "Point Pattern Fill": "point_pattern",
    "Random Marker Fill": "random_marker",
    "Raster Fill": "raster_image",
    "SVG Fill": "svg",
    "Shapeburst Fill": "shapeburst",
    "Outline: Arrow": "outline_arrow",
    "Outline: Filled Line": "outline_filled",
    "Outline: Hashed Line": "outline_hashed",
    "Outline: Interpolated Line": "outline_interpolated",
    "Outline: Linear Referencing": "outline_linear_ref",
    "Outline: Lineburst": "outline_lineburst",
    "Outline: Marker Line": "outline_marker",
    "Outline: Raster Line": "outline_raster",
    "Outline: Simple Line": "outline_simple"
}

class SymbologyTab(SymbologyActionsMixin, QWidget):
    """Tab quản lý và thiết lập ký hiệu bản đồ địa chính."""

    def __init__(self, plugin_state, parent=None):
        super().__init__(parent)
        self.plugin_state = plugin_state
        self.plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.current_pattern_map = PATTERN_MAP

        self.ui = SymbologyTabUi()
        self.ui.setup_ui(self)
        self.table_mapper = SymbologyTableMapper(self.table)
        self.inline_editor = SymbologyInlineEditor(self.table)
        self.bulk_editor = SymbologyBulkEditor(self.table, self)
        self.context_menu = SymbologyContextMenuHandler(
            self.table,
            self.bulk_editor,
            self.table_mapper,
            self,
        )
        self.import_export = SymbologyImportExportHandler(self)
        self.selection_preserver = TableSelectionPreserver(self.table, self)
        self.table.viewport().installEventFilter(self.selection_preserver)
        self._connect_signals()
        
        # Nạp dữ liệu ban đầu trì hoãn bằng QTimer để tránh block UI
        from qgis.PyQt.QtCore import QTimer
        QTimer.singleShot(0, self._deferred_init)
        
        # Đăng ký nhận đồng bộ trạng thái
        self.plugin_state.signals.layer_changed.connect(self._on_shared_layer_changed)
        self.plugin_state.signals.code_field_changed.connect(self._on_shared_field_changed)

    def _deferred_init(self):
        self.populate_layers()
        self.reset_to_defaults()

    def _connect_signals(self):
        self.cbo_layer.currentIndexChanged.connect(self._on_layer_changed)
        self.cbo_field.currentIndexChanged.connect(self._on_field_changed)
        self.btn_scan.clicked.connect(self._on_scan_layer_codes)
        self.btn_apply.clicked.connect(self.apply_symbology)
        self.btn_reset.clicked.connect(self.reset_to_defaults)
        self.txt_search.textChanged.connect(self._on_search_text_changed)
        self.btn_import.clicked.connect(self._on_import_clicked)
        self.btn_export.clicked.connect(self._on_export_clicked)
        self.btn_export_qml.clicked.connect(self._on_export_qml_clicked)
        self.table.itemChanged.connect(self._on_item_changed)
        self.table.itemSelectionChanged.connect(self.inline_editor.on_selection_changed)
        self.table.customContextMenuRequested.connect(
            self.context_menu.show_context_menu
        )
        QgsProject.instance().layersAdded.connect(self.populate_layers)
        QgsProject.instance().layersRemoved.connect(self.populate_layers)

    def populate_layers(self, *_args):
        """Refresh the native layer combo and restore the shared selection."""
        layer_id = self.plugin_state.active_layer_id
        if layer_id:
            layer = QgsProject.instance().mapLayer(layer_id)
            if layer:
                self.cbo_layer.setLayer(layer)
        # QgsMapLayerComboBox may already point at the requested layer during
        # deferred initialization. In that case setLayer() emits no change
        # signal, so the field combo would remain empty until the user picked
        # another polygon and came back. Always synchronize the dependent
        # field list after restoring the layer.
        self._on_layer_changed()

    def selected_layer(self):
        """Return the selected polygon layer with a compatibility fallback."""
        current_layer = getattr(self.cbo_layer, "currentLayer", None)
        if callable(current_layer):
            layer = current_layer()
            if layer:
                return layer
        layer_id = self.cbo_layer.currentData()
        return QgsProject.instance().mapLayer(layer_id) if layer_id else None

    def _on_layer_changed(self, *_args):
        """Update available fields when the active polygon layer changes."""
        self.cbo_field.blockSignals(True)
        self.cbo_field.clear()
        layer = self.selected_layer()
        if not layer:
            self.cbo_field.blockSignals(False)
            return

        self.plugin_state.active_layer_id = layer.id()
        suggested_idx = 0
        suggestions = {
            "LOAIDAT",
            "MA_DAT",
            "LOAI_DAT",
            "MADOITUONG",
            "LOAIDAT_TT25",
            "KHLOAIDAT",
            "MALOAIDAT",
        }
        for idx, field in enumerate(layer.fields()):
            field_name = field.name()
            self.cbo_field.addItem(field_name)
            if field_name.upper() in suggestions:
                suggested_idx = idx

        self.cbo_field.blockSignals(False)
        if self.cbo_field.count() > 0:
            self.cbo_field.setCurrentIndex(suggested_idx)
            self._on_field_changed()

    def _on_field_changed(self):
        """Đồng bộ trường dữ liệu đang chọn với Shared State và cập nhật thứ tự ưu tiên."""
        field_name = self.cbo_field.currentText()
        if field_name:
            self.plugin_state.code_field = field_name
            # Sắp xếp lại bảng để đưa các mã của dự án lên đầu khi đổi trường dữ liệu
            current_configs = self.get_current_code_configs()
            if current_configs:
                self.load_code_configs_to_table(current_configs)

    def _on_search_text_changed(self, text):
        """Lọc các hàng trong bảng dựa trên từ khóa tìm kiếm (Mã hoặc Tên loại đất)."""
        q = text.strip().lower()
        for row in range(self.table.rowCount()):
            item_code = self.table.item(row, 1)
            item_name = self.table.item(row, 2)
            
            code_text = item_code.text().lower() if item_code else ""
            name_text = item_name.text().lower() if item_name else ""
            
            if not q or q in code_text or q in name_text:
                self.table.setRowHidden(row, False)
            else:
                self.table.setRowHidden(row, True)

    def _on_shared_layer_changed(self, layer_id):
        """Synchronize the native layer combo with shared plugin state."""
        layer = QgsProject.instance().mapLayer(layer_id)
        if layer and layer is not self.selected_layer():
            self.cbo_layer.blockSignals(True)
            self.cbo_layer.setLayer(layer)
            self.cbo_layer.blockSignals(False)
            self._on_layer_changed()

    def _on_shared_field_changed(self, field_name):
        """Đồng bộ từ các tab khác khi trường mã loại đất thay đổi."""
        idx = self.cbo_field.findText(field_name)
        if idx != -1 and idx != self.cbo_field.currentIndex():
            self.cbo_field.blockSignals(True)
            self.cbo_field.setCurrentIndex(idx)
            self.cbo_field.blockSignals(False)

    def _get_active_layer_unique_codes(self) -> set[str]:
        """Return normalized codes present in the selected layer."""
        return ScannerApplier.scan_layer_codes(self.selected_layer(), self.cbo_field.currentText())

    def reset_to_defaults(self):
        """Tải cấu hình bảng mặc định từ file land_use_codes.json."""
        configs = ConfigLoader.load_defaults(self.plugin_dir, iface)
        if configs:
            self.load_code_configs_to_table(configs)

    def load_code_configs_to_table(self, configs: list[dict]):
        """Sort project codes first, then delegate table rendering."""
        scanned_codes = self._get_active_layer_unique_codes()
        sorted_configs = sorted(
            configs,
            key=lambda config: (
                config.get("code", "").strip().upper() not in scanned_codes,
            ),
        )
        self.table_mapper.load_code_configs_to_table(
            sorted_configs,
            scanned_codes,
            self.current_pattern_map,
        )

    def get_current_code_configs(self) -> list[dict]:
        return self.table_mapper.get_current_code_configs(
            self.current_pattern_map
        )


    def _check_missing_codes(self, scanned_codes: set[str], configs: list[dict]):
        """Đếm số thửa đất chứa mã chưa nằm trong bảng cấu hình và hiện cảnh báo."""
        missing_codes = ScannerApplier.check_missing_codes(scanned_codes, configs)
        missing_count = len(missing_codes)
        
        if missing_count > 0 and iface:
            msg = f"Có {missing_count} loại mã đất chưa nhận dạng được ({', '.join(list(missing_codes)[:5])}...)."
            iface.messageBar().pushMessage(
                "Cảnh báo ký hiệu", msg + " Hãy bổ sung vào tab Ký hiệu.",
                level=Qgis.Warning, duration=10
            )


    def _show_context_menu(self, pos):
        self.context_menu.show_context_menu(pos)

    def _add_row_at(self, row):
        self.table_mapper.add_row_at(row)

    def _delete_row_at(self, row):
        self.table_mapper.delete_row_at(row)

    def _update_row_numbers(self):
        self.table_mapper.update_row_numbers()

    def _on_item_changed(self, item):
        self.inline_editor.on_item_changed(item)

    # Import/export compatibility methods kept for existing callers.

    def _on_import_clicked(self):
        self.import_export.open_import()

    def _on_export_clicked(self):
        self.import_export.open_export()

    def _on_export_qml_clicked(self):
        self.import_export.export_qml()

    def _open_import_export_dialog(self, active_tab_index):
        self.import_export._open_dialog(active_tab_index)

    def _handle_imported_config(self, config_info):
        self.import_export.handle_imported_config(config_info)
