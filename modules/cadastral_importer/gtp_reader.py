# -*- coding: utf-8 -*-
"""Read gCadas .gtp files.
from ..common.common_utils import log_critical, log_warning


The observed gCadas GTP format is a SQLite database XOR-obfuscated by page.
This module decodes the file into a temporary SQLite database and exposes the
core cadastral tables needed for import checks.
"""

from __future__ import annotations

import os
from ..common.common_utils import log_warning
import sqlite3
import tempfile
from collections import Counter
from dataclasses import dataclass

from .texts import cadastral_text as tx


PAGE_SIZE = 4096


@dataclass
class GtpDecodeResult:
    source_path: str
    sqlite_path: str
    page_count: int
    mask_page_count: int
    integrity: str


@dataclass
class GtpSummary:
    decoded: GtpDecodeResult
    non_empty_tables: list[tuple[str, int]]
    parcel_count: int
    person_count: int
    registration_count: int
    land_use_count: int
    topo_count: int


def decode_gtp(input_path: str, output_path: str | None = None, is_canceled_cb=None) -> GtpDecodeResult:
    """Decode a gCadas GTP file to SQLite and run integrity_check."""
    if output_path is None:
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(tempfile.gettempdir(), f"{base_name}_gtp_decoded.sqlite")

    def has_non_ascii(s: str) -> bool:
        try:
            s.encode("ascii")
            return False
        except UnicodeEncodeError:
            return True

    from ..common.bin_utils import get_cad_reader_path
    exe_path = get_cad_reader_path()
    
    if exe_path:
        import subprocess
        import shutil
        import uuid
        
        # Sao chép sang file tạm nếu đường dẫn chứa tiếng Việt
        temp_input_path = None
        temp_output_path = None
        work_input_path = input_path
        work_output_path = output_path
        
        if has_non_ascii(input_path) or has_non_ascii(output_path):
            temp_dir = tempfile.gettempdir()
            if has_non_ascii(input_path):
                temp_input_path = os.path.join(temp_dir, f"vnu2f_in_{uuid.uuid4().hex}.gtp")
                try:
                    shutil.copy2(input_path, temp_input_path)
                    work_input_path = temp_input_path
                except Exception:  # noqa: BLE001 — intentional suppress
                    temp_input_path = None
            if has_non_ascii(output_path):
                temp_output_path = os.path.join(temp_dir, f"vnu2f_out_{uuid.uuid4().hex}.sqlite")
                work_output_path = temp_output_path

        try:
            env = os.environ.copy()
            gcc_bin = os.environ.get("GCC_BIN_DIR", "")
            if gcc_bin and os.path.exists(gcc_bin):
                env["PATH"] = gcc_bin + os.pathsep + env.get("PATH", "")
                
            cmd = [exe_path, "gtp-decode", work_input_path, work_output_path]
            subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)
            
            # Nếu dùng tệp xuất tạm, sao chép về đích thực tế
            if temp_output_path and os.path.exists(temp_output_path):
                shutil.copy2(temp_output_path, output_path)

            connection = sqlite3.connect(output_path)
            try:
                integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            finally:
                connection.close()
            
            file_size = os.path.getsize(input_path)
            page_count = file_size // PAGE_SIZE
            
            return GtpDecodeResult(
                source_path=input_path,
                sqlite_path=output_path,
                page_count=page_count,
                mask_page_count=page_count,
                integrity=integrity,
            )
        except Exception as err:
            log_warning(f"Lỗi chạy Rust GTP decoder: {str(err)}. Tự động fallback sang Python native parser.")
        finally:
            # Dọn dẹp tệp tạm
            for path in (temp_input_path, temp_output_path):
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError:
                        pass

    # Fallback to python decryption loop
    file_size = os.path.getsize(input_path)
    if file_size % PAGE_SIZE != 0:
        raise ValueError(tx("gtp.error.invalid_size", page_size=PAGE_SIZE))
        
    page_count = file_size // PAGE_SIZE

    # Đọc lướt để đếm trang mặt nạ phổ biến nhất
    page_counts = Counter()
    with open(input_path, "rb") as handle:
        while True:
            if is_canceled_cb and is_canceled_cb():
                raise RuntimeError("Tác vụ bị hủy bởi người dùng.")
            page = handle.read(PAGE_SIZE)
            if not page:
                break
            page_counts[page] += 1

    mask_page, mask_page_count = page_counts.most_common(1)[0]
    if mask_page_count < 2:
        raise ValueError(tx("gtp.error.mask_missing"))

    empty_sqlite_leaf = bytearray(PAGE_SIZE)
    empty_sqlite_leaf[0] = 0x0D
    empty_sqlite_leaf[5] = 0x10

    # Thực hiện giải mã dạng stream và ghi trực tiếp ra file
    with open(input_path, "rb") as in_handle, open(output_path, "wb") as out_handle:
        while True:
            if is_canceled_cb and is_canceled_cb():
                raise RuntimeError("Tác vụ bị hủy bởi người dùng.")
            page = in_handle.read(PAGE_SIZE)
            if not page:
                break
            decoded_page = bytes(a ^ b ^ c for a, b, c in zip(page, mask_page, empty_sqlite_leaf))
            out_handle.write(decoded_page)

    # Kiểm tra tính hợp lệ của header SQLite
    with open(output_path, "rb") as check_handle:
        header = check_handle.read(16)
        if not header.startswith(b"SQLite format 3\x00"):
            raise ValueError(tx("gtp.error.sqlite_header_missing"))

    connection = sqlite3.connect(output_path)
    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        connection.close()

    return GtpDecodeResult(
        source_path=input_path,
        sqlite_path=output_path,
        page_count=page_count,
        mask_page_count=mask_page_count,
        integrity=integrity,
    )


