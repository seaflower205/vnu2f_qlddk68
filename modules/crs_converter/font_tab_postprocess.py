"""Mechanically extracted functions from font_utils.py."""
from __future__ import annotations

import os
import struct

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
    except Exception as e:  # noqa: BLE001 — intentional suppress
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

    except Exception as e:  # noqa: BLE001 — intentional suppress
        _log(f'⚠️ Lỗi hậu xử lý tệp nhị phân .DAT: {e}')
