# -*- coding: utf-8 -*-

def test_qgis_app_smoke(qgis_app):
    assert qgis_app is not None
    from qgis.core import Qgis
    version = Qgis.QGIS_VERSION
    print("\nQGIS Version in test_smoke:", version)

def test_symbology_build_fill_symbol(qgis_app):
    """Verify that build_fill_symbol constructs QgsFillSymbol with all brush and outline patterns."""
    from cadastral_tools.core.symbology_manager import build_fill_symbol
    from qgis.core import QgsFillSymbol
    
    all_patterns = [
        # Brush styles
        "solid", "no_brush", "diagonal_cross", 
        "dense_1", "dense_2", "dense_3", "dense_4", "dense_5", "dense_6", "dense_7",
        # Custom hatch / advanced patterns
        "dots", "horizontal", "vertical", "diagonal_fwd", "diagonal_bwd", "cross",
        "centroid", "geom_generator", "gradient", "line_pattern", "point_pattern",
        "random_marker", "raster_image", "svg", "shapeburst",
        # Outline styles
        "outline_arrow", "outline_filled", "outline_hashed", "outline_interpolated",
        "outline_lineburst", "outline_marker", "outline_raster", "outline_simple",
        "outline_linear_ref"
    ]
    for pat in all_patterns:
        config = {
            "fill_color": "#FF0000",
            "border_color": "#00FF00",
            "border_width_mm": 0.5,
            "opacity": 0.8,
            "pattern": pat
        }
        symbol = build_fill_symbol(config)
        assert isinstance(symbol, QgsFillSymbol)
        assert symbol.symbolLayerCount() > 0

def test_symbology_renderer_and_apply(qgis_app):
    """Verify build_renderer and apply_to_layer functions."""
    from cadastral_tools.core.symbology_manager import build_renderer, apply_to_layer
    from qgis.core import QgsCategorizedSymbolRenderer, QgsVectorLayer
    
    code_configs = [
        {"code": "ONT", "name_vi": "Đất ở nông thôn", "fill_color": "#FF0000", "border_color": "#000000", "pattern": "solid"},
        {"code": "ODT", "name_vi": "Đất ở đô thị", "fill_color": "#00FF00", "border_color": "#000000", "pattern": "svg"}
    ]
    
    renderer = build_renderer("loaidat", code_configs)
    assert isinstance(renderer, QgsCategorizedSymbolRenderer)
    
    # Create a dummy memory layer to test apply_to_layer
    layer = QgsVectorLayer("Polygon?crs=EPSG:4326", "Test Layer", "memory")
    assert layer.isValid()
    
    apply_to_layer(layer, "loaidat", code_configs)
    assert isinstance(layer.renderer(), QgsCategorizedSymbolRenderer)

def test_campaign_5_smoke():
    from modules.crs_converter.tabs import plot_data_parser
