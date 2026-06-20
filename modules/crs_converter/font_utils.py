# -*- coding: utf-8 -*-
"""
Bộ công cụ chuyển đổi bảng mã Tiếng Việt (TCVN3, VNI ↔ Unicode)
và hỗ trợ hậu xử lý tệp dữ liệu MapInfo TAB / dBASE .DAT.
"""

import os
import struct

from . import font_tables as _font_tables
globals().update({key: value for key, value in vars(_font_tables).items() if key.startswith("_")})

# ═══════════════════════════════════════════════════════════════
# CÁC THUẬT TOÁN CHUYỂN ĐỔI BẢNG MÃ
# ═══════════════════════════════════════════════════════════════













# ═══════════════════════════════════════════════════════════════
# CÁC TIỆN ÍCH HẬU XỬ LÝ CHO MAPINFO TAB
# ═══════════════════════════════════════════════════════════════




from .font_legacy_conversion import clean_double_encoding, convert_tcvn3_to_unicode, convert_text_by_mode, convert_unicode_to_tcvn3, convert_vni_to_unicode, looks_like_unicode_vietnamese

from .font_tab_postprocess import patch_tab_charset, postprocess_tab
