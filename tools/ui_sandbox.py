# -*- coding: utf-8 -*-
"""UI Sandbox & Live Previewer — Phase 5, Component 4.

Standalone application for previewing QGIS plugin UI tabs outside of QGIS
Desktop.  Uses a headless QgsApplication core (NOT sys.modules mocking)
to avoid C++ SIP segmentation faults.

Usage:
    # From plugin root (requires QGIS installed on system):
    python tools/ui_sandbox.py

    # With explicit QGIS prefix:
    set QGIS_PREFIX_PATH=C:\\OSGeo4W\\apps\\qgis
    python tools/ui_sandbox.py

Prerequisites:
    - QGIS must be installed on the system.
    - The QGIS Python environment must be accessible (e.g. via OSGeo4W shell
      or by adding QGIS Python paths to PYTHONPATH / sys.path).
"""

from __future__ import annotations

import os
import sys

# ---------------------------------------------------------------------------
# 0. Ensure plugin root's PARENT is on sys.path so package imports resolve.
#
# QGIS loads plugins by adding the parent of the plugin directory to sys.path
# and importing via the plugin package name (e.g. ``import vnu2f_qlddk68``).
# Relative imports like ``from ...modules.ui_utils`` in SymbologyTab traverse
# up through: ui → cadastral_tools → vnu2f_qlddk68 (root package).
# If we added the plugin root itself to sys.path, Python would see
# ``cadastral_tools`` as a top-level package and ``...`` (3 levels) would
# escape the package boundary → ImportError.
# ---------------------------------------------------------------------------
PLUGIN_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir)
)
PLUGIN_PARENT = os.path.dirname(PLUGIN_ROOT)  # e.g. "3D Objects/Qgis project"

if PLUGIN_PARENT not in sys.path:
    sys.path.insert(0, PLUGIN_PARENT)
# Also keep plugin root for absolute imports like ``from modules.xxx``
if PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, PLUGIN_ROOT)

# Ensure UTF-8 stdout on Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# 1. QGIS Headless Bootstrap
# ---------------------------------------------------------------------------

def _find_qgis_prefix() -> str:
    """Auto-detect QGIS installation prefix path.

    Search order:
      1. QGIS_PREFIX_PATH environment variable
      2. OSGeo4W default install (C:\\OSGeo4W\\apps\\qgis)
      3. QGIS standalone installs (C:\\Program Files\\QGIS 3.*)
      4. Linux/macOS standard paths

    Returns the prefix path or raises RuntimeError.
    """
    # Check env var first
    env_prefix = os.environ.get("QGIS_PREFIX_PATH", "")
    if env_prefix and os.path.isdir(env_prefix):
        return env_prefix

    if sys.platform == "win32":
        import glob

        # OSGeo4W
        osgeo_qgis = r"C:\OSGeo4W\apps\qgis"
        if os.path.isdir(osgeo_qgis):
            return osgeo_qgis

        # Standalone QGIS (newest first)
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        for entry in sorted(
            glob.glob(os.path.join(program_files, "QGIS 3*")), reverse=True
        ):
            candidate = os.path.join(entry, "apps", "qgis")
            if os.path.isdir(candidate):
                return candidate
            # Some installs put python/ directly under the QGIS dir
            if os.path.isdir(os.path.join(entry, "python")):
                return entry
    else:
        # Linux / macOS
        for prefix in ["/usr", "/usr/local"]:
            if os.path.isdir(os.path.join(prefix, "share", "qgis")):
                return prefix
        mac_prefix = "/Applications/QGIS.app/Contents/MacOS"
        if os.path.isdir(mac_prefix):
            return mac_prefix

    raise RuntimeError(
        "Không tìm thấy QGIS installation.\n"
        "Đặt biến môi trường QGIS_PREFIX_PATH hoặc cài QGIS vào vị trí chuẩn.\n"
        "Ví dụ: set QGIS_PREFIX_PATH=C:\\OSGeo4W\\apps\\qgis"
    )


