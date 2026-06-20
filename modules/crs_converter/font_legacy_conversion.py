"""Mechanically extracted functions from font_utils.py."""
from __future__ import annotations

from .font_tables import _TCVN2UNI_1, _TCVN2UNI_2, _UNICODE_FULL, _UNI2TCVN

def looks_like_unicode_vietnamese(text):
    """
    Nhận diện chuỗi đã là Unicode tiếng Việt để tránh dịch nhầm sang TCVN3/VNI.

    Các bảng mã legacy thường được QGIS/GDAL trả về dạng byte Latin-1, trong khi
    Unicode tiếng Việt dựng sẵn có nhiều ký tự ngoài Latin-1 như ă, đ, ơ, ư,
    ấ, ể, ộ... Đây là tín hiệu đủ mạnh để bỏ qua bước legacy -> Unicode.
    """
    if not isinstance(text, str):
        return False
    return any(ch in _UNICODE_FULL and ord(ch) > 255 for ch in text)

def clean_double_encoding(text):
    """
    Khắc phục lỗi double-encoding khi tệp TCVN3/VNI bị lưu dưới dạng UTF-8.
    Giải mã chuỗi Latin-1 về dạng raw bytes, rồi dịch ngược lại từ UTF-8 nếu hợp lệ.
    """
    if not isinstance(text, str):
        return text
    try:
        raw = text.encode('latin-1')
        return raw.decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text

def convert_tcvn3_to_unicode(text):
    """
    Chuyển đổi TCVN3 → Unicode.
    Sử dụng phương pháp quét vị trí một lần (Single-pass scan) tránh lỗi dịch chuỗi dây chuyền.
    """
    if not isinstance(text, str):
        return text
    text = clean_double_encoding(text)
    if looks_like_unicode_vietnamese(text):
        return text
    result = []
    i = 0
    length = len(text)
    while i < length:
        # Thử ghép 2 byte trước (Cho chữ in hoa có dấu: chữ cái nền + dấu phụ)
        if i + 1 < length:
            pair = text[i:i + 2]
            if pair in _TCVN2UNI_2:
                result.append(_TCVN2UNI_2[pair])
                i += 2
                continue
        # Chuyển đổi 1 byte
        ch = text[i]
        if ch in _TCVN2UNI_1:
            result.append(_TCVN2UNI_1[ch])
        else:
            result.append(ch)
        i += 1
    return ''.join(result)

def convert_unicode_to_tcvn3(text):
    """
    Chuyển đổi Unicode → TCVN3.
    Ánh xạ từng ký tự Unicode thành chuỗi TCVN3 1 hoặc 2 byte tương ứng.
    """
    if not isinstance(text, str):
        return text
    result = []
    for ch in text:
        if ch in _UNI2TCVN:
            result.append(_UNI2TCVN[ch])
        else:
            result.append(ch)
    return ''.join(result)

