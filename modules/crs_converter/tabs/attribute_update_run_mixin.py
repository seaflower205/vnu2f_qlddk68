"""Mechanically extracted responsibilities from attribute_update_tab.py."""

import re
import traceback
from qgis.PyQt.QtCore import QMetaType


class _QVariantCompat:
    String = QMetaType.Type.QString


QVariant = _QVariantCompat()
from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGroupBox, QGridLayout, 
    QMessageBox, QProgressBar, QTextEdit, QDialog, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QDialogButtonBox
)
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsField
from qgis.gui import QgsMapLayerComboBox
from qgis.PyQt.QtWidgets import QApplication
from modules.common.ui_utils import create_themed_button


class AttributeUpdateRunMixin:
    def _on_run_clicked(self):
        layer = self.cmb_layer.currentLayer()
        if not layer:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn một lớp dữ liệu Polygon hợp lệ.")
            return

        if not layer.isValid():
            QMessageBox.warning(self, "Lỗi", "Lớp dữ liệu không hợp lệ.")
            return

        fields = layer.fields()
        if fields.indexOf('MDSD2003') == -1:
            QMessageBox.warning(self, "Lỗi", "Lớp dữ liệu phải có trường 'MDSD2003' để thực hiện tính năng này.")
            return

        self.btn_run.setEnabled(False)
        self.progress.show()
        self.progress.setValue(0)
        self.txt_log.clear()
        self._log(f"Bắt đầu xử lý lớp: {layer.name()}")

        try:
            # Kiểm tra xem có trường HTSDD2026 chưa, nếu chưa thì thêm mới
            field_idx = fields.indexOf('HTSDD2026')
            if field_idx == -1:
                self._log("Chưa có trường HTSDD2026. Đang tự động thêm mới...")
                layer.startEditing()
                if not layer.addAttribute(QgsField('HTSDD2026', QVariant.String, len=50)):
                    layer.rollBack()
                    raise Exception("Không thể tạo trường HTSDD2026.")
                layer.commitChanges()
                self._log("Đã thêm trường HTSDD2026 thành công.")

            # Cập nhật dữ liệu
            layer.startEditing()
            field_idx = layer.fields().indexOf('HTSDD2026')
            
            features = list(layer.getFeatures())
            total = len(features)
            if total == 0:
                self._log("Lớp dữ liệu không có đối tượng nào.")
                layer.rollBack()
                self.btn_run.setEnabled(True)
                self.progress.hide()
                return

            priorities = {
                'ODT': 1, 'ONT': 1,
                'TMD': 2, 'SKC': 2, 'CQC': 2, 'DTS': 2, 'DVH': 2, 'DYT': 2, 'DGD': 2, 'TTN': 2, 'CQP': 2, 'SKK': 2, 'SKX': 2, 'PNK': 2,
                'LUC': 3, 'LUK': 3, 'BHK': 3, 'NHK': 3,
                'CLN': 4, 'RSX': 4, 'RPH': 4, 'RDD': 4,
                'NTS': 5, 'LMQ': 5,
            }

            # Quét tìm các mã hỗn hợp cần người dùng quyết định
            mixed_codes_set = set()
            for feat in features:
                raw_mdsd = feat['MDSD2003']
                if not raw_mdsd or not isinstance(raw_mdsd, str):
                    continue
                parts = re.split(r'\+|-|,|/|\s+', str(raw_mdsd).strip())
                if len(parts) > 1:
                    codes = []
                    for p in parts:
                        clean_p = p.strip().upper()
                        if len(clean_p) >= 3:
                            codes.append(clean_p[:3])
                        elif len(clean_p) > 0:
                            codes.append(clean_p)
                    
                    if not codes:
                        continue
                    
                    has_residential = any(priorities.get(c, 99) == 1 for c in codes)
                    if not has_residential:
                        mixed_codes_set.add(str(raw_mdsd).strip())
            
            user_mappings = {}
            if mixed_codes_set:
                dialog = self.resolver_dialog_class(list(mixed_codes_set), priorities, self)
                if dialog.exec_() == QDialog.Accepted:
                    user_mappings = dialog.user_mappings
                else:
                    self._log("Người dùng đã hủy bỏ quá trình cập nhật.")
                    layer.rollBack()
                    self.btn_run.setEnabled(True)
                    self.progress.hide()
                    return

            self.progress.setMaximum(total)
            updated_count = 0
            
            for i, feat in enumerate(features):
                raw_mdsd = feat['MDSD2003']
                if raw_mdsd and isinstance(raw_mdsd, str):
                    raw_mdsd_str = str(raw_mdsd).strip()
                    if raw_mdsd_str in user_mappings:
                        new_val = user_mappings[raw_mdsd_str]
                    else:
                        new_val = self._get_prioritized_land_code(raw_mdsd)
                        
                    if new_val:
                        layer.changeAttributeValue(feat.id(), field_idx, new_val)
                        updated_count += 1
                
                # Cập nhật giao diện sau mỗi 100 đối tượng
                if i % 100 == 0:
                    self.progress.setValue(i)
                    QApplication.processEvents()

            if not layer.commitChanges():
                raise Exception("Lỗi khi lưu các thay đổi vào CSDL QGIS.")

            self.progress.setValue(total)
            self._log(f"✅ Hoàn tất! Đã cập nhật {updated_count}/{total} đối tượng.")
            QMessageBox.information(self, "Thành công", f"Cập nhật thành công {updated_count} bản ghi.")
            
        except Exception as e:
            if layer.isEditable():
                layer.rollBack()
            self._log(f"❌ Lỗi trong quá trình xử lý: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Lỗi", f"Không thể cập nhật: {e}")
        finally:
            self.btn_run.setEnabled(True)
            self.progress.hide()
