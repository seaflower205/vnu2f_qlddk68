# -*- coding: utf-8 -*-
import os
import tempfile
import pytest

from modules.cadastral_importer.xml_exchange_connector import (
    parse_exchange_xml
)
from modules.cadastral_importer.tolerance_checker import (
    get_ms_by_scale,
    calculate_max_area_tolerance,
    check_area_tolerance
)
from modules.cadastral_importer.sync_importer import (
    _make_sync_index,
    _match_sync
)

# --- XML Parser and Exporter Tests ---

def test_xml_exchange_happy():
    """Verify parsing a valid cadastral XML file based on mapping."""
    xml_content = """<?xml version="1.0" encoding="utf-8"?>
    <CadastralData>
      <ThuaDat>
        <soHieuToBanDo>10</soHieuToBanDo>
        <soThuTuThua>25</soThuTuThua>
        <dienTich>120.5</dienTich>
        <hoTen>Nguyễn Văn Hùng</hoTen>
        <diaChi>Hà Nội</diaChi>
        <loaiMucDichSuDungKiemKeId>ODT</loaiMucDichSuDungKiemKeId>
      </ThuaDat>
      <ThuaDat soHieuToBanDo="10" soThuTuThua="26" dienTich="95.2" hoTen="Phạm Văn Đồng" diaChi="Hải Phòng" loaiMucDichSuDungKiemKeId="LUA" />
    </CadastralData>
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
        f.write(xml_content)
        temp_xml = f.name

    try:
        summary = parse_exchange_xml(temp_xml)
        assert summary.parcel_count == 2
        assert len(summary.records) == 2
        
        # Test record 1 (nested tag fields)
        rec1 = summary.records[0]
        assert rec1["so_hieu_to_ban_do"] == 10
        assert rec1["so_thu_tu_thua"] == 25
        assert rec1["dien_tich"] == 120.5
        assert rec1["chu_su_dung"] == "Nguyễn Văn Hùng"
        assert rec1["dia_chi"] == "Hà Nội"
        assert rec1["loai_dat"] == "ODT"

        # Test record 2 (attribute fields)
        rec2 = summary.records[1]
        assert rec2["so_hieu_to_ban_do"] == 10
        assert rec2["so_thu_tu_thua"] == 26
        assert rec2["dien_tich"] == 95.2
        assert rec2["chu_su_dung"] == "Phạm Văn Đồng"
        assert rec2["dia_chi"] == "Hải Phòng"
        assert rec2["loai_dat"] == "LUA"
    finally:
        os.unlink(temp_xml)

def test_xml_exchange_edge():
    """Verify parsing empty or mismatched XML format returns empty list gracefully."""
    xml_content = """<?xml version="1.0" encoding="utf-8"?>
    <CadastralData>
      <OtherTag>
        <someField>123</someField>
      </OtherTag>
    </CadastralData>
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
        f.write(xml_content)
        temp_xml = f.name

    try:
        summary = parse_exchange_xml(temp_xml)
        assert summary.parcel_count == 0
        assert len(summary.records) == 0
    finally:
        os.unlink(temp_xml)

def test_xml_exchange_fail():
    """Verify parsing non-existent XML file path throws FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        parse_exchange_xml("non_existent_file_path_123.xml")

# --- Area Tolerance Checker Tests (Circular 25/2014/TT-BTNMT) ---

def test_tolerance_checker_ms():
    """Verify ms mappings match Circular 25/2014/TT-BTNMT Article 7."""
    assert get_ms_by_scale(500) == 0.10
    assert get_ms_by_scale(1000) == 0.20
    assert get_ms_by_scale(2000) == 0.30
    assert get_ms_by_scale(5000) == 0.80
    assert get_ms_by_scale(10000) == 1.50

def test_tolerance_checker_calc():
    """Verify limit calculation formula: Delta_P = 2 * ms * sqrt(P)."""
    # area = 100m2, scale = 1000 -> ms = 0.20
    # Delta_P = 2 * 0.20 * sqrt(100) = 0.40 * 10 = 4.0 m2
    limit = calculate_max_area_tolerance(100.0, 1000)
    assert abs(limit - 4.0) < 1e-7

    # area <= 0
    assert calculate_max_area_tolerance(0.0, 1000) == 0.0
    assert calculate_max_area_tolerance(-50.0, 1000) == 0.0

def test_tolerance_checker_check():
    """Verify check_area_tolerance returns correct status and values."""
    # Within tolerance
    res = check_area_tolerance(101.5, 100.0, 1000)
    assert res["status"] == "OK"
    assert res["diff"] == 1.5
    assert res["max_tolerance"] == 4.03 # 2 * 0.2 * sqrt(101.5) ~= 4.03
    
    # Exceeds tolerance
    res2 = check_area_tolerance(105.0, 100.0, 1000)
    assert res2["status"] == "WARNING"
    assert res2["diff"] == 5.0

# --- Sync Importer Integration Tests ---

def test_sync_index_matching_xml():
    """Verify indexing and matching features from XML works correctly."""
    xml_records = [
        {
            "source": "XML",
            "sheet": 5,
            "parcel": 42,
            "area": 120.0,
            "owner": "Chủ XML",
            "address": "Địa chỉ XML",
            "land_use": "CLN"
        }
    ]
    
    index = _make_sync_index([], [], [], xml_records)
    assert "xml_by_sheet_parcel" in index
    assert (5, 42) in index["xml_by_sheet_parcel"]
    
    # Test matching
    candidate = {
        "sheet": 5,
        "parcel": 42,
        "area": 120.0
    }
    sync = _match_sync(candidate, index)
    assert sync["xml"] is not None
    assert sync["xml"]["owner"] == "Chủ XML"
    assert sync["xml"]["land_use"] == "CLN"

def test_xml_exchange_with_geometry():
    """Verify parsing geometry from the XML fixture and testing tolerance check on them."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    fixture_path = os.path.join(current_dir, "fixtures", "test_exchange.xml")
    
    summary = parse_exchange_xml(fixture_path)
    assert summary.parcel_count == 3
    
    # Verify coordinates of parcel 101
    rec1 = summary.records[0]
    assert rec1["so_thu_tu_thua"] == 101
    assert "hinh_hoc" in rec1
    assert len(rec1["hinh_hoc"]) == 5
    assert rec1["hinh_hoc"][0] == {"x": 0.0, "y": 0.0}
    assert rec1["hinh_hoc"][2] == {"x": 10.0, "y": 10.0}

    # Verify tolerance checking for parcel 103 (WARNING)
    geom_area = 100.0
    doc_area = rec1["dien_tich"] # 100.0
    res1 = check_area_tolerance(geom_area, doc_area, 500)
    assert res1["status"] == "OK"
    
    rec3 = summary.records[2]
    assert rec3["so_thu_tu_thua"] == 103
    doc_area_3 = rec3["dien_tich"] # 105.0
    res3 = check_area_tolerance(geom_area, doc_area_3, 500)
    assert res3["status"] == "WARNING"
