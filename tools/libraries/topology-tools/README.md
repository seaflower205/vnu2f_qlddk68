# topology-tools

[![topology-tools CI](https://github.com/<OWNER>/<REPOSITORY>/actions/workflows/topology-tools-ci.yml/badge.svg)](https://github.com/<OWNER>/<REPOSITORY>/actions/workflows/topology-tools-ci.yml)

A standalone, headless Python library for boundary line cleaning, vertex snapping, dangle removal, polygonization, and topology validation. This library provides a clean spatial geometry processing pipeline outside QGIS, allowing spatial workflows to be automated in CLI scripts, batch pipelines, and server applications.


## Requirements

- **Python**: 3.8+
- **Shapely**: `>=2.0` (required and pinned for modern vectorized geometry operations)

## Installation

Install directly from the source directory:

```bash
cd tools/libraries/topology-tools
pip install .
```

Or install in editable mode for development:

```bash
pip install -e .
```

## Quick-Start Example

```python
from shapely.geometry import LineString, Point
from topology_tools import clean_lines, create_polygons, assign_labels

# 1. Prepare raw, dirty boundary lines (with a small gap of 0.02m and a dangle)
raw_lines = [
    LineString([(0, 0), (4.98, 0)]),
    LineString([(5.0, 0), (10, 0)]),
    LineString([(10, 0), (10, 10)]),
    LineString([(10, 10), (0, 10)]),
    LineString([(0, 10), (0, 0)]),
    LineString([(10, 0), (10, 0.2)])  # Hanging dangle of 0.2m
]

# 2. Clean lines: snap the 0.02m gap and cut the 0.2m dangle
clean_segments = clean_lines(raw_lines, tolerance=0.05, dangle_threshold=0.5)

# 3. Polygonize the closed boundaries
parcels = create_polygons(clean_segments)
print(f"Created {len(parcels)} parcel(s). Area: {parcels[0].area} sqm")
# Output: Created 1 parcel(s). Area: 100.0 sqm

# 4. Assign attributes using label points
labels = [
    {
        "geometry": Point(5, 5),
        "attributes": {"SOTHUA": "105", "SOTO": "14", "LOAIDAT": "ONT"}
    }
]
results = assign_labels(parcels, labels)
print("Assigned Attributes:", results[0]["attributes"])
# Output: Assigned Attributes: {'SOTHUA': '105', 'SOTO': '14', 'LOAIDAT': 'ONT', 'DIENTICH_HP': 100.0}
```

## API Reference

| Exported Symbol | Signature / Type | Description |
| :--- | :--- | :--- |
| `clean_lines` | `(lines: List[Union[LineString, MultiLineString]], tolerance: float = 0.05, dangle_threshold: float = 0.5) -> List[LineString]` | Snaps line vertices within a tolerance and trims hanging dangles shorter than the threshold. |
| `create_polygons` | `(lines: List[LineString]) -> List[Polygon]` | Polygonizes a list of lines into closed, valid Shapely polygons. |
| `assign_labels` | `(polygons: List[Polygon], label_points: List[Dict[str, Any]], cad_reader_path: Optional[str] = None, require_cad_reader: bool = False) -> List[Dict[str, Any]]` | Maps attribute label points to their enclosing polygons using an optional Rust CLI tool or a pure Shapely fallback. |
| `validate_and_repair`| `(polygon: Polygon, sliver_threshold: float = 0.1) -> Dict[str, Any]` | Validates a single polygon's structure, flags if it is a sliver, and repairs invalid boundaries. |
| `check_topology_errors`| `(polygons: List[Polygon], overlap_tolerance: float = 0.01) -> List[Dict[str, Any]]` | Scans a list of adjacent polygons and returns details of any overlapping areas. |

## Error Handling

All functions handle invalid spatial inputs gracefully:
- `validate_and_repair` returns a validation dictionary highlighting error details in the `'reason'` field rather than raising exceptions.
- `assign_labels` will throw a `RuntimeError` if `require_cad_reader=True` and the external `cad_reader` binary is missing or encounters a execution error. If `require_cad_reader=False` (default), it logs a warning and falls back to pure Python `shapely` contains scanning.

## Running Tests Locally

You can replicate the CI testing environment locally using the provided helper scripts:

- **Linux/macOS**:
  ```bash
  ./scripts/run-tests.sh
  ```
- **Windows**:
  ```powershell
  ./scripts/run-tests.ps1
  ```

These scripts set the correct execution directory and run `pytest` against the test suite.

## Contributing

For internal development:
1. Ensure all code changes include Python type hints.
2. Run the test suite using `pytest` before submitting a merge request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
