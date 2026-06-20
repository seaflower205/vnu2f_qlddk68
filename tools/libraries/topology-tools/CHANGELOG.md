# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-06-20

### Added
- Initial release of `topology-tools`.
- Boundary line cleaner (`clean_lines`) with vertex snapping and dangle cutting.
- Polygonizer (`create_polygons`) to convert LineStrings to closed Polygon geometries.
- Label assigner (`assign_labels`) with spatial contains queries, supporting both pure-Python Shapely and Rust `cad_reader` integration.
- Geometry validator and auto-repair (`validate_and_repair`) using Shapely's validation utilities.
- Multi-polygon overlap detection (`check_topology_errors`) to find overlapping topology errors.
- PEP 561 type annotation marker `py.typed`.