def convert_vni_to_unicode(text):
    """
    Chuyển đổi VNI → Unicode.
    Thay thế tuần tự các cụm ký tự tổ hợp 2 ký tự trước, sau đó thay thế 1 ký tự.
    """
    if not isinstance(text, str):
        return text
    text = clean_double_encoding(text)
    if looks_like_unicode_vietnamese(text):
        return text
        
    _vni2 = [
        ('aâ', 'â'), ('AÂ', 'Â'), ('aê', 'ă'), ('AÊ', 'Ă'),
        ('eâ', 'ê'), ('EÂ', 'Ê'), ('aù', 'á'), ('AÙ', 'Á'),
        ('aø', 'à'), ('AØ', 'À'), ('aû', 'ả'), ('AÛ', 'Ả'),
        ('aõ', 'ã'), ('AÕ', 'Ã'), ('aï', 'ạ'), ('AÏ', 'Ạ'),
        ('aá', 'ấ'), ('AÁ', 'Ấ'), ('aà', 'ầ'), ('AÀ', 'Ầ'),
        ('aå', 'ẩ'), ('AÅ', 'Ẩ'), ('aã', 'ẫ'), ('AÃ', 'Ẫ'),
        ('aä', 'ậ'), ('AÄ', 'Ậ'), ('aé', 'ắ'), ('AÉ', 'Ắ'),
        ('aè', 'ằ'), ('AÈ', 'Ằ'), ('aú', 'ẳ'), ('AÚ', 'Ẳ'),
        ('aü', 'ẵ'), ('AÜ', 'Ẵ'), ('aë', 'ặ'), ('AË', 'Ặ'),
        ('eù', 'é'), ('EÙ', 'É'), ('eø', 'è'), ('EØ', 'È'),
        ('eû', 'ẻ'), ('EÛ', 'Ẻ'), ('eõ', 'ẽ'), ('EÕ', 'Ẽ'),
        ('eï', 'ẹ'), ('EÏ', 'Ẹ'), ('eá', 'ế'), ('EÁ', 'Ế'),
        ('eà', 'ề'), ('EÀ', 'Ề'), ('eå', 'ể'), ('EÅ', 'Ể'),
        ('eã', 'ễ'), ('EÃ', 'Ễ'), ('eä', 'ệ'), ('EÄ', 'Ệ'),
        ('oû', 'ỏ'), ('OÛ', 'Ỏ'), ('oõ', 'õ'), ('OÕ', 'Õ'),
        ('oï', 'ọ'), ('OÏ', 'Ọ'), ('oá', 'ố'), ('OÁ', 'Ố'),
        ('oà', 'ồ'), ('OÀ', 'Ồ'), ('oå', 'ổ'), ('OÅ', 'Ổ'),
        ('oã', 'ỗ'), ('OÃ', 'Ỗ'), ('oä', 'ộ'), ('OÄ', 'Ộ'),
        ('ôù', 'ớ'), ('ÔÙ', 'Ớ'), ('ôø', 'ờ'), ('ÔØ', 'Ờ'),
        ('ôû', 'ở'), ('ÔÛ', 'Ở'), ('ôõ', 'ỡ'), ('ÔÕ', 'Ỡ'),
        ('ôï', 'ợ'), ('ÔÏ', 'Ợ'), ('uù', 'ú'), ('UÙ', 'Ú'),
        ('uø', 'ù'), ('UØ', 'Ù'), ('uû', 'ủ'), ('UÛ', 'Ủ'),
        ('uõ', 'ũ'), ('UÕ', 'Ũ'), ('uï', 'ụ'), ('UÏ', 'Ụ'),
        ('öù', 'ứ'), ('ÖÙ', 'Ứ'), ('öø', 'ừ'), ('ÖØ', 'Ừ'),
        ('öû', 'ử'), ('ÖÛ', 'Ử'), ('öõ', 'ữ'), ('ÖÕ', 'Ữ'),
        ('öï', 'ự'), ('ÖÏ', 'Ự'), ('yø', 'ỳ'), ('YØ', 'Ỳ'),
        ('yû', 'ỷ'), ('YÛ', 'Ỷ'), ('yõ', 'ỹ'), ('YÕ', 'Ỹ'),
        ('yù', 'ý'), ('YÙ', 'Ý'), ('où', 'ó'), ('OÙ', 'Ó'),
        ('oø', 'ò'), ('OØ', 'Ò'), ('oâ', 'ô'), ('OÂ', 'Ô'),
    ]
    _vni1 = [
        ('ñ', 'đ'), ('Ñ', 'Đ'), ('í', 'í'), ('Í', 'Í'),
        ('ì', 'ì'), ('Ì', 'Ì'), ('æ', 'ỉ'), ('Æ', 'Ỉ'),
        ('ö', 'ư'), ('Ö', 'Ư'), ('î', 'ỵ'), ('Î', 'Ỵ'),
    ]
    
    for old, new in _vni2:
        text = text.replace(old, new)
    for old, new in _vni1:
        text = text.replace(old, new)
    return text

def convert_text_by_mode(text, mode):
    """Convert one text value using the UI conversion mode.

    Mode values follow ``FontTab``: 0=TCVN3->Unicode, 1=VNI->Unicode,
    2=Unicode->TCVN3, 3=no conversion.
    """
    if not isinstance(text, str) or not text or mode is None or mode >= 3:
        return text
    if mode == 0:
        return convert_tcvn3_to_unicode(text)
    if mode == 1:
        return convert_vni_to_unicode(text)
    if mode == 2:
        return convert_unicode_to_tcvn3(text)
    return text