def _setup_qgis_python_paths(prefix: str) -> None:
    """Add QGIS Python directories to sys.path if needed."""
    if sys.platform == "win32":
        # OSGeo4W layout: prefix = C:\OSGeo4W\apps\qgis
        parent = os.path.dirname(prefix)  # C:\OSGeo4W\apps
        osgeo_root = os.path.dirname(parent)  # C:\OSGeo4W
        python_dirs = [
            os.path.join(prefix, "python"),
            os.path.join(prefix, "python", "plugins"),
            os.path.join(osgeo_root, "apps", "Python312", "Lib", "site-packages"),
            os.path.join(osgeo_root, "apps", "Python311", "Lib", "site-packages"),
            os.path.join(osgeo_root, "apps", "Python39", "Lib", "site-packages"),
        ]
        for d in python_dirs:
            if os.path.isdir(d) and d not in sys.path:
                sys.path.insert(0, d)

        # Add bin to PATH for DLLs
        bin_dir = os.path.join(osgeo_root, "bin")
        if os.path.isdir(bin_dir):
            os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
    else:
        python_dir = os.path.join(prefix, "share", "qgis", "python")
        if os.path.isdir(python_dir) and python_dir not in sys.path:
            sys.path.insert(0, python_dir)


def init_headless_qgis():
    """Initialize QgsApplication in headless mode.

    This is the ONLY safe way to use QGIS C++ API outside of QGIS Desktop.
    NEVER use sys.modules.update() to mock QGIS — it causes segfaults.

    Returns:
        QgsApplication instance.
    """
    prefix = _find_qgis_prefix()
    _setup_qgis_python_paths(prefix)

    from qgis.core import QgsApplication

    QgsApplication.setPrefixPath(prefix, True)
    # False = no GUI (headless mode, but we will create our own QMainWindow)
    qgs = QgsApplication([], False)
    qgs.initQgis()

    print(f"[Sandbox] QGIS headless initialized — prefix: {prefix}")
    return qgs


# ---------------------------------------------------------------------------
# 2. MockPluginState — ONLY mocks business logic, NOT QGIS C++ API
# ---------------------------------------------------------------------------

def _create_mock_plugin_state():
    """Create a MockPluginState using real PyQt signals from QGIS.

    This replicates the interface of cadastral_tools.core.plugin_state.PluginState
    but provides sandbox-friendly default values.
    """
    from qgis.PyQt.QtCore import QObject, pyqtSignal

    class MockPluginStateSignals(QObject):
        """Signals matching PluginStateSignals interface."""
        state_changed = pyqtSignal()
        layer_changed = pyqtSignal(str)
        code_field_changed = pyqtSignal(str)
        area_field_changed = pyqtSignal(str)

    class MockPluginState:
        """Mock PluginState with sandbox default values.

        Replicates the property interface of PluginState:
          - active_layer_id, code_field, area_field, active_preset
        Mock data is injected via populate_layers monkey-patch, not here.
        """

        def __init__(self):
            self.signals = MockPluginStateSignals()
            self._active_layer_id = ""
            self._code_field = "LOAI_DAT"
            self._area_field = "DIEN_TICH"
            self._active_preset = "Địa chính chuẩn"

        @property
        def active_layer_id(self) -> str:
            return self._active_layer_id

        @active_layer_id.setter
        def active_layer_id(self, val: str):
            if self._active_layer_id != val:
                self._active_layer_id = val
                try:
                    self.signals.layer_changed.emit(val)
                    self.signals.state_changed.emit()
                except RuntimeError:
                    pass

        @property
        def code_field(self) -> str:
            return self._code_field

        @code_field.setter
        def code_field(self, val: str):
            if self._code_field != val:
                self._code_field = val
                try:
                    self.signals.code_field_changed.emit(val)
                    self.signals.state_changed.emit()
                except RuntimeError:
                    pass

        @property
        def area_field(self) -> str:
            return self._area_field

        @area_field.setter
        def area_field(self, val: str):
            if self._area_field != val:
                self._area_field = val
                try:
                    self.signals.area_field_changed.emit(val)
                    self.signals.state_changed.emit()
                except RuntimeError:
                    pass

        @property
        def active_preset(self) -> str:
            return self._active_preset

        @active_preset.setter
        def active_preset(self, val: str):
            if self._active_preset != val:
                self._active_preset = val
                try:
                    self.signals.state_changed.emit()
                except RuntimeError:
                    pass

    return MockPluginState()


