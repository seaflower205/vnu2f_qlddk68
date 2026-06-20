# -*- coding: utf-8 -*-
"""Read FAMIS/gCadas .pol parcel sidecar files."""

from __future__ import annotations

import struct
from dataclasses import dataclass

from .texts import cadastral_text as tx

try:
    from ..crs_converter.font_utils import convert_tcvn3_to_unicode
except Exception:  # noqa: BLE001 — intentional suppress
    def convert_tcvn3_to_unicode(text):  # type: ignore
        return text


@dataclass
class PolRecord:
    index: int
    offset: int
    reference_id: int
    code: int
    parcel_number: int
    area: float
    owner: str
    address: str
    vertex_count: int
    summary_values: tuple[float, float, float, float, float, float]
    vertices: tuple[tuple[float, float], ...] = ()


@dataclass
class PolSummary:
    source_path: str
    header_path: str
    record_count_header: int
    map_sheet: int
    layer_text: str
    records: list[PolRecord]


def _decode_tcvn3_field(raw: bytes) -> str:
    chunks: list[bytes] = []
    current = bytearray()
    for byte in raw:
        if byte == 0:
            if current:
                chunks.append(bytes(current))
                current.clear()
        else:
            current.append(byte)
    if current:
        chunks.append(bytes(current))

    if not chunks:
        return ""
    text = max(chunks, key=len).decode("latin1", "ignore").strip()
    return convert_tcvn3_to_unicode(text).strip()


def parse_pol(path: str, is_canceled_cb=None) -> PolSummary:
    data = open(path, "rb").read()
    if len(data) < 76:
        raise ValueError(tx("pol.error.too_short"))

    header_path = data[:32].split(b"\0", 1)[0].decode("ascii", "replace")
    record_count_header = struct.unpack_from("<I", data, 40)[0]
    map_sheet = struct.unpack_from("<I", data, 44)[0]
    layer_text = data[52:64].split(b"\0", 1)[0].decode("ascii", "replace")

    records: list[PolRecord] = []
    offset = 76
    while offset + 248 <= len(data):
        if is_canceled_cb and is_canceled_cb():
            raise RuntimeError("Tác vụ bị hủy bởi người dùng.")
        reference_id, code, parcel_number = struct.unpack_from("<III", data, offset)
        area = struct.unpack_from("<d", data, offset + 48)[0]
        vertex_count = struct.unpack_from("<I", data, offset + 240)[0]
        if not (0 <= parcel_number <= 100000 and 0 < area < 1e10 and 0 <= vertex_count < 100000):
            break

        summary_raw = struct.unpack_from("<IIIIII", data, offset + 24)
        summary_values = tuple(value / 1000 for value in summary_raw)
        vertex_offset = offset + 248
        vertices = tuple(
            struct.unpack_from("<dd", data, vertex_offset + index * 16)
            for index in range(vertex_count)
        )
        records.append(
            PolRecord(
                index=len(records) + 1,
                offset=offset,
                reference_id=reference_id,
                code=code,
                parcel_number=parcel_number,
                area=area,
                owner=_decode_tcvn3_field(data[offset + 108 : offset + 156]),
                address=_decode_tcvn3_field(data[offset + 156 : offset + 240]),
                vertex_count=vertex_count,
                summary_values=summary_values,  # type: ignore[arg-type]
                vertices=vertices,
            )
        )
        offset += 248 + vertex_count * 16

    if offset != len(data):
        raise ValueError(
            tx("pol.error.parser_stopped", offset=offset, size=len(data))
        )

    return PolSummary(
        source_path=path,
        header_path=header_path,
        record_count_header=record_count_header,
        map_sheet=map_sheet,
        layer_text=layer_text,
        records=records,
    )


def preview_records(summary: PolSummary, limit: int = 500) -> list[dict[str, object]]:
    rows = []
    for record in summary.records[:limit]:
        rows.append(
            {
                "index": record.index,
                "parcel_number": record.parcel_number,
                "area": record.area,
                "owner": record.owner,
                "address": record.address,
                "vertex_count": record.vertex_count,
                "code": record.code,
                "reference_id": record.reference_id,
            }
        )
    return rows



