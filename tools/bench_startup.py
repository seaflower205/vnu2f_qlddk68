# -*- coding: utf-8 -*-
import sys
import time

def measure_import(module_name):
    # Force reload by clearing from sys.modules
    if module_name in sys.modules:
        del sys.modules[module_name]
    
    start = time.perf_counter()
    try:
        __import__(module_name)
        end = time.perf_counter()
        return (end - start) * 1000  # in ms
    except Exception as e:
        return f"Error: {e}"

# 1. Measure heavy libraries
heavy_libs = ["ezdxf", "openpyxl", "shapely", "pandas"]
print("=== HEAVY LIBRARIES LOAD TIME (BEFORE LAZY IMPORT) ===")
total_heavy = 0.0
for lib in heavy_libs:
    t = measure_import(lib)
    if isinstance(t, float):
        print(f"- {lib}: {t:.2f} ms")
        total_heavy += t
    else:
        print(f"- {lib}: {t}")

# 2. Measure plugin core modules (utilizing lazy loading now)
plugin_modules = [
    "cadastral_tools.core.symbology_manager",
    "cadastral_tools.core.label_manager",
    "cadastral_tools.core.stats_manager",
    "cadastral_tools.core.import_export_manager",
    "modules.common.ui_utils",
    "vnu2f_qlddk68"
]

print("\n=== PLUGIN CORE LOAD TIME (WITH LAZY IMPORT ACTIVE) ===")
total_lazy = 0.0
for mod in plugin_modules:
    t = measure_import(mod)
    if isinstance(t, float):
        print(f"- {mod}: {t:.2f} ms")
        total_lazy += t
    else:
        print(f"- {mod}: {t}")

print("\n=== STARTUP BENCHMARK SUMMARY ===")
print(f"Total Heavy Libraries Overhead: {total_heavy:.2f} ms")
print(f"Total Plugin Core Startup Time: {total_lazy:.2f} ms")
if total_heavy > 0 and total_lazy > 0:
    overhead_saved = (total_heavy / (total_heavy + total_lazy)) * 100
    print(f"Estimated Startup Overhead Saved: {overhead_saved:.1f}%")