# ---------------------------------------------------------------------------
# 3. Monkey-patch: inject mock data into tabs
# ---------------------------------------------------------------------------

# Mock layer data for ComboBox population
MOCK_LAYERS = [
    ("📂 Ranh_gioi_thua_dat_Hoa_Binh.shp", "mock_layer_1"),
    ("📂 Quy_hoach_su_dung_dat_2024.shp", "mock_layer_2"),
    ("📂 Bien_dong_dat_dai_Q1_2025.gpkg", "mock_layer_3"),
]

MOCK_CODE_FIELDS = ["LOAI_DAT", "MA_LOAI", "LOAI_HINH", "SDD"]
MOCK_AREA_FIELDS = ["DIEN_TICH", "AREA_M2", "Shape_Area"]


def patch_tab_for_sandbox(tab_instance):
    """Monkey-patch tab methods that depend on iface or live QgsProject layers.

    QGIS C++ API (QgsProject, etc.) is real and initialized headless.
    We only need to mock:
      1. populate_layers → inject fake layer names (headless has no map layers)
      2. iface-dependent methods → no-op (headless has no iface)
      3. trigger_refresh → no-op (no real data to refresh)
    """
    # 1. Override populate_layers to inject mock data
    if hasattr(tab_instance, "populate_layers"):
        def _mock_populate():
            if hasattr(tab_instance, "cbo_layer"):
                tab_instance.cbo_layer.clear()
                for display, data in MOCK_LAYERS:
                    tab_instance.cbo_layer.addItem(display, data)
            if hasattr(tab_instance, "cbo_field"):
                tab_instance.cbo_field.clear()
                tab_instance.cbo_field.addItems(MOCK_CODE_FIELDS)
            if hasattr(tab_instance, "cbo_field_code"):
                tab_instance.cbo_field_code.clear()
                tab_instance.cbo_field_code.addItems(MOCK_CODE_FIELDS)
            if hasattr(tab_instance, "cbo_field_area"):
                tab_instance.cbo_field_area.clear()
                tab_instance.cbo_field_area.addItems(MOCK_AREA_FIELDS)

        tab_instance.populate_layers = _mock_populate

    # 2. No-op iface-dependent methods
    noop_methods = [
        "_apply_style_to_layer",
        "trigger_refresh",
        "_connect_layer_signals",
        "_disconnect_layer_signals",
        "_on_layer_features_changed",
    ]
    for method_name in noop_methods:
        if hasattr(tab_instance, method_name):
            setattr(tab_instance, method_name, lambda *a, **kw: None)


# ---------------------------------------------------------------------------
# 4. SandboxWindow — Main UI
# ---------------------------------------------------------------------------

