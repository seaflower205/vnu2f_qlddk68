# -*- coding: utf-8 -*-
"""
Unit tests for the polygonizer module of topology-tools.
"""

import pytest
from shapely.geometry import LineString, Polygon, Point
from topology_tools.polygonizer import create_polygons, assign_labels

def test_create_polygons_closed_box():
    """Should successfully polygonize lines that form a closed loop."""
    lines = [
        LineString([(0, 0), (10, 0)]),
        LineString([(10, 0), (10, 10)]),
        LineString([(10, 10), (0, 10)]),
        LineString([(0, 10), (0, 0)])
    ]
    polys = create_polygons(lines)
    assert len(polys) == 1
    assert isinstance(polys[0], Polygon)
    assert polys[0].area == 100.0

def test_create_polygons_open_lines():
    """Should return no polygons if the lines do not form a closed loop."""
    lines = [
        LineString([(0, 0), (10, 0)]),
        LineString([(10, 0), (10, 10)]),
        LineString([(10, 10), (5, 10)])  # Gap between (5,10) and (0,0)
    ]
    polys = create_polygons(lines)
    assert len(polys) == 0

def test_assign_labels_happy_path(label_points):
    """Should assign matching attributes to polygons containing the label points (Shapely fallback)."""
    poly_a = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])  # Contains Point(5, 5)
    poly_b = Polygon([(10, 0), (20, 0), (20, 10), (10, 10), (10, 0)])  # Contains Point(15, 5)

    results = assign_labels([poly_a, poly_b], label_points, cad_reader_path=None, require_cad_reader=False)
    assert len(results) == 2

    # Check poly_a attributes
    assert results[0]['attributes']['SOTHUA'] == "100"
    assert results[0]['attributes']['LOAIDAT'] == "ONT"

    # Check poly_b attributes
    assert results[1]['attributes']['SOTHUA'] == "101"
    assert results[1]['attributes']['LOAIDAT'] == "LUC"

def test_assign_labels_no_match():
    """Should assign default fallback attributes when no label points are inside a polygon."""
    poly = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
    empty_label = {"geometry": Point(25, 25), "attributes": {"SOTHUA": "99"}}  # Outside

    results = assign_labels([poly], [empty_label], cad_reader_path=None, require_cad_reader=False)
    assert len(results) == 1
    assert results[0]['attributes']['SOTHUA'] == ""
    assert results[0]['attributes']['_warning'] in ("No labels assigned to this polygon", "Thửa chưa gán nhãn")

def test_assign_labels_multiple_matches():
    """Should resolve to the closest label when multiple points lie inside the same polygon."""
    poly = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])  # Centroid at (5,5)
    
    # Point A is closer to centroid than Point B
    pt_a = {"geometry": Point(5.1, 5.1), "attributes": {"SOTHUA": "100-A"}}
    pt_b = {"geometry": Point(1.0, 1.0), "attributes": {"SOTHUA": "100-B"}}

    results = assign_labels([poly], [pt_a, pt_b], cad_reader_path=None, require_cad_reader=False)
    assert len(results) == 1
    assert results[0]['attributes']['SOTHUA'] == "100-A"  # Point A wins
    warning = results[0]['attributes']['_warning']
    assert "Found 2 overlapping labels" in warning or "Phát hiện trùng 2 nhãn" in warning

def test_assign_labels_require_cad_reader_error(monkeypatch):
    """Should raise a RuntimeError when require_cad_reader is True but no path is resolved."""
    poly = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
    import topology_tools.polygonizer as p
    monkeypatch.setattr(p, "_find_cad_reader", lambda *args: None)
    with pytest.raises(RuntimeError) as excinfo:
        assign_labels([poly], [], require_cad_reader=True)
    assert "no valid cad_reader binary was resolved" in str(excinfo.value)

def test_assign_labels_require_cad_reader_invalid_path():
    """Should raise a RuntimeError when require_cad_reader is True and the path is invalid."""
    poly = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
    with pytest.raises(RuntimeError) as excinfo:
        assign_labels([poly], [], cad_reader_path="nonexistent_binary.exe", require_cad_reader=True)
    assert "resolved cad_reader path does not exist" in str(excinfo.value)

