"""
QGIS CONSOLE TEST SCRIPT
Copy toàn bộ script này vào QGIS Python Console và chạy.
Kết quả sẽ in ra Console với nhãn PASS/FAIL rõ ràng.
"""
import traceback
from pathlib import Path

results = []

def check(name, fn):
    try:
        fn()
        results.append(f"  ✅ PASS: {name}")
    except Exception as e:
        results.append(f"  ❌ FAIL: {name}\n       {e}\n{traceback.format_exc()}")

# === TEST 1: Import module không crash ===
def t1():
    from modules.dxf_engine import read_dxf_data
    from modules.dxf_engine import decode_tcvn3
    from modules.report_generator import write_cadastral_report
check("Import tất cả module chính", t1)

# === TEST 2: TCVN3 decoder hoạt động ===
def t2():
    from modules.dxf_engine import decode_tcvn3
    result = decode_tcvn3("ABC")
    assert result == "ABC", f"ASCII phải giữ nguyên, got: {result}"
check("TCVN3 decoder — ASCII unchanged", t2)

# === TEST 3: Đọc DXF có polygon không crash ===
def t3():
    fixture = Path(__file__).parent / "fixtures/dxf/simple_polygon.dxf"
    if not fixture.exists():
        raise FileNotFoundError(f"Chạy create_test_dxf.py trước: {fixture}")
    from modules.dxf_engine import read_dxf_data
    result = read_dxf_data(str(fixture))
    assert result is not None, "read_dxf_data trả None — lỗi đọc file"
check("DXF reader — đọc polygon không crash", t3)

# === TEST 4: Đọc DXF có TCVN3 text ===
def t4():
    fixture = Path(__file__).parent / "fixtures/dxf/tcvn3_text.dxf"
    if not fixture.exists():
        raise FileNotFoundError(f"Chạy create_test_dxf.py trước: {fixture}")
    from modules.dxf_engine import read_dxf_data
    result = read_dxf_data(str(fixture))
    # Text không được là raw byte TCVN3
    if result and hasattr(result, '__iter__'):
        for item in result:
            if isinstance(item, dict) and "text" in item:
                assert "\xf0" not in str(item["text"]), \
                    "Text vẫn còn byte TCVN3 — decoder chưa hoạt động"
check("DXF reader — TCVN3 text được decode", t4)

# === TEST 5: CRS warning khi USER: code ===
def t5():
    content = Path("modules/webgis_launcher.py").read_text(encoding="utf-8")
    assert 'startswith("USER:")' in content, \
        "webgis_launcher.py thiếu check USER: CRS"
check("WebGIS — có warning khi CRS là USER:", t5)

# === TEST 6: report_tab tính area từ geometry ===
def t6():
    content = Path("modules/crs_converter/tabs/report_tab.py").read_text(encoding="utf-8")
    assert "geom.area()" in content, \
        "report_tab.py chưa tính area từ geometry"
check("Report tab — tính area từ geometry thực tế", t6)

# === IN KẾT QUẢ ===
print("\n" + "="*50)
print("QGIS PLUGIN TEST RESULTS")
print("="*50)
for r in results:
    print(r)
passed = sum(1 for r in results if "PASS" in r)
failed = sum(1 for r in results if "FAIL" in r)
print(f"\nTổng: {passed} PASS / {failed} FAIL / {len(results)} tests")
if failed == 0:
    print("✅ Plugin sẵn sàng test thủ công trong QGIS UI")
else:
    print("❌ Có lỗi cần xem lại trước khi test UI")
print("="*50)
