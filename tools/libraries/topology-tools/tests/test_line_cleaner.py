# -*- coding: utf-8 -*-
"""
Unit tests for the line cleaner module of topology-tools.
"""

import pytest
from shapely.geometry import LineString, MultiLineString
from topology_tools.line_cleaner import clean_lines

def test_clean_lines_empty_input():
    """Should return an empty list when input is empty or null."""
    assert clean_lines([]) == []
    assert clean_lines([None]) == []

def test_clean_lines_snapping(snap_candidate_lines):
    """Should snap vertices within the specified tolerance distance."""
    # Gap is 0.02. With tolerance=0.05, they should snap.
    cleaned = clean_lines(snap_candidate_lines, tolerance=0.05, dangle_threshold=0.0)
    assert len(cleaned) == 3
    # Verify that the lines now touch and form a continuous chain
    # Seg 0 connects to Seg 1 at (4.98, 0.0)
    assert cleaned[0].coords[-1] == cleaned[1].coords[0] == (4.98, 0.0)
    # Seg 1 connects to Seg 2 at (5.0, 0.0)
    assert cleaned[1].coords[-1] == cleaned[2].coords[0] == (5.0, 0.0)

def test_clean_lines_no_snapping(snap_candidate_lines):
    """Should not snap vertices when tolerance is zero or too small."""
    # Gap is 0.02. With tolerance=0.01, they should not snap.
    cleaned = clean_lines(snap_candidate_lines, tolerance=0.01, dangle_threshold=0.0)
    assert len(cleaned) == 2
    p1 = cleaned[0].coords[-1]
    p2 = cleaned[1].coords[0]
    assert p1 == (4.98, 0.0)
    assert p2 == (5.0, 0.0)

def test_clean_lines_dangle_removal(dangle_lines):
    """Should remove dangling lines shorter than the specified threshold."""
    # Dangle length is 0.2. With dangle_threshold=0.5, it should be removed.
    cleaned = clean_lines(dangle_lines, tolerance=0.0, dangle_threshold=0.5)
    assert len(cleaned) == 1
    assert cleaned[0].length == 10.0  # Only main line remains

def test_clean_lines_dangle_preservation(dangle_lines):
    """Should preserve dangling lines longer than the specified threshold."""
    # Dangle length is 0.2. With dangle_threshold=0.1, it should be preserved.
    cleaned = clean_lines(dangle_lines, tolerance=0.0, dangle_threshold=0.1)
    assert len(cleaned) == 2

def test_clean_lines_multilinestring_unpacking():
    """Should unpack MultiLineString inputs into individual LineString segments."""
    ml = MultiLineString([
        LineString([(0, 0), (5, 0)]),
        LineString([(5, 0), (5, 5)])
    ])
    cleaned = clean_lines([ml], tolerance=0.0, dangle_threshold=0.0)
    assert len(cleaned) == 2
    assert all(isinstance(g, LineString) for g in cleaned)