def test_assign_labels_with_mocked_cad_reader(monkeypatch, tmp_path):
    """Should call the external cad_reader executable and read the output JSON correctly when mocked."""
    poly = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
    label = {"geometry": Point(5, 5), "attributes": {"SOTHUA": "102"}}

    # Create a fake executable file so os.path.exists passes
    fake_exe = tmp_path / "fake_cad_reader.exe"
    fake_exe.write_text("dummy binary content")

    import subprocess
    def mock_run(cmd, *args, **kwargs):
        # cmd: [exe, "topology-join", "--polygons", poly_in, "--labels", label_in, "--output", output_path]
        output_file_path = cmd[7]
        # Write dummy output data in expected JSON format
        output_data = [{
            "shell": [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0), (0.0, 0.0)],
            "holes": [],
            "attributes": {"SOTHUA": "102", "DIENTICH_HP": 100.0}
        }]
        with open(output_file_path, "w", encoding="utf-8") as f:
            import json
            json.dump(output_data, f)
        
        # Return a mock CompletedProcess
        class MockCompletedProcess:
            returncode = 0
            stdout = "success"
            stderr = ""
        return MockCompletedProcess()

    monkeypatch.setattr(subprocess, "run", mock_run)

    results = assign_labels([poly], [label], cad_reader_path=str(fake_exe), require_cad_reader=True)
    assert len(results) == 1
    assert results[0]['attributes']['SOTHUA'] == "102"
    assert isinstance(results[0]['geometry'], Polygon)
    assert results[0]['geometry'].area == 100.0

def test_assign_labels_chunked(label_points):
    """Should assign matching attributes correctly even when point geometries are queried in small chunks."""
    poly_a = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
    poly_b = Polygon([(10, 0), (20, 0), (20, 10), (10, 10), (10, 0)])

    results = assign_labels([poly_a, poly_b], label_points, cad_reader_path=None, require_cad_reader=False, chunk_size=1)
    assert len(results) == 2
    assert results[0]['attributes']['SOTHUA'] == "100"
    assert results[1]['attributes']['SOTHUA'] == "101"

def test_assign_labels_shapely_fallback():
    """Should run assign_labels successfully using pure-Python Shapely STRtree fallback when no binary is found."""
    from unittest.mock import patch
    poly_a = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
    poly_b = Polygon([(10, 0), (20, 0), (20, 10), (10, 10), (10, 0)])
    
    labels = [
        {"geometry": Point(5, 5), "attributes": {"SOTHUA": "100"}},
        {"geometry": Point(15, 5), "attributes": {"SOTHUA": "101"}},
        {"geometry": Point(25, 5), "attributes": {"SOTHUA": "999"}}  # Outside
    ]
    
    with patch("topology_tools.polygonizer._find_cad_reader", return_value=None):
        results = assign_labels([poly_a, poly_b], labels, require_cad_reader=False)
        
    assert len(results) == 2
    assert results[0]['attributes']['SOTHUA'] == "100"
    assert results[1]['attributes']['SOTHUA'] == "101"
    
    overlap_labels = [
        {"geometry": Point(5.1, 5.1), "attributes": {"SOTHUA": "100-A"}},
        {"geometry": Point(1.0, 1.0), "attributes": {"SOTHUA": "100-B"}},
    ]
    with patch("topology_tools.polygonizer._find_cad_reader", return_value=None):
        results_overlap = assign_labels([poly_a], overlap_labels, require_cad_reader=False)
    assert len(results_overlap) == 1
    assert results_overlap[0]['attributes']['SOTHUA'] == "100-A"
    assert "Found 2 overlapping labels" in results_overlap[0]['attributes']['_warning']

    with patch("topology_tools.polygonizer._find_cad_reader", return_value=None):
        results_empty = assign_labels([poly_a], [], require_cad_reader=False)
    assert len(results_empty) == 1
    assert results_empty[0]['attributes']['SOTHUA'] == ""
    assert results_empty[0]['attributes']['_warning'] == "No labels assigned to this polygon"



