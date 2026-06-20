# -*- coding: utf-8 -*-
def test_crs_converter_importable():
    from modules.crs_converter import crs_dialog
    from modules.crs_converter.tabs import plot_data_parser
    assert hasattr(plot_data_parser, 'PlotDataParser')
