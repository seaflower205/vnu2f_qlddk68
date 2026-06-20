"""Kiểm tra map.js có chứa VN land mapping sau FIX #8."""
from pathlib import Path

def test_vn_land_map_exists_in_mapjs():
    content = Path("webgis_demo/js/map/map.js").read_text(encoding="utf-8")
    assert "VN_LAND_KIND_MAP" in content, \
        "map.js thiếu VN_LAND_KIND_MAP — FIX #8 chưa áp dụng"

def test_vn_land_map_has_key_codes():
    content = Path("webgis_demo/js/map/map.js").read_text(encoding="utf-8")
    for code in ["ONT", "CLN", "TMD", "DGD", "SKC"]:
        assert f"'{code}'" in content or f'"{code}"' in content, \
            f"Thiếu mã đất '{code}' trong VN_LAND_KIND_MAP"

def test_normalized_kind_used():
    content = Path("webgis_demo/js/map/map.js").read_text(encoding="utf-8")
    assert "normalizedKind" in content, \
        "normalizedKind chưa được dùng trong map.js"
