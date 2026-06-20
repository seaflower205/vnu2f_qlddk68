# -*- coding: utf-8 -*-
"""
QGIS Compatibility Validator for vnu2f_qlddk68 plugin.

This script verifies whether the plugin can successfully load, initialize,
and unload within a real QGIS Python environment. It mocks QGIS interface objects
and tests QGIS API imports and dependencies.
"""

from __future__ import annotations

import os
import sys
import subprocess
from pathlib import Path

# Reconfigure console streams to use UTF-8 on Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Setup mock classes to simulate QGIS interface without a GUI
MockMainWindow = None
MockMapCanvas = None
MockToolBar = None
MockMessageBar = None
MockInterface = None

def setup_mocks():
    global MockMainWindow, MockMapCanvas, MockToolBar, MockMessageBar, MockInterface
    from qgis.PyQt.QtWidgets import QWidget
    
    class LocalMockMainWindow(QWidget):
        pass

    class LocalMockMapCanvas:
        def mapSettings(self):
            class MockSettings:
                def destinationCrs(self):
                    class MockCrs:
                        def authid(self):
                            return "EPSG:4326"
                    return MockCrs()
            return MockSettings()

    class LocalMockToolBar:
        def setObjectName(self, name: str) -> None:
            pass
        def addAction(self, action) -> None:
            pass

    class LocalMockMessageBar:
        def pushSuccess(self, title: str, msg: str) -> None:
            print(f"    [MESSAGEBAR SUCCESS] {title}: {msg}")
        def pushWarning(self, title: str, msg: str) -> None:
            print(f"    [MESSAGEBAR WARNING] {title}: {msg}")
        def pushInfo(self, title: str, msg: str) -> None:
            print(f"    [MESSAGEBAR INFO] {title}: {msg}")
        def pushMessage(self, title: str, msg: str, level=0) -> None:
            print(f"    [MESSAGEBAR MSG] {title}: {msg}")

    class LocalMockInterface:
        def __init__(self):
            self._window = LocalMockMainWindow()
            self._canvas = LocalMockMapCanvas()
            self._toolbar = LocalMockToolBar()
            self._message_bar = LocalMockMessageBar()

        def mainWindow(self):
            return self._window

        def mapCanvas(self):
            return self._canvas

        def addToolBar(self, name: str):
            return self._toolbar

        def addPluginToMenu(self, menu_name: str, action) -> None:
            pass

        def removePluginMenu(self, menu_name: str, action) -> None:
            pass

        def removeToolBarIcon(self, action) -> None:
            pass

        def messageBar(self):
            return self._message_bar

    MockMainWindow = LocalMockMainWindow
    MockMapCanvas = LocalMockMapCanvas
    MockToolBar = LocalMockToolBar
    MockMessageBar = LocalMockMessageBar
    MockInterface = LocalMockInterface


