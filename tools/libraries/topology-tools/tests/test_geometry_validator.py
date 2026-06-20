# -*- coding: utf-8 -*-
"""
Unit tests for the geometry validator module of topology-tools.
"""

import pytest
from shapely.geometry import Polygon, Point
from topology_tools.geometry_validator import validate_and_repair, check_topology_errors

def test_validate_and_repair_valid_polygon(valid_square):
    """Should validate a clean, valid polygon and return it unrepaired."""
    result = validate_and_repair(valid_square)
    assert result['is_valid'] is True
    assert result['is_sliver'] is False
    assert result['reason'] == 'Valid'
    assert result['repaired_geometry'] == valid_square

def test_validate_and_repair_sliver_polygon(sliver_polygon):
    """Should detect sliver polygons below the specified area threshold."""
    result = validate_and_repair(sliver_polygon, sliver_threshold=0.1)
    assert result['is_sliver'] is True
    assert result['is_valid'] is True  # Sliver is small but geometrically valid

def test_validate_and_repair_invalid_self_intersecting(invalid_self_intersecting):
    """Should detect self-intersections and successfully repair the geometry."""
    result = validate_and_repair(invalid_self_intersecting)
    assert result['is_valid'] is True  # Restored/repaired to valid MultiPolygon or Polygon
    assert 'Invalid geometry' in result['reason']
    assert 'repaired' in result['reason']
    assert result['repaired_geometry'].is_valid

def test_validate_and_repair_empty_geometry():
    """Should handle empty or null geometries gracefully."""
    empty_poly = Polygon()
    result = validate_and_repair(empty_poly)
    assert result['is_valid'] is False
    assert 'Empty' in result['reason']

    result_none = validate_and_repair(None)
    assert result_none['is_valid'] is False
    assert 'Empty' in result_none['reason']

def test_validate_and_repair_invalid_type():
    """Should reject incorrect input types gracefully."""
    result = validate_and_repair(Point(0, 0))
    assert result['is_valid'] is False
    assert 'Expected shapely.geometry.Polygon' in result['reason']

def test_check_topology_errors_overlapping(overlapping_squares):
    """Should detect overlaps between adjacent polygons exceeding tolerance."""
    errors = check_topology_errors(overlapping_squares, overlap_tolerance=0.01)
    assert len(errors) == 1
    assert errors[0]['idx_a'] == 0
    assert errors[0]['idx_b'] == 1
    assert errors[0]['overlap_area'] == 5.0

def test_check_topology_errors_no_overlap(valid_square):
    """Should return no errors for disjoint or boundary-touching polygons."""
    # Disjoint square
    disjoint_square = Polygon([(20, 20), (30, 20), (30, 30), (20, 30), (20, 20)])
    errors = check_topology_errors([valid_square, disjoint_square])
    assert len(errors) == 0

    # Touching square (boundary only, area of overlap is 0.0)
    touching_square = Polygon([(10, 0), (20, 0), (20, 10), (10, 10), (10, 0)])
    errors_touch = check_topology_errors([valid_square, touching_square])
    assert len(errors_touch) == 0

def test_check_topology_errors_chunked(overlapping_squares):
    """Should detect overlaps correctly even when processed in small chunks."""
    errors = check_topology_errors(overlapping_squares, overlap_tolerance=0.01, chunk_size=1)
    assert len(errors) == 1
    assert errors[0]['idx_a'] == 0
    assert errors[0]['idx_b'] == 1
    assert errors[0]['overlap_area'] == 5.0

def test_validate_and_repair_make_valid_exception(invalid_self_intersecting):
    """Should handle exception during make_valid repair gracefully."""
    from unittest.mock import patch
    with patch("shapely.validation.make_valid", side_effect=ValueError("Mocked repair failure")):
        result = validate_and_repair(invalid_self_intersecting)
    assert result['is_valid'] is False
    assert "Repair failed" in result['reason']

def test_check_topology_errors_too_few_polygons():
    """Should return empty errors list if fewer than 2 valid polygons are provided."""
    poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
    errors = check_topology_errors([poly])
    assert errors == []

def test_check_topology_errors_intersection_exception(overlapping_squares):
    """Should handle exception during intersection calculation gracefully."""
    from unittest.mock import patch
    with patch("shapely.geometry.base.BaseGeometry.intersection", side_effect=RuntimeError("Mocked intersection failure")):
        errors = check_topology_errors(overlapping_squares, overlap_tolerance=0.01)
    assert errors == []


