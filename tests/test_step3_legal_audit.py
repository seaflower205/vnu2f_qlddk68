from datetime import date
import pytest
from qgis.core import QgsGeometry

from cadastral_tools.ai.qa_runner import LayerSnapshot, FeatureSnapshot
from cadastral_tools.ai.legal_resolver import LegalContext
from cadastral_tools.ai.step3_legal_audit import (
    run_legal_audit_checks,
    check_duplicate_parcel_numbers,
    check_minimum_area,
)

# Helper function to create FeatureSnapshot
def make_feature(fid, wkt, attrs):
    geom = QgsGeometry.fromWkt(wkt) if wkt else QgsGeometry()
    return FeatureSnapshot(
        fid=fid,
        wkb=geom.asWkb() if not geom.isNull() else b"",
        bbox=(0, 0, 1, 1) if not geom.isNull() else None,
        attrs=attrs,
    )

@pytest.fixture
def legal_ctx():
    return LegalContext(mode="current_law", as_of_date=date(2026, 1, 1))

def test_case_1_duplicate_diff_commune(legal_ctx):
    # Trùng tờ/thửa nhưng khác xã -> KHÔNG duplicate
    # 00002 doesn't exist in seed data, so it gets DUP-002 instead. Still, no DUP-001.
    feat1 = make_feature(1, "Polygon ((0 0, 10 0, 10 10, 0 10, 0 0))", {"MaDVHC": "00001", "SoTo": 10, "SoThua": 25})
    feat2 = make_feature(2, "Polygon ((20 0, 30 0, 30 10, 20 10, 20 0))", {"MaDVHC": "00002", "SoTo": 10, "SoThua": 25})
    snapshot = LayerSnapshot("layer1", "Layer 1", "EPSG:3405", ["MaDVHC", "SoTo", "SoThua"], [feat1, feat2], "")
    
    issues, _ = check_duplicate_parcel_numbers(snapshot, legal_ctx)
    assert not any(i.rule_id == "DUP-001" for i in issues)

def test_case_2_duplicate_same_commune(legal_ctx):
    # Trùng tờ/thửa cùng xã -> ERROR duplicate
    feat1 = make_feature(1, "Polygon ((0 0, 10 0, 10 10, 0 10, 0 0))", {"MaDVHC": "00001", "SoTo": 10, "SoThua": 25})
    feat2 = make_feature(2, "Polygon ((20 0, 30 0, 30 10, 20 10, 20 0))", {"MaDVHC": "00001", "SoTo": 10, "SoThua": 25})
    snapshot = LayerSnapshot("layer1", "Layer 1", "EPSG:3405", ["MaDVHC", "SoTo", "SoThua"], [feat1, feat2], "")
    
    issues, _ = check_duplicate_parcel_numbers(snapshot, legal_ctx)
    assert len(issues) == 2
    assert all(i.rule_id == "DUP-001" and i.severity == "ERROR" for i in issues)

def test_case_3_multiple_communes_in_layer(legal_ctx):
    # Đa ĐVHC xử lý độc lập
    feat1 = make_feature(1, None, {"MaDVHC": "00001", "SoTo": 1, "SoThua": 1})
    feat2 = make_feature(2, None, {"MaDVHC": "00001", "SoTo": 1, "SoThua": 1})
    # 00002 will get DUP-002, so total DUP-001 is 2, DUP-002 is 2
    feat3 = make_feature(3, None, {"MaDVHC": "00002", "SoTo": 1, "SoThua": 1})
    feat4 = make_feature(4, None, {"MaDVHC": "00002", "SoTo": 1, "SoThua": 1})
    snapshot = LayerSnapshot("layer1", "Layer 1", "EPSG:3405", ["MaDVHC", "SoTo", "SoThua"], [feat1, feat2, feat3, feat4], "")
    
    issues, _ = check_duplicate_parcel_numbers(snapshot, legal_ctx)
    assert sum(1 for i in issues if i.rule_id == "DUP-001") == 2
    assert sum(1 for i in issues if i.rule_id == "DUP-002") == 2

def test_case_4_leading_zero(legal_ctx):
    # Default province code "1" normalizes to "01"
    feat1 = make_feature(1, "Polygon ((0 0, 3 0, 3 3, 0 3, 0 0))", {"LoaiDat": "ODT"}) # 9 m2
    snapshot = LayerSnapshot("layer1", "Layer 1", "EPSG:3405", ["LoaiDat"], [feat1], "")
    
    issues, _ = check_minimum_area(snapshot, legal_ctx, "kiem_tra_hien_trang", default_province_code="1")
    print("ISSUES:", issues)
    min_area_issues = [i for i in issues if i.rule_id == "MINAREA-001"]
    assert len(min_area_issues) == 1
    assert "01" in min_area_issues[0].description or "mức tối thiểu" in min_area_issues[0].description

