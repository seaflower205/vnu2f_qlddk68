# -*- coding: utf-8 -*-
"""
Bộ công cụ chuyển đổi bảng mã Tiếng Việt (TCVN3, VNI ↔ Unicode)
và hỗ trợ hậu xử lý tệp dữ liệu MapInfo TAB / dBASE .DAT.
"""

import os
import struct

# ═══════════════════════════════════════════════════════════════
# BẢNG ÁNH XẠ TCVN3 (ABC) ↔ UNICODE
# ═══════════════════════════════════════════════════════════════
_UNICODE_FULL = [
    'À', 'Á', 'Â', 'Ã', 'È', 'É', 'Ê', 'Ì', 'Í', 'Ò',
    'Ó', 'Ô', 'Õ', 'Ù', 'Ú', 'Ý', 'à', 'á', 'â', 'ã',
    'è', 'é', 'ê', 'ì', 'í', 'ò', 'ó', 'ô', 'õ', 'ù',
    'ú', 'ý', 'Ă', 'ă', 'Đ', 'đ', 'Ĩ', 'ĩ', 'Ũ', 'ũ',
    'Ơ', 'ơ', 'Ư', 'ư', 'Ạ', 'ạ', 'Ả', 'ả', 'Ấ', 'ấ',
    'Ầ', 'ầ', 'Ẩ', 'ẩ', 'Ẫ', 'ẫ', 'Ậ', 'ậ', 'Ắ', 'ắ',
    'Ằ', 'ằ', 'Ẳ', 'ẳ', 'Ẵ', 'ẵ', 'Ặ', 'ặ', 'Ẹ', 'ẹ',
    'Ẻ', 'ẻ', 'Ẽ', 'ẽ', 'Ế', 'ế', 'Ề', 'ề', 'Ể', 'ể',
    'Ễ', 'ễ', 'Ệ', 'ệ', 'Ỉ', 'ỉ', 'Ị', 'ị', 'Ọ', 'ọ',
    'Ỏ', 'ỏ', 'Ố', 'ố', 'Ồ', 'ồ', 'Ổ', 'ổ', 'Ỗ', 'ỗ',
    'Ộ', 'ộ', 'Ớ', 'ớ', 'Ờ', 'ờ', 'Ở', 'ở', 'Ỡ', 'ỡ',
    'Ợ', 'ợ', 'Ụ', 'ụ', 'Ủ', 'ủ', 'Ứ', 'ứ', 'Ừ', 'ừ',
    'Ử', 'ử', 'Ữ', 'ữ', 'Ự', 'ự', 'Ỳ', 'ỳ', 'Ỵ', 'ỵ',
    'Ỷ', 'ỷ', 'Ỹ', 'ỹ',
]

_TCVN3_FULL = [
    'A\xb5',
    'A\xb8',
    '\xa2',
    'A\xb7',
    'E\xcc',
    'E\xd0',
    '\xa3',
    'I\xd7',
    'I\xdd',
    'O\xdf',
    'O\xe3',
    '\xa4',
    'O\xe2',
    'U\xef',
    'U\xf3',
    'Y\xfd',
    '\xb5',
    '\xb8',
    '\xa9',
    '\xb7',
    '\xcc',
    '\xd0',
    '\xaa',
    '\xd7',
    '\xdd',
    '\xdf',
    '\xe3',
    '\xab',
    '\xe2',
    '\xef',
    '\xf3',
    '\xfd',
    '\xa1',
    '\xa8',
    '\xa7',
    '\xae',
    'I\xdc',
    '\xdc',
    'U\xf2',
    '\xf2',
    '\xa5',
    '\xac',
    '\xa6',
    '\xad',
    'A\xb9',
    '\xb9',
    'A\xb6',
    '\xb6',
    '\xa2\xca',
    '\xca',
    '\xa2\xc7',
    '\xc7',
    '\xa2\xc8',
    '\xc8',
    '\xa2\xc9',
    '\xc9',
    '\xa2\xcb',
    '\xcb',
    '\xa1\xbe',
    '\xbe',
    '\xa1\xbb',
    '\xbb',
    '\xa1\xbc',
    '\xbc',
    '\xa1\xbd',
    '\xbd',
    '\xa1\xc6',
    '\xc6',
    'E\xd1',
    '\xd1',
    'E\xce',
    '\xce',
    'E\xcf',
    '\xcf',
    '\xa3\xd5',
    '\xd5',
    '\xa3\xd2',
    '\xd2',
    '\xa3\xd3',
    '\xd3',
    '\xa3\xd4',
    '\xd4',
    '\xa3\xd6',
    '\xd6',
    'I\xd8',
    '\xd8',
    'I\xde',
    '\xde',
    'O\xe4',
    '\xe4',
    'O\xe1',
    '\xe1',
    '\xa4\xe8',
    '\xe8',
    '\xa4\xe5',
    '\xe5',
    '\xa4\xe6',
    '\xe6',
    '\xa4\xe7',
    '\xe7',
    '\xa4\xe9',
    '\xe9',
    '\xa5\xed',
    '\xed',
    '\xa5\xea',
    '\xea',
    '\xa5\xeb',
    '\xeb',
    '\xa5\xec',
    '\xec',
    '\xa5\xee',
    '\xee',
    'U\xf4',
    '\xf4',
    'U\xf1',
    '\xf1',
    '\xa6\xf8',
    '\xf8',
    '\xa6\xf5',
    '\xf5',
    '\xa6\xf6',
    '\xf6',
    '\xa6\xf7',
    '\xf7',
    '\xa6\xf9',
    '\xf9',
    'Y\xfa',
    '\xfa',
    'Y\xfe',
    '\xfe',
    'Y\xfb',
    '\xfb',
    'Y\xfc',
    '\xfc',
]

