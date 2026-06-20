# -*- coding: utf-8 -*-
"""
Module for cleaning boundary lines (snapping vertices, node splitting, and dangle removal) for parcel polygonization.
"""

import logging
from typing import List, Union
from shapely.geometry import LineString, MultiLineString

logger = logging.getLogger("topology_tools")

# Default values
DEFAULT_SNAP_TOLERANCE = 0.05  # Snapping distance in meters
DEFAULT_DANGLE_THRESHOLD = 0.5  # Maximum length of hanging dangle segment to cut in meters

def clean_lines(
    lines: List[Union[LineString, MultiLineString]],
    tolerance: float = DEFAULT_SNAP_TOLERANCE,
    dangle_threshold: float = DEFAULT_DANGLE_THRESHOLD
) -> List[LineString]:
    """
    Cleans parcel boundary lines through snapping, node splitting, and dangle cutting:
    1. Snaps free vertices lying within the tolerance radius.
    2. Node splits lines at intersection points and removes duplicate geometries (unary union).
    3. Iteratively filters out hanging dangles (dangling lines with length less than the threshold).

    Args:
        lines (List[Union[LineString, MultiLineString]]): A list of boundary LineString or MultiLineString geometries.
        tolerance (float): Snapping radius in meters. Set to 0 to disable snapping.
        dangle_threshold (float): Maximum length in meters of dangling lines to be removed.

    Returns:
        List[LineString]: A clean list of LineString segments.
    """
    if not lines:
        return []

    # 1. Normalize input geometries to a list of LineStrings
    valid_lines: List[LineString] = []
    for g in lines:
        if g is None or g.is_empty:
            continue
        if g.geom_type == 'LineString':
            valid_lines.append(g)
        elif g.geom_type == 'MultiLineString':
            # MultiLineString.geoms contains the sub-geometries
            valid_lines.extend(list(g.geoms))

    if not valid_lines:
        return []

    from shapely.ops import unary_union, snap

    # 2. Perform snapping
    merged = MultiLineString(valid_lines)
    del valid_lines
    if tolerance > 0:
        try:
            merged = snap(merged, merged, tolerance)
        except Exception as e:
            logger.warning("Geometry snapping failed: %s", e)

    # 3. Node split at intersections & deduplicate lines
    try:
        noded = unary_union(merged)
    except Exception:
        # Fallback if union calculation fails on complex cases
        noded = merged
    del merged

    # Extract single LineStrings from the result
    segments: List[LineString] = []
    if noded.geom_type == 'LineString':
        segments = [noded]
    elif noded.geom_type == 'MultiLineString':
        segments = list(noded.geoms)
    elif hasattr(noded, 'geoms'):
        segments = [g for g in noded.geoms if g.geom_type == 'LineString']
    else:
        # Fallback cast
        segments = [noded]

    if not segments:
        return []

    # 4. Remove dangling segments iteratively in O(N) linear time
    from collections import defaultdict

    # Map each coordinate to a set of segment indices
    coord_to_segs = defaultdict(set)
    for idx, seg in enumerate(segments):
        coords = seg.coords
        if len(coords) >= 2:
            coord_to_segs[coords[0]].add(idx)
            coord_to_segs[coords[-1]].add(idx)

    removed_segs = set()

    # Find initial dangle candidates (endpoints with degree == 1)
    dangle_queue = []
    for idx in range(len(segments)):
        seg = segments[idx]
        coords = seg.coords
        if len(coords) >= 2:
            p_start, p_end = coords[0], coords[-1]
            if (len(coord_to_segs[p_start]) == 1 or len(coord_to_segs[p_end]) == 1) and seg.length < dangle_threshold:
                dangle_queue.append(idx)

    # Process dangle pruning propagation
    while dangle_queue:
        idx = dangle_queue.pop()
        if idx in removed_segs:
            continue

        seg = segments[idx]
        coords = seg.coords
        p_start, p_end = coords[0], coords[-1]

        # Remove segment
        removed_segs.add(idx)

        # Update degrees of endpoints and check if neighbors become new dangles
        for p in (p_start, p_end):
            if idx in coord_to_segs[p]:
                coord_to_segs[p].remove(idx)
            # If the connected coordinate now has exactly 1 remaining segment, it might be a new dangle
            if len(coord_to_segs[p]) == 1:
                remaining_idx = next(iter(coord_to_segs[p]))
                remaining_seg = segments[remaining_idx]
                if remaining_seg.length < dangle_threshold:
                    dangle_queue.append(remaining_idx)

    # Reconstruct final cleaned segments list
    cleaned_segments = [segments[idx] for idx in range(len(segments)) if idx not in removed_segs]
    return cleaned_segments
