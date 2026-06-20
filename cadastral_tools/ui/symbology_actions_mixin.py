"""Mechanically extracted responsibilities from symbology_tab.py."""

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


class SymbologyActionsMixin:
    def apply_symbology(self):
        """Xây dựng và áp dụng ký hiệu màu sắc lên layer đang chọn."""
        layer = self.selected_layer()
        field_name = self.cbo_field.currentText()

        if not layer or not field_name:
            if iface:
                iface.messageBar().pushMessage(
                    "Cảnh báo",
                    "Vui lòng chọn đầy đủ Layer và Trường thuộc tính trước.",
                    level=Qgis.Warning,
                    duration=4,
                )
            return

        scanned_codes = self._get_active_layer_unique_codes()
        
        if not scanned_codes:
            if iface:
                iface.messageBar().pushMessage(
                    "Cảnh báo", "Không tìm thấy bất kỳ mã loại đất nào trong lớp bản đồ đã chọn hoặc trường dữ liệu rỗng.",
                    level=Qgis.Warning, duration=4
                )
            return

        configs = self.get_current_code_configs()
        total_configs = len(configs)
        
        applied_count, skipped_count = ScannerApplier.apply_symbology(layer, field_name, configs, scanned_codes)
        
        if applied_count == 0:
            if iface:
                iface.messageBar().pushMessage(
                    "Cảnh báo",
                    "Không có mã nào trong bảng cấu hình khớp với dữ liệu thực tế của lớp bản đồ.",
                    level=Qgis.Warning, duration=4
                )
            return
            
        if iface:
            msg = f"Đã áp dụng thành công {applied_count}/{total_configs} mã loại đất (bỏ qua {skipped_count} mã không có trong dự án)."
            iface.messageBar().pushMessage(
                "Địa chính", msg,
                level=Qgis.Success, duration=4
            )
            
        if self.chk_highlight_unmatched.isChecked():
            self._check_missing_codes(scanned_codes, configs)
    def _on_scan_layer_codes(self):
        """Quét toàn bộ layer tìm các mã loại đất chưa được cấu hình và thêm vào bảng."""
        scanned_codes = self._get_active_layer_unique_codes()
        if not scanned_codes:
            return

        # Lấy các mã hiện tại trong bảng
        current_configs = self.get_current_code_configs()
        current_codes = {cfg["code"] for cfg in current_configs}
        
        # Tải bộ từ điển land_use_codes mặc định để map nếu có
        land_use_codes = ConfigLoader.get_land_use_codes_dict(self.plugin_dir)

        added_count = 0
        new_configs = list(current_configs)
        
        for code in scanned_codes:
            if code not in current_codes:
                # Tìm thông tin mặc định
                if code in land_use_codes:
                    cfg = land_use_codes[code].copy()
                    cfg["code"] = code
                else:
                    cfg = {
                        "code": code,
                        "name_vi": f"Loại đất {code} (quét được)",
                        "fill_color": "#e2e8f0",
                        "border_color": "#000000",
                        "border_width_mm": 0.26,
                        "pattern": "solid",
                        "opacity": 1.0,
                        "source": "approximated"
                    }
                new_configs.append(cfg)
                added_count += 1
                
        if added_count > 0:
            self.load_code_configs_to_table(new_configs)
            if iface:
                iface.messageBar().pushMessage(
                    "Quét mã", f"Đã quét và bổ sung thêm {added_count} mã mới vào bảng.",
                    level=Qgis.Info, duration=4
                )
        else:
            if iface:
                iface.messageBar().pushMessage(
                    "Quét mã", "Không phát hiện mã loại đất mới nào so với bảng hiện có.",
                    level=Qgis.Info, duration=4
                )
