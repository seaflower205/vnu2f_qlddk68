"""Test logic excel_writer không liên quan QGIS."""
import inspect
from pathlib import Path

def test_permission_error_handler_exists():
    """Đảm bảo FIX #4 đã áp dụng — có except PermissionError riêng."""
    content = Path("modules/report_generator/excel_writer.py").read_text(encoding="utf-8")
    assert "PermissionError" in content, \
        "excel_writer.py thiếu handler PermissionError — FIX #4 chưa áp dụng"
    assert "QMessageBox" in content, \
        "excel_writer.py thiếu QMessageBox import — FIX #4 chưa áp dụng"

def test_no_bare_except_pass():
    """Không còn except bare pass (FIX #3)."""
    files = [
        "modules/dxf_engine/dxf_reader.py",
        "modules/dxf_engine/dxf_block_extractor.py",
        "modules/report_generator/excel_writer.py",
    ]
    for filepath in files:
        content = Path(filepath).read_text(encoding="utf-8")
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped in ("except Exception: pass", "except: pass"):
                assert False, \
                    f"{filepath} dòng {i}: còn bare except pass — FIX #3 chưa hoàn chỉnh"

def test_geometry_area_override_in_report_tab():
    """Đảm bảo FIX #2 đã áp dụng — tính area từ geometry."""
    content = Path("modules/crs_converter/tabs/report_tab.py").read_text(encoding="utf-8")
    assert "geom.area()" in content, \
        "report_tab.py thiếu geom.area() — FIX #2 chưa áp dụng"
    assert "fallback" in content.lower() or "isNull" in content, \
        "report_tab.py thiếu fallback khi geometry rỗng"