def _table_count(connection: sqlite3.Connection, table_name: str) -> int:
    try:
        return int(connection.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0])
    except sqlite3.Error:
        return 0


def summarize_gtp(sqlite_path: str, decoded: GtpDecodeResult) -> GtpSummary:
    """Return high-level table counts for a decoded GTP SQLite database."""
    connection = sqlite3.connect(sqlite_path)
    try:
        table_rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        non_empty: list[tuple[str, int]] = []
        for (table_name,) in table_rows:
            count = _table_count(connection, table_name)
            if count:
                non_empty.append((table_name, count))

        return GtpSummary(
            decoded=decoded,
            non_empty_tables=non_empty,
            parcel_count=_table_count(connection, "ThuaDat"),
            person_count=_table_count(connection, "Nguoi"),
            registration_count=_table_count(connection, "DangKyThua"),
            land_use_count=_table_count(connection, "DaMucDichSuDung"),
            topo_count=_table_count(connection, "ThuaDatTopo"),
        )
    finally:
        connection.close()


def decode_and_summarize(input_path: str, output_path: str | None = None, is_canceled_cb=None) -> GtpSummary:
    decoded = decode_gtp(input_path, output_path, is_canceled_cb=is_canceled_cb)
    return summarize_gtp(decoded.sqlite_path, decoded)


def fetch_parcel_preview(sqlite_path: str, limit: int = 500) -> list[dict[str, object]]:
    """Read parcel/owner rows from decoded GTP for preview and validation."""
    query = """
        SELECT
            td.thuaDatId,
            td.soHieuToBanDo,
            td.soThuTuThua,
            td.dienTich,
            td.TamX,
            td.TamY,
            dt.nguoiId,
            n.hoTen,
            n.diaChi,
            dt.daMucDichSuDungId,
            dm.loaiMucDichSuDungKiemKeId,
            dm.dienTich AS dienTichMucDich,
            length(td.geom) AS geomSize
        FROM ThuaDat td
        LEFT JOIN DangKyThua dt
            ON dt.thuaDatId = td.thuaDatId
            AND (dt.trangThai = 1 OR dt.trangThai = '''1''' OR dt.trangThai IS NULL)
        LEFT JOIN Nguoi n
            ON n.nguoiId = dt.nguoiId
        LEFT JOIN DaMucDichSuDung dm
            ON dm.daMucDichSuDungId = dt.daMucDichSuDungId
        ORDER BY td.thuaDatId, dt.nguoiId
        LIMIT ?
    """
    rows: list[dict[str, object]] = []
    connection = sqlite3.connect(sqlite_path)
    try:
        connection.row_factory = sqlite3.Row
        for row in connection.execute(query, (limit,)):
            rows.append(dict(row))
    finally:
        connection.close()
    return rows



