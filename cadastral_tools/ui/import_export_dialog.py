# -*- coding: utf-8 -*-
"""
Hộp thoại Nhập/Xuất cấu hình (Import/Export Dialog).
Hỗ trợ chọn các mục cần xuất (Ký hiệu, Nhãn, Cài đặt chung) và cấu hình gộp khi nhập.
"""

import os
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QCheckBox, 
    QRadioButton, QButtonGroup, QLabel, QPushButton, QFileDialog, 
    QMessageBox, QGroupBox, QLineEdit
)
from qgis.core import QgsProject, QgsMessageLog, Qgis

from ..core import import_export_manager as ie_mgr
from modules.common.ui_utils import get_dialog_stylesheet, customize_combo_boxes, create_themed_button, create_file_browser_row, create_bottom_action_bar
from .import_export_ui_mixin import ImportExportUiMixin

class ImportExportDialog(ImportExportUiMixin, QDialog):
    """Hộp thoại Nhập/Xuất cấu hình địa chính."""
    
    # Phát tín hiệu khi cấu hình thay đổi cần nạp lại UI
    config_imported = pyqtSignal(dict)

    def __init__(self, active_layer=None, parent=None):
        super().__init__(parent)
        self.active_layer = active_layer
        self.setWindowTitle("Nhập / Xuất Cấu Hình Địa Chính")
        self.resize(500, 420)
        self.setMinimumSize(450, 380)
        
        self._setup_ui()
        self.setStyleSheet(get_dialog_stylesheet())
        customize_combo_boxes(self)


    def _update_export_ui_state(self):
        """Cập nhật trạng thái enabled của phần chọn định dạng dựa trên checkbox."""
        only_symbology = self.chk_symbology.isChecked() and not self.chk_labels.isChecked() and not self.chk_settings.isChecked()
        self.grp_format.setEnabled(only_symbology)
        
        # Nếu chọn nhiều mục, mặc định lưu là profile
        has_selections = self.chk_symbology.isChecked() or self.chk_labels.isChecked() or self.chk_settings.isChecked()
        self.btn_export.setEnabled(has_selections)

    def _on_browse_import_file(self):
        """Mở hộp thoại chọn file nhập và thực hiện nhận dạng định dạng."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file cấu hình để nhập", "", 
            "Cấu hình địa chính (*.json *.qml *.cadprofile);;Tất cả các file (*.*)"
        )
        if not file_path:
            return
            
        self.txt_file.setText(file_path)
        
        # Nhận dạng định dạng file
        fmt = ie_mgr.detect_format(file_path)
        if fmt == "symbology_json":
            self.lbl_format_status.setText("Định dạng nhận diện: Ký hiệu màu sắc (JSON)")
            self.lbl_format_status.setStyleSheet("font-weight: bold; color: #22c55e;")
            self.grp_merge.setVisible(True)
        elif fmt == "symbology_qml":
            self.lbl_format_status.setText("Định dạng nhận diện: Style QML QGIS chuẩn")
            self.lbl_format_status.setStyleSheet("font-weight: bold; color: #22c55e;")
            self.grp_merge.setVisible(False)
        elif fmt == "label_json":
            self.lbl_format_status.setText("Định dạng nhận diện: Cấu hình nhãn (JSON)")
            self.lbl_format_status.setStyleSheet("font-weight: bold; color: #22c55e;")
            self.grp_merge.setVisible(False)
        elif fmt == "profile":
            self.lbl_format_status.setText("Định dạng nhận diện: Profile toàn bộ (.cadprofile)")
            self.lbl_format_status.setStyleSheet("font-weight: bold; color: #22c55e;")
            self.grp_merge.setVisible(False)
        else:
            self.lbl_format_status.setText("Định dạng: Không nhận dạng được hoặc file lỗi.")
            self.lbl_format_status.setStyleSheet("font-weight: bold; color: #ef4444;")
            self.grp_merge.setVisible(False)

    def _on_export(self):
        """Thực hiện xuất cấu hình dựa trên các mục được check."""
        # Kiểm tra xuất đơn lẻ Ký hiệu QML
        only_symbology = self.chk_symbology.isChecked() and not self.chk_labels.isChecked() and not self.chk_settings.isChecked()
        
        try:
            if only_symbology and self.rad_qml.isChecked():
                if not self.active_layer:
                    QMessageBox.warning(self, "Cảnh báo", "Hãy chọn một layer đang hoạt động để xuất file QML.")
                    return
                file_path, _ = QFileDialog.getSaveFileName(self, "Lưu file QML", "", "QGIS Layer Style (*.qml)")
                if file_path:
                    ie_mgr.export_symbology_qml(self.active_layer, file_path)
                    QMessageBox.information(self, "Thành công", f"Đã xuất style ký hiệu QML ra:\n{os.path.basename(file_path)}")
                    self.accept()
            else:
                # Nếu là JSON hoặc nhiều mục (đóng gói thành .cadprofile hoặc JSON)
                if not (self.chk_symbology.isChecked() or self.chk_labels.isChecked() or self.chk_settings.isChecked()):
                    return
                    
                # Quyết định file extension
                is_profile = (int(self.chk_symbology.isChecked()) + int(self.chk_labels.isChecked()) + int(self.chk_settings.isChecked())) > 1
                
                default_ext = "Hồ sơ trọn bộ (*.cadprofile)" if is_profile else "Cấu hình JSON (*.json)"
                file_path, _ = QFileDialog.getSaveFileName(
                    self, "Lưu file cấu hình", "", 
                    default_ext + ";;Tất cả các file (*.*)"
                )
                if not file_path:
                    return
                    
                # Chuẩn bị dữ liệu để xuất (UI chính hoặc Tab cha sẽ truyền xuống)
                # Vì dialog mở độc lập, ta sẽ gửi tín hiệu yêu cầu UI chính cung cấp dữ liệu
                # Hoặc lấy tạm dữ liệu từ PluginState
                # Ở đây chúng ta sẽ giả định người gọi dialog này sẽ lắng nghe và gọi trực tiếp các hàm export.
                # Để thuận tiện, ta truyền một callback hoặc dữ liệu vào lúc khởi tạo.
                # Để đơn giản và trực tiếp nhất: ta định nghĩa một tín hiệu/callback hoặc thu thập trực tiếp.
                # Lấy dữ liệu mẫu từ parent (QDockWidget panel chứa các tab):
                parent_panel = self.parent()
                symbology_data = []
                label_data = {}
                settings_data = {}
                
                # Thu thập dữ liệu từ các tab hiện có thông qua parent panel
                if parent_panel and hasattr(parent_panel, "tab_symbology"):
                    symbology_data = parent_panel.tab_symbology.get_current_code_configs()
                if parent_panel and hasattr(parent_panel, "tab_labels"):
                    label_data = parent_panel.tab_labels.get_current_label_config()
                if parent_panel and hasattr(parent_panel, "tab_settings"):
                    settings_data = parent_panel.tab_settings.get_current_settings()
                
                if is_profile:
                    # Xuất toàn bộ profile
                    ie_mgr.export_full_profile(
                        code_configs=symbology_data if self.chk_symbology.isChecked() else [],
                        label_config=label_data if self.chk_labels.isChecked() else {},
                        general_settings=settings_data if self.chk_settings.isChecked() else {},
                        file_path=file_path
                    )
                    QMessageBox.information(self, "Thành công", f"Đã xuất hồ sơ trọn bộ ra:\n{os.path.basename(file_path)}")
                else:
                    # Xuất đơn lẻ
                    if self.chk_symbology.isChecked():
                        ie_mgr.export_symbology_json(symbology_data, file_path)
                        QMessageBox.information(self, "Thành công", f"Đã xuất cấu hình ký hiệu màu sắc ra:\n{os.path.basename(file_path)}")
                    elif self.chk_labels.isChecked():
                        ie_mgr.export_label_json(label_data, file_path)
                        QMessageBox.information(self, "Thành công", f"Đã xuất cấu hình nhãn ra:\n{os.path.basename(file_path)}")
                    elif self.chk_settings.isChecked():
                        # Settings đơn lẻ cũng xuất thành JSON
                        with open(file_path, "w", encoding="utf-8") as f:
                            import json
                            json.dump(settings_data, f, ensure_ascii=False, indent=2)
                        QMessageBox.information(self, "Thành công", f"Đã xuất cấu hình cài đặt chung ra:\n{os.path.basename(file_path)}")
                
                self.accept()
        except Exception as e:  # noqa: BLE001 — intentional suppress
            QMessageBox.critical(self, "Lỗi", f"Có lỗi xảy ra khi xuất cấu hình: {str(e)}")

    def _on_import(self):
        """Thực hiện nhập cấu hình dựa trên file được chọn."""
        file_path = self.txt_file.text().strip()
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn file cấu hình hợp lệ để nhập.")
            return
            
        fmt = ie_mgr.detect_format(file_path)
        if fmt == "unknown":
            QMessageBox.warning(self, "Lỗi", "Định dạng file không được hỗ trợ hoặc file trống.")
            return
            
        try:
            imported_data = {}
            if fmt == "symbology_json":
                # Đọc mã và thực hiện gộp
                new_codes = ie_mgr.import_symbology_json(file_path)
                
                # Xác định chế độ gộp
                mode = "merge"
                if self.rad_merge_replace.isChecked():
                    mode = "replace"
                elif self.rad_merge_update.isChecked():
                    mode = "update_existing"
                    
                imported_data = {
                    "type": "symbology_json",
                    "data": new_codes,
                    "merge_mode": mode
                }
                
            elif fmt == "symbology_qml":
                if not self.active_layer:
                    QMessageBox.warning(self, "Cảnh báo", "Hãy chọn một layer đang hoạt động để áp dụng style QML.")
                    return
                success = ie_mgr.import_symbology_qml(file_path, self.active_layer)
                if success:
                    imported_data = {
                        "type": "symbology_qml",
                        "file_path": file_path
                    }
                else:
                    raise RuntimeError("QGIS không nạp được style QML.")
                    
            elif fmt == "label_json":
                labels = ie_mgr.import_label_json(file_path)
                imported_data = {
                    "type": "label_json",
                    "data": labels
                }
                
            elif fmt == "profile":
                profile = ie_mgr.import_full_profile(file_path)
                imported_data = {
                    "type": "profile",
                    "data": profile
                }
                if profile.get("version_warning"):
                    QMessageBox.warning(
                        self, "Cảnh báo phiên bản", 
                        "File .cadprofile được tạo từ phiên bản khác. Plugin sẽ cố gắng nhập các phần tương thích."
                    )
            
            # Phát tín hiệu báo cho panel chính cập nhật UI các tab
            self.config_imported.emit(imported_data)
            
            # Thông báo thành công
            QMessageBox.information(
                self, "Thành công", 
                f"Đã nhập dữ liệu cấu hình thành công từ:\n{os.path.basename(file_path)}"
            )
            self.accept()
            
        except Exception as e:  # noqa: BLE001 — intentional suppress
            QMessageBox.critical(self, "Lỗi", f"Không thể nhập cấu hình: {str(e)}")
