# -*- coding: utf-8 -*-
import os
from qgis.PyQt.QtWidgets import QMessageBox, QInputDialog, QFileDialog
from qgis.core import QgsProject, Qgis
from qgis.utils import iface

from vnu2f_qlddk68.cadastral_tools.core import label_manager as lbl_mgr
from vnu2f_qlddk68.cadastral_tools.core import import_export_manager as ie_mgr
from vnu2f_qlddk68.cadastral_tools.core.config_repository import ConfigRepository

class LabelConfigurator:
    @staticmethod
    def get_current_label_config(ui) -> dict:
        return {
            "preset": ui.cbo_preset.currentText(),
            "expression": ui.txt_expr_preview.toPlainText(),
            "font_family": ui.cbo_font.currentText(),
            "font_size_pt": ui.sp_font_size.value(),
            "color": ui.btn_color.hex_color(),
            "buffer_enabled": ui.chk_buffer.isChecked(),
            "buffer_color": ui.btn_buffer_color.hex_color(),
            "buffer_size": ui.sp_buffer_size.value(),
            "scale_limit": ui.cbo_scale_limit.currentData(),
            "placement_mode": ui.cbo_placement.currentData(),
            "conflict_resolution": ui.chk_conflict.isChecked(),
            
            "field_mapping": {
                "sothua": ui.cbo_f_sothua.currentText(),
                "ma_dat": ui.cbo_f_ma_dat.currentText(),
                "dientich": ui.cbo_f_dientich.currentText(),
                "to_ban_do": ui.cbo_f_to_ban_do.currentData()
            }
        }

    @staticmethod
    def apply_labels(layer_id, ui):
        if not layer_id:
            return
            
        layer = QgsProject.instance().mapLayer(layer_id)
        if not layer:
            return

        config = LabelConfigurator.get_current_label_config(ui)
        lbl_mgr.apply_to_layer(layer, config)
        
        if iface:
            iface.messageBar().pushMessage(
                "Địa chính", "Đã bật hiển thị nhãn địa chính thành công.",
                level=Qgis.Success, duration=4
            )

    @staticmethod
    def disable_labels(layer_id):
        if not layer_id:
            return
            
        layer = QgsProject.instance().mapLayer(layer_id)
        if not layer:
            return
            
        lbl_mgr.disable_labels(layer)
        if iface:
            iface.messageBar().pushMessage(
                "Địa chính", "Đã tắt hiển thị nhãn trên bản đồ.",
                level=Qgis.Info, duration=3
            )

    @staticmethod
    def save_current_as_preset(parent_widget, ui, presets):
        name, ok = QInputDialog.getText(parent_widget, "Lưu Preset nhãn", "Nhập tên cho Preset nhãn mới:")
        if not ok or not name.strip():
            return False, None
            
        name = name.strip()
        
        if name in ["Địa chính chuẩn", "Rút gọn", "Đầy đủ", "Tùy chỉnh"]:
            QMessageBox.warning(parent_widget, "Cảnh báo", "Không thể ghi đè các Preset mặc định.")
            return False, None

        preset_name = ui.cbo_preset.currentText()
        base_template = presets.get(preset_name, {}).get("expression_template", "{sothua}")

        new_preset = {
            "expression_template": base_template,
            "scale_limit": ui.cbo_scale_limit.currentData(),
            "font_family": ui.cbo_font.currentText(),
            "font_size_pt": ui.sp_font_size.value(),
            "color": ui.btn_color.hex_color(),
            "buffer_enabled": ui.chk_buffer.isChecked(),
            "buffer_color": ui.btn_buffer_color.hex_color(),
            "buffer_size": ui.sp_buffer_size.value(),
            "conflict_resolution": ui.chk_conflict.isChecked(),
            "placement_mode": ui.cbo_placement.currentData()
        }
        
        presets[name] = new_preset

        if ConfigRepository.save_config("label_presets", presets):
            QMessageBox.information(parent_widget, "Thành công", f"Đã lưu thành công preset nhãn '{name}'.")
            return True, name
        else:
            QMessageBox.critical(parent_widget, "Lỗi", "Không thể lưu preset nhãn.")
            return False, None

    @staticmethod
    def import_preset(parent_widget, current_presets):
        file_path, _ = QFileDialog.getOpenFileName(parent_widget, "Nhập preset nhãn", "", "Cấu hình nhãn (*.json)")
        if not file_path:
            return False
            
        try:
            imported = ie_mgr.import_label_json(file_path)
            for name, preset_cfg in imported.items():
                if name not in ["Địa chính chuẩn", "Rút gọn", "Đầy đủ", "Tùy chỉnh"]:
                    current_presets[name] = preset_cfg
                    
            ConfigRepository.save_config("label_presets", current_presets)
            if iface:
                iface.messageBar().pushMessage(
                    "Nhập preset", f"Đã nhập thành công các preset nhãn từ {os.path.basename(file_path)}",
                    level=Qgis.Success, duration=5
                )
            return True
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(parent_widget, "Lỗi", f"Không thể nhập preset nhãn: {str(e)}")
            return False

    @staticmethod
    def export_preset(parent_widget, current_presets):
        file_path, _ = QFileDialog.getSaveFileName(parent_widget, "Xuất các preset nhãn", "", "Cấu hình nhãn (*.json)")
        if not file_path:
            return
            
        try:
            ie_mgr.export_label_json(current_presets, file_path)
            if iface:
                iface.messageBar().pushMessage(
                    "Xuất preset", f"Đã xuất các preset nhãn ra: {os.path.basename(file_path)}",
                    level=Qgis.Success, duration=5
                )
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(parent_widget, "Lỗi", f"Không thể xuất preset nhãn: {str(e)}")
