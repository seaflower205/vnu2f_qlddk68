"""Mechanically extracted responsibilities from health_tab.py."""

import os
import threading
from qgis.PyQt.QtCore import Qt, QTimer, QThread, pyqtSignal
from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QTextEdit
)
from ...common.dep_installer import (
    read_requirements, get_package_info, is_online, install_package,
    get_install_logs, log_message
)
from modules.common.ui_utils import is_dark_mode, create_themed_button, create_centered_panel, create_form_group
from .tab_text import tab_text
from ...common.qt_compat import NoEditTriggers, HeaderStretch, HeaderResizeToContents, SelectRows, SingleSelection


def tx(key, **kwargs):
    return tab_text("health", key, **kwargs)


class HealthTabUiMixin:
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 18, 10, 18)
        layout.setSpacing(16)

        panel, panel_layout = create_centered_panel(self, layout, panel_spacing=18)

        # 1. Thông tin chung & Kết nối mạng
        self.grp_info, grp_info_layout = create_form_group(
            "1. Thông tin hệ thống", self, minimum_height=110
        )
        
        h_info = QHBoxLayout()
        self.lbl_manifest = QLabel(self.grp_info)
        self.lbl_network = QLabel(self.grp_info)
        
        h_info.addWidget(self.lbl_manifest)
        h_info.addSpacing(30)
        h_info.addWidget(self.lbl_network)
        h_info.addStretch()
        
        grp_info_layout.addLayout(h_info)
        panel_layout.addWidget(self.grp_info)

        # 2. Bảng thư viện phụ thuộc
        self.grp_deps, grp_deps_layout = create_form_group(
            "2. Trạng thái các thư viện phụ thuộc (requirements-qgis.txt)", self, minimum_height=200
        )
        
        self.table = QTableWidget(self.grp_deps)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            tx("col.name"),
            tx("col.required"),
            tx("col.status"),
            tx("col.version"),
            tx("col.path")
        ])
        
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(NoEditTriggers)
        self.table.setSelectionBehavior(SelectRows)
        self.table.setSelectionMode(SingleSelection)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setDefaultSectionSize(32)
        
        # Apply style sheet based on Light/Dark Mode
        dark = is_dark_mode()
        bg = "#18181b" if dark else "#ffffff"
        fg = "#fafafa" if dark else "#09090b"
        border = "#27272a" if dark else "#e4e4e7"
        hdr_bg = "#27272a" if dark else "#f4f4f5"
        hdr_fg = "#fafafa" if dark else "#18181b"
        
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {border};
                gridline-color: transparent;
            }}
            QTableWidget::item {{
                border-bottom: 1px solid {border};
                padding-left: 8px;
            }}
            QHeaderView::section {{
                background-color: {hdr_bg};
                color: {hdr_fg};
                border: none;
                padding-left: 8px;
                font-weight: bold;
                height: 32px;
            }}
        """)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, HeaderResizeToContents)
        header.setSectionResizeMode(1, HeaderResizeToContents)
        header.setSectionResizeMode(2, HeaderResizeToContents)
        header.setSectionResizeMode(3, HeaderResizeToContents)
        header.setSectionResizeMode(4, HeaderStretch)
        
        grp_deps_layout.addWidget(self.table)
        panel_layout.addWidget(self.grp_deps)

        # 3. Log nạp & cài đặt
        self.grp_log, grp_log_layout = create_form_group(
            tx("log.title"), self, minimum_height=180
        )
        
        self.txt_log = QTextEdit(self.grp_log)
        self.txt_log.setReadOnly(True)
        self.txt_log.setStyleSheet(f"""
            QTextEdit {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {border};
                font-family: 'Courier New', monospace;
                font-size: 11px;
            }}
        """)
        grp_log_layout.addWidget(self.txt_log)
        panel_layout.addWidget(self.grp_log)

        # 4. Action buttons
        h_buttons = QHBoxLayout()
        self.btn_check = create_themed_button(tx("btn.check"), theme="standard", parent=self)
        self.btn_check.clicked.connect(self._refresh_status)
        
        self.btn_install = create_themed_button(tx("btn.install"), theme="primary", parent=self)
        self.btn_install.setObjectName("btn_primary")
        self.btn_install.clicked.connect(self._on_install_click)
        
        h_buttons.addWidget(self.btn_check)
        h_buttons.addStretch()
        h_buttons.addWidget(self.btn_install)
        
        layout.addLayout(h_buttons)
