# -*- coding: utf-8 -*-
"""
Tab: Hệ thống & Thư viện (Health Check Tab)
Kiểm tra các gói thư viện phụ thuộc và cho phép người dùng cài đặt thủ công.
"""

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
from .health_tab_ui_mixin import HealthTabUiMixin

class HealthCheckWorker(QThread):
    finished_signal = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
    def run(self):
        try:
            online = is_online()
            core_reqs, opt_reqs = read_requirements()
            all_reqs = [(name, spec, True) for name, spec in core_reqs] + [(name, spec, False) for name, spec in opt_reqs]
            
            req_infos = []
            for name, spec, is_core in all_reqs:
                info = get_package_info(name)
                req_infos.append((name, spec, is_core, info))
                
            result = {
                "online": online,
                "req_infos": req_infos,
                "logs": get_install_logs()
            }
            self.finished_signal.emit(result)
        except Exception as e:
            self.finished_signal.emit({"error": str(e)})

def tx(key, **kwargs):
    return tab_text("health", key, **kwargs)

class HealthTab(HealthTabUiMixin, QWidget):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.parent_dialog = parent
        self._install_thread = None
        self._timer = None
        
        self._build_ui()
        self._refresh_status()


    def _get_manifest_version(self):
        try:
            plugin_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            metadata_path = os.path.join(plugin_root, "metadata.txt")
            if os.path.exists(metadata_path):
                import configparser
                config = configparser.ConfigParser()
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if not content.strip().startswith('['):
                    content = '[general]\n' + content
                config.read_string(content)
                return config.get('general', 'version', fallback='Unknown')
        except Exception:  # noqa: BLE001 — intentional suppress
            pass
        return "0.3.0"

    def _refresh_status(self):
        self.btn_check.setEnabled(False)
        self.lbl_network.setText(f"<b>{tx('label.network')}</b> <i>Đang kiểm tra...</i>")
        
        self._worker = HealthCheckWorker(self)
        self._worker.finished_signal.connect(self._on_health_check_finished)
        self._worker.start()

    def _on_health_check_finished(self, result):
        self.btn_check.setEnabled(True)
        if "error" in result:
            self.lbl_network.setText(f"<b>{tx('label.network')}</b> <span style='color: #ef4444;'>Lỗi kiểm tra</span>")
            return
            
        # 1. Update manifest version
        version = self._get_manifest_version()
        self.lbl_manifest.setText(f"<b>{tx('label.manifest')}</b> {version}")
        
        # 2. Update network status
        online = result["online"]
        status_text = tx("status.online") if online else tx("status.offline")
        color = "#22c55e" if online else "#ef4444"
        self.lbl_network.setText(f"<b>{tx('label.network')}</b> <span style='color: {color};'>{status_text}</span>")
        
        # 3. Populate requirements table
        self.table.setRowCount(0)
        for i, (name, spec, is_core, info) in enumerate(result["req_infos"]):
            self.table.insertRow(i)
            
            # Name
            self.table.setItem(i, 0, QTableWidgetItem(name))
            
            # Requirement Type
            req_type = tx("core") if is_core else tx("optional")
            self.table.setItem(i, 1, QTableWidgetItem(req_type))
            
            # Status
            status_str = tx("installed") if info["installed"] else tx("missing")
            status_item = QTableWidgetItem(status_str)
            status_item.setForeground(Qt.GlobalColor.black if not is_dark_mode() else Qt.GlobalColor.white)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 2, status_item)
            
            # Version
            ver_str = info["version"] or "-"
            self.table.setItem(i, 3, QTableWidgetItem(ver_str))
            
            # Path
            path_str = info["path"] or "-"
            self.table.setItem(i, 4, QTableWidgetItem(path_str))
            
        # Update log view
        self.txt_log.setPlainText(result["logs"])

    def _on_install_click(self):
        self.btn_install.setEnabled(False)
        self.btn_check.setEnabled(False)
        self.txt_log.append("\n========================================")
        self.txt_log.append("BẮT ĐẦU QUY TRÌNH CÀI ĐẶT / CẬP NHẬT THƯ VIỆN...")
        self.txt_log.append("========================================\n")
        
        # Run in a background thread to keep UI interactive
        self._install_thread = threading.Thread(
            target=self._run_installation_bg,
            daemon=True
        )
        self._install_thread.start()
        
        # Start QTimer to poll logs and update QTextEdit in real-time
        self._timer = QTimer(self)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self._on_timer_tick)
        self._timer.start()

    def _run_installation_bg(self):
        online = is_online()
        self._run_installation(online)

    def _run_installation(self, online):
        core_reqs, opt_reqs = read_requirements()
        all_reqs = [(name, spec, True) for name, spec in core_reqs] + [(name, spec, False) for name, spec in opt_reqs]
        
        # Offline mode fallback: if not online, we use offline
        offline = not online
        
        for name, spec, is_core in all_reqs:
            info = get_package_info(name)
            # Only install if not installed (or if it's pandas and it's missing)
            if not info["installed"]:
                log_message(f"Phát hiện thiếu thư viện: {name}", "info")
                success = install_package(name, spec=spec, offline=offline)
                if not success and online:
                    log_message(f"Cài online thất bại, thử fallback offline từ wheels cho '{name}'.", "warning")
                    success = install_package(name, spec=spec, offline=True)
                if not success and is_core:
                    log_message(f"LỖI CỰC KỲ NGHIÊM TRỌNG: Không cài được thư viện bắt buộc '{name}'!", "error")
            else:
                log_message(f"Thư viện '{name}' đã được cài đặt sẵn (phiên bản: {info['version']}). Bỏ qua.", "info")
                
        log_message("Hoàn tất quy trình cài đặt phụ thuộc.", "info")

    def hideEvent(self, event):
        """Dừng timer khi tab bị ẩn để tránh cập nhật UI rác."""
        self._stop_timer()
        super().hideEvent(event)

    def _stop_timer(self):
        if hasattr(self, "_timer") and self._timer:
            try:
                self._timer.stop()
            except Exception:  # noqa: BLE001 — intentional suppress
                pass
            self._timer = None

    def _on_timer_tick(self):
        try:
            self.txt_log.setPlainText(get_install_logs())
            # Scroll to bottom
            self.txt_log.moveCursor(self.txt_log.textCursor().MoveOperation.End)
            
            if self._install_thread and not self._install_thread.is_alive():
                self._stop_timer()
                self.btn_install.setEnabled(True)
                self.btn_check.setEnabled(True)
                self._refresh_status()
                self.txt_log.append("\n>>> Hoàn thành! Đã làm mới trạng thái hệ thống.")
        except (RuntimeError, AttributeError):
            # Cảnh giác trường hợp đối tượng C++ đã bị giải phóng
            self._stop_timer()

    def cleanup(self):
        """Dọn dẹp tài nguyên khi đóng hộp thoại."""
        self._stop_timer()
