# -*- coding: utf-8 -*-
import os
import pytest
import tempfile
from shapely.geometry import Polygon

# Import modules to test
from modules.dxf_engine import read_dxf_data
from modules.report_generator import write_cadastral_report
from modules.cadastral_importer.dossier import scan_sources

try:
    from topology_tools.geometry_validator import validate_and_repair
except ImportError:
    import sys
    sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "tools", "libraries"))
    from topology_tools.geometry_validator import validate_and_repair

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- DXF CAD Parsing Tests ---

def test_dxf_parsing_happy():
    """Verify parsing a valid DXF file if available in scratch, else skip."""
    dxf_sample = os.path.join(PROJECT_ROOT, "scratch", "dc20.dxf")
    if not os.path.exists(dxf_sample):
        pytest.skip("Sample DXF file 'scratch/dc20.dxf' not found")
    
    doc = read_dxf_data(dxf_sample)
    assert "polylines" in doc
    assert "texts" in doc

def test_dxf_parsing_edge():
    """Verify parsing an empty DXF file returns empty dict structures."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.dxf', delete=False) as f:
        f.write("")
        empty_dxf = f.name
    try:
        res = read_dxf_data(empty_dxf)
        assert isinstance(res, dict)
        assert not res.get("polylines")
    finally:
        os.unlink(empty_dxf)

def test_dxf_parsing_fail():
    """Verify parsing non-existent DXF path returns empty structure safely."""
    res = read_dxf_data("non_existent_dxf_file_path.dxf")
    assert isinstance(res, dict)
    assert not res.get("polylines")


# --- Topology Repair Tests ---

def test_topology_repair_happy():
    """Verify repairing a clean polygon returns it as valid."""
    s_poly = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
    repaired = validate_and_repair(s_poly)
    assert repaired['is_valid'] is True

def test_topology_repair_edge():
    """Verify repairing a self-intersecting bowtie polygon resolves self-intersection."""
    bowtie = Polygon([(0, 0), (10, 10), (10, 0), (0, 10), (0, 0)])
    repaired = validate_and_repair(bowtie)
    assert repaired['is_valid'] is True

def test_topology_repair_fail():
    """Verify passing None input handles it gracefully without throwing errors."""
    res = validate_and_repair(None)
    assert isinstance(res, dict)
    assert res["is_valid"] is False


# --- Excel Report Writer Tests ---

def test_excel_report_writer_happy():
    """Verify generating Excel reports from templates."""
    template_path = os.path.join(PROJECT_ROOT, "modules", "report_generator", "templates", "so_muc_ke.xlsx")
    if not os.path.exists(template_path):
        pytest.skip("Excel report template not found")
        
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
        out_excel = f.name
    try:
        data = [
            {
                "soto": "1",
                "sothua": "100",
                "tenchu": "Nguyễn Văn A",
                "diachi": "Xã B",
                "dientich": 150.5,
                "hinhthuc": "Riêng",
                "loaidat": "ONT",
                "thoihan": "Lâu dài",
                "nguongoc": "Nhà nước giao",
                "ghichu": "",
                "doi_tuong": "Gia đình/Cá nhân"
            }
        ]
        success = write_cadastral_report(template_path, out_excel, data, report_type="so_muc_ke")
        assert success is True
        assert os.path.exists(out_excel)
    finally:
        os.unlink(out_excel)

def test_excel_report_writer_edge():
    """Verify writing report with empty data row list completes successfully."""
    template_path = os.path.join(PROJECT_ROOT, "modules", "report_generator", "templates", "so_muc_ke.xlsx")
    if not os.path.exists(template_path):
        pytest.skip("Excel report template not found")
        
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
        out_excel = f.name
    try:
        success = write_cadastral_report(template_path, out_excel, [], report_type="so_dia_chinh")
        assert success is True
    finally:
        os.unlink(out_excel)

def test_excel_report_writer_fail():
    """Verify writing report with invalid template path returns False."""
    success = write_cadastral_report("missing_template_abc.xlsx", "out.xlsx", [])
    assert success is False


# --- Multi-source File Scanner Tests ---

def test_file_scanner_happy():
    """Verify scanning a directory for file grouping works."""
    groups = scan_sources(os.path.join(PROJECT_ROOT, "scratch"))
    assert isinstance(groups, list)

def test_file_scanner_edge():
    """Verify scanning empty folder returns empty list."""
    with tempfile.TemporaryDirectory() as empty_dir:
        groups = scan_sources(empty_dir)
        assert len(groups) == 0

def test_file_scanner_fail():
    """Verify scanning non-existent folder handles it gracefully returning empty list."""
    groups = scan_sources("non_existent_folder_path_xyz")
    assert len(groups) == 0
