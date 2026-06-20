# -*- coding: utf-8 -*-
"""Calculates area tolerance limits for land parcels in Vietnam (Circular 25/2014/TT-BTNMT)."""

import math

def get_ms_by_scale(scale_denominator: int) -> float:
    """Return ms (root-mean-square error of boundary points in meters) based on map scale denominator.
    
    Circular 25/2014/TT-BTNMT - Article 7:
    - Scale 1:500: ms = 0.10m
    - Scale 1:1000: ms = 0.20m
    - Scale 1:2000: ms = 0.30m
    - Scale 1:5000: ms = 0.80m
    - Scale 1:10000: ms = 1.50m
    """
    if scale_denominator <= 500:
        return 0.10
    elif scale_denominator <= 1000:
        return 0.20
    elif scale_denominator <= 2000:
        return 0.30
    elif scale_denominator <= 5000:
        return 0.80
    else:
        return 1.50

def calculate_max_area_tolerance(area: float, scale_denominator: int) -> float:
    """Calculate the maximum allowable area discrepancy (Hạn sai diện tích) in square meters.
    
    Formula: Delta_P = 2.0 * ms * sqrt(P)
    Where:
    - ms is the boundary point error (meters)
    - P is the area of the parcel (square meters)
    """
    if area <= 0.0:
        return 0.0
    ms = get_ms_by_scale(scale_denominator)
    return 2.0 * ms * math.sqrt(area)

def check_area_tolerance(geom_area: float, doc_area: float, scale_denominator: int) -> dict:
    """Compare geometric area with documented area and verify if the difference exceeds tolerance.
    
    Returns
    -------
    dict
        - geom_area: float
        - doc_area: float
        - diff: float (absolute difference)
        - max_tolerance: float (allowable limit)
        - status: str ("OK" if diff <= max_tolerance else "WARNING")
        - pct: float (discrepancy percentage)
    """
    diff = abs(geom_area - doc_area)
    # Dùng diện tích hình học (geom_area) làm diện tích P tham chiếu
    max_tolerance = calculate_max_area_tolerance(geom_area, scale_denominator)
    
    status = "OK"
    if diff > max_tolerance:
        status = "WARNING"
        
    pct = (diff / doc_area * 100.0) if doc_area > 0.0 else 0.0
    
    return {
        "geom_area": geom_area,
        "doc_area": doc_area,
        "diff": round(diff, 2),
        "max_tolerance": round(max_tolerance, 2),
        "status": status,
        "pct": round(pct, 2)
    }
