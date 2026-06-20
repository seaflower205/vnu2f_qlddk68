# -*- coding: utf-8 -*-
"""
Giao diện phân hệ Xuất báo cáo địa chính Excel (Report Tab).
"""

import os
from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QComboBox, QMessageBox, QTableWidget,
    QTableWidgetItem, QLineEdit, QFileDialog
)
from qgis.core import (
    QgsMapLayerProxyModel
)
from qgis.gui import QgsMapLayerComboBox

from ...common.qt_compat import HeaderStretch, ItemIsEnabled, ItemIsSelectable
from ...common.scroll_utils import make_scroll_area
from modules.common.ui_utils import (
    create_themed_button,
    create_centered_panel,
    create_form_group,
    create_growing_form,
    tune_form_controls,
)
from ...common.i18n import tr
from ...common.dep_installer import is_installed
from ...report_generator.field_mapper import auto_detect_mapping
from .tab_text import tab_text
from .report_tab_ui_mixin import ReportTabUiMixin


def tx(key, **kwargs):
    return tab_text("report", key, **kwargs)

class ReportTab(ReportTabUiMixin, QWidget):
    """Giao diện lập biểu và xuất báo cáo địa chính Excel."""

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.parent_dialog = parent
        
        # Danh sách trường chuẩn cần ánh xạ
        self.std_fields = {
            "sothua": tx("field.sothua"),
            "soto": tx("field.soto"),
            "loaidat": tx("field.loaidat"),
            "tenchu": tx("field.tenchu"),
            "dientich": tx("field.dientich")
        }
        
        # Ánh xạ hiện tại (chuẩn -> trường QGIS)
        self.current_mapping = {}
        self.lbl_warn = None
        
        self._build_ui()


    def _deps_ready(self):
        return is_installed("openpyxl")

    def showEvent(self, event):
        """Khi tab được kích hoạt, tự động kiểm tra lại dependency xem đã cài đặt xong chưa."""
        super().showEvent(event)
        now_ok = self._deps_ready()
        if now_ok != self.deps_ok:
            self.deps_ok = now_ok
            self._set_dependency_controls(now_ok)

    def _set_dependency_controls(self, enabled: bool):
        self.btn_export.setEnabled(enabled)
        if self.lbl_warn:
            self.lbl_warn.setVisible(not enabled)

    def _on_layer_changed(self):
        """Kích hoạt khi chọn lớp dữ liệu khác để tự động quét ánh xạ trường."""
        layer = self.cmb_poly_layer.currentLayer()
        if not layer:
            self.tbl_mapping.setRowCount(0)
            return
            
        # Tự động phát hiện ánh xạ
        self.current_mapping = auto_detect_mapping(layer.fields())
        
        # Thiết lập bảng ánh xạ
        self.tbl_mapping.setRowCount(len(self.std_fields))
        
        # Danh sách tất cả các trường trong layer hiện tại để làm combobox
        field_list = [""] + [f.name() for f in layer.fields()]
        
        for idx, (std_key, std_label) in enumerate(self.std_fields.items()):
            # Cột 1: Nhãn cột Excel
            item_lbl = QTableWidgetItem(std_label)
            item_lbl.setFlags(ItemIsEnabled | ItemIsSelectable)
            self.tbl_mapping.setItem(idx, 0, item_lbl)
            
            # Cột 2: Combobox chọn trường QGIS
            cmb_field = QComboBox(self.tbl_mapping)
            cmb_field.addItems(field_list)
            
            # Chọn giá trị tự động phát hiện được
            detected = self.current_mapping.get(std_key, "")
            if detected in field_list:
                cmb_field.setCurrentText(detected)
                
            self.tbl_mapping.setCellWidget(idx, 1, cmb_field)

    def _get_current_mapping_from_ui(self):
        """Lấy thông tin ánh xạ được chọn trên giao diện bảng."""
        mapping = {}
        for idx, (std_key, _) in enumerate(self.std_fields.items()):
            cmb = self.tbl_mapping.cellWidget(idx, 1)
            if cmb:
                mapping[std_key] = cmb.currentText()
        return mapping

    def _on_export_report(self):
        """Trích xuất dữ liệu từ lớp QGIS và ghi vào mẫu biểu Excel."""
        if not self._deps_ready():
            QMessageBox.warning(self, tr("common.warning"), tx("missing.deps"))
            return
        layer = self.cmb_poly_layer.currentLayer()
        if not layer:
            QMessageBox.warning(self, tr("common.warning"), tx("warn.need_layer"))
            return
            
        mapping = self._get_current_mapping_from_ui()
        if not mapping.get("sothua") or not mapping.get("dientich"):
            QMessageBox.warning(self, tr("common.warning"), tx("warn.need_required_fields"))
            return
            
        report_type = self.cmb_report_type.currentData()
        
        # Tìm đường dẫn template tương ứng
        plugin_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        template_name = "mau_01dk_so_dia_chinh.xlsx"
        if report_type == "so_cap_gcn":
            template_name = "mau_02dk_so_cap_gcn.xlsx"
        elif report_type == "so_muc_ke":
            template_name = "so_muc_ke.xlsx"
            
        template_path = os.path.join(plugin_dir, "modules", "report_generator", "templates", template_name)
        if not os.path.exists(template_path):
            QMessageBox.critical(self, tr("common.error"), tx("error.no_template", path=template_path))
            return
            
        # Chọn đường dẫn lưu báo cáo đầu ra
        save_path, _ = QFileDialog.getSaveFileName(
            self, tx("dialog.save"), "", "Excel Workbook (*.xlsx)"
        )
        if not save_path:
            return
            
        # Đọc dữ liệu từ layer QGIS
        data_rows = []
        for feat in layer.getFeatures():
            # Đọc các thuộc tính theo ánh xạ trường
            data = {}
            for std_key, layer_field in mapping.items():
                if layer_field:
                    val = feat[layer_field]
                    # Format giá trị NULL
                    if val == NULL or val is None:
                        val = ""
                    data[std_key] = val
                else:
                    data[std_key] = ""
                    
            # Ép kiểu an toàn cho Diện tích từ thuộc tính làm fallback
            try:
                fallback_area = float(str(data.get("dientich", 0)).replace(",", "."))
            except Exception:  # noqa: BLE001 — intentional suppress
                fallback_area = 0.0
                
            # Tính diện tích từ geometry thực tế (OVERRIDE giá trị attribute)
            geom = feat.geometry()
            if geom and not geom.isNull():
                data["dientich"] = round(geom.area(), 1)
            else:
                data["dientich"] = fallback_area
                
            data_rows.append(data)
            
        if not data_rows:
            QMessageBox.warning(self, tr("common.warning"), tx("warn.empty_layer"))
            return
            
        # Sắp xếp danh sách thửa đất theo Số tờ bản đồ -> Số thửa tăng dần (chuẩn nghiệp vụ địa chính)
        try:
            data_rows.sort(key=lambda x: (
                int(str(x.get("soto", 0)).strip() or 0),
                int(str(x.get("sothua", 0)).strip() or 0)
            ))
        except Exception:  # noqa: BLE001 — intentional suppress
            pass
            
        # Thông tin hành chính
        extra_info = {
            "xa": self.txt_xa.text().strip(),
            "huyen": self.txt_huyen.text().strip(),
            "tinh": self.txt_tinh.text().strip(),
            "nguoi_lap": self.txt_nguoi_lap.text().strip()
        }
        
        from ...report_generator.excel_writer import write_cadastral_report

        # Ghi file báo cáo địa chính
        success = write_cadastral_report(template_path, save_path, data_rows, report_type, extra_info)
        
        if success:
            QMessageBox.information(
                self, tr("common.success"),
                tx("success.export", path=save_path)
            )
            # Tự động mở file Excel vừa tạo trên Windows
            try:
                os.startfile(save_path)
            except Exception:  # noqa: BLE001 — intentional suppress
                pass
        else:
            QMessageBox.critical(self, tr("common.error"), tx("error.write"))

    def reset(self):
        """Đặt lại các trường nhập liệu."""
        self.txt_xa.clear()
        self.txt_huyen.clear()
        self.txt_tinh.clear()
        self.txt_nguoi_lap.clear()
        self.cmb_report_type.setCurrentIndex(0)
        self._on_layer_changed()

# Khai báo NULL tương thích với QGIS
try:
    from qgis.core import NULL
except ImportError:
    NULL = None
