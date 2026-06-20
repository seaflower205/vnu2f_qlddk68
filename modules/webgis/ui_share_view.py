# -*- coding: utf-8 -*-
"""Zinc view builder shared by the WebGIS sharing dialog."""

import os
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget
from modules.common.ui_utils import create_themed_button, is_dark_mode
from ..common.scroll_utils import make_scroll_area

class WebGISShareViewMixin:
    def _custom_stylesheet(self) -> str:
        dark = is_dark_mode()
        title_color = "#fafafa" if dark else "#09090b"
        desc_color = "#a1a1aa" if dark else "#71717a"

        return f"""
        QLabel#dialogTitle {{
            color: {title_color};
            font-size: 14px;
            font-weight: 700;
        }}
        QLabel#dialogDesc {{
            color: {desc_color};
            font-size: 12px;
        }}
        QPushButton {{
            min-height: 38px;
        }}
        QLineEdit {{
            min-height: 38px;
        }}
        """

    def _update_btn_theme(self, btn, theme):
        btn.setProperty("theme", theme)
        btn.setObjectName(f"btn_{theme}" if theme else "")
        btn.style().unpolish(btn)
        btn.style().polish(btn)

    def _reset_copy_btn(self, btn):
        btn.setText("Sao chép")
        plugin_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        copy_icon_path = os.path.join(plugin_root, "icon_copy.svg")
        if os.path.exists(copy_icon_path):
            btn.setIcon(QIcon(copy_icon_path))

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        lbl_title = QLabel("CHIA SẺ BẢN ĐỒ WEBGIS LÊN INTERNET", self)
        lbl_title.setObjectName("dialogTitle")
        layout.addWidget(lbl_title)

        lbl_desc = QLabel(
            "Chọn phương thức để chia sẻ WebGIS quản lý thửa đất hiện tại ra ngoài Internet:",
            self
        )
        lbl_desc.setObjectName("dialogDesc")
        lbl_desc.setWordWrap(True)
        layout.addWidget(lbl_desc)

        # Wrap groupboxes in a scroll area to prevent squeezing and cut-offs on small screens
        scroll, container, container_layout = make_scroll_area(
            self,
            spacing=16,
            margins=(0, 0, 8, 0),
            stylesheet="QScrollArea { background-color: transparent; border: none; } QScrollArea > QWidget > QWidget { background-color: transparent; }"
        )

        # Passcode display widget (common for dynamic sharing options)
        plugin_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        copy_icon_path = os.path.join(plugin_root, "icon_copy.svg")

        self.widget_passcode = QWidget(container)
        passcode_layout = QHBoxLayout(self.widget_passcode)
        passcode_layout.setContentsMargins(0, 0, 0, 0)
        passcode_layout.setSpacing(8)

        lbl_passcode_title = QLabel("Khóa bảo mật WebGIS (Passcode):", self.widget_passcode)
        lbl_passcode_title.setFixedWidth(180)
        passcode_layout.addWidget(lbl_passcode_title)

        self.txt_passcode = QLineEdit(self.widget_passcode)
        self.txt_passcode.setReadOnly(True)
        passcode_str = getattr(self.launcher, "passcode", "")
        self.txt_passcode.setText(passcode_str)
        self.txt_passcode.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.txt_passcode.setStyleSheet("font-weight: bold; font-size: 13px; letter-spacing: 0.1em;")
        passcode_layout.addWidget(self.txt_passcode)

        self.btn_copy_passcode = QPushButton("Sao chép khóa", self.widget_passcode)
        self.btn_copy_passcode.setFixedWidth(120)
        self.btn_copy_passcode.clicked.connect(self._on_copy_passcode_click)

        if os.path.exists(copy_icon_path):
            self.btn_copy_passcode.setIcon(QIcon(copy_icon_path))

        passcode_layout.addWidget(self.btn_copy_passcode)
        container_layout.addWidget(self.widget_passcode)

        # 1. Quick Share (Serveo)
        self.grp_quick = QGroupBox("1. Chia sẻ nhanh qua Internet (Tạm thời)", container)
        quick_layout = QVBoxLayout(self.grp_quick)
        quick_layout.setContentsMargins(12, 16, 12, 12)
        quick_layout.setSpacing(8)

        self.btn_quick = create_themed_button("Kích hoạt chia sẻ nhanh", theme="primary", parent=self.grp_quick)
        self.btn_quick.clicked.connect(self._on_quick_click)
        quick_layout.addWidget(self.btn_quick)

        self.lbl_quick_status = QLabel("Trạng thái: Chưa chia sẻ", self.grp_quick)
        self.lbl_quick_status.setWordWrap(True)
        quick_layout.addWidget(self.lbl_quick_status)

        self.widget_quick_url = QWidget(self.grp_quick)
        quick_url_layout = QHBoxLayout(self.widget_quick_url)
        quick_url_layout.setContentsMargins(0, 0, 0, 0)
        quick_url_layout.setSpacing(8)

        self.txt_quick_url = QLineEdit(self.widget_quick_url)
        self.txt_quick_url.setReadOnly(True)
        self.txt_quick_url.setPlaceholderText("Đường dẫn chia sẻ sẽ hiển thị ở đây...")
        quick_url_layout.addWidget(self.txt_quick_url)

        self.btn_copy_quick = QPushButton("Sao chép", self.widget_quick_url)
        self.btn_copy_quick.setFixedWidth(100)
        self.btn_copy_quick.clicked.connect(self._on_copy_quick_click)

        if os.path.exists(copy_icon_path):
            self.btn_copy_quick.setIcon(QIcon(copy_icon_path))

        quick_url_layout.addWidget(self.btn_copy_quick)
        quick_layout.addWidget(self.widget_quick_url)
        self.widget_quick_url.hide()

        self.lbl_quick_extra = QLabel(self.grp_quick)
        self.lbl_quick_extra.setWordWrap(True)
        self.lbl_quick_extra.setOpenExternalLinks(True)
        quick_layout.addWidget(self.lbl_quick_extra)
        self.lbl_quick_extra.hide()

        container_layout.addWidget(self.grp_quick)

        # 2. GitHub Pages
        self.grp_perm = QGroupBox("2. Đăng vĩnh viễn lên GitHub Pages (Miễn phí & Ổn định)", container)
        perm_layout = QVBoxLayout(self.grp_perm)
        perm_layout.setContentsMargins(12, 16, 12, 12)
        perm_layout.setSpacing(8)

        form = QFormLayout()
        form.setSpacing(8)
        self.txt_username = QLineEdit(self.grp_perm)
        self.txt_username.setText(self.settings.value("vnu2f/github_user", ""))
        self.txt_username.setPlaceholderText("Ví dụ: hungbui-gis")
        form.addRow("GitHub Username:", self.txt_username)

        self.txt_token = QLineEdit(self.grp_perm)
        self.txt_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_token.setText(self.settings.value("vnu2f/github_token", ""))
        self.txt_token.setPlaceholderText("GitHub Personal Access Token (PAT)")
        form.addRow("GitHub Token (PAT):", self.txt_token)
        perm_layout.addLayout(form)

        self.btn_perm = create_themed_button("Tải lên GitHub Pages", theme="success", parent=self.grp_perm)
        self.btn_perm.clicked.connect(self._on_perm_click)
        perm_layout.addWidget(self.btn_perm)

        self.lbl_perm_status = QLabel("Trạng thái: Chưa đăng", self.grp_perm)
        self.lbl_perm_status.setWordWrap(True)
        perm_layout.addWidget(self.lbl_perm_status)

        self.widget_perm_url = QWidget(self.grp_perm)
        perm_url_layout = QHBoxLayout(self.widget_perm_url)
        perm_url_layout.setContentsMargins(0, 0, 0, 0)
        perm_url_layout.setSpacing(8)

        self.txt_perm_url = QLineEdit(self.widget_perm_url)
        self.txt_perm_url.setReadOnly(True)
        self.txt_perm_url.setPlaceholderText("Đường dẫn trang GitHub Pages sẽ hiển thị ở đây...")
        perm_url_layout.addWidget(self.txt_perm_url)

        self.btn_copy_perm = QPushButton("Sao chép", self.widget_perm_url)
        self.btn_copy_perm.setFixedWidth(100)
        self.btn_copy_perm.clicked.connect(self._on_copy_perm_click)

        if os.path.exists(copy_icon_path):
            self.btn_copy_perm.setIcon(QIcon(copy_icon_path))

        perm_url_layout.addWidget(self.btn_copy_perm)
        perm_layout.addWidget(self.widget_perm_url)
        self.widget_perm_url.hide()

        self.lbl_perm_extra = QLabel(self.grp_perm)
        self.lbl_perm_extra.setWordWrap(True)
        self.lbl_perm_extra.setOpenExternalLinks(True)
        perm_layout.addWidget(self.lbl_perm_extra)
        self.lbl_perm_extra.hide()

        container_layout.addWidget(self.grp_perm)

        # 3. DuckDNS
        self.grp_duck = QGroupBox("3. Liên kết tên miền DuckDNS miễn phí (Cập nhật IP động)", container)
        duck_layout = QVBoxLayout(self.grp_duck)
        duck_layout.setContentsMargins(12, 16, 12, 12)
        duck_layout.setSpacing(8)

        duck_form = QFormLayout()
        duck_form.setSpacing(8)
        self.txt_duck_domain = QLineEdit(self.grp_duck)
        self.txt_duck_domain.setText(self.settings.value("vnu2f/duckdns_domain", ""))
        self.txt_duck_domain.setPlaceholderText("Ví dụ: bandodat-vnu2f")
        duck_form.addRow("DuckDNS Subdomain:", self.txt_duck_domain)

        self.txt_duck_token = QLineEdit(self.grp_duck)
        self.txt_duck_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_duck_token.setText(self.settings.value("vnu2f/duckdns_token", ""))
        self.txt_duck_token.setPlaceholderText("Nhập DuckDNS Token...")
        duck_form.addRow("DuckDNS Token:", self.txt_duck_token)
        duck_layout.addLayout(duck_form)

        self.btn_duck = create_themed_button("Cập nhật IP & Kích hoạt tên miền", theme="primary", parent=self.grp_duck)
        self.btn_duck.clicked.connect(self._on_duckdns_click)
        duck_layout.addWidget(self.btn_duck)

        self.lbl_duck_status = QLabel("Trạng thái: Chưa cập nhật", self.grp_duck)
        self.lbl_duck_status.setWordWrap(True)
        duck_layout.addWidget(self.lbl_duck_status)

        self.widget_duck_url = QWidget(self.grp_duck)
        duck_url_layout = QHBoxLayout(self.widget_duck_url)
        duck_url_layout.setContentsMargins(0, 0, 0, 0)
        duck_url_layout.setSpacing(8)

        self.txt_duck_url = QLineEdit(self.widget_duck_url)
        self.txt_duck_url.setReadOnly(True)
        self.txt_duck_url.setPlaceholderText("Đường dẫn tên miền DuckDNS...")
        duck_url_layout.addWidget(self.txt_duck_url)

        self.btn_copy_duck = QPushButton("Sao chép", self.widget_duck_url)
        self.btn_copy_duck.setFixedWidth(100)
        self.btn_copy_duck.clicked.connect(self._on_copy_duck_click)

        if os.path.exists(copy_icon_path):
            self.btn_copy_duck.setIcon(QIcon(copy_icon_path))
        duck_url_layout.addWidget(self.btn_copy_duck)
        duck_layout.addWidget(self.widget_duck_url)
        self.widget_duck_url.hide()

        container_layout.addWidget(self.grp_duck)

        layout.addWidget(scroll)

        # Bottom Buttons
        bottom_layout = QHBoxLayout()
        self.btn_history = QPushButton("Lịch sử chia sẻ", self)
        history_icon_path = os.path.join(plugin_root, "icon_history.svg")
        if os.path.exists(history_icon_path):
            self.btn_history.setIcon(QIcon(history_icon_path))
        self.btn_history.clicked.connect(self._on_history_click)
        bottom_layout.addWidget(self.btn_history)

        bottom_layout.addStretch()

        btn_close = create_themed_button("Đóng", theme=None, parent=self)
        btn_close.clicked.connect(self.close)
        bottom_layout.addWidget(btn_close)

        layout.addLayout(bottom_layout)