def run_qgis_tests() -> int:
    """Runs tests inside QGIS Python interpreter environment."""
    print("=" * 60)
    print("⚡ CHẠY KIỂM TRA TRONG MÔI TRƯỜNG QGIS PYTHON ⚡")
    print(f"Python: {sys.version}")
    print(f"Interpreter: {sys.executable}")
    print("=" * 60)

    errors = 0
    warnings = 0

    # 1. Check QGIS Imports
    print("1. Kiểm tra nạp thư viện lõi QGIS & PyQt:")
    try:
        from qgis.core import QgsProject, Qgis, QgsMessageLog, QgsApplication
        from qgis.gui import QgsMapCanvas
        from qgis.PyQt.QtCore import QCoreApplication
        from qgis.PyQt.QtWidgets import QAction
        print("   [OK] Đã nạp thành công qgis.core, qgis.gui và qgis.PyQt!")
    except ImportError as exc:
        print(f"   [FAIL] Lỗi nạp thư viện QGIS/PyQt: {exc}")
        return 1

    try:
        qgs_app = QgsApplication([], False)
        qgs_app.initQgis()
        print("   [OK] Đã khởi tạo QgsApplication thành công!")
    except Exception as exc:
        print(f"   [FAIL] Lỗi khởi tạo QgsApplication: {exc}")
        return 1

    try:
        try:
            print("   [TRACE] Đang thiết lập các mock object...", flush=True)
            setup_mocks()
            print("   [TRACE] Thiết lập mock object thành công.", flush=True)
        except Exception as exc:
            print(f"   [FAIL] Không thể khởi tạo các đối tượng Mock: {exc}", flush=True)
            return 1

        # 2. Check third-party dependencies inside QGIS Python
        print("\n2. Kiểm tra thư viện phụ thuộc của Plugin:", flush=True)
        deps = ["ezdxf", "openpyxl", "shapely", "pandas"]
        for dep in deps:
            try:
                print(f"   [TRACE] Thử import {dep}...", flush=True)
                mod = __import__(dep)
                path = getattr(mod, "__file__", "Built-in")
                print(f"   [OK] {dep:<10} - Đã cài đặt (Path: {path})", flush=True)
            except ImportError:
                print(f"   [WARN] {dep:<10} - Chưa cài đặt trong môi trường QGIS này.", flush=True)
                warnings += 1

        # 3. Add parent directory of plugin to path and try importing it as a package
        print("\n3. Thử nạp Plugin và kiểm tra entry points:", flush=True)
        plugin_root = Path(__file__).resolve().parents[1]
        plugin_parent = plugin_root.parent
        plugin_name = plugin_root.name
        print(f"   [TRACE] plugin_root: {plugin_root}, plugin_parent: {plugin_parent}, plugin_name: {plugin_name}", flush=True)
        sys.path.insert(0, str(plugin_parent))

        # Fake QGIS system module environment
        sys.modules["qgis.utils"] = type(sys)("qgis.utils")
        sys.modules["qgis.utils"].iface = MockInterface()

        try:
            print(f"   [TRACE] Đang nạp gói {plugin_name}...", flush=True)
            import importlib
            plugin_package = importlib.import_module(plugin_name)
            print(f"   [OK] Gói {plugin_name} được nạp thành công!", flush=True)
        except Exception as exc:
            print(f"   [FAIL] Không thể nạp gói {plugin_name}: {exc}", flush=True)
            import traceback
            traceback.print_exc()
            return 1

        # Test classFactory
        if not hasattr(plugin_package, "classFactory"):
            print("   [FAIL] Thiếu hàm bắt buộc classFactory(iface) trong __init__.py!", flush=True)
            return 1
        
        print("   [OK] Tìm thấy hàm classFactory(iface).", flush=True)

        # Instantiate plugin
        try:
            print("   [TRACE] Đang khởi tạo lớp Plugin qua classFactory...", flush=True)
            mock_iface = MockInterface()
            plugin_instance = plugin_package.classFactory(mock_iface)
            print(f"   [OK] Khởi tạo thành công lớp Plugin: {plugin_instance.__class__.__name__}", flush=True)
        except Exception as exc:
            print(f"   [FAIL] Không thể khởi tạo lớp Plugin qua classFactory: {exc}")
            import traceback
            traceback.print_exc()
            return 1

        # Test initGui
        print("\n4. Kiểm thử đăng ký giao diện (initGui):")
        try:
            plugin_instance.initGui()
            print("   [OK] Lệnh initGui() hoàn thành không lỗi!")
        except Exception as exc:
            print(f"   [FAIL] Lỗi xảy ra trong initGui(): {exc}")
            import traceback
            traceback.print_exc()
            errors += 1

        # Test unload
        print("\n5. Kiểm thử hủy đăng ký giao diện (unload):")
        try:
            plugin_instance.unload()
            print("   [OK] Lệnh unload() hoàn thành không lỗi!")
        except Exception as exc:
            print(f"   [FAIL] Lỗi xảy ra trong unload(): {exc}")
            import traceback
            traceback.print_exc()
            errors += 1

        # 6. Verify critical imports
        print("\n6. Kiểm tra nạp các phân hệ chính:")
        modules_to_test = [
            (f"{plugin_name}.modules.crs_converter.crs_dialog", "CRSConverterDialog"),
            (f"{plugin_name}.modules.crs_converter.crs_utils", "CoordinateTransformer"),
            (f"{plugin_name}.modules.cadastral_importer.dialog", "CadastralImportDialog"),
            (f"{plugin_name}.modules.cadastral_importer.cad_reader", "import_cad_to_memory_layers"),
            (f"{plugin_name}.modules.webgis_launcher", "WebGISLauncher"),
        ]
        for mod_path, class_name in modules_to_test:
            try:
                mod = __import__(mod_path, fromlist=[class_name])
                getattr(mod, class_name)
                print(f"   [OK] Nạp thành công: {mod_path}.{class_name}")
            except Exception as exc:
                print(f"   [FAIL] Lỗi nạp phân hệ {mod_path}.{class_name}: {exc}")
                errors += 1

        # 7. Test Dialog instantiation to verify sub-widgets and tab layouts
        print("\n7. Kiểm thử khởi tạo các hộp thoại giao diện chính (CRSConverterDialog, CadastralImportDialog):")
        try:
            from vnu2f_qlddk68.modules.crs_converter.crs_dialog import CRSConverterDialog
            from vnu2f_qlddk68.modules.cadastral_importer.dialog import CadastralImportDialog
            
            print("   [TRACE] Đang khởi tạo thử CRSConverterDialog...", flush=True)
            crs_dlg = CRSConverterDialog(parent=mock_iface.mainWindow())
            print("   [OK] CRSConverterDialog khởi tạo thành công!", flush=True)
            
            print("   [TRACE] Đang khởi tạo thử CadastralImportDialog...", flush=True)
            cad_dlg = CadastralImportDialog(parent=mock_iface.mainWindow())
            print("   [OK] CadastralImportDialog khởi tạo thành công!", flush=True)
        except Exception as exc:
            print(f"   [FAIL] Lỗi khởi tạo hộp thoại giao diện: {exc}", flush=True)
            import traceback
            traceback.print_exc()
            errors += 1

        print("\n" + "=" * 60)
        if errors > 0:
            print(f"❌ KẾT QUẢ: THẤT BẠI - Phát hiện {errors} lỗi nghiêm trọng!")
            return 1
        
        print(f"✔️ KẾT QUẢ: THÀNH CÔNG! (Cảnh báo: {warnings})")
        print("Plugin tương thích tốt với môi trường QGIS hiện tại.")
        print("=" * 60)
        return 0
    finally:
        try:
            qgs_app.exitQgis()
            print("✔️ Đã giải phóng QgsApplication thành công.")
        except Exception:
            pass


