# vn-mapfont-converter

A standalone, dependency-free Python library for converting legacy Vietnamese map font encodings (TCVN3 / ABC, VNI) to Unicode. It also includes binary post-processing utilities for MapInfo TAB dBASE `.dat` files.

This library was extracted from the QGIS plugin `vnu2f_qlddk68` so it can be run in batch processing pipelines, command line tools, and web applications outside the QGIS desktop environment.

## Features

- **TCVN3 (ABC) to Unicode**: Direct conversion of TCVN3 strings to Unicode.
- **VNI to Unicode**: Single-pass conversion of VNI encoding to Unicode.
- **Unicode to TCVN3**: Backward encoding for legacy applications.
- **MapInfo TAB & dBASE Post-processor**: Corrects character sets (`Neutral` to `WindowsLatin1`) in `.tab` files and re-encodes fields in the binary `.dat` file to prevent encoding corruption in QGIS/GDAL.
- **Dependency-Free**: Uses only the Python Standard Library (`struct`, `os`).

## Installation

Build and install from source:

```bash
cd tools/libraries/vn_mapfont_converter
python -m build
pip install dist/vn_mapfont_converter-1.0.0-py3-none-any.whl
```

Or install in editable mode for development:

```bash
pip install -e .
```

## Usage

### Converting Strings

```python
from vn_mapfont_converter import convert_tcvn3_to_unicode, convert_vni_to_unicode

# TCVN3 (ABC) to Unicode
legacy_tcvn3 = "UBND TØnh B¾c Ninh"
unicode_str = convert_tcvn3_to_unicode(legacy_tcvn3)
print(unicode_str)  # Output: UBND Tỉnh Bắc Ninh

# VNI to Unicode
legacy_vni = "UBND Tænh Baéc Ninh"
unicode_str_vni = convert_vni_to_unicode(legacy_vni)
print(unicode_str_vni)  # Output: UBND Tỉnh Bắc Ninh
```

### Post-processing MapInfo TAB Files

```python
from vn_mapfont_converter import postprocess_tab

# Repairs charset headers and re-encodes the .dat dBASE III table bytes
postprocess_tab("path/to/mapinfo_file.tab", log_callback=print)
```
