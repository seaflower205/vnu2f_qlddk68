"""
Configurable field name mapping.

Dữ liệu địa chính VN có nhiều cách đặt tên trường:
SoTo, SOTO, SH_TO, SoHieuToBanDo, Số tờ, ...

Module này cung cấp canonical name → actual name mapping,
cho phép plugin xử lý linh hoạt mà không cần user đổi tên field.
"""
from __future__ import annotations


DEFAULT_FIELD_MAPPING: dict[str, list[str]] = {
    "so_to": [
        "SoTo", "SOTO", "SH_TO", "SoHieuToBanDo",
        "Số tờ", "so_to", "So_To", "SOHIEUTOBANDO",
    ],
    "so_thua": [
        "SoThua", "SOTHUA", "SH_THUA", "SoHieuThua",
        "Số thửa", "so_thua", "So_Thua", "SOHIEUTHUA",
    ],
    "dien_tich": [
        "DienTich", "DIENTICH", "Shape_Area",
        "Diện tích", "dien_tich", "Dien_Tich",
    ],
    "loai_dat": [
        "LoaiDat", "LOAIDAT", "MaLoaiDat",
        "Loại đất", "loai_dat", "Loai_Dat",
    ],
    "ma_dvhc": [
        "MaDVHC", "MADVHC", "MaXa", "Ma_DVHC",
        "ma_dvhc", "MAXA",
    ],
    "chu_su_dung": [
        "ChuSuDung", "CHUSUDUNG", "TenChuSD",
        "Chủ sử dụng", "chu_su_dung",
    ],
    "dia_chi": [
        "DiaChi", "DIACHI", "Địa chỉ", "dia_chi",
    ],
}


def resolve_field(
    layer_fields: list[str],
    canonical_name: str,
    custom_mapping: dict[str, list[str]] | None = None,
) -> str | None:
    """Tìm field name thực tế trong layer khớp canonical name.

    Args:
        layer_fields: Danh sách tên field của layer.
        canonical_name: Tên chuẩn (VD: "so_to", "dien_tich").
        custom_mapping: Mapping tùy chỉnh ghi đè DEFAULT_FIELD_MAPPING.

    Returns:
        Tên field thực tế hoặc None nếu không tìm thấy.
    """
    mapping = custom_mapping if custom_mapping else DEFAULT_FIELD_MAPPING
    aliases = mapping.get(canonical_name, [])

    # Exact match
    for alias in aliases:
        if alias in layer_fields:
            return alias

    # Case-insensitive fallback
    layer_fields_lower = {f.lower(): f for f in layer_fields}
    for alias in aliases:
        matched = layer_fields_lower.get(alias.lower())
        if matched is not None:
            return matched

    return None


def resolve_fields(
    layer_fields: list[str],
    canonical_names: list[str],
    custom_mapping: dict[str, list[str]] | None = None,
) -> dict[str, str | None]:
    """Resolve nhiều canonical names cùng lúc.

    Returns:
        Dict {canonical_name: actual_field_name | None}
    """
    return {
        name: resolve_field(layer_fields, name, custom_mapping)
        for name in canonical_names
    }
