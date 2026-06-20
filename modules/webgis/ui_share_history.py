# -*- coding: utf-8 -*-
"""Sharing history dialog for WebGIS."""

import json
import os
from qgis.PyQt.QtCore import QSettings, Qt, QTimer, QUrl
from qgis.PyQt.QtGui import QDesktopServices, QGuiApplication, QIcon
from qgis.PyQt.QtWidgets import QAbstractItemView, QDialog, QHBoxLayout, QHeaderView, QLabel, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget
from modules.common.ui_utils import create_themed_button, get_dialog_stylesheet, is_dark_mode, set_dialog_icon

class SharingHistoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Lịch sử chia sẻ bản đồ WebGIS")
        self.setMinimumWidth(620)
        self.setMinimumHeight(400)
        self.setModal(True)
        self.settings = QSettings()
        set_dialog_icon(self, "icon_history.svg")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        lbl_title = QLabel("LỊCH SỬ LIÊN KẾT ĐẠI DIỆN ĐÃ CHIA SẺ", self)
        lbl_title.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(lbl_title)

        self.table = QTableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Thời gian", "Phương thức", "Đường dẫn", "Thống kê"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(32)

        self.table.setShowGrid(True)
        self.table.setStyleSheet("""
            QTableWidget {
                gridline-color: #e4e4e7;
            }
        """ if not is_dark_mode() else """
            QTableWidget {
                gridline-color: #27272a;
            }
        """)

        layout.addWidget(self.table)
        self._load_history()

        bottom_layout = QHBoxLayout()
        self.btn_clear = QPushButton("Xóa lịch sử", self)
        self.btn_clear.clicked.connect(self._on_clear_click)
        bottom_layout.addWidget(self.btn_clear)

        bottom_layout.addStretch()

        self.btn_close = create_themed_button("Đóng", theme="primary", parent=self)
        self.btn_close.clicked.connect(self.close)
        bottom_layout.addWidget(self.btn_close)

        layout.addLayout(bottom_layout)

        self.setStyleSheet(get_dialog_stylesheet() + """
            QPushButton {
                min-height: 38px;
            }
            QTableWidget QPushButton {
                min-height: 24px;
                padding: 2px 8px;
                font-size: 11px;
            }
        """)

    def _load_history(self):
        history_data = self.settings.value("vnu2f/sharing_history", "[]")
        try:
            history = json.loads(history_data)
        except Exception:  # noqa: BLE001 — intentional suppress
            history = []

        self.table.setRowCount(len(history))

        plugin_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        copy_icon_path = os.path.join(plugin_root, "icon_copy.svg")

        for row, entry in enumerate(history):
            self.table.setItem(row, 0, QTableWidgetItem(entry.get("time", "")))
            self.table.setItem(row, 1, QTableWidgetItem(entry.get("type", "")))

            url = entry.get("url", "")
            url_widget = QWidget()
            url_layout = QHBoxLayout(url_widget)
            url_layout.setContentsMargins(4, 0, 4, 0)
            url_layout.setSpacing(6)

            lbl_url = QLabel(url)
            lbl_url.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            url_layout.addWidget(lbl_url)
            url_layout.addStretch()

            btn_copy = QPushButton("Sao chép")
            if os.path.exists(copy_icon_path):
                btn_copy.setIcon(QIcon(copy_icon_path))
            btn_copy.clicked.connect(lambda checked, u=url, b=btn_copy: self._copy_url(u, b))
            url_layout.addWidget(btn_copy)

            self.table.setCellWidget(row, 2, url_widget)

            stats_url = entry.get("stats", "")
            if stats_url:
                btn_stats = QPushButton("Mở thống kê ↗")
                btn_stats.clicked.connect(lambda checked, s=stats_url: QDesktopServices.openUrl(QUrl(s)))
                self.table.setCellWidget(row, 3, btn_stats)
            else:
                self.table.setItem(row, 3, QTableWidgetItem("N/A"))

        self.table.setColumnWidth(0, 140)
        self.table.setColumnWidth(1, 95)
        self.table.setColumnWidth(2, 260)

    def _copy_url(self, url, btn):
        QApplication = QGuiApplication
        QApplication.clipboard().setText(url)
        btn.setText("✓ Đã copy!")
        btn.setIcon(QIcon())
        QTimer.singleShot(1500, lambda: self._reset_copy_btn(btn))

    def _reset_copy_btn(self, btn):
        btn.setText("Sao chép")
        plugin_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        copy_icon_path = os.path.join(plugin_root, "icon_copy.svg")
        if os.path.exists(copy_icon_path):
            btn.setIcon(QIcon(copy_icon_path))

    def _on_clear_click(self):
        reply = QMessageBox.question(
            self,
            "Xác nhận",
            "Bạn có chắc chắn muốn xóa toàn bộ lịch sử chia sẻ không?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.settings.setValue("vnu2f/sharing_history", "[]")
            self.table.setRowCount(0)

