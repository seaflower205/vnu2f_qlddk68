"""
Bảng diện tích tối thiểu tách thửa — theo QĐ UBND cấp tỉnh.

Dùng mã ĐVHC làm khóa (không dùng tên tỉnh), có version.
as_of REQUIRED — không fallback date.today().

Trả về MinAreaRuleResult với status rõ ràng:
RESOLVED, NO_MATCH, AMBIGUOUS, MOCK, UNVERIFIED
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal


@dataclass(frozen=True)
class MinAreaRule:
    """Quy định diện tích tối thiểu cho tách thửa."""

    admin_unit_code: str  # Mã ĐVHC cấp tỉnh
    land_type: str  # "dat_o_do_thi" | "dat_o_nong_thon" | "dat_nong_nghiep"
    zone_type: str | None  # "trung_tam" | "ngoai_o" | None = chung
    min_area_m2: float | None
    min_frontage_m: float | None  # Chiều rộng mặt tiền tối thiểu
    min_depth_m: float | None  # Chiều sâu tối thiểu
    source_doc: str  # Số QĐ UBND tỉnh
    article: str | None  # Điều khoản cụ thể
    effective_from: date
    effective_to: date | None  # None = còn hiệu lực
    notes: str | None = None
    is_mock: bool = False
    source_verified: bool = False


@dataclass(frozen=True)
class MinAreaRuleResult:
    """Kết quả tra cứu rule diện tích tối thiểu."""
    status: Literal["RESOLVED", "NO_MATCH", "AMBIGUOUS", "MOCK", "UNVERIFIED"]
    rule: MinAreaRule | None
    candidates: list[MinAreaRule] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ============================================================
# MIN AREA RULES DATA
# Source: QĐ UBND cấp tỉnh.
# ============================================================

MIN_AREA_RULES: list[MinAreaRule] = [
    # --- Seed data minh họa ---
    MinAreaRule(
        admin_unit_code="01",  # Hà Nội
        land_type="ODT",  # Đất ở đô thị (mock classification)
        zone_type=None,
        min_area_m2=30.0,
        min_frontage_m=3.0,
        min_depth_m=3.0,
        source_doc="QĐ 20/2017/QĐ-UBND (MOCK)",
        article="Điều 5",
        effective_from=date(2017, 6, 1),
        effective_to=None,
        is_mock=True,
        source_verified=False,
    ),
    MinAreaRule(
        admin_unit_code="01",  # Hà Nội
        land_type="ONT",  # Đất ở nông thôn (mock classification)
        zone_type=None,
        min_area_m2=60.0,
        min_frontage_m=4.0,
        min_depth_m=4.0,
        source_doc="QĐ 20/2017/QĐ-UBND (MOCK)",
        article="Điều 5",
        effective_from=date(2017, 6, 1),
        effective_to=None,
        is_mock=True,
        source_verified=False,
    )
]


def get_min_area_rule(
    admin_unit_code: str,
    land_type: str,
    as_of: date,
    zone_type: str | None = None,
) -> MinAreaRuleResult:
    """Tìm rule diện tích tối thiểu phù hợp nhất.

    Args:
        admin_unit_code: Mã ĐVHC cấp tỉnh.
        land_type: Loại đất.
        as_of: Ngày áp dụng. REQUIRED — TypeError nếu thiếu.
        zone_type: Loại vùng (optional).

    Returns:
        MinAreaRuleResult
    """
    candidates = [
        r
        for r in MIN_AREA_RULES
        if r.admin_unit_code == admin_unit_code
        and r.land_type == land_type
        and r.effective_from <= as_of
        and (r.effective_to is None or as_of <= r.effective_to)
    ]

    if not candidates:
        return MinAreaRuleResult(
            status="NO_MATCH",
            rule=None,
            warnings=["Không tìm thấy quy định diện tích tối thiểu phù hợp."],
        )

    # Ưu tiên zone_type khớp chính xác
    exact_matches = [r for r in candidates if r.zone_type == zone_type]
    
    # Nếu không có match chính xác, tìm fallback quy định chung
    if not exact_matches:
        exact_matches = [r for r in candidates if r.zone_type is None]
        
    if not exact_matches:
        return MinAreaRuleResult(
            status="NO_MATCH",
            rule=None,
            candidates=candidates,
            warnings=["Không có quy định diện tích tối thiểu khớp với zone_type yêu cầu."],
        )

    if len(exact_matches) > 1:
        return MinAreaRuleResult(
            status="AMBIGUOUS",
            rule=None,
            candidates=exact_matches,
            warnings=["Có nhiều hơn 1 quy định diện tích tối thiểu có hiệu lực cùng lúc (Xung đột pháp lý)."],
        )

    rule = exact_matches[0]
    
    if rule.is_mock:
        return MinAreaRuleResult(
            status="MOCK",
            rule=rule,
            candidates=exact_matches,
            warnings=["Rule diện tích tối thiểu là mock/test data, không dùng nghiệm thu chính thức."],
        )
        
    if not rule.source_verified:
        return MinAreaRuleResult(
            status="UNVERIFIED",
            rule=rule,
            candidates=exact_matches,
            warnings=["Rule diện tích tối thiểu chưa được verify (UNVERIFIED), không dùng nghiệm thu chính thức."],
        )

    return MinAreaRuleResult(
        status="RESOLVED",
        rule=rule,
        candidates=exact_matches,
    )
