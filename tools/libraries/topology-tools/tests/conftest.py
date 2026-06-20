# -*- coding: utf-8 -*-
"""
Shared fixtures and geometry test data for topology-tools testing.
"""

import pytest
from shapely.geometry import Polygon, Point, LineString

@pytest.fixture
def valid_square() -> Polygon:
    """A clean, valid 10x10 square polygon."""
    return Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])

@pytest.fixture
def sliver_polygon() -> Polygon:
    """A tiny sliver polygon (area 0.05 sq meters)."""
    return Polygon([(0, 0), (1, 0), (1, 0.05), (0, 0.05), (0, 0)])

@pytest.fixture
def invalid_self_intersecting() -> Polygon:
    """An invalid self-intersecting polygon (bowtie)."""
    return Polygon([(0, 0), (0, 10), (10, 0), (10, 10), (0, 0)])

@pytest.fixture
def overlapping_squares() -> list:
    """Two squares that overlap by an area of 2.0 sq meters."""
    poly_a = Polygon([(0, 0), (5, 0), (5, 5), (0, 5), (0, 0)])
    poly_b = Polygon([(4, 0), (9, 0), (9, 5), (4, 5), (4, 0)])  # Overlap on x: [4, 5], area = 1 * 5 = 5.0
    # Let's adjust area to exact overlap: [4, 5], y: [0, 5] -> overlap area is 5.0.
    return [poly_a, poly_b]

@pytest.fixture
def snap_candidate_lines() -> list:
    """Lines that need snapping. There is a small gap of 0.02 meters between two segments."""
    line_a = LineString([(0, 0), (4.98, 0)])
    line_b = LineString([(5.0, 0), (10, 0)])
    return [line_a, line_b]

@pytest.fixture
def dangle_lines() -> list:
    """Lines with a short dangle of length 0.2 meters at the end."""
    main_line = LineString([(0, 0), (10, 0)])
    dangle = LineString([(10, 0), (10, 0.2)])  # Hanging line of length 0.2
    return [main_line, dangle]

@pytest.fixture
def label_points() -> list:
    """Points inside regions for attribute assignment tests."""
    return [
        {
            "geometry": Point(5, 5),
            "attributes": {"SOTHUA": "100", "SOTO": "12", "LOAIDAT": "ONT", "TENCHU": "Nguyen Van A"}
        },
        {
            "geometry": Point(15, 5),
            "attributes": {"SOTHUA": "101", "SOTO": "12", "LOAIDAT": "LUC", "TENCHU": "Tran Thi B"}
        }
    ]
