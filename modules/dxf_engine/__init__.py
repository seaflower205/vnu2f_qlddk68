"""
Public API của package dxf_engine.
Import từ đây thay vì import trực tiếp vào dxf_reader.py hay dxf_writer.py.
"""
from .dxf_reader import read_dxf_data, match_parcels_with_attributes
from .dxf_writer import export_features_to_dxf
from .dxf_block_extractor import extract_block_attributes
from .tcvn3_decoder import decode_tcvn3

__all__ = [
    "read_dxf_data",
    "match_parcels_with_attributes",
    "export_features_to_dxf",
    "extract_block_attributes",
    "decode_tcvn3",
]
