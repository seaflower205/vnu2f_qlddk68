# -*- coding: utf-8 -*-
"""
Module for polygonizing cleaned boundary lines and assigning attribute labels to the resulting polygons.
"""

import logging
from typing import List, Dict, Any, Optional
from shapely.geometry import Polygon, Point

logger = logging.getLogger("topology_tools")

MIN_AREA_THRESHOLD = 1e-4
INTERIOR_INTERSECTION_PATTERN = "T********"
DEFAULT_LAND_CLASS = "Khac"
LAND_CLASS_FIELD = "LOAIDAT"

def create_polygons(lines: List[Any]) -> List[Polygon]:
    """
    Converts a list of cleaned LineString geometries into closed Polygon geometries.

    Args:
        lines (List[Any]): A list of Shapely LineString geometries.

    Returns:
        List[Polygon]: A list of valid, non-empty Shapely Polygon geometries.
    """
    if not lines:
        return []

    from shapely.ops import polygonize
    try:
        # Use Shapely's polygonize operator
        polys = list(polygonize(lines))
    except Exception as e:
        logger.error("Failed to polygonize lines: %s", e)
        return []

    if not polys:
        return []

    # Use Shapely 2.x vectorized operations to avoid Python loop overhead
    import numpy as np
    import shapely

    polys_arr = np.array(polys, dtype=object)
    mask = shapely.is_valid(polys_arr) & ~shapely.is_empty(polys_arr) & (shapely.area(polys_arr) > MIN_AREA_THRESHOLD)
    return list(polys_arr[mask])

def _find_cad_reader(explicit_path: Optional[str] = None) -> Optional[str]:
    """
    Resolves the path to the cad_reader executable.
    Checks:
      1. explicit_path
      2. CAD_READER_PATH environment variable
      3. Package local bin/cad_reader_windows.exe (on Windows only)
    """
    import os
    import sys

    if explicit_path:
        return explicit_path

    env_path = os.environ.get("CAD_READER_PATH")
    if env_path:
        return env_path

    if sys.platform == "win32":
        base_dir = os.path.dirname(__file__)
        pkg_bin = os.path.abspath(os.path.join(base_dir, "bin", "cad_reader_windows.exe"))
        if os.path.exists(pkg_bin):
            return pkg_bin
        repo_bin = os.path.abspath(os.path.join(base_dir, "..", "..", "bin", "cad_reader_windows.exe"))
        if os.path.exists(repo_bin):
            return repo_bin

    return None

