# -*- coding: utf-8 -*-
"""
Module for validating geometry quality and detecting topological errors (overlaps, slivers) between parcels.
"""

from typing import List, Dict, Any, Optional
from shapely.geometry import Polygon

MIN_AREA_THRESHOLD = 1e-4
INTERIOR_INTERSECTION_PATTERN = "T********"
DEFAULT_LAND_CLASS = "Khac"
LAND_CLASS_FIELD = "LOAIDAT"

# Default thresholds
DEFAULT_SLIVER_THRESHOLD = 0.1  # Minimum area (sq. meters) to filter out slivers
DEFAULT_OVERLAP_TOLERANCE = 0.01  # Maximum overlap area (sq. meters) allowed

def validate_and_repair(
    polygon: Polygon, 
    sliver_threshold: float = DEFAULT_SLIVER_THRESHOLD
) -> Dict[str, Any]:
    """
    Validates a single Polygon and attempts automatic repair using Shapely.

    Args:
        polygon (Polygon): The Shapely Polygon geometry to validate.
        sliver_threshold (float): The minimum area (sq. meters) for a polygon. 
            Polygons with an area smaller than this are flagged as slivers.

    Returns:
        Dict[str, Any]: Validation and repair results:
            {
                'is_valid': bool,                  # True if the geometry is structurally valid (or successfully repaired)
                'reason': str,                     # Human-readable explanation of validity status or failure reason
                'is_sliver': bool,                 # True if the polygon's area is below the sliver threshold
                'repaired_geometry': BaseGeometry  # The original or repaired Shapely geometry
            }
    """
    result: Dict[str, Any] = {
        'is_valid': True,
        'reason': 'Valid',
        'is_sliver': False,
        'repaired_geometry': polygon
    }

    if polygon is None or polygon.is_empty:
        result['is_valid'] = False
        result['reason'] = 'Empty or null geometry'
        return result

    if not isinstance(polygon, Polygon):
        result['is_valid'] = False
        result['reason'] = f'Expected shapely.geometry.Polygon, received {type(polygon).__name__}'
        return result

    # 1. Check for sliver (tiny fragment)
    if polygon.area < sliver_threshold:
        result['is_sliver'] = True

    # 2. Check structural validity
    if not polygon.is_valid:
        result['is_valid'] = False
        from shapely.validation import explain_validity, make_valid
        invalid_reason = explain_validity(polygon)
        result['reason'] = f"Invalid geometry: {invalid_reason}"

        try:
            # Repair using make_valid
            repaired = make_valid(polygon)
            result['repaired_geometry'] = repaired
            result['is_valid'] = True
            result['reason'] += " (Successfully repaired)"
        except Exception as e:
            result['reason'] += f" | Repair failed: {str(e)}"

    return result

def check_topology_errors(
    polygons: List[Polygon], 
    overlap_tolerance: float = DEFAULT_OVERLAP_TOLERANCE,
    chunk_size: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Detects topological overlaps (intersections with non-zero area) between adjacent polygons.

    Args:
        polygons (List[Polygon]): A list of Shapely Polygon geometries to check.
        overlap_tolerance (float): The maximum allowed overlapping area (sq. meters) 
            to filter out insignificant numerical inaccuracies.
        chunk_size (Optional[int]): If specified, processes query polygons in batches of this size 
            to limit peak memory consumption by bounding NumPy query arrays.

    Returns:
        List[Dict[str, Any]]: A list of discovered overlap errors.
            Each error dict has the form:
            {
                'idx_a': int,                       # Index of the first polygon in the input list
                'idx_b': int,                       # Index of the second polygon in the input list
                'overlap_area': float,              # Area of the overlapping region
                'overlap_geometry': BaseGeometry    # The Shapely geometry of the overlapping region
            }
    """
    errors: List[Dict[str, Any]] = []
    
    # Filter out empty or invalid polygons in input while maintaining original indices
    valid_polys: List[Polygon] = []
    original_indices: List[int] = []
    for idx, poly in enumerate(polygons):
        if poly is not None and isinstance(poly, Polygon) and not poly.is_empty:
            valid_polys.append(poly)
            original_indices.append(idx)
            
    if len(valid_polys) < 2:
        return errors

    # Build spatial index tree
    from shapely import STRtree
    import shapely

    tree = STRtree(valid_polys)

    # Determine chunks to control memory allocation footprint
    if chunk_size is None or chunk_size <= 0:
        chunks = [valid_polys]
        chunk_offsets = [0]
    else:
        chunks = [valid_polys[i:i + chunk_size] for i in range(0, len(valid_polys), chunk_size)]
        chunk_offsets = list(range(0, len(valid_polys), chunk_size))

    for chunk, offset in zip(chunks, chunk_offsets):
        # Query matching intersections for this chunk
        res = tree.query(chunk, predicate="intersects")
        query_indices = res[0] + offset
        tree_indices = res[1]

        # Filter unique pairs where query index is less than tree index (i < j)
        mask = query_indices < tree_indices
        i_indices = query_indices[mask]
        j_indices = tree_indices[mask]

        # Clean up temporary query arrays immediately inside the loop to free memory
        del res
        del mask

        # Check candidates
        for i, j in zip(i_indices, j_indices):
            poly_a = valid_polys[i]
            poly_b = valid_polys[j]

            # Fast filter: check if their interiors intersect using DE-9IM pattern (ignores boundary touches)
            if shapely.relate_pattern(poly_a, poly_b, INTERIOR_INTERSECTION_PATTERN):
                try:
                    # Calculate actual overlap geometry and area
                    inter = poly_a.intersection(poly_b)
                    if inter and not inter.is_empty and inter.area > overlap_tolerance:
                        if inter.geom_type in ('Polygon', 'MultiPolygon') or (
                            hasattr(inter, 'geoms') and any(g.geom_type in ('Polygon', 'MultiPolygon') for g in inter.geoms)
                        ):
                            errors.append({
                                'idx_a': original_indices[i],
                                'idx_b': original_indices[j],
                                'overlap_area': round(inter.area, 3),
                                'overlap_geometry': inter
                            })
                except Exception:
                    pass

        # Clear chunk loop variables
        del query_indices
        del tree_indices
        del i_indices
        del j_indices

    # Clean up tree to release memory early
    del tree
    del valid_polys
    del original_indices
    return errors