def _create_sandbox_window():
    """Build and return the SandboxWindow QMainWindow.

    Separated into a function to avoid import-time side effects.
    """
    from qgis.PyQt.QtWidgets import (
        QMainWindow,
        QWidget,
        QHBoxLayout,
        QVBoxLayout,
        QListWidget,
        QStackedWidget,
        QPushButton,
        QComboBox,
        QLabel,
        QStatusBar,
        QApplication,
    )
    from qgis.PyQt.QtCore import Qt

    class SandboxWindow(QMainWindow):
        """Live previewer for plugin UI tabs with language/size/theme toggles."""

        WINDOW_PRESETS = {
            "800×600": (800, 600),
            "1024×768": (1024, 768),
            "1280×720": (1280, 720),
            "1920×1080": (1920, 1080),
        }

        def __init__(self):
            super().__init__()
            self.setWindowTitle("🔬 VNU2F UI Sandbox — Live Previewer")
            self.resize(1200, 800)

            self._tabs = []
            self._state = _create_mock_plugin_state()

            self._build_ui()
            self._load_tabs()
            self._update_status()

        def _build_ui(self):
            # --- Central widget ---
            central = QWidget()
            self.setCentralWidget(central)
            main_layout = QHBoxLayout(central)
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.setSpacing(0)

            # --- Sidebar: tab selector ---
            self.tab_list = QListWidget()
            self.tab_list.setFixedWidth(200)
            self.tab_list.setStyleSheet("""
                QListWidget {
                    background-color: #18181b;
                    color: #fafafa;
                    border: none;
                    font-size: 13px;
                    padding: 8px 0;
                }
                QListWidget::item {
                    padding: 10px 16px;
                    border-bottom: 1px solid #27272a;
                }
                QListWidget::item:selected {
                    background-color: #27272a;
                    color: #22c55e;
                    font-weight: bold;
                }
                QListWidget::item:hover {
                    background-color: #27272a;
                }
            """)
            main_layout.addWidget(self.tab_list)

            # --- Preview area ---
            self.stack = QStackedWidget()
            self.stack.setStyleSheet("background-color: #09090b;")
            main_layout.addWidget(self.stack, 1)

            self.tab_list.currentRowChanged.connect(self._on_tab_changed)

            # --- Toolbar ---
            toolbar = self.addToolBar("Controls")
            toolbar.setMovable(False)
            toolbar.setStyleSheet("""
                QToolBar {
                    background-color: #18181b;
                    border-bottom: 1px solid #27272a;
                    padding: 4px 8px;
                    spacing: 8px;
                }
            """)

            # Language toggle
            self.lang_btn = QPushButton("🌐 VI")
            self.lang_btn.setCheckable(True)
            self.lang_btn.setFixedWidth(80)
            self.lang_btn.setStyleSheet("""
                QPushButton {
                    background-color: #27272a;
                    color: #fafafa;
                    border: 1px solid #3f3f46;
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 13px;
                }
                QPushButton:checked {
                    background-color: #22c55e;
                    color: #09090b;
                    border-color: #22c55e;
                }
                QPushButton:hover {
                    background-color: #3f3f46;
                }
            """)
            self.lang_btn.clicked.connect(self._toggle_language)
            toolbar.addWidget(self.lang_btn)

            # Spacer label
            toolbar.addWidget(QLabel("  Kích thước: "))

            # Window size presets
            self.size_combo = QComboBox()
            self.size_combo.addItems(list(self.WINDOW_PRESETS.keys()))
            self.size_combo.setCurrentText("1024×768")
            self.size_combo.setFixedWidth(130)
            self.size_combo.setStyleSheet("""
                QComboBox {
                    background-color: #27272a;
                    color: #fafafa;
                    border: 1px solid #3f3f46;
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 13px;
                }
            """)
            self.size_combo.currentTextChanged.connect(self._apply_size)
            toolbar.addWidget(self.size_combo)

            # Theme toggle
            self.theme_btn = QPushButton("🌙 Dark")
            self.theme_btn.setCheckable(True)
            self.theme_btn.setFixedWidth(100)
            self.theme_btn.setStyleSheet(self.lang_btn.styleSheet())
            self.theme_btn.clicked.connect(self._toggle_theme)
            toolbar.addWidget(self.theme_btn)

            # --- Status bar ---
            self.status_bar = QStatusBar()
            self.status_bar.setStyleSheet("""
                QStatusBar {
                    background-color: #18181b;
                    color: #a1a1aa;
                    border-top: 1px solid #27272a;
                    font-size: 12px;
                }
            """)
            self.setStatusBar(self.status_bar)

        def _load_tabs(self):
            """Load SymbologyTab and StatsTab with mock data."""
            # Use fully-qualified package path (vnu2f_qlddk68.cadastral_tools.*)
            # so that relative imports like ``from ...modules.ui_utils`` resolve
            # correctly through the package hierarchy.
            plugin_pkg = os.path.basename(PLUGIN_ROOT)  # "vnu2f_qlddk68"
            tab_specs = [
                ("🎨  Ký hiệu (Symbology)", f"{plugin_pkg}.cadastral_tools.ui.symbology_tab", "SymbologyTab"),
                ("📊  Thống kê (Stats)", f"{plugin_pkg}.cadastral_tools.ui.stats_tab", "StatsTab"),
            ]

            for display_name, module_path, class_name in tab_specs:
                try:
                    import importlib
                    mod = importlib.import_module(module_path)
                    TabClass = getattr(mod, class_name)

                    # Construct with MockPluginState
                    tab = TabClass(self._state)

                    # Monkey-patch BEFORE calling populate
                    patch_tab_for_sandbox(tab)
                    tab.populate_layers()

                    self.stack.addWidget(tab)
                    self.tab_list.addItem(display_name)
                    self._tabs.append((display_name, tab))
                    print(f"[Sandbox] ✅ Loaded: {display_name}")

                except Exception as exc:
                    print(f"[Sandbox] ❌ Failed to load {display_name}: {exc}")
                    import traceback
                    traceback.print_exc()

                    # Add a placeholder error widget
                    error_label = QLabel(f"⚠️ Failed to load {class_name}:\n{exc}")
                    error_label.setStyleSheet(
                        "color: #ef4444; padding: 20px; font-size: 14px;"
                    )
                    self.stack.addWidget(error_label)
                    self.tab_list.addItem(f"❌ {display_name}")
                    self._tabs.append((display_name, error_label))

            # Select first tab
            if self.tab_list.count() > 0:
                self.tab_list.setCurrentRow(0)

        def _on_tab_changed(self, index):
            self.stack.setCurrentIndex(index)
            self._update_status()

        def _toggle_language(self, checked):
            os.environ["VNU2F_LANG"] = "en" if checked else "vi"
            self.lang_btn.setText("🌐 EN" if checked else "🌐 VI")
            self._update_status()
            # Note: changing language at runtime requires re-creating tabs
            # since i18n.tr() calls are evaluated at construction time.
            # A full re-render is possible but complex; for sandbox purposes
            # the toggle demonstrates the mechanism.

        def _apply_size(self, text):
            if text in self.WINDOW_PRESETS:
                w, h = self.WINDOW_PRESETS[text]
                self.resize(w, h)
                self._update_status()

        def _toggle_theme(self, checked):
            self.theme_btn.setText("☀️ Light" if checked else "🌙 Dark")
            try:
                from vnu2f_qlddk68.modules.common.ui_utils import get_dialog_stylesheet
                qss = get_dialog_stylesheet()
                # Apply to preview area widgets
                for _, tab in self._tabs:
                    tab.setStyleSheet(qss)
            except Exception as exc:
                print(f"[Sandbox] Theme toggle: {exc}")
            self._update_status()

        def _update_status(self):
            from qgis.PyQt.QtWidgets import QComboBox, QLabel as QL

            current_tab = self.stack.currentWidget()
            if current_tab is None:
                return

            lang = os.environ.get("VNU2F_LANG", "vi")
            w, h = self.width(), self.height()
            n_combo = len(current_tab.findChildren(QComboBox))
            n_label = len(current_tab.findChildren(QL))

            self.status_bar.showMessage(
                f"  📐 {w}×{h}  |  🌐 {lang.upper()}  |  "
                f"ComboBox: {n_combo}  |  Label: {n_label}  |  "
                f"Tabs loaded: {len(self._tabs)}"
            )

    return SandboxWindow()


