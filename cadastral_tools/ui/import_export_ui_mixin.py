"""Mechanically extracted responsibilities from import_export_dialog.py."""

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


class ImportExportUiMixin:
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # Tab Widget phân biệt Nhập / Xuất
        self.tabs = QTabWidget(self)
        
        # ── TAB 1: XUẤT CẤU HÌNH ──────────────────────────────
        self.tab_export = QWidget(self)
        export_layout = QVBoxLayout(self.tab_export)
        export_layout.setSpacing(12)
        
        # 1. Chọn nội dung xuất
        self.grp_content = QGroupBox("Chọn nội dung xuất", self.tab_export)
        grp_content_layout = QVBoxLayout(self.grp_content)
        grp_content_layout.setSpacing(8)
        
        self.chk_symbology = QCheckBox("Ký hiệu màu sắc (bảng mã loại đất)", self.tab_export)
        self.chk_symbology.setChecked(True)
        self.chk_labels = QCheckBox("Cấu hình nhãn (preset + field mapping)", self.tab_export)
        self.chk_labels.setChecked(True)
        self.chk_settings = QCheckBox("Cài đặt chung (CRS, trường mặc định)", self.tab_export)
        self.chk_settings.setChecked(True)
        
        grp_content_layout.addWidget(self.chk_symbology)
        grp_content_layout.addWidget(self.chk_labels)
        grp_content_layout.addWidget(self.chk_settings)
        export_layout.addWidget(self.grp_content)
        
        # 2. Định dạng xuất ký hiệu (chỉ bật khi chỉ chọn ký hiệu)
        self.grp_format = QGroupBox("Định dạng xuất ký hiệu", self.tab_export)
        grp_format_layout = QVBoxLayout(self.grp_format)
        
        self.rad_json = QRadioButton("JSON (Dùng cho plugin cadastral_tools)", self.grp_format)
        self.rad_json.setChecked(True)
        self.rad_qml = QRadioButton("QML (File Style chuẩn QGIS, chỉ lưu symbology)", self.grp_format)
        
        self.fmt_group = QButtonGroup(self.tab_export)
        self.fmt_group.addButton(self.rad_json)
        self.fmt_group.addButton(self.rad_qml)
        
        grp_format_layout.addWidget(self.rad_json)
        grp_format_layout.addWidget(self.rad_qml)
        export_layout.addWidget(self.grp_format)
        
        # Logic thay đổi lựa chọn checkbox
        self.chk_symbology.stateChanged.connect(self._update_export_ui_state)
        self.chk_labels.stateChanged.connect(self._update_export_ui_state)
        self.chk_settings.stateChanged.connect(self._update_export_ui_state)
        self._update_export_ui_state()
        
        # Nút xuất dưới cùng
        export_action_bar = QWidget(self.tab_export)
        export_action_layout = QHBoxLayout(export_action_bar)
        export_action_layout.setContentsMargins(0, 0, 0, 0)
        
        self.btn_export = create_themed_button("Xuất cấu hình", "primary", export_action_bar)
        self.btn_export.clicked.connect(self._on_export)
        btn_close_exp = create_themed_button("Đóng", None, export_action_bar)
        btn_close_exp.clicked.connect(self.close)
        
        export_action_layout.addWidget(self.btn_export)
        export_action_layout.addStretch()
        export_action_layout.addWidget(btn_close_exp)
        export_layout.addWidget(export_action_bar)
        
        self.tabs.addTab(self.tab_export, "📤 Xuất Cấu Hình")
        
        # ── TAB 2: NHẬP CẤU HÌNH ──────────────────────────────
        self.tab_import = QWidget(self)
        import_layout = QVBoxLayout(self.tab_import)
        import_layout.setSpacing(12)
        
        # 1. Dòng chọn file nhập
        lbl_file = QLabel("Chọn file cấu hình để nhập:", self.tab_import)
        import_layout.addWidget(lbl_file)
        
        file_row, self.txt_file, btn_browse = create_file_browser_row(
            "Đường dẫn đến file .json, .qml, .cadprofile...", False, self.tab_import
        )
        btn_browse.clicked.connect(self._on_browse_import_file)
        import_layout.addLayout(file_row)
        
        # Label hiển thị kết quả nhận dạng định dạng
        self.lbl_format_status = QLabel("Trạng thái: Chưa chọn file.", self.tab_import)
        self.lbl_format_status.setStyleSheet("font-weight: bold; color: #71717a;")
        import_layout.addWidget(self.lbl_format_status)
        
        # 2. Tùy chọn gộp bảng mã (chỉ hiển thị khi nhận dạng là symbology_json)
        self.grp_merge = QGroupBox("Tùy chọn nhập ký hiệu màu sắc", self.tab_import)
        grp_merge_layout = QVBoxLayout(self.grp_merge)
        
        self.rad_merge_gop = QRadioButton("Gộp (giữ mã hiện tại, thêm mã mới)", self.grp_merge)
        self.rad_merge_gop.setChecked(True)
        self.rad_merge_replace = QRadioButton("Thay thế hoàn toàn bảng hiện tại", self.grp_merge)
        self.rad_merge_update = QRadioButton("Chỉ cập nhật màu sắc các mã đã tồn tại", self.grp_merge)
        
        self.merge_group = QButtonGroup(self.tab_import)
        self.merge_group.addButton(self.rad_merge_gop)
        self.merge_group.addButton(self.rad_merge_replace)
        self.merge_group.addButton(self.rad_merge_update)
        
        grp_merge_layout.addWidget(self.rad_merge_gop)
        grp_merge_layout.addWidget(self.rad_merge_replace)
        grp_merge_layout.addWidget(self.rad_merge_update)
        import_layout.addWidget(self.grp_merge)
        self.grp_merge.setVisible(False)
        
        # Nút nhập dưới cùng
        import_action_bar = QWidget(self.tab_import)
        import_action_layout = QHBoxLayout(import_action_bar)
        import_action_layout.setContentsMargins(0, 0, 0, 0)
        
        self.btn_import = create_themed_button("Nhập cấu hình", "success", import_action_bar)
        self.btn_import.clicked.connect(self._on_import)
        btn_close_imp = create_themed_button("Đóng", None, import_action_bar)
        btn_close_imp.clicked.connect(self.close)
        
        import_action_layout.addWidget(self.btn_import)
        import_action_layout.addStretch()
        import_action_layout.addWidget(btn_close_imp)
        import_layout.addWidget(import_action_bar)
        
        self.tabs.addTab(self.tab_import, "📥 Nhập Cấu Hình")
        
        main_layout.addWidget(self.tabs)
