# -*- coding: utf-8 -*-
"""
vn-mapfont-converter: A standalone library for Vietnamese map font conversion.
"""

from .font_utils import (
    looks_like_unicode_vietnamese,
    clean_double_encoding,
    convert_tcvn3_to_unicode,
    convert_unicode_to_tcvn3,
    convert_vni_to_unicode,
    convert_text_by_mode,
    patch_tab_charset,
    postprocess_tab,
)

__all__ = [
    'looks_like_unicode_vietnamese',
    'clean_double_encoding',
    'convert_tcvn3_to_unicode',
    'convert_unicode_to_tcvn3',
    'convert_vni_to_unicode',
    'convert_text_by_mode',
    'patch_tab_charset',
    'postprocess_tab',
]
