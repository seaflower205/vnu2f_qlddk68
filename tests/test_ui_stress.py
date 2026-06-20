# -*- coding: utf-8 -*-
import sys
import time
from qgis.PyQt.QtWidgets import QApplication

def get_memory_usage():
    """Returns the current process RSS memory in bytes without external dependencies."""
    if sys.platform == 'win32':
        try:
            import ctypes
            from ctypes import wintypes
            class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]
            process = ctypes.windll.kernel32.GetCurrentProcess()
            counters = PROCESS_MEMORY_COUNTERS()
            counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
            if ctypes.windll.psapi.GetProcessMemoryInfo(process, ctypes.byref(counters), counters.cb):
                return counters.WorkingSetSize
        except Exception:
            pass
    else:
        try:
            with open('/proc/self/status', 'r') as f:
                for line in f:
                    if line.startswith('VmRSS:'):
                        return int(line.split()[1]) * 1024
        except Exception:
            pass
    return 0

def test_crs_dialog_tab_stress(qgis_app):
    """Stress test tab switching for CRSConverterDialog."""
    from modules.crs_converter.crs_dialog import CRSConverterDialog
    dialog = CRSConverterDialog()
    dialog.show()
    QApplication.processEvents()

    tab_count = dialog.sidebar.count()
    assert tab_count > 0

    mem_before = get_memory_usage()
    start_time = time.perf_counter()

    for i in range(50):
        dialog.sidebar.setCurrentRow(i % tab_count)
        QApplication.processEvents()
        time.sleep(0.01)

    duration = (time.perf_counter() - start_time) * 1000
    mem_after = get_memory_usage()
    mem_diff = mem_after - mem_before

    print(f"\n[STRESS] CRS Dialog: {duration:.2f} ms total, {duration/50:.2f} ms/switch, RAM delta: {mem_diff/1024:.2f} KB")
    dialog.close()

def test_cadastral_dialog_tab_stress(qgis_app):
    """Stress test tab switching for CadastralImportDialog."""
    from modules.cadastral_importer.dialog import CadastralImportDialog
    dialog = CadastralImportDialog()
    dialog.show()
    QApplication.processEvents()

    tab_count = dialog.tabs.count()
    assert tab_count > 0

    mem_before = get_memory_usage()
    start_time = time.perf_counter()

    for i in range(50):
        dialog.tabs.setCurrentIndex(i % tab_count)
        QApplication.processEvents()
        time.sleep(0.01)

    duration = (time.perf_counter() - start_time) * 1000
    mem_after = get_memory_usage()
    mem_diff = mem_after - mem_before

    print(f"\n[STRESS] Cadastral Dialog: {duration:.2f} ms total, {duration/50:.2f} ms/switch, RAM delta: {mem_diff/1024:.2f} KB")
    dialog.close()


def test_stats_tab_coalesces_rapid_refresh_requests(qgis_app, qtbot):
    """Field/tab signals must share one single-shot refresh window."""
    from cadastral_tools.core.plugin_state import PluginState
    from cadastral_tools.ui.stats_tab import StatsTab

    tab = StatsTab(PluginState())
    qtbot.addWidget(tab)
    tab._refresh_timer.stop()

    for _ in range(10):
        tab.trigger_refresh()

    assert tab._refresh_timer.isSingleShot()
    assert tab._refresh_timer.interval() == 180
    assert tab._refresh_timer.isActive()
    tab.cleanup()
    assert not tab._refresh_timer.isActive()


def test_stats_tab_does_not_recompute_cached_data_on_show(qgis_app, qtbot):
    """Switching back to a populated Stats tab must not rescan the layer."""
    from unittest.mock import MagicMock

    from cadastral_tools.core.plugin_state import PluginState
    from cadastral_tools.ui.stats_tab import StatsTab

    tab = StatsTab(PluginState())
    qtbot.addWidget(tab)
    tab._refresh_timer.stop()
    tab.stats_data = [{"code": "ONT"}]
    tab.trigger_refresh = MagicMock()

    tab.showEvent(None)

    tab.trigger_refresh.assert_not_called()
    tab.cleanup()


def test_stats_tab_defers_refresh_when_hidden(qgis_app, qtbot):
    """When StatsTab is hidden, trigger_refresh should start the timer, but _start_refresh_task should defer execution."""
    from unittest.mock import MagicMock

    from cadastral_tools.core.plugin_state import PluginState
    from cadastral_tools.ui.stats_tab import StatsTab

    tab = StatsTab(PluginState())
    qtbot.addWidget(tab)

    # Force hidden state
    tab.setVisible(False)

    # Clear any pending flags or tasks
    tab._refresh_pending = False
    tab.stats_data = [{"code": "ONT"}]  # pretend we have some old data

    # Trigger refresh
    tab.trigger_refresh()
    assert tab._refresh_timer.isActive()

    # Directly invoke _start_refresh_task (simulating timer timeout)
    tab._start_refresh_task()

    # Since it is hidden, it should defer
    assert tab._refresh_pending is True
    assert tab.current_task is None

    # Simulate the lifecycle callback directly so the test does not depend on
    # whether an unparented Qt widget receives a native show event.
    tab.trigger_refresh = MagicMock()
    tab.showEvent(None)

    # It should have triggered a refresh because of the pending flag
    tab.trigger_refresh.assert_called_once()
    assert tab._refresh_pending is False

    tab.cleanup()