# ---------------------------------------------------------------------------
# 5. Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    """Initialize headless QGIS, open sandbox window, run event loop."""
    print("=" * 60)
    print("  🔬 VNU2F UI Sandbox — Live Previewer")
    print("  Sử dụng QGIS Headless Core (KHÔNG mock sys.modules)")
    print("=" * 60)

    try:
        qgs = init_headless_qgis()
    except RuntimeError as exc:
        print(f"\n❌ {exc}")
        return 1

    # Pre-import the root plugin package so that the package hierarchy
    # is established in sys.modules BEFORE tabs attempt relative imports
    # like ``from ...modules.ui_utils``.
    plugin_pkg = os.path.basename(PLUGIN_ROOT)
    try:
        import importlib
        importlib.import_module(plugin_pkg)
        print(f"[Sandbox] Plugin package '{plugin_pkg}' loaded.")
    except Exception as exc:
        print(f"[Sandbox] ⚠️ Could not pre-import {plugin_pkg}: {exc}")
        print(f"[Sandbox]    Tabs will fall back to direct imports.")

    try:
        window = _create_sandbox_window()
        window.show()

        print("[Sandbox] Window opened. Close the window to exit.")
        exit_code = qgs.exec()
    except Exception as exc:
        print(f"\n❌ Sandbox error: {exc}")
        import traceback
        traceback.print_exc()
        exit_code = 1
    finally:
        try:
            from qgis.core import QgsApplication
            QgsApplication.exitQgis()
        except Exception:
            pass

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
