# -*- coding: utf-8 -*-
"""Zinc UI builder and discovery presenter for cadastral import."""

import os

from qgis.PyQt.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..common.qt_compat import (
    NoEditTriggers,
    SelectRows,
    SizePolicyExpanding,
    SizePolicyFixed,
    FrameStyledPanel,
)
from modules.common.ui_utils import create_themed_button
from .dialog_styles import dialog_stylesheet
from .texts import cadastral_text as tx
from .dialog_discovery_mixin import CadastralDiscoveryMixin


class CadastralImportDialogUi(CadastralDiscoveryMixin):
    def __init__(self, owner):
        self.owner = owner

    def setup_ui(self):
        from qgis.PyQt.QtWidgets import QStackedWidget
        
        layout = QVBoxLayout(self.owner)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # ZONE A - Header
        header = QFrame(self.owner)
        header.setObjectName("importHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(2)
        title = QLabel(tx("title"), header)
        title.setObjectName("dialogTitle")
        subtitle = QLabel(tx("subtitle"), header)
        subtitle.setObjectName("dialogSubtitle")
        subtitle.setWordWrap(True)
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addWidget(header)

        # ZONE B - Source selection
        source_group = QGroupBox("Chọn nguồn dữ liệu", self.owner)
        source_layout = QGridLayout(source_group)
        source_layout.setContentsMargins(16, 22, 16, 16)
        source_layout.setHorizontalSpacing(10)
        source_layout.setVerticalSpacing(10)
        source_layout.setColumnStretch(1, 1)

        self.owner.txt_path = QLineEdit(source_group)
        self.owner.txt_path.setPlaceholderText("Kéo thả bản vẽ CAD hoặc chọn tệp/thư mục chứa hồ sơ địa chính...")
        self.owner.txt_path.editingFinished.connect(self.owner._scan) # Quét an toàn khi kết thúc nhập
        source_layout.addWidget(QLabel(tx("label.path")), 0, 0)
        source_layout.addWidget(self.owner.txt_path, 0, 1)

        self.owner.btn_file = create_themed_button(tx("button.file"), parent=source_group)
        self.owner.btn_file.setObjectName("compactButton")
        self.owner.btn_file.setFixedWidth(92)
        self.owner.btn_file.clicked.connect(self.owner._choose_file)
        source_layout.addWidget(self.owner.btn_file, 0, 2)

        self.owner.btn_folder = create_themed_button(tx("button.folder"), parent=source_group)
        self.owner.btn_folder.setObjectName("compactButton")
        self.owner.btn_folder.setFixedWidth(112)
        self.owner.btn_folder.clicked.connect(self.owner._choose_folder)
        source_layout.addWidget(self.owner.btn_folder, 0, 3)
        layout.addWidget(source_group)

        # ZONE C - Discovery Summary & Results stacked card
        self.owner.zone_c = QStackedWidget(self.owner)
        self.owner.zone_c.setMinimumHeight(140)
        
        # Page 0: Discovery summary
        self.owner.page_discovery = QWidget(self.owner.zone_c)
        self.owner.layout_discovery = QVBoxLayout(self.owner.page_discovery)
        self.owner.layout_discovery.setContentsMargins(0, 0, 0, 0)
        self.owner.frame_discovery = QFrame(self.owner.page_discovery)
        self.owner.frame_discovery.setFrameShape(FrameStyledPanel)
        self.owner.frame_discovery.setStyleSheet("QFrame { background-color: rgba(0, 0, 0, 0.02); border: 1px solid rgba(0, 0, 0, 0.08); border-radius: 6px; }")
        self.owner.layout_discovery_frame = QVBoxLayout(self.owner.frame_discovery)
        self.owner.layout_discovery_frame.setContentsMargins(14, 14, 14, 14)
        self.owner.lbl_discovery = QLabel(self.owner.frame_discovery)
        self.owner.lbl_discovery.setWordWrap(True)
        self.owner.lbl_discovery.setText("<i>Chưa chọn tệp tin hoặc thư mục nguồn.</i>")
        self.owner.layout_discovery_frame.addWidget(self.owner.lbl_discovery)
        self.owner.layout_discovery.addWidget(self.owner.frame_discovery)
        self.owner.zone_c.addWidget(self.owner.page_discovery)

        # Page 1: Import Results
        self.owner.page_results = QWidget(self.owner.zone_c)
        self.owner.layout_results = QVBoxLayout(self.owner.page_results)
        self.owner.layout_results.setContentsMargins(0, 0, 0, 0)
        self.owner.tbl_import = self._make_table()
        self.owner.layout_results.addWidget(self.owner.tbl_import)
        self.owner.zone_c.addWidget(self.owner.page_results)
        
        self.owner.zone_c.hide() # Ẩn mặc định
        layout.addWidget(self.owner.zone_c)

        # ZONE D - Parameters Group
        self.owner.param_group = QGroupBox("Cấu hình hệ tọa độ & Tỷ lệ hạn sai", self.owner)
        self.owner.param_layout = QGridLayout(self.owner.param_group)
        self.owner.param_layout.setContentsMargins(16, 22, 16, 16)
        self.owner.param_layout.setHorizontalSpacing(10)
        self.owner.param_layout.setVerticalSpacing(10)
        self.owner.param_layout.setColumnStretch(1, 1)

        self.owner.cmb_group = QComboBox(self.owner.param_group)
        self.owner.cmb_group.currentIndexChanged.connect(self.owner._on_group_changed)
        self.owner.param_layout.addWidget(QLabel("Bộ file địa chính:"), 0, 0)
        self.owner.param_layout.addWidget(self.owner.cmb_group, 0, 1)

        self.owner.cmb_cad_crs = QComboBox(self.owner.param_group)
        self.owner.cmb_cad_crs.setMinimumWidth(280)
        self.owner._populate_cad_crs_combo()
        self.owner.cmb_cad_crs.currentIndexChanged.connect(self.owner._check_hn72_warning)
        self.owner.param_layout.addWidget(QLabel(tx("label.cad_crs")), 1, 0)
        self.owner.param_layout.addWidget(self.owner.cmb_cad_crs, 1, 1)

        self.owner.lbl_warning_hn72 = QLabel(self.owner.param_group)
        self.owner.lbl_warning_hn72.setWordWrap(True)
        self.owner.lbl_warning_hn72.setStyleSheet("color: #ff9800; font-weight: bold; padding: 6px; border: 1px solid #ff9800; border-radius: 4px; background-color: rgba(255, 152, 0, 0.05);")
        self.owner.lbl_warning_hn72.setText("⚠️ Cảnh báo trắc địa: HN-72 sang VN-2000 là phép chuyển đổi gần đúng địa phương (sai số ~5-10m). Đối với bản đồ địa chính tỷ lệ lớn, hãy kiểm nghiệm lại.")
        self.owner.lbl_warning_hn72.hide()
        self.owner.param_layout.addWidget(self.owner.lbl_warning_hn72, 2, 0, 1, 2)

        self.owner.cmb_map_scale = QComboBox(self.owner.param_group)
        self.owner.cmb_map_scale.addItems(["1:500", "1:1000", "1:2000", "1:5000", "1:10000"])
        self.owner.cmb_map_scale.setCurrentIndex(1)
        self.owner.param_layout.addWidget(QLabel("Tỷ lệ bản đồ:"), 3, 0)
        self.owner.param_layout.addWidget(self.owner.cmb_map_scale, 3, 1)
        layout.addWidget(self.owner.param_group)

        # ZONE E - Primary action & Progress Bar (Cách B)
        self.owner.zone_e_layout = QVBoxLayout()
        self.owner.btn_import_sync = create_themed_button("NHẬP VÀO QGIS", theme="success", parent=self.owner)
        self.owner.btn_import_sync.setObjectName("btn_success")
        self.owner.btn_import_sync.setMinimumHeight(45)
        self.owner.btn_import_sync.clicked.connect(self.owner._import_sync)
        self.owner.zone_e_layout.addWidget(self.owner.btn_import_sync)

        # Progress bar container
        self.owner.progress_container = QFrame(self.owner)
        self.owner.progress_container.setObjectName("progressContainer")
        progress_layout = QHBoxLayout(self.owner.progress_container)
        progress_layout.setContentsMargins(0, 4, 0, 4)
        progress_layout.setSpacing(10)
        self.owner.lbl_progress = QLabel(self.owner.progress_container)
        self.owner.lbl_progress.setObjectName("progressLabel")
        progress_layout.addWidget(self.owner.lbl_progress)
        self.owner.progress_bar = QProgressBar(self.owner.progress_container)
        self.owner.progress_bar.setObjectName("taskProgressBar")
        progress_layout.addWidget(self.owner.progress_bar, 1)
        self.owner.btn_cancel = create_themed_button("Hủy", parent=self.owner.progress_container)
        self.owner.btn_cancel.setObjectName("cancelButton")
        self.owner.btn_cancel.setFixedWidth(80)
        self.owner.btn_cancel.clicked.connect(self.owner._cancel_current_task)
        progress_layout.addWidget(self.owner.btn_cancel)
        self.owner.progress_container.hide()
        self.owner.zone_e_layout.addWidget(self.owner.progress_container)
        layout.addLayout(self.owner.zone_e_layout)

        # ZONE F - Accordion & Lazy-load preview tabs
        self.owner.btn_accordion = QPushButton("▶ Xem chi tiết dữ liệu thô", self.owner)
        self.owner.btn_accordion.setCheckable(True)
        self.owner.btn_accordion.setChecked(False)
        self.owner.btn_accordion.setMinimumHeight(34)
        self.owner.btn_accordion.clicked.connect(self.owner._toggle_accordion)
        layout.addWidget(self.owner.btn_accordion)

        self.owner.preview_widget = QWidget(self.owner)
        self.owner.preview_layout = QVBoxLayout(self.owner.preview_widget)
        self.owner.preview_layout.setContentsMargins(0, 0, 0, 0)
        
        self.owner.tabs = QTabWidget(self.owner.preview_widget)
        self.owner.tabs.setObjectName("previewTabs")
        self.owner.tabs.setMinimumHeight(240)
        
        self.owner.tbl_cad = self._make_table()
        self.owner.tbl_gtp = self._make_table()
        self.owner.tbl_pol = self._make_table()
        
        self.owner.tabs.addTab(self._wrap_table(self.owner.tbl_cad), "Bản vẽ CAD")
        self.owner.tabs.addTab(self._wrap_table(self.owner.tbl_gtp), "CSDL GTP")
        self.owner.tabs.addTab(self._wrap_table(self.owner.tbl_pol), "Tệp nhị phân POL")
        self.owner.preview_layout.addWidget(self.owner.tabs)
        self.owner.preview_widget.hide()
        layout.addWidget(self.owner.preview_widget)

        # Connect currentChanged signal for lazy load
        self.owner.tabs.currentChanged.connect(self.owner._on_tab_changed)

        # ZONE G - System console log
        self.owner.txt_log = QTextEdit(self.owner)
        self.owner.txt_log.setObjectName("processingLog")
        self.owner.txt_log.setReadOnly(True)
        self.owner.txt_log.setPlaceholderText(tx("log.placeholder"))
        self.owner.txt_log.setMaximumHeight(80)
        log_label = QLabel(tx("label.log"), self.owner)
        log_label.setObjectName("sectionLabel")
        layout.addWidget(log_label)
        layout.addWidget(self.owner.txt_log)

        # Close button at bottom
        bottom = QHBoxLayout()
        bottom.addStretch()
        btn_close = create_themed_button(tx("button.close"), parent=self.owner)
        btn_close.setFixedWidth(120)
        btn_close.clicked.connect(self.owner.close)
        bottom.addWidget(btn_close)
        layout.addLayout(bottom)

        # Kích hoạt drag & drop trên toàn bộ bề mặt dialog
        self.owner.setAcceptDrops(True)

        self._tune_control_sizes()

    def _tune_control_sizes(self):
        for label in self.owner.findChildren(QLabel):
            label.setWordWrap(True)
            if label.text():
                label.setToolTip(label.text())

        for widget in self.owner.findChildren((QLineEdit, QComboBox)):
            widget.setMinimumHeight(38)
            widget.setSizePolicy(SizePolicyExpanding, SizePolicyFixed)

        for button in self.owner.findChildren(QPushButton):
            if button.text():
                button.setToolTip(button.text())
            button.setMinimumHeight(38)
            button.setSizePolicy(SizePolicyFixed, SizePolicyFixed)

    def _make_table(self)-> QTableWidget:
        table = QTableWidget(self.owner)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(SelectRows)
        table.setEditTriggers(NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(32)
        table.setShowGrid(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.setMinimumHeight(220)
        return table

    def _wrap_table(self, table: QTableWidget) -> QWidget:
        wrapper = QWidget(self.owner)
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(10, 10, 10, 10)
        frame = QFrame(wrapper)
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.addWidget(table)
        layout.addWidget(frame)
        return wrapper

    def _dialog_stylesheet(self)-> str:
        return dialog_stylesheet()


