# -*- coding: utf-8 -*-
"""Utilities for managing, downloading, and finding compiled binary tools."""
from .common_utils import log_warning


import os
import platform
import stat
import urllib.request
import ssl

def verify_binary(path: str, system: str) -> bool:
    """Verify that the binary matches the expected SHA-256 hash."""
    import hashlib
    EXPECTED_HASHES = {
        "windows": "269fcbc9b4d7df2a8a4418b25e0bb1f8e29e29ae1fb0bc41bb4395c234100a09",
    }
    expected_hash = EXPECTED_HASHES.get(system)
    if not expected_hash:
        return True
    
    sha256 = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        h = sha256.hexdigest().lower()
        if h != expected_hash.lower():
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:  # noqa: BLE001 — intentional suppress
                    pass
            raise RuntimeError("Binary bị hỏng hoặc không hợp lệ")
        return True
    except Exception as e:  # noqa: BLE001 — intentional suppress
        if isinstance(e, RuntimeError):
            raise e
        raise RuntimeError(f"Lỗi khi đọc xác minh file binary: {e}")

def download_cad_reader(system: str, target_path: str, iface=None) -> bool:
    """Download the appropriate cad_reader binary from GitHub Releases on-demand."""
    try:
        from qgis.core import Qgis
        from qgis.PyQt.QtWidgets import QMessageBox, QProgressBar
        has_qgis = True
    except ImportError:
        has_qgis = False
        Qgis = None
        QMessageBox = None
        QProgressBar = None
    
    binary_name = "cad_reader.exe" if system == "windows" else "cad_reader"
    
    # 1. Ask user for permission first if running inside QGIS GUI
    if iface and has_qgis:
        parent = iface.mainWindow()
        reply = QMessageBox.question(
            parent,
            "Tải bộ phân tích CAD",
            f"Không tìm thấy bộ phân tích CAD nhị phân cho hệ điều hành {platform.system()}.\n\n"
            "Bạn có muốn tải xuống tự động từ GitHub (~1.3 MB) để tiếp tục không?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        if reply != QMessageBox.StandardButton.Yes:
            return False
            
    # 2. Build download URL (pointing to a specific pinned release tag)
    base_url = os.environ.get(
        "QGIS_CAD_READER_DOWNLOAD_URL",
        "https://github.com/vnu2f/qlddk68/releases/download/v0.3.0/"
    )
    url = f"{base_url}{binary_name}"
    
    # 3. Perform download
    msg_bar_item = None
    try:
        # Create parent directories if missing
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        
        # Show progress bar in QGIS message bar if running in GUI
        if iface and has_qgis:
            progress = QProgressBar()
            progress.setMaximum(100)
            msg_bar_item = iface.messageBar().createMessage(
                "Đang tải bộ phân tích CAD...", 
                f"Đang tải {binary_name} từ GitHub..."
            )
            msg_bar_item.layout().addWidget(progress)
            iface.messageBar().pushWidget(msg_bar_item, Qgis.Info)

        # Download handler with progress (ignore SSL errors if user has proxy issues)
        ctx = ssl._create_unverified_context()
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        
        with urllib.request.urlopen(req, context=ctx, timeout=30) as response, open(target_path, "wb") as out_file:
            total_size = int(response.info().get('Content-Length', 0))
            block_size = 16384
            downloaded = 0
            
            while True:
                buffer = response.read(block_size)
                if not buffer:
                    break
                downloaded += len(buffer)
                out_file.write(buffer)
                
                # Update QGIS progress bar
                if total_size > 0 and iface and has_qgis and msg_bar_item:
                    percentage = int((downloaded / total_size) * 100)
                    progress.setValue(percentage)
                    
        # Verify file integrity after download
        verify_binary(target_path, system)
                     
        # Remove progress bar on success
        if iface and has_qgis and msg_bar_item:
            try:
                iface.messageBar().popWidget(msg_bar_item)
            except Exception:  # noqa: BLE001 — intentional suppress
                pass
            iface.messageBar().pushSuccess("Thành công", f"Đã tải thành công bộ phân tích CAD ({binary_name}).")
            
        # Set execute permissions on Linux
        if system == "linux":
            st = os.stat(target_path)
            os.chmod(target_path, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
            
        return True
    except Exception as e:
        # Safely clean up progress bar widget on failure
        if iface and has_qgis and msg_bar_item:
            try:
                iface.messageBar().popWidget(msg_bar_item)
            except Exception:
                pass
        error_msg = f"Lỗi tải bộ phân tích CAD từ GitHub: {e}"
        log_warning(error_msg)
        if iface and has_qgis:
            iface.messageBar().pushMessage(
                "Lỗi kết nối", 
                f"Không thể tải tự động bộ phân tích CAD: {e}. Vui lòng tải thủ công file '{binary_name}' đặt vào thư mục: {os.path.dirname(target_path)}",
                level=Qgis.Critical,
                duration=15
            )
        return False

def get_cad_reader_path(iface=None) -> str | None:
    """Detect operating system and return the appropriate cad_reader path.
    If not found, triggers on-demand download from GitHub.
    """
    system = platform.system().lower()
    
    # Define binary names based on OS
    if system == "windows":
        binary_name = "cad_reader.exe"
        subfolder = "win"
    elif system == "linux":
        binary_name = "cad_reader"
        subfolder = "linux"
    else:
        log_warning(f"Hệ điều hành '{platform.system()}' không hỗ trợ chạy binary native. Sẽ sử dụng Python fallback.")
        return None

    plugin_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # 0. Check in vendor/ first (bundled/priority version)
    vendor_bin_path = os.path.join(plugin_root, "vendor", "bin", subfolder, binary_name)
    if os.path.exists(vendor_bin_path):
        try:
            verify_binary(vendor_bin_path, system)
            return vendor_bin_path
        except Exception:  # noqa: BLE001 — intentional suppress
            pass
            
    bin_dir = os.path.join(plugin_root, "modules", "cadastral_importer", "bin")
    
    # Paths we search (in order)
    # 1. Target win/ or linux/ subfolders
    exe_path = os.path.join(bin_dir, subfolder, binary_name)
    
    # 2. Legacy bin/ folder (backward compatibility)
    if not os.path.exists(exe_path):
        legacy_path = os.path.join(bin_dir, binary_name)
        if os.path.exists(legacy_path):
            exe_path = legacy_path

    # 3. Development Rust target release/debug folders
    if not os.path.exists(exe_path):
        target_subfolder = "release" if system == "windows" else "debug"
        dev_path = os.path.join(
            plugin_root,
            "tools",
            "cad_reader_rs",
            "target",
            target_subfolder,
            binary_name
        )
        if os.path.exists(dev_path):
            exe_path = dev_path
        else:
            for folder in ["release", "debug"]:
                alt_path = os.path.join(
                    plugin_root,
                    "tools",
                    "cad_reader_rs",
                    "target",
                    folder,
                    binary_name
                )
                if os.path.exists(alt_path):
                    exe_path = alt_path
                    break

    # If binary is found, set execution permissions on Linux and return it
    if os.path.exists(exe_path):
        try:
            verify_binary(exe_path, system)
            if system == "linux":
                try:
                    st = os.stat(exe_path)
                    os.chmod(exe_path, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
                except Exception as e:
                    log_warning(f"Không thể đặt quyền chạy (chmod +x) cho '{exe_path}': {e}")
            return exe_path
        except Exception:  # noqa: BLE001 — intentional suppress
            pass
        
    # If binary does not exist, trigger on-demand download
    if iface is None:
        try:
            from qgis.utils import iface as qgis_iface
            iface = qgis_iface
        except ImportError:
            pass

    target_download_path = os.path.join(bin_dir, subfolder, binary_name)
    success = download_cad_reader(system, target_download_path, iface)
    if success and os.path.exists(target_download_path):
        return target_download_path

    return None
