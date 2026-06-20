# -*- coding: utf-8 -*-
"""Dependency installer helper for the QGIS plugin."""

import importlib
import importlib.util
import os
import re
import socket
import subprocess
import sys
from datetime import datetime

# Setup local vendor/ path dynamically
vendor_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "vendor"))
if vendor_path not in sys.path:
    sys.path.insert(0, vendor_path)

# We will support running without QGIS for CLI preflight checks
try:
    from qgis.core import QgsMessageLog, Qgis
    HAS_QGIS = True
except ImportError:
    HAS_QGIS = False

INSTALL_LOGS = []

def log_message(msg, level="info"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] [{level.upper()}] {msg}"
    INSTALL_LOGS.append(formatted)
    
    if HAS_QGIS:
        qgis_level = Qgis.Info
        if level == "warning":
            qgis_level = Qgis.Warning
        elif level == "error":
            qgis_level = Qgis.Critical
        elif level == "success":
            qgis_level = Qgis.Success
        QgsMessageLog.logMessage(msg, "VNU2F_DEP", qgis_level)
    else:
        print(formatted)

def get_install_logs():
    return "\n".join(INSTALL_LOGS)

def is_installed(package_name):
    try:
        spec = importlib.util.find_spec(package_name)
        return spec is not None
    except Exception:  # noqa: BLE001 — intentional suppress
        return False

def get_package_info(package_name):
    info = {"installed": False, "version": None, "path": None}
    try:
        # Try importlib.metadata first for version
        try:
            import importlib.metadata
            info["version"] = importlib.metadata.version(package_name)
        except Exception:  # noqa: BLE001 — intentional suppress
            pass
            
        # Try direct import/spec check to confirm installation and path
        mod_name = package_name.lower().replace("-", "_")
        spec = importlib.util.find_spec(mod_name)
        if spec is not None:
            info["installed"] = True
            if spec.origin:
                info["path"] = spec.origin
            elif spec.submodule_search_locations:
                info["path"] = list(spec.submodule_search_locations)[0]
                
            # If version is still unknown, try importing to check __version__
            if not info["version"]:
                try:
                    mod = importlib.import_module(mod_name)
                    if hasattr(mod, "__version__"):
                        info["version"] = str(mod.__version__)
                except Exception:  # noqa: BLE001 — intentional suppress
                    pass
    except Exception:  # noqa: BLE001 — intentional suppress
        pass
    return info

def is_online():
    """Checks if there is an active internet connection by testing PyPI connection."""
    try:
        with socket.create_connection(("pypi.org", 443), timeout=3):
            pass
        return True
    except OSError:
        return False

def read_requirements():
    """Reads requirements-qgis.txt and returns lists of (name, spec, is_optional)."""
    core = []
    optional = []
    
    # plugin root is 3 levels up from modules/common/dep_installer.py
    plugin_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    req_path = os.path.join(plugin_root, "requirements-qgis.txt")
    
    if not os.path.exists(req_path):
        # Fallbacks
        core = [("ezdxf", ">=1.1.0,<2.0.0"), ("openpyxl", ">=3.1.0,<4.0.0"), ("shapely", ">=2.0.0,<3.0.0")]
        optional = [("pandas", ">=2.0.0,<3.0.0")]
        return core, optional
        
    try:
        current_is_optional = False
        with open(req_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("#"):
                    if "optional" in line.lower():
                        current_is_optional = True
                    elif "core" in line.lower():
                        current_is_optional = False
                    continue
                
                # Match package name and optional specifier (e.g., ezdxf>=1.1.0)
                match = re.match(r"^([a-zA-Z0-9_\-]+)(.*)$", line)
                if match:
                    name = match.group(1)
                    spec = match.group(2).strip()
                    if current_is_optional:
                        optional.append((name, spec))
                    else:
                        core.append((name, spec))
    except Exception as e:  # noqa: BLE001 — intentional suppress
        log_message(f"Lỗi khi đọc file requirements: {e}", "warning")
        core = [("ezdxf", ">=1.1.0,<2.0.0"), ("openpyxl", ">=3.1.0,<4.0.0"), ("shapely", ">=2.0.0,<3.0.0")]
        optional = [("pandas", ">=2.0.0,<3.0.0")]
        
    if not core:
        core = [("ezdxf", ">=1.1.0,<2.0.0"), ("openpyxl", ">=3.1.0,<4.0.0"), ("shapely", ">=2.0.0,<3.0.0")]
        optional = [("pandas", ">=2.0.0,<3.0.0")]
        
    return core, optional

def install_package(package_name, spec="", offline=False):
    """Runs pip install for package_name using QGIS Python interpreter."""
    try:
        plugin_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        wheels_dir = os.path.join(plugin_root, "vendor", "wheels")
        vendor_dir = os.path.abspath(os.path.join(plugin_root, "vendor"))
        os.makedirs(vendor_dir, exist_ok=True)
        
        # Windows startup info to prevent CLI window flashing
        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

        cmd = [sys.executable, "-m", "pip", "install"]
        
        if offline:
            log_message(f"Đang cài đặt offline thư viện '{package_name}' từ wheels...", "info")
            if not os.path.exists(wheels_dir):
                log_message(f"Không tìm thấy thư mục wheels offline tại: {wheels_dir}", "error")
                return False
            cmd.extend(["--no-index", f"--find-links={wheels_dir}"])
        else:
            log_message(f"Đang cài đặt online thư viện '{package_name}' qua pip...", "info")

        requirement = f"{package_name}{spec}" if spec else package_name
        cmd.extend([requirement, "--target", vendor_dir])
        
        log_message(f"Chạy lệnh: {' '.join(cmd)}", "info")
        
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            startupinfo=startupinfo,
            timeout=180
        )
        
        if proc.returncode == 0:
            log_message(f"Cài đặt thành công thư viện '{package_name}'!", "success")
            return True
        else:
            error_text = proc.stderr or proc.stdout or "Không rõ nguyên nhân."
            log_message(
                f"Không thể cài đặt '{package_name}'. Lỗi: {error_text}",
                "error"
            )
            # Push critical notification to viewport if inside QGIS
            if HAS_QGIS:
                try:
                    from qgis.utils import iface
                    if iface:
                        iface.messageBar().pushMessage(
                            "Lỗi cài đặt thư viện",
                            f"Không thể cài đặt tự động thư viện bắt buộc '{package_name}': {error_text}. Vui lòng thử lại qua tab Health Check.",
                            level=Qgis.Critical,
                            duration=10
                        )
                except Exception:  # noqa: BLE001 — intentional suppress
                    pass
            return False
    except Exception as e:  # noqa: BLE001 — intentional suppress
        log_message(f"Lỗi hệ thống khi cài '{package_name}': {e}", "error")
        if HAS_QGIS:
            try:
                from qgis.utils import iface
                if iface:
                    iface.messageBar().pushMessage(
                        "Lỗi hệ thống",
                        f"Lỗi hệ thống khi cài '{package_name}': {e}",
                        level=Qgis.Critical,
                        duration=10
                    )
            except Exception:
                pass
        return False
