# -*- coding: utf-8 -*-
"""Launch the bundled parcel WebGIS demo from inside QGIS."""

from __future__ import annotations
import os
import shutil
import subprocess
import time
import json
from qgis.PyQt.QtGui import QGuiApplication
from qgis.PyQt.QtCore import QObject, pyqtSignal, QThread
from qgis.core import Qgis, QgsMessageLog

from .webgis.exporter import export_layer_to_geojson, _get_geojson_data
from .webgis.tunnel import start_internet_tunnel, update_duckdns, deploy_to_github
from .webgis.ui_share_dialog import WebGISShareDialog
from .webgis_browser_mixin import WebGISBrowserMixin

class WebGISServerThread(QThread):
    started_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, launcher, parent=None):
        super().__init__(parent)
        self.launcher = launcher
        self.server = None

    def run(self):
        import functools
        from .webgis.server import _QuietHandler, generate_passcode, ThreadingHTTPServer, _active_servers
        
        launcher = self.launcher
        _QuietHandler.launcher = launcher
        
        if not getattr(launcher, "passcode", None):
            launcher.passcode = generate_passcode()
            
        handler = functools.partial(_QuietHandler, directory=launcher.webgis_dir)
        last_error = None
        for port in range(8765, 8796):
            try:
                server = ThreadingHTTPServer(("0.0.0.0", port), handler)
                server.daemon_threads = True
                self.server = server
                launcher._server = server
                
                url = f"http://127.0.0.1:{port}/?key={launcher.passcode}"
                launcher._url = url
                _active_servers.append(server)
                
                self.started_signal.emit(url)
                
                server.serve_forever()
                return
            except OSError as exc:
                last_error = exc

        self.error_signal.emit(f"Không khởi động được WebGIS server nội bộ: {last_error}")

class WebGISShareSignals(QObject):
    tunnel_finished = pyqtSignal(bool, str, str, object)
    deploy_finished = pyqtSignal(bool, str, str)
    duckdns_finished = pyqtSignal(bool, str)

class WebGISLauncher(WebGISBrowserMixin):
    """Serve the local WebGIS folder and open it in the user's browser."""

    def __init__(self, plugin_dir, iface, plugin_name):
        self.plugin_dir = plugin_dir
        self.iface = iface
        self.plugin_name = plugin_name
        self.webgis_dir = os.path.join(plugin_dir, "webgis_demo")
        self.land_type_colors = self._load_land_type_colors()
        self._server = None
        self._thread = None
        self._url = None
        self.signals = WebGISShareSignals()

    def _get_local_ip(self):
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:  # noqa: BLE001 — intentional suppress
            return "127.0.0.1"

    def open(self, layer=None):
        if not os.path.exists(os.path.join(self.webgis_dir, "index.html")):
            self._push_error("Không tìm thấy thư mục WebGIS demo trong plugin.")
            return
            
        self.active_layer = layer
        if not self.active_layer and self.iface:
            self.active_layer = self.iface.activeLayer()

        if not self._export_layer_to_geojson(self.active_layer):
            return

        self._ensure_server_and_open()

    def _ensure_server_and_open(self):
        if self._url and self._thread and self._thread.isRunning():
            self._on_server_started(self._url)
            return

        self.stop()

        self._thread = WebGISServerThread(self)
        self._thread.started_signal.connect(self._on_server_started)
        self._thread.error_signal.connect(self._push_error)
        self._thread.start()

    def _on_server_started(self, url):
        ts = int(time.time())
        separator = "&" if "?" in url else "?"
        open_url = f"{url}{separator}ts={ts}"
        
        local_ip = self._get_local_ip()
        port = url.split(":")[-1].split("?")[0].replace("/", "")
        lan_url = f"http://{local_ip}:{port}/?key={self.passcode}&ts={ts}"
        
        self._copy_url_to_clipboard(lan_url)
        opened = self._open_in_browser(open_url)
        if self.iface:
            if opened:
                self.iface.messageBar().pushSuccess(
                    self.plugin_name, 
                    f"Đã mở WebGIS (Local: {open_url}). Đã tự động copy URL chia sẻ mạng LAN: {lan_url}"
                )
            else:
                self.iface.messageBar().pushMessage(
                    self.plugin_name,
                    f"Không tìm thấy trình duyệt để mở tự động. Link LAN đã copy: {lan_url} | Link Local: {open_url}",
                    level=Qgis.Warning,
                    duration=10,
                )

    def stop(self):
        if not self._server:
            return
        try:
            from .webgis.server import stop_server
            stop_server(self._server)
        except Exception:  # noqa: BLE001 — intentional suppress
            pass
        self._server = None
        if self._thread:
            try:
                self._thread.quit()
                self._thread.wait(1000)
            except Exception:  # noqa: BLE001 — intentional suppress
                pass
        self._thread = None
        self._url = None
        
        if hasattr(self, "_tunnel_process") and self._tunnel_process:
            try:
                self._tunnel_process.terminate()
            except Exception:  # noqa: BLE001 — intentional suppress
                pass
            self._tunnel_process = None

    def _ensure_server_sync(self):
        if self._url and self._thread and self._thread.isRunning():
            return self._url
        self.stop()
        self._thread = WebGISServerThread(self)
        self._thread.start()
        start_time = time.time()
        while time.time() - start_time < 3.0:
            if self._url:
                break
            QGuiApplication.processEvents()
            time.sleep(0.05)
        return self._url

    def show_share_dialog(self):
        self._ensure_server_sync()
        if not hasattr(self, "_share_dialog") or not self._share_dialog:
            self._share_dialog = WebGISShareDialog(self)
        self._share_dialog.show()
        self._share_dialog.raise_()
        self._share_dialog.activateWindow()

    def start_internet_tunnel(self):
        start_internet_tunnel(self)

    def update_duckdns(self, domain, token):
        update_duckdns(self, domain, token)

    def deploy_to_github(self, username, token):
        deploy_to_github(self, username, token)


    def _copy_url_to_clipboard(self, url):
        try:
            QGuiApplication.clipboard().setText(url)
        except Exception:  # noqa: BLE001 — intentional suppress
            pass


    def _export_layer_to_geojson(self, layer):
        crs = layer.crs()
        if crs.authid().startswith("USER:"):
            from qgis.PyQt.QtWidgets import QMessageBox
            reply = QMessageBox.warning(
                None,
                "Cảnh báo CRS",
                f"Lớp '{layer.name()}' đang dùng CRS nội bộ ({crs.authid()}).\n"
                "File GeoJSON xuất ra có thể không đọc được bởi ArcGIS hoặc phần mềm khác.\n\n"
                "Tiếp tục xuất?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return False
        return export_layer_to_geojson(self, layer)

    def _get_geojson_data(self, layer, bbox=None):
        return _get_geojson_data(self, layer, bbox)


    def _clamp_color(self, value):
        try:
            return max(0, min(255, int(value)))
        except (TypeError, ValueError):
            return 0

    def _push_warning(self, message):
        QgsMessageLog.logMessage(message, self.plugin_name, Qgis.Warning)
        if self.iface:
            self.iface.messageBar().pushMessage(
                self.plugin_name,
                message,
                level=Qgis.Warning,
                duration=8,
            )

    def _push_error(self, message):
        QgsMessageLog.logMessage(message, self.plugin_name, Qgis.Critical)
        if self.iface:
            self.iface.messageBar().pushMessage(
                self.plugin_name,
                message,
                level=Qgis.Critical,
                duration=8,
            )
