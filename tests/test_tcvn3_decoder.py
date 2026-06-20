import pytest
from modules.dxf_engine import decode_tcvn3

class TestTCVN3Decoder:

    def test_empty_string(self):
        assert decode_tcvn3("") == ""

    def test_none_input(self):
        assert decode_tcvn3(None) is None

    def test_plain_ascii_unchanged(self):
        assert decode_tcvn3("ABC 123") == "ABC 123"

    def test_known_tcvn3_char(self):
        # \xf0 trong TCVN3 = 'đ' trong Unicode
        result = decode_tcvn3("\xf0\xc1t")
        assert "đ" in result or result != "\xf0\xc1t", \
            "TCVN3 ký tự phải được convert, không giữ nguyên byte"

    def test_mixed_content(self):
        # Chuỗi kết hợp ASCII và TCVN3
        result = decode_tcvn3("So thua \xf0\xc1t: 123")
        assert "123" in result
        assert "So thua" in result
