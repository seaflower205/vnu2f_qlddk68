"""Chuyển đổi chuỗi mã hóa TCVN3 sang Unicode UTF-8."""

TCVN3_TO_UNICODE = {
    '\xa1': 'Ắ', '\xa2': 'ắ', '\xa3': 'Ặ', '\xa4': 'ặ',
    '\xa5': 'Ấ', '\xa6': 'ấ', '\xa7': 'Ầ', '\xa8': 'ầ',
    '\xa9': 'Ẩ', '\xaa': 'ẩ', '\xab': 'Ẫ', '\xac': 'ẫ',
    '\xad': 'Ậ', '\xae': 'ậ', '\xb0': 'Ắ', '\xb1': 'ắ',
    '\xb2': 'Ặ', '\xb3': 'ặ', '\xb4': 'Ế', '\xb5': 'ế',
    '\xb6': 'Ề', '\xb7': 'ề', '\xb8': 'Ể', '\xb9': 'ể',
    '\xba': 'Ễ', '\xbb': 'ễ', '\xbc': 'Ệ', '\xbd': 'ệ',
    '\xc0': 'À', '\xc1': 'Á', '\xc2': 'Â', '\xc3': 'Ã',
    '\xc8': 'È', '\xc9': 'É', '\xca': 'Ê',
    '\xcc': 'Ì', '\xcd': 'Í',
    '\xd0': 'Đ', '\xd1': 'Ñ',
    '\xd2': 'Ò', '\xd3': 'Ó', '\xd4': 'Ô', '\xd5': 'Õ',
    '\xd8': 'Ø', '\xd9': 'Ù', '\xda': 'Ú',
    '\xe0': 'à', '\xe1': 'á', '\xe2': 'â', '\xe3': 'ã',
    '\xe8': 'è', '\xe9': 'é', '\xea': 'ê',
    '\xec': 'ì', '\xed': 'í',
    '\xf0': 'đ', '\xf2': 'ò', '\xf3': 'ó', '\xf4': 'ô',
    '\xf5': 'õ', '\xf9': 'ù', '\xfa': 'ú',
}

def decode_tcvn3(text: str) -> str:
    """Thử decode chuỗi TCVN3 sang Unicode. Nếu không phải TCVN3 thì giữ nguyên."""
    if not text:
        return text
    try:
        return ''.join(TCVN3_TO_UNICODE.get(c, c) for c in text)
    except Exception:
        return text