def test_case_5_missing_madvhc(legal_ctx):
    # Missing MaDVHC -> WARNING, no false positive duplicate
    feat1 = make_feature(1, None, {"SoTo": 1, "SoThua": 1})
    feat2 = make_feature(2, None, {"SoTo": 1, "SoThua": 1})
    snapshot = LayerSnapshot("layer1", "Layer 1", "EPSG:3405", ["SoTo", "SoThua"], [feat1, feat2], "")
    
    issues, _ = check_duplicate_parcel_numbers(snapshot, legal_ctx)
    errs = [i for i in issues if i.rule_id == "DUP-001"]
    warns = [i for i in issues if i.rule_id == "DUP-002"]
    assert len(errs) == 0
    assert len(warns) == 2

def test_case_7_no_madvhc_no_default_min_area(legal_ctx):
    # No MaDVHC + No Default -> WARNING MINAREA-002
    feat1 = make_feature(1, "Polygon ((0 0, 10 0, 10 10, 0 10, 0 0))", {"LoaiDat": "ODT"})
    snapshot = LayerSnapshot("layer1", "Layer 1", "EPSG:3405", ["LoaiDat"], [feat1], "")
    
    issues, _ = check_minimum_area(snapshot, legal_ctx, "kiem_tra_hien_trang")
    assert any(i.rule_id == "MINAREA-002" for i in issues)

def test_case_8_mock_rule_fallback(legal_ctx):
    # Mock Rule Fallback -> WARNING with "MOCK/UNVERIFIED"
    feat1 = make_feature(1, "Polygon ((0 0, 3 0, 3 3, 0 3, 0 0))", {"MaDVHC": "01", "LoaiDat": "ODT"}) # 9m2
    snapshot = LayerSnapshot("layer1", "Layer 1", "EPSG:3405", ["MaDVHC", "LoaiDat"], [feat1], "")
    
    issues, _ = check_minimum_area(snapshot, legal_ctx, "kiem_tra_hien_trang")
    assert len(issues) == 1
    assert "MOCK" in issues[0].description.upper() or "UNVERIFIED" in issues[0].description.upper()
    assert issues[0].severity == "WARNING"

def test_case_9_kiem_tra_hien_trang_always_warning(legal_ctx):
    # Always WARNING for min area
    feat1 = make_feature(1, "Polygon ((0 0, 3 0, 3 3, 0 3, 0 0))", {"MaDVHC": "01", "LoaiDat": "ODT"})
    snapshot = LayerSnapshot("layer1", "Layer 1", "EPSG:3405", ["MaDVHC", "LoaiDat"], [feat1], "")
    
    issues, _ = check_minimum_area(snapshot, legal_ctx, "tach_thua")
    assert len(issues) == 1
    assert issues[0].severity == "WARNING"

def test_case_10_mixed_land_types(legal_ctx):
    # ODT and ONT resolved independently
    feat1 = make_feature(1, "Polygon ((0 0, 4 0, 4 4, 0 4, 0 0))", {"MaDVHC": "01", "LoaiDat": "ODT"}) # 16m2 < 30
    feat2 = make_feature(2, "Polygon ((0 0, 8 0, 8 8, 0 8, 0 0))", {"MaDVHC": "01", "LoaiDat": "ONT"}) # 64m2 >= 60 (NO WARNING)
    snapshot = LayerSnapshot("layer1", "Layer 1", "EPSG:3405", ["MaDVHC", "LoaiDat"], [feat1, feat2], "")
    
    issues, _ = check_minimum_area(snapshot, legal_ctx, "kiem_tra_hien_trang")
    min_area_issues = [i for i in issues if i.rule_id == "MINAREA-001"]
    assert len(min_area_issues) == 1
    assert min_area_issues[0].feature_id == 1

def test_case_13a_default_commune_duplicate(legal_ctx):
    # 13a. Default commune code handles missing MaDVHC
    feat1 = make_feature(1, None, {"SoTo": 1, "SoThua": 1})
    feat2 = make_feature(2, None, {"SoTo": 1, "SoThua": 1})
    snapshot = LayerSnapshot("layer1", "Layer 1", "EPSG:3405", ["SoTo", "SoThua"], [feat1, feat2], "")
    
    issues, _ = check_duplicate_parcel_numbers(snapshot, legal_ctx, default_commune_code="00001")
    assert len(issues) == 2
    assert all(i.rule_id == "DUP-001" for i in issues)
    assert all("default commune code used" in i.description for i in issues)

