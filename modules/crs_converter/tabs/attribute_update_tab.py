# -*- coding: utf-8 -*-
"""Tab Cập nhật Thuộc tính (MDSD2003 -> HTSDD2026) theo độ ưu tiên loại đất."""

import re
import traceback

from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGroupBox, QGridLayout, 
    QMessageBox, QProgressBar, QTextEdit, QDialog, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QDialogButtonBox
)
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsField
from qgis.gui import QgsMapLayerComboBox

# Hỗ trợ compatibility cho PyQt
from qgis.PyQt.QtWidgets import QApplication

class QVariantShim(object):
    try:
        from qgis.PyQt.QtCore import QMetaType
        String = QMetaType.Type.QString
        Int = QMetaType.Type.Int
        Double = QMetaType.Type.Double
    except (ImportError, AttributeError):
        from qgis.PyQt.QtCore import QVariant as QVar
        String = QVar.String
        Int = QVar.Int
        Double = QVar.Double

QVariant = QVariantShim()

from modules.common.ui_utils import create_themed_button
from .attribute_update_run_mixin import AttributeUpdateRunMixin

class MixedLandUseResolverDialog(QDialog):
    def __init__(self, mixed_codes, priorities, parent=None):
        super().__init__(parent)
        self.mixed_codes = mixed_codes
        self.priorities = priorities
        self.user_mappings = {}
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("Xử lý Đất hỗn hợp (Không chứa Đất ở)")
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        
        lbl_info = QLabel("Phát hiện các mã đất hỗn hợp không chứa đất ở (ONT, ODT).\\n"
                          "Vui lòng chọn mã bạn muốn gán, hoặc giữ nguyên toàn bộ chuỗi.")
        lbl_info.setWordWrap(True)
        layout.addWidget(lbl_info)
        
        self.table = QTableWidget(len(self.mixed_codes), 2)
        self.table.setHorizontalHeaderLabels(["Mã gốc (MDSD2003)", "Mã sẽ gán (HTSDD2026)"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        
        self.combos = []
        for i, raw_code in enumerate(self.mixed_codes):
            item_raw = QTableWidgetItem(raw_code)
            item_raw.setFlags(item_raw.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 0, item_raw)
            
            cmb = QComboBox()
            options = [raw_code]
            parts = re.split(r'\+|-|,|/|\s+', str(raw_code).strip())
            codes = []
            for p in parts:
                clean_p = p.strip().upper()
                if len(clean_p) >= 3:
                    codes.append(clean_p[:3])
                elif len(clean_p) > 0:
                    codes.append(clean_p)
                    
            codes.sort(key=lambda x: self.priorities.get(x, 99))
            for c in codes:
                if c not in options:
                    options.append(c)
                    
            cmb.addItems(options)
            self.table.setCellWidget(i, 1, cmb)
            self.combos.append((raw_code, cmb))
            
        layout.addWidget(self.table)
        
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def accept(self):
        for raw_code, cmb in self.combos:
            self.user_mappings[raw_code] = cmb.currentText()
        super().accept()


class AttributeUpdateTab(AttributeUpdateRunMixin, QWidget):
    resolver_dialog_class = MixedLandUseResolverDialog

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # 1. Header
        lbl_title = QLabel("Cập nhật Loại đất (HTSDD2026)")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        lbl_desc = QLabel("Trích xuất và chuẩn hóa mã loại đất từ trường MDSD2003 sang HTSDD2026.\n"
                          "Tự động ưu tiên nhóm đất ở (ONT, ODT) khi có đất hỗn hợp (VD: CLN+ONT -> ONT).")
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #71717a;")
        
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_desc)

        # 2. Controls
        group = QGroupBox("Cấu hình lớp dữ liệu")
        g_layout = QGridLayout(group)
        g_layout.setContentsMargins(16, 22, 16, 16)
        g_layout.setVerticalSpacing(12)
        
        g_layout.addWidget(QLabel("Chọn lớp ranh thửa (Polygon):"), 0, 0)
        self.cmb_layer = QgsMapLayerComboBox(self)
        
        # Sửa lỗi bộ lọc QgsMapLayerComboBox (cần QgsMapLayerProxyModel)
        from qgis.core import QgsMapLayerProxyModel
        self.cmb_layer.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        
        self.cmb_layer.setMinimumHeight(38)
        g_layout.addWidget(self.cmb_layer, 0, 1)

        layout.addWidget(group)

        # 3. Action button
        self.btn_run = create_themed_button("CẬP NHẬT DỮ LIỆU", theme="success")
        self.btn_run.setMinimumHeight(45)
        self.btn_run.clicked.connect(self._on_run_clicked)
        layout.addWidget(self.btn_run)
        
        # 4. Progress
        self.progress = QProgressBar(self)
        self.progress.hide()
        layout.addWidget(self.progress)
        
        # 5. Log output
        self.txt_log = QTextEdit(self)
        self.txt_log.setReadOnly(True)
        self.txt_log.setPlaceholderText("Nhật ký xử lý...")
        layout.addWidget(self.txt_log)
        
        layout.addStretch()

    def _log(self, msg):
        self.txt_log.append(msg)
        

    def _get_prioritized_land_code(self, raw_code: str) -> str:
        """Trích xuất và trả về 3 ký tự đầu của mã loại đất có độ ưu tiên cao nhất."""
        if not raw_code:
            return ""
        
        # Mức độ ưu tiên của các loại đất theo thông tư (số nhỏ = ưu tiên cao)
        priorities = {
            'ODT': 1, 'ONT': 1,
            'TMD': 2, 'SKC': 2, 'CQC': 2, 'DTS': 2, 'DVH': 2, 'DYT': 2, 'DGD': 2, 'TTN': 2, 'CQP': 2, 'SKK': 2, 'SKX': 2, 'PNK': 2,
            'LUC': 3, 'LUK': 3, 'BHK': 3, 'NHK': 3,
            'CLN': 4, 'RSX': 4, 'RPH': 4, 'RDD': 4,
            'NTS': 5, 'LMQ': 5,
        }
        
        # Tách các mã đất nếu có dấu +, -, khoảng trắng, dấu phẩy...
        parts = re.split(r'\+|-|,|/|\s+', str(raw_code).strip())
        
        codes = []
        for p in parts:
            clean_p = p.strip().upper()
            if len(clean_p) >= 3:
                # Lấy 3 ký tự đầu
                codes.append(clean_p[:3])
            elif len(clean_p) > 0:
                codes.append(clean_p)
                
        if not codes:
            return ""
            
        # Sắp xếp dựa trên dictionary ưu tiên. Mặc định mã không có trong list thì gán độ ưu tiên 99
        codes.sort(key=lambda x: priorities.get(x, 99))
        
        # Trả về 3 ký tự đầu tiên của mã được ưu tiên nhất
        return codes[0][:3]

    def reset(self):
        self.txt_log.clear()
        self.progress.hide()
        self.progress.setValue(0)
