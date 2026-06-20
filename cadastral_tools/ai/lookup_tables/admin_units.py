"""
Bảng đơn vị hành chính có versioning.

Hỗ trợ parent chain traversal: xã → huyện → tỉnh.
Sau NQ 202/2025/QH15 (12/06/2025) cả nước còn 34 ĐVHC cấp tỉnh.

KHÔNG chứa kinh tuyến trục — xem crs_profiles.py.

Source: NQ 202/2025/QH15 + Tổng cục Thống kê.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class AdminUnit:
    """Đơn vị hành chính có thời gian hiệu lực."""

    code: str
    name: str
    level: str  # "province" | "district" | "commune"
    valid_from: date
    valid_to: date | None  # None = còn hiệu lực
    parent_code: str | None  # Mã ĐVHC cấp trên (xã→huyện, huyện→tỉnh)
    legacy_codes: tuple[str, ...] = ()  # Mã cũ (trước sáp nhập)
    notes: str | None = None


# ============================================================
# ADMIN UNITS DATA
# Populate đầy đủ trước production deploy.
# Hiện tại: seed data minh họa cho Hà Nội.
# ============================================================

ADMIN_UNITS: list[AdminUnit] = [
    # --- Thành phố Hà Nội (không thay đổi sau NQ 202) ---
    AdminUnit(
        code="01",
        name="Thành phố Hà Nội",
        level="province",
        valid_from=date(2008, 8, 1),
        valid_to=None,
        parent_code=None,
        legacy_codes=("HN",),
    ),
    # --- Quận Ba Đình, Hà Nội ---
    AdminUnit(
        code="001",
        name="Quận Ba Đình",
        level="district",
        valid_from=date(2008, 8, 1),
        valid_to=None,
        parent_code="01",
    ),
    # --- Phường Phúc Xá, Ba Đình ---
    AdminUnit(
        code="00001",
        name="Phường Phúc Xá",
        level="commune",
        valid_from=date(2008, 8, 1),
        valid_to=None,
        parent_code="001",
    ),
    # --- TP Hồ Chí Minh ---
    AdminUnit(
        code="79",
        name="Thành phố Hồ Chí Minh",
        level="province",
        valid_from=date(1976, 7, 2),
        valid_to=None,
        parent_code=None,
        legacy_codes=("HCM", "SG"),
    ),
    # TODO: Populate đầy đủ 34 tỉnh/TP + tỉnh cũ legacy_codes
    # TODO: Populate quận/huyện + phường/xã cho các tỉnh cần test
]


def resolve_admin_unit(code: str, as_of: date) -> AdminUnit | None:
    """Tìm ĐVHC hợp lệ tại thời điểm as_of.

    Tìm trực tiếp theo code, sau đó tìm qua legacy_codes.
    """
    # Tìm trực tiếp
    for u in ADMIN_UNITS:
        if u.code == code and u.valid_from <= as_of:
            if u.valid_to is None or as_of <= u.valid_to:
                return u

    # Tìm qua legacy_codes
    for u in ADMIN_UNITS:
        if code in u.legacy_codes and u.valid_from <= as_of:
            if u.valid_to is None or as_of <= u.valid_to:
                return u

    return None


def resolve_province(code: str, as_of: date) -> AdminUnit | None:
    """Leo cây cha từ xã/huyện lên tỉnh.

    Dùng khi dữ liệu layer có MaDVHC cấp xã nhưng cần match
    rule cấp tỉnh (VD: rule tách thửa, kinh tuyến trục).
    """
    unit = resolve_admin_unit(code, as_of)
    while unit is not None:
        if unit.level == "province":
            return unit
        if unit.parent_code is None:
            break
        unit = resolve_admin_unit(unit.parent_code, as_of)
    return None


def normalize_admin_code(raw: object, expected_level: str | None = None) -> str | None:
    """Chuẩn hóa mã ĐVHC an toàn.

    expected_level:
    - "province": trả mã 2 ký tự, ví dụ 1 / 1.0 / "1" -> "01"
    - "commune": giữ mã xã đầy đủ sau khi strip; không cắt 2 ký tự
    - None: chỉ strip và validate format rõ ràng; nếu mơ hồ (như chuỗi số) thì None
    """
    if raw is None:
        return None
    val_str = str(raw).strip()
    if not val_str:
        return None

    # Xử lý trường hợp đọc từ Excel/Shapefile bị dạng float (ví dụ: 1.0)
    if val_str.endswith(".0"):
        val_str = val_str[:-2]

    if expected_level == "province":
        if val_str.isdigit() and len(val_str) < 2:
            return val_str.zfill(2)
        return val_str
    elif expected_level == "commune":
        return val_str
    elif expected_level == "district":
        return val_str
    else:
        # expected_level is None
        # Nếu là chuỗi số, không thể tự đoán cấp độ (ví dụ "001" có thể là huyện, xã, hay mã legacy)
        if val_str.isdigit():
            return None
        return val_str