def find_qgis_python() -> str | None:
    """Attempts to find the QGIS Python environment batch file."""
    search_paths = [
        r"C:\Program Files\QGIS 4.0.2\bin\python-qgis.bat",
        r"C:\Program Files\QGIS 4.0\bin\python-qgis.bat",
        r"C:\Program Files\QGIS 3.34\bin\python-qgis.bat",
        r"C:\Program Files\QGIS 3.28\bin\python-qgis.bat",
        r"C:\OSGeo4W\bin\python-qgis.bat",
        r"C:\OSGeo4W64\bin\python-qgis.bat",
    ]
    for path in search_paths:
        if os.path.exists(path):
            return path
            
    # Try finding any QGIS directory in Program Files
    prog_files = Path(r"C:\Program Files")
    if prog_files.exists():
        for item in prog_files.glob("QGIS *"):
            bat_path = item / "bin" / "python-qgis.bat"
            if bat_path.exists():
                return str(bat_path)
                
    return None


def main() -> int:
    # Check if we are already running inside the QGIS Python interpreter
    try:
        from qgis.core import QgsProject
        # Already inside QGIS Python
        return run_qgis_tests()
    except ImportError:
        # Reconfigure console streams to use UTF-8 on Windows for standard python
        if hasattr(sys.stdout, 'reconfigure'):
            try:
                sys.stdout.reconfigure(encoding='utf-8')
            except Exception:
                pass
        if hasattr(sys.stderr, 'reconfigure'):
            try:
                sys.stderr.reconfigure(encoding='utf-8')
            except Exception:
                pass

        # Not inside QGIS Python, need to launch QGIS Python environment recursively
        print("Đang quét tìm môi trường QGIS trên máy tính...")
        qgis_bat = find_qgis_python()
        if not qgis_bat:
            print("❌ LỖI: Không tìm thấy tệp 'python-qgis.bat' trên hệ thống.")
            print("Vui lòng chạy script này trực tiếp từ QGIS Python console hoặc cài đặt QGIS.")
            return 1
            
        print(f"✔️ Tìm thấy môi trường QGIS tại: {qgis_bat}")
        print("Đang khởi động tiến trình kiểm tra trong môi trường QGIS Python...")
        
        script_path = os.path.abspath(__file__)
        result = subprocess.run([qgis_bat, script_path], capture_output=True, text=True, encoding='utf-8', errors='ignore')
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return result.returncode


if __name__ == "__main__":
    sys.exit(main())