# Tạo các từ điển tra cứu nhanh
_UNI2TCVN = {}
_TCVN2UNI_1 = {}   # Ký tự TCVN3 1 byte → Unicode
_TCVN2UNI_2 = {}   # Chuỗi TCVN3 2 byte → Unicode

for _i in range(len(_UNICODE_FULL)):
    _u = _UNICODE_FULL[_i]
    _t = _TCVN3_FULL[_i]
    _UNI2TCVN[_u] = _t
    if len(_t) == 2:
        _TCVN2UNI_2[_t] = _u
    else:
        _TCVN2UNI_1[_t] = _u


# ═══════════════════════════════════════════════════════════════
# CÁC THUẬT TOÁN CHUYỂN ĐỔI BẢNG MÃ
# ═══════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════
# CÁC TIỆN ÍCH HẬU XỬ LÝ CHO MAPINFO TAB
# ═══════════════════════════════════════════════════════════════

def patch_tab_charset(tab_path, log_callback=None):
    """
    Sửa nhãn Charset trong tiêu đề file .TAB thành WindowsLatin1 để hiển thị đúng TCVN3/VNI.
    """
    def _log(msg):
        if log_callback:
            log_callback(msg)
            
    try:
        with open(tab_path, 'r', encoding='ascii', errors='replace') as f:
            header = f.read()
        patched = header.replace(
            'Charset "Neutral"', 'Charset "WindowsLatin1"'
        ).replace(
            '!charset Neutral', '!charset WindowsLatin1'
        )
        if patched != header:
            with open(tab_path, 'w', encoding='ascii', errors='replace') as f:
                f.write(patched)
            _log('📝 Đã sửa Charset tiêu đề .TAB: Neutral → WindowsLatin1')
    except Exception as e:
        _log(f'⚠️ Lỗi vá tiêu đề .TAB: {e}')


def postprocess_tab(tab_path, log_callback=None):
    """
    Đọc cấu trúc nhị phân file .dat của MapInfo (dBASE III), chuyển đổi 
    chuỗi text UTF-8 đa byte về dạng đơn byte (latin-1) tương ứng,
    bảo toàn độ rộng cố định của các trường (fixed-width records).
    """
    def _log(msg):
        if log_callback:
            log_callback(msg)

    # 1. Sửa nhãn Charset trong tiêu đề .TAB
    patch_tab_charset(tab_path, log_callback)

    # 2. Xử lý lại mã hóa file nhị phân .DAT đi kèm
    dat_path = os.path.splitext(tab_path)[0] + '.dat'
    if not os.path.exists(dat_path):
        return

    try:
        with open(dat_path, 'rb') as f:
            data = bytearray(f.read())

        if len(data) < 32:
            return

        # Đọc Header dBASE III
        num_records = struct.unpack_from('<I', data, 4)[0]
        header_size = struct.unpack_from('<H', data, 8)[0]
        record_size = struct.unpack_from('<H', data, 10)[0]

        # Đọc các thuộc tính trường (mỗi trường 32 byte từ offset 32)
        fields = []
        offset = 32
        while offset < header_size - 1 and data[offset] != 0x0D:
            raw_name = data[offset:offset + 11]
            fname = raw_name.split(b'\x00')[0].decode('ascii', errors='replace')
            ftype = chr(data[offset + 11])
            flen = data[offset + 16]
            fields.append((fname, ftype, flen))
            offset += 32

        # Chuyển đổi dữ liệu từng bản ghi
        n_fixed = 0
        for rec_idx in range(num_records):
            rec_start = header_size + rec_idx * record_size
            field_offset = 1  # Bỏ qua byte cờ xóa (deletion flag)

            for fname, ftype, flen in fields:
                fstart = rec_start + field_offset
                fend = fstart + flen

                # Chỉ xử lý các trường dữ liệu ký tự 'C'
                if ftype == 'C' and fend <= len(data):
                    raw = bytes(data[fstart:fend])
                    try:
                        # Giải mã từ UTF-8
                        text = raw.decode('utf-8')
                        # Mã hóa lại thành latin-1 (giữ nguyên byte 0x00-0xFF)
                        latin = text.encode('latin-1', errors='replace')
                        # Căn lề phải bằng Space padding cho đủ chiều rộng trường flen
                        padded = latin[:flen].ljust(flen, b' ')
                        if padded != raw:
                            data[fstart:fend] = padded
                            n_fixed += 1
                    except (UnicodeDecodeError, UnicodeEncodeError):
                        pass

                field_offset += flen

        if n_fixed > 0:
            with open(dat_path, 'wb') as f:
                f.write(bytes(data))
            _log(f'🔧 Đã mã hóa lại {n_fixed} trường dữ liệu nhị phân (UTF-8 → latin-1) trong file .DAT')
        else:
            _log('📝 File .DAT không cần re-encode bổ sung.')

    except Exception as e:
        _log(f'⚠️ Lỗi hậu xử lý tệp nhị phân .DAT: {e}')