def test_case_13b_default_province_duplicate(legal_ctx):
    # 13b. Default province code does NOT help with duplicate (requires commune)
    feat1 = make_feature(1, None, {"SoTo": 1, "SoThua": 1})
    feat2 = make_feature(2, None, {"SoTo": 1, "SoThua": 1})
    snapshot = LayerSnapshot("layer1", "Layer 1", "EPSG:3405", ["SoTo", "SoThua"], [feat1, feat2], "")
    
    issues, _ = check_duplicate_parcel_numbers(snapshot, legal_ctx, default_commune_code=None)
    assert not any(i.rule_id == "DUP-001" for i in issues)
    assert sum(1 for i in issues if i.rule_id == "DUP-002") == 2

def test_case_15_invalid_geometry_area_guard(legal_ctx):
    # Invalid geometry -> no min area check
    wkt = "Polygon ((0 0, 10 10, 10 0, 0 10, 0 0))" 
    feat1 = make_feature(1, wkt, {"MaDVHC": "01", "LoaiDat": "ODT"})
    snapshot = LayerSnapshot("layer1", "Layer 1", "EPSG:3405", ["MaDVHC", "LoaiDat"], [feat1], "")
    
    issues, _ = check_minimum_area(snapshot, legal_ctx, "kiem_tra_hien_trang")
    assert len(issues) == 0

def test_case_17_min_area_with_default_province(legal_ctx):
    # Default province works for min area
    feat1 = make_feature(1, "Polygon ((0 0, 3 0, 3 3, 0 3, 0 0))", {"LoaiDat": "ODT"}) # 9m2
    snapshot = LayerSnapshot("layer1", "Layer 1", "EPSG:3405", ["LoaiDat"], [feat1], "")
    
    issues, _ = check_minimum_area(snapshot, legal_ctx, "kiem_tra_hien_trang", default_province_code="01")
    min_area_issues = [i for i in issues if i.rule_id == "MINAREA-001"]
    assert len(min_area_issues) == 1

def test_case_18_min_area_with_default_commune(legal_ctx):
    # Default commune works for min area (resolves to province)
    feat1 = make_feature(1, "Polygon ((0 0, 3 0, 3 3, 0 3, 0 0))", {"LoaiDat": "ODT"}) # 9m2
    snapshot = LayerSnapshot("layer1", "Layer 1", "EPSG:3405", ["LoaiDat"], [feat1], "")
    
    issues, _ = check_minimum_area(snapshot, legal_ctx, "kiem_tra_hien_trang", default_commune_code="00001")
    min_area_issues = [i for i in issues if i.rule_id == "MINAREA-001"]
    assert len(min_area_issues) == 1

def test_case_19_madvhc_is_province(legal_ctx):
    # Feature MaDVHC="01" (Province) -> WARNING not commune, NO duplicate error
    feat1 = make_feature(1, None, {"MaDVHC": "01", "SoTo": 1, "SoThua": 1})
    feat2 = make_feature(2, None, {"MaDVHC": "01", "SoTo": 1, "SoThua": 1})
    snapshot = LayerSnapshot("layer1", "Layer 1", "EPSG:3405", ["MaDVHC", "SoTo", "SoThua"], [feat1, feat2], "")
    
    issues, _ = check_duplicate_parcel_numbers(snapshot, legal_ctx)
    assert not any(i.rule_id == "DUP-001" for i in issues)
    assert sum(1 for i in issues if i.rule_id == "DUP-002") == 2

def test_case_20_madvhc_is_district(legal_ctx):
    # Feature MaDVHC="001" (District) -> WARNING not commune, NO duplicate error
    feat1 = make_feature(1, None, {"MaDVHC": "001", "SoTo": 1, "SoThua": 1})
    feat2 = make_feature(2, None, {"MaDVHC": "001", "SoTo": 1, "SoThua": 1})
    snapshot = LayerSnapshot("layer1", "Layer 1", "EPSG:3405", ["MaDVHC", "SoTo", "SoThua"], [feat1, feat2], "")
    
    issues, _ = check_duplicate_parcel_numbers(snapshot, legal_ctx)
    assert not any(i.rule_id == "DUP-001" for i in issues)
    assert sum(1 for i in issues if i.rule_id == "DUP-002") == 2
