"""
CRS Profiles — kinh tuyến trục theo ĐVHC, hỗ trợ tỉnh sáp nhập.

Sau sáp nhập (NQ 202/2025/QH15), một tỉnh mới có thể bao gồm
nhiều tỉnh cũ có kinh tuyến trục khác nhau. Mỗi profile ứng với
một context kinh tuyến trục cụ thể.

Khi resolve ra nhiều profiles → check_crs() phải trả WARNING
yêu cầu KS chọn old province context.

Source: TT26/2024/TT-BTNMT, Phụ lục kinh tuyến trục.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class CRSProfile:
    """Kinh tuyến trục cho một ĐVHC tại một khoảng thời gian."""

    admin_unit_code: str  # Mã ĐVHC áp dụng
    valid_from: date
    valid_to: date | None  # None = còn hiệu lực
    central_meridian: float  # Kinh tuyến trục (độ)
    source_doc: str  # VD: "TT26/2024, Phụ lục"
    applies_to_legacy_codes: tuple[str, ...] = ()
    notes: str | None = None


# ============================================================
# CRS PROFILES DATA
# Source: TT26/2024/TT-BTNMT, Phụ lục kinh tuyến trục.
# Populate đầy đủ trước production deploy.
# ============================================================

CRS_PROFILES: list[CRSProfile] = [
    # --- Hà Nội ---
    CRSProfile(
        admin_unit_code="01",
        valid_from=date(2025, 1, 15),
        valid_to=None,
        central_meridian=105.75,
        source_doc="TT26/2024/TT-BTNMT, Phụ lục kinh tuyến trục",
    ),
    # --- TP Hồ Chí Minh ---
    CRSProfile(
        admin_unit_code="79",
        valid_from=date(2025, 1, 15),
        valid_to=None,
        central_meridian=105.75,
        source_doc="TT26/2024/TT-BTNMT, Phụ lục kinh tuyến trục",
        notes="Xác nhận lại kinh tuyến trục chính thức cho HCM",
    ),
    # TODO: Populate đầy đủ 34 tỉnh/TP + profiles cho tỉnh cũ trước sáp nhập
]


def resolve_crs_profiles(
    admin_code: str,
    as_of: date,
    legacy_admin_code: str | None = None,
) -> list[CRSProfile]:
    """Tìm CRS profiles hợp lệ. Có thể trả NHIỀU profile.

    Caller (check_crs) phải xử lý:
    - 0 profiles → WARNING "Không tìm thấy CRS profile"
    - 1 profile → dùng trực tiếp
    - >1 profiles → WARNING "Nhiều kinh tuyến trục, KS chọn context"
    """
    results: list[CRSProfile] = []

    # Nếu có legacy_admin_code, ưu tiên tìm theo mã cũ
    if legacy_admin_code:
        for p in CRS_PROFILES:
            if legacy_admin_code == p.admin_unit_code or (
                legacy_admin_code in p.applies_to_legacy_codes
            ):
                if p.valid_from <= as_of and (
                    p.valid_to is None or as_of <= p.valid_to
                ):
                    results.append(p)
        if results:
            return results

    # Tìm theo admin_code hiện tại
    for p in CRS_PROFILES:
        if p.admin_unit_code == admin_code:
            if p.valid_from <= as_of and (
                p.valid_to is None or as_of <= p.valid_to
            ):
                results.append(p)

    # Tìm qua applies_to_legacy_codes
    if not results:
        for p in CRS_PROFILES:
            if admin_code in p.applies_to_legacy_codes:
                if p.valid_from <= as_of and (
                    p.valid_to is None or as_of <= p.valid_to
                ):
                    results.append(p)

    return results
