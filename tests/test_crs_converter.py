# -*- coding: utf-8 -*-
import pytest
from modules.crs_converter.crs_utils import CoordinateTransformer, Vn2000DbHelper
from modules.crs_converter.font_utils import convert_tcvn3_to_unicode, looks_like_unicode_vietnamese

def test_dms_conversion_happy():
    """Verify DMS parsing and Decimal Degree conversion matches expected coordinates."""
    dd_lat = CoordinateTransformer.parse_dms("21°14'05\"N")
    dd_lon = CoordinateTransformer.parse_dms("105°45'20\"E")
    
    assert abs(dd_lat - 21.234722) < 1e-5
    assert abs(dd_lon - 105.755555) < 1e-5
    
    lat_str = CoordinateTransformer.dd_to_dms(dd_lat, is_lat=True)
    lon_str = CoordinateTransformer.dd_to_dms(dd_lon, is_lat=False)
    
    assert "21°14'" in lat_str
    assert "105°45'" in lon_str

def test_dms_conversion_edge():
    """Verify DMS parsing with zero coordinates handles boundaries correctly."""
    zero_dd = CoordinateTransformer.parse_dms("0°0'0\"")
    assert zero_dd == 0.0

def test_dms_conversion_fail():
    """Verify DMS parsing raises errors on invalid coordinate formats."""
    with pytest.raises(Exception):
        CoordinateTransformer.parse_dms("invalid_coordinate_string")

def test_vietnamese_font_conversion_happy():
    """Verify TCVN3 to Unicode encoding conversion."""
    uni_val = convert_tcvn3_to_unicode("ThÞ ót Nhá")
    assert uni_val == "Thị út Nhỏ"

def test_vietnamese_font_conversion_edge():
    """Verify checks for existing Unicode strings."""
    assert looks_like_unicode_vietnamese("Thửa Đất Số 1") is True

def test_vietnamese_font_conversion_fail():
    """Verify font converter handles null and empty inputs gracefully."""
    assert convert_tcvn3_to_unicode(None) is None
    assert convert_tcvn3_to_unicode("") == ""

def test_crs_auto_registration(registered_vn2000_crs):
    """Verify that VN-2000 CRSs are successfully registered in the QGIS system database."""
    success, msg = registered_vn2000_crs
    assert success is True
    # Re-run should be safe and idempotent
    success_rerun, msg_rerun = Vn2000DbHelper.register_provinces()
    assert success_rerun is True
