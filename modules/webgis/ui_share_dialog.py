# -*- coding: utf-8 -*-
"""WebGIS sharing controller dialog with compatibility exports."""

import json
from datetime import datetime
from qgis.PyQt.QtCore import QSettings, Qt, QTimer
from qgis.PyQt.QtGui import QCursor, QGuiApplication, QIcon
from qgis.PyQt.QtWidgets import QDialog, QMessageBox
from modules.common.ui_utils import get_dialog_stylesheet, set_dialog_icon
from .tunnel_manager import TunnelManager
from .ui_share_history import SharingHistoryDialog
from .ui_share_view import WebGISShareViewMixin

class WebGISShareDialog(WebGISShareViewMixin, QDialog):
    def __init__(self, launcher, parent=None):
        super().__init__(parent or launcher.iface.mainWindow())
        self.launcher = launcher
        self.setWindowTitle("VNU2F - Chia sẻ bản đồ WebGIS")
        self.setMinimumWidth(500)
        self.setModal(True)

        self.settings = QSettings()
        self._tunnel_proc = None
        self._last_quick_url = None
        self._last_perm_url = None
        self._last_duck_url = None

        # Connect signals
        self.launcher.signals.tunnel_finished.connect(self._on_tunnel_finished)
        self.launcher.signals.deploy_finished.connect(self._on_deploy_finished)
        self.launcher.signals.duckdns_finished.connect(self._on_duckdns_finished)

        set_dialog_icon(self, "icon_share.svg")
        self._build_ui()
        self.setStyleSheet(get_dialog_stylesheet() + self._custom_stylesheet())
        self.resize(520, 620)
    def _on_copy_passcode_click(self):
        passcode = self.txt_passcode.text().strip()
        if passcode:
            self.launcher._copy_url_to_clipboard(passcode)
            self.btn_copy_passcode.setText("Đã chép!")
            QTimer.singleShot(2000, lambda: self.btn_copy_passcode.setText("Sao chép khóa"))

    def _on_quick_click(self):
        self.btn_quick.setEnabled(False)
        self.widget_quick_url.hide()
        self.lbl_quick_extra.hide()
        self._last_quick_url = None
        self.lbl_quick_status.setText("Đang khởi tạo đường truyền bảo mật (SSH tunnel)...")
        QGuiApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
        self._tunnel = TunnelManager("tunnel", self.launcher)
        self._tunnel.tunnel_finished.connect(self._on_tunnel_finished)
        self._tunnel.start()

    def _on_tunnel_finished(self, success, long_url, short_url, process):
        QGuiApplication.restoreOverrideCursor()
        if success:
            self._tunnel_proc = process
            self.launcher._tunnel_process = process
            self.btn_quick.setText("Đang chia sẻ (Nhấn để tắt)")
            self.btn_quick.setEnabled(True)
            self._update_btn_theme(self.btn_quick, "danger")

            try:
                self.btn_quick.clicked.disconnect()
            except Exception:  # noqa: BLE001 — intentional suppress
                pass
            self.btn_quick.clicked.connect(self._on_stop_quick_click)

            self._last_quick_url = short_url if short_url else long_url
            self.launcher._copy_url_to_clipboard(self._last_quick_url)

            self._save_to_history(
                "Nhanh",
                self._last_quick_url,
                f"https://is.gd/stats.php?url={short_url.split('/')[-1]}" if short_url else ""
            )

            self.txt_quick_url.setText(self._last_quick_url)
            self.widget_quick_url.show()
            self.lbl_quick_status.setText("Thành công! Link công khai đã được copy:")

            extra_html = ""
            if short_url:
                stats_url = f"https://is.gd/stats.php?url={short_url.split('/')[-1]}"
                extra_html = (
                    f"<a style='color: #2563eb; text-decoration: underline;' href='{long_url}'>Xem link gốc ↗</a><br>"
                    f"<a style='color: #16a34a; font-weight: bold; text-decoration: underline;' href='{stats_url}'>Xem thống kê lượt truy cập ↗</a>"
                )
            self.lbl_quick_extra.setText(extra_html)
            self.lbl_quick_extra.setVisible(bool(extra_html))
        else:
            self.btn_quick.setEnabled(True)
            self._update_btn_theme(self.btn_quick, "primary")
            self.widget_quick_url.hide()
            self.lbl_quick_extra.hide()
            self._last_quick_url = None
            self.lbl_quick_status.setText(f"Thất bại: {long_url}")

    def _on_stop_quick_click(self):
        if self._tunnel_proc:
            try:
                self._tunnel_proc.terminate()
            except Exception:  # noqa: BLE001 — intentional suppress
                pass
            self._tunnel_proc = None
            if self.launcher._tunnel_process:
                self.launcher._tunnel_process = None

        self.btn_quick.setText("Kích hoạt chia sẻ nhanh")
        self._update_btn_theme(self.btn_quick, "primary")
        try:
            self.btn_quick.clicked.disconnect()
        except Exception:  # noqa: BLE001 — intentional suppress
            pass
        self.btn_quick.clicked.connect(self._on_quick_click)
        self.lbl_quick_status.setText("Trạng thái: Đã dừng chia sẻ")
        self.widget_quick_url.hide()
        self.lbl_quick_extra.hide()
        self._last_quick_url = None

    def _on_copy_quick_click(self):
        if self._last_quick_url:
            self.launcher._copy_url_to_clipboard(self._last_quick_url)
            self.btn_copy_quick.setText("✓ Đã copy!")
            self.btn_copy_quick.setIcon(QIcon())
            QTimer.singleShot(1500, lambda: self._reset_copy_btn(self.btn_copy_quick))

    def _on_copy_perm_click(self):
        if self._last_perm_url:
            self.launcher._copy_url_to_clipboard(self._last_perm_url)
            self.btn_copy_perm.setText("✓ Đã copy!")
            self.btn_copy_perm.setIcon(QIcon())
            QTimer.singleShot(1500, lambda: self._reset_copy_btn(self.btn_copy_perm))

    def _on_perm_click(self):
        username = self.txt_username.text().strip()
        token = self.txt_token.text().strip()
        if not username or not token:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập cả GitHub Username và Personal Access Token (PAT)!")
            return

        self.settings.setValue("vnu2f/github_user", username)
        self.settings.setValue("vnu2f/github_token", token)

        self.btn_perm.setEnabled(False)
        self.widget_perm_url.hide()
        self.lbl_perm_extra.hide()
        self._last_perm_url = None
        self.lbl_perm_status.setText("Đang khởi tạo repo và upload file dữ liệu lên GitHub...")
        QGuiApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
        self._tunnel = TunnelManager("github", self.launcher, username=username, token=token)
        self._tunnel.deploy_finished.connect(self._on_deploy_finished)
        self._tunnel.start()

    def _on_deploy_finished(self, success, long_url, short_url=None):
        QGuiApplication.restoreOverrideCursor()
        self.btn_perm.setEnabled(True)
        if success:
            self._last_perm_url = short_url if short_url else long_url
            self.launcher._copy_url_to_clipboard(self._last_perm_url)

            self._save_to_history(
                "GitHub Pages",
                self._last_perm_url,
                f"https://is.gd/stats.php?url={short_url.split('/')[-1]}" if short_url else ""
            )

            self.txt_perm_url.setText(self._last_perm_url)
            self.widget_perm_url.show()
            self.lbl_perm_status.setText("Thành công! WebGIS đã được đăng vĩnh viễn tại:")

            extra_html = ""
            if short_url:
                stats_url = f"https://is.gd/stats.php?url={short_url.split('/')[-1]}"
                extra_html = (
                    f"<a style='color: #2563eb; text-decoration: underline;' href='{long_url}'>Xem link gốc ↗</a><br>"
                    f"<a style='color: #16a34a; font-weight: bold; text-decoration: underline;' href='{stats_url}'>Xem thống kê lượt truy cập ↗</a><br>"
                    f"<i>(Đã copy link. Có thể mất 30s-1 phút để GitHub kích hoạt Pages lần đầu)</i>"
                )
            else:
                extra_html = "<i>(Đã copy link. Có thể mất 30s-1 phút để GitHub kích hoạt Pages lần đầu)</i>"
            self.lbl_perm_extra.setText(extra_html)
            self.lbl_perm_extra.setVisible(bool(extra_html))
        else:
            self.widget_perm_url.hide()
            self.lbl_perm_extra.hide()
            self._last_perm_url = None
            self.lbl_perm_status.setText(f"Lỗi đăng bài: {long_url}")

    def _on_duckdns_click(self):
        domain = self.txt_duck_domain.text().strip()
        token = self.txt_duck_token.text().strip()
        if not domain or not token:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập cả DuckDNS Subdomain và Token!")
            return

        self.settings.setValue("vnu2f/duckdns_domain", domain)
        self.settings.setValue("vnu2f/duckdns_token", token)

        self.btn_duck.setEnabled(False)
        self.widget_duck_url.hide()
        self._last_duck_url = None
        self.lbl_duck_status.setText("Đang gửi yêu cầu cập nhật IP tới DuckDNS...")
        QGuiApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
        self._tunnel = TunnelManager("duckdns", self.launcher, domain=domain, token=token)
        self._tunnel.duckdns_finished.connect(self._on_duckdns_finished)
        self._tunnel.start()

    def _on_duckdns_finished(self, success, message):
        QGuiApplication.restoreOverrideCursor()
        self.btn_duck.setEnabled(True)
        if success:
            port = "8765"
            if self.launcher._url:
                from urllib.parse import urlparse
                try:
                    parsed_url = urlparse(self.launcher._url)
                    if parsed_url.port:
                        port = str(parsed_url.port)
                except Exception:  # noqa: BLE001 — intentional suppress
                    pass

            domain = self.txt_duck_domain.text().strip()
            self._last_duck_url = f"http://{domain}.duckdns.org:{port}/"
            self.launcher._copy_url_to_clipboard(self._last_duck_url)

            self._save_to_history("DuckDNS", self._last_duck_url)

            self.txt_duck_url.setText(self._last_duck_url)
            self.widget_duck_url.show()
            self.lbl_duck_status.setText("Thành công! Tên miền DuckDNS đã trỏ về máy bạn:")
        else:
            self.widget_duck_url.hide()
            self._last_duck_url = None
            self.lbl_duck_status.setText(f"Cập nhật thất bại: {message}")

    def _on_copy_duck_click(self):
        if self._last_duck_url:
            self.launcher._copy_url_to_clipboard(self._last_duck_url)
            self.btn_copy_duck.setText("✓ Đã copy!")
            self.btn_copy_duck.setIcon(QIcon())
            QTimer.singleShot(1500, lambda: self._reset_copy_btn(self.btn_copy_duck))

    def _save_to_history(self, type_name, url, stats_url=""):
        entry = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": type_name,
            "url": url,
            "stats": stats_url
        }

        try:
            history = json.loads(self.settings.value("vnu2f/sharing_history", "[]"))
        except Exception:  # noqa: BLE001 — intentional suppress
            history = []

        if history and history[0].get("url") == url:
            return

        history.insert(0, entry)
        history = history[:50]
        self.settings.setValue("vnu2f/sharing_history", json.dumps(history))

    def _on_history_click(self):
        self._history_dialog = SharingHistoryDialog(self)
        self._history_dialog.show()
        self._history_dialog.raise_()
        self._history_dialog.activateWindow()
