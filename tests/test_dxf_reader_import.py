"""Test dxf_reader import đúng sau FIX #1."""

def test_shapely_imports_present():
    """Đảm bảo không còn NameError khi import module."""
    try:
        from modules.dxf_engine import dxf_reader
        assert hasattr(dxf_reader, 'read_dxf_data'), \
            "Hàm read_dxf_data phải tồn tại"
    except ImportError as e:
        if "qgis" in str(e).lower():
            import pytest
            pytest.skip("Cần môi trường QGIS — bỏ qua ở pytest thuần")
        raise

def test_shapely_geometry_importable():
    """Shapely phải import được độc lập."""
    from shapely.geometry import Point, LineString, Polygon
    from shapely.errors import ShapelyError
    p = Polygon([(0,0),(1,0),(1,1),(0,1)])
    assert p.area == 1.0

def test_tcvn3_module_importable():
    """tcvn3_decoder phải import được."""
    from modules.dxf_engine import decode_tcvn3
    assert callable(decode_tcvn3)