def assign_labels(
    polygons: List[Polygon],
    label_points: List[Dict[str, Any]],
    cad_reader_path: Optional[str] = None,
    require_cad_reader: bool = False,
    chunk_size: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Spatial join to assign label attributes to each polygon based on point-in-polygon relations.

    Note:
        While the Rust cad_reader path is supported for CLI/offline pipelines, the pure-in-memory
        Shapely vectorized join (using STRtree) is significantly faster and preferred for in-process
        Python/QGIS calls due to the subprocess spawning and disk I/O serialization overhead.

    Args:
        polygons (List[Polygon]): A list of Shapely Polygon geometries.
        label_points (List[Dict[str, Any]]): A list of dictionaries representing label points.
            Each dictionary must contain:
                - 'geometry': shapely.geometry.Point
                - 'attributes': dict
        cad_reader_path (Optional[str]): Path to the compiled Rust `cad_reader` CLI executable.
            If not specified, checks the `CAD_READER_PATH` environment variable.
        require_cad_reader (bool): If True, throws a RuntimeError if the `cad_reader` path is invalid
            or fails, instead of falling back to Shapely sequential logic.
        chunk_size (Optional[int]): If specified, processes query points in batches of this size 
            to limit peak memory consumption by bounding NumPy query arrays.

    Returns:
        List[Dict[str, Any]]: A list of parcel dicts containing:
            {
                'geometry': Polygon,
                'attributes': dict
            }

    Raises:
        RuntimeError: If require_cad_reader is True and the cad_reader executable is missing or fails.
    """
    import os
    import json
    import subprocess
    import tempfile

    # 1. Resolve cad_reader_path
    exe_path = _find_cad_reader(cad_reader_path)

    # If require_cad_reader is True, validate path presence immediately
    if require_cad_reader and not exe_path:
        raise RuntimeError(
            "require_cad_reader is set to True, but no valid cad_reader binary was resolved. "
            "Please provide a valid cad_reader_path argument, set the CAD_READER_PATH environment variable, "
            "or ensure the binary is placed in tools/libraries/topology-tools/bin/cad_reader_windows.exe on Windows."
        )

    # 2. Try running Rust R-Tree binary if available
    if exe_path:
        if not os.path.exists(exe_path):
            if require_cad_reader:
                raise RuntimeError(
                    f"require_cad_reader is set to True, but the resolved cad_reader path "
                    f"does not exist: {exe_path}"
                )
            else:
                logger.warning(
                    "Resolved cad_reader path does not exist: %s. Falling back to Shapely sequential logic.", 
                    exe_path
                )
        else:
            with tempfile.TemporaryDirectory() as tmpdir:
                poly_path = os.path.join(tmpdir, "poly_in.json")
                label_path = os.path.join(tmpdir, "label_in.json")
                output_path = os.path.join(tmpdir, "poly_out.json")

                try:
                    # Export polygons to temporary JSON
                    poly_list = []
                    for idx, poly in enumerate(polygons):
                        if not poly or poly.is_empty:
                            continue
                        shell = list(poly.exterior.coords)
                        holes = [list(interior.coords) for interior in poly.interiors]
                        poly_list.append({
                            "id": idx,
                            "shell": shell,
                            "holes": holes
                        })

                    with open(poly_path, "w", encoding="utf-8") as f:
                        json.dump(poly_list, f, ensure_ascii=False)

                    # Export labels to temporary JSON
                    label_list = []
                    for lp in label_points:
                        pt = lp.get('geometry')
                        if not pt or pt.is_empty:
                            continue
                        label_list.append({
                            "x": pt.x,
                            "y": pt.y,
                            "attributes": lp.get("attributes", {})
                        })

                    with open(label_path, "w", encoding="utf-8") as f:
                        json.dump(label_list, f, ensure_ascii=False)

                    # Subprocess environment Setup
                    env = os.environ.copy()
                    
                    cmd = [
                        exe_path, "topology-join",
                        "--polygons", poly_path,
                        "--labels", label_path,
                        "--output", output_path
                    ]
                    
                    # Run Rust CLI tool
                    subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)

                    # Read results from temporary JSON
                    with open(output_path, "r", encoding="utf-8") as f:
                        out_list = json.load(f)

                    results = []
                    for item in out_list:
                        shell = item["shell"]
                        holes = item["holes"]
                        attrs = item["attributes"]

                        geom = Polygon(shell, holes)
                        results.append({
                            'geometry': geom,
                            'attributes': attrs
                        })
                    return results

                except Exception as err:
                    error_msg = f"cad_reader CLI execution failed: {err}"
                    if require_cad_reader:
                        raise RuntimeError(error_msg) from err
                    else:
                        logger.warning(
                            "%s. Falling back to Shapely sequential logic.", 
                            error_msg
                        )

    # 3. Fallback logic: Vectorized spatial search using STRtree
    from collections import defaultdict
    from shapely import STRtree

    # Build tree from polygons (fewer, larger geometries)
    tree = STRtree(polygons)

    # Extract valid point geometries and map to their original index
    point_geoms: List[Point] = []
    valid_lp_indices: List[int] = []
    for idx, lp in enumerate(label_points):
        pt = lp.get('geometry')
        if pt and isinstance(pt, Point) and not pt.is_empty:
            point_geoms.append(pt)
            valid_lp_indices.append(idx)

    poly_to_labels = defaultdict(list)
    if point_geoms:
        # Determine point chunks to control NumPy query size in memory
        if chunk_size is None or chunk_size <= 0:
            point_chunks = [point_geoms]
            chunk_offsets = [0]
        else:
            point_chunks = [point_geoms[i:i + chunk_size] for i in range(0, len(point_geoms), chunk_size)]
            chunk_offsets = list(range(0, len(point_geoms), chunk_size))

        for chunk, offset in zip(point_chunks, chunk_offsets):
            # Vectorized call: queries points in this chunk
            res = tree.query(chunk, predicate="within")
            point_indices = res[0] + offset
            polygon_indices = res[1]

            # Populate matched labels mapping
            for pt_idx, poly_idx in zip(point_indices, polygon_indices):
                original_lp_idx = valid_lp_indices[pt_idx]
                poly_to_labels[poly_idx].append(label_points[original_lp_idx])

            # Clear temporary query variables immediately
            del res
            del point_indices
            del polygon_indices

    # Clean up tree and geometries early
    del tree
    del point_geoms
    del valid_lp_indices

    results_shapely: List[Dict[str, Any]] = []
    for poly_idx, poly in enumerate(polygons):
        matched_labels = poly_to_labels[poly_idx]

        if len(matched_labels) == 1:
            attrs = matched_labels[0]['attributes'].copy()
        elif len(matched_labels) > 1:
            centroid = poly.centroid
            # Sort by distance to centroid to get the closest label
            matched_labels.sort(key=lambda x: centroid.distance(x['geometry']))
            attrs = matched_labels[0]['attributes'].copy()
            attrs['_warning'] = f"Found {len(matched_labels)} overlapping labels in polygon"
        else:
            # Default empty attributes
            attrs = {
                "SOTHUA": "",
                "SOTO": "",
                LAND_CLASS_FIELD: DEFAULT_LAND_CLASS,
                "TENCHU": "",
                "DIENTICH": round(poly.area, 1),
                "_warning": "No labels assigned to this polygon"
            }

        # Standard calculation properties
        attrs['DIENTICH_HP'] = round(poly.area, 2)

        results_shapely.append({
            'geometry': poly,
            'attributes': attrs
        })

    # Clear matched dict to free memory before return
    del poly_to_labels
    return results_shapely
