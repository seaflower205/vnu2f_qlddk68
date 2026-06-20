"""Mechanically extracted responsibilities from webgis_launcher.py."""

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


class WebGISBrowserMixin:
    def _open_in_browser(self, url):
        from qgis.PyQt.QtGui import QDesktopServices
        from qgis.PyQt.QtCore import QUrl
        try:
            if QDesktopServices.openUrl(QUrl(url)):
                return True
        except Exception as exc:
            QgsMessageLog.logMessage(
                f"Lỗi khi dùng QDesktopServices.openUrl: {exc}",
                self.plugin_name,
                Qgis.Warning
            )

        import webbrowser
        try:
            if webbrowser.open(url):
                return True
        except Exception:  # noqa: BLE001 — intentional suppress
            pass

        errors = []
        for browser_path in self._browser_paths():
            try:
                subprocess.Popen([browser_path, url], close_fds=True)
                return True
            except Exception as exc:  # noqa: BLE001 — intentional suppress
                errors.append(f"{browser_path}: {exc}")

        QgsMessageLog.logMessage(
            "Không mở được WebGIS bằng trình duyệt trực tiếp. " + " | ".join(errors),
            self.plugin_name,
            Qgis.Warning,
        )
        return False
    def _browser_paths(self):
        seen = set()
        for command in ("msedge", "chrome", "firefox", "brave", "browser", "opera"):
            path = shutil.which(command)
            if path and path not in seen:
                seen.add(path)
                yield path

        if os.name != "nt":
            return

        roots = [
            os.environ.get("ProgramFiles"),
            os.environ.get("ProgramFiles(x86)"),
            os.environ.get("LocalAppData"),
        ]
        relative_paths = [
            os.path.join("Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join("Google", "Chrome", "Application", "chrome.exe"),
            os.path.join("Mozilla Firefox", "firefox.exe"),
            os.path.join("BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
            os.path.join("CocCoc", "Browser", "Application", "browser.exe"),
            os.path.join("Opera Software", "Opera Stable", "opera.exe"),
        ]
        for root in roots:
            if not root:
                continue
            for relative_path in relative_paths:
                path = os.path.join(root, relative_path)
                if os.path.exists(path) and path not in seen:
                    seen.add(path)
                    yield path
    def _load_land_type_colors(self):
        path = os.path.join(self.plugin_dir, "config", "land_types.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            QgsMessageLog.logMessage(
                f"Không đọc được bảng màu loại đất '{path}': {exc}",
                self.plugin_name,
                Qgis.Warning,
            )
            return {}

        colors = {}
        for code, item in data.items():
            rgb = item.get("color") if isinstance(item, dict) else None
            if isinstance(rgb, list) and len(rgb) >= 3:
                colors[str(code).upper()] = "#{:02x}{:02x}{:02x}".format(
                    self._clamp_color(rgb[0]),
                    self._clamp_color(rgb[1]),
                    self._clamp_color(rgb[2]),
                )
        return colors
