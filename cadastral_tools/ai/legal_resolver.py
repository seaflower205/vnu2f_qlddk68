"""
Legal Resolver — Chọn đúng bộ quy định cho ngữ cảnh cụ thể.

Không bao giờ tự "phán luật" nếu thiếu căn cứ.
Không đủ rule → WARNING, không tự kết luận.

Ba chế độ:
1. current_law:       Nghiệm thu / QA theo quy định hiện hành
2. historical_law:    Kiểm tra dữ liệu cũ theo snapshot pháp lý tại ngày X
3. migration_warning: Chuyển đổi dữ liệu cũ → hệ thống mới (2 lớp đánh giá)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal

from .legal_registry import LEGAL_RULES, LegalRule

EvaluationMode = Literal["current_law", "historical_law", "migration_warning"]

ResolutionStatus = Literal[
    "RESOLVED",
    "NO_MATCH",
    "AMBIGUOUS",
    "SOURCE_UNVERIFIED",
]


@dataclass
class LegalContext:
    """Ngữ cảnh pháp lý — bắt buộc truyền khi chạy QA.

    Attributes:
        mode: Chế độ đánh giá.
        as_of_date: Ngày áp dụng pháp lý (REQUIRED).
        admin_unit_code: Mã ĐVHC chính (current-law / historical-law).
        operation_type: "lap_moi" | "chinh_ly" | "tach_thua" | "nghiem_thu"
            | "chuyen_doi_du_lieu" | "kiem_tra_du_lieu_lich_su"
        document_date: Ngày lập bản đồ / hồ sơ.
        audit_date: Ngày kiểm tra.
        historical_admin_unit_code: Mã ĐVHC tại thời điểm lập (tỉnh cũ).
            Chỉ dùng trong migration_warning mode.
        current_admin_unit_code: Mã ĐVHC hiện tại (tỉnh mới sau sáp nhập).
            Chỉ dùng trong migration_warning mode.
        secondary_as_of_date: Ngày hiện hành (cho migration).
    """

    mode: EvaluationMode
    as_of_date: date
    admin_unit_code: str | None = None
    operation_type: str | None = None
    document_date: date | None = None
    audit_date: date | None = None
    # Migration-specific
    historical_admin_unit_code: str | None = None
    current_admin_unit_code: str | None = None
    secondary_as_of_date: date | None = None


@dataclass
class ResolvedRules:
    """Kết quả resolve — dùng trong audit report.

    Attributes:
        resolution_status: Phân biệt rõ lý do rules=[]:
            RESOLVED = resolve thành công
            NO_MATCH = không tìm thấy rule
            AMBIGUOUS = nhiều rule cùng priority
            SOURCE_UNVERIFIED = có rule nhưng chưa hash nguồn
        is_ambiguous: True khi nhiều rule cùng priority.
            Downstream chỉ tạo WARNING, KHÔNG tạo ERROR.
    """

    mode: EvaluationMode
    as_of_date: date
    rules: list[LegalRule]
    warnings: list[str]
    legal_snapshot_version: str
    source_integrity: str  # "VERIFIED" | "PARTIALLY_VERIFIED" | "UNVERIFIED"
    resolution_status: ResolutionStatus
    is_ambiguous: bool = False


def resolve_rules(
    subject: str,
    context: LegalContext,
) -> ResolvedRules:
    """Resolve bộ rule cho subject tại context.

    Logic:
    1. Filter rules by subject + effective_at + admin_unit match
    2. Warn if admin_code=None but provincial rules exist
    3. Sort by priority, select top tier
    4. If ambiguous (>1 top rules) → is_ambiguous=True, rules=[]
    5. Check source_verified → set source_integrity + resolution_status
    """
    warnings: list[str] = []

    candidates = [
        r
        for r in LEGAL_RULES
        if r.subject == subject
        and r.is_effective_at(context.as_of_date)
        and r.matches_admin_unit(
            context.admin_unit_code, context.as_of_date
        )
    ]

    # Cảnh báo nếu thiếu ĐVHC nhưng tồn tại rule cấp tỉnh
    if context.admin_unit_code is None:
        has_provincial = any(
            r
            for r in LEGAL_RULES
            if r.subject == subject
            and r.is_effective_at(context.as_of_date)
            and r.jurisdiction != "national"
        )
        if has_provincial:
            warnings.append(
                "Thiếu mã ĐVHC nên không thể áp dụng rule địa phương. "
                "Chỉ áp dụng rule quốc gia. KS cần cung cấp mã ĐVHC."
            )

    is_ambiguous = False
    resolution_status: ResolutionStatus = "RESOLVED"

    if not candidates:
        resolution_status = "NO_MATCH"
        warnings.append(
            f"Chưa có rule pháp lý xác định cho subject='{subject}' "
            f"tại {context.as_of_date}, ĐVHC={context.admin_unit_code}. "
            f"KS cần xác minh văn bản nguồn."
        )
    else:
        # Priority-based selection
        candidates.sort(key=lambda r: r.priority, reverse=True)
        top_priority = candidates[0].priority
        top_rules = [
            r for r in candidates if r.priority == top_priority
        ]

        # Ambiguous → rules=[], chỉ WARNING, KHÔNG tạo ERROR
        if len(top_rules) > 1:
            rule_ids = ", ".join(r.rule_id for r in top_rules)
            warnings.append(
                f"Nhiều rule cùng priority cho subject='{subject}': "
                f"[{rule_ids}]. "
                f"Hệ thống không tự chọn — KS cần xác nhận rule "
                f"áp dụng."
            )
            is_ambiguous = True
            resolution_status = "AMBIGUOUS"
            top_rules = []

        candidates = top_rules

    # Source integrity
    if not candidates:
        source_integrity = "UNVERIFIED"
    elif all(r.source_verified for r in candidates):
        source_integrity = "VERIFIED"
    elif any(r.source_verified for r in candidates):
        source_integrity = "PARTIALLY_VERIFIED"
    else:
        source_integrity = "UNVERIFIED"
        if resolution_status == "RESOLVED":
            resolution_status = "SOURCE_UNVERIFIED"

    return ResolvedRules(
        mode=context.mode,
        as_of_date=context.as_of_date,
        rules=candidates,
        warnings=warnings,
        legal_snapshot_version="2026-06-verified",
        source_integrity=source_integrity,
        resolution_status=resolution_status,
        is_ambiguous=is_ambiguous,
    )


def resolve_migration_rules(
    subject: str,
    context: LegalContext,
) -> tuple[ResolvedRules, ResolvedRules]:
    """Migration-warning mode: resolve 2 bộ rule, 2 mã ĐVHC.

    Returns:
        (historical_rules, current_rules)

    Kết quả tách 2 nhóm:
    - ERROR = sai theo luật tại thời điểm lập hồ sơ
    - WARNING = không còn phù hợp luật hiện hành, KS xem xét chỉnh lý
    """
    if context.mode != "migration_warning":
        raise ValueError(
            f"Expected mode='migration_warning', got '{context.mode}'"
        )
    if context.document_date is None:
        raise ValueError(
            "migration_warning mode yêu cầu document_date"
        )
    if context.secondary_as_of_date is None:
        raise ValueError(
            "migration_warning mode yêu cầu secondary_as_of_date"
        )

    historical_ctx = LegalContext(
        mode="historical_law",
        as_of_date=context.document_date,
        admin_unit_code=context.historical_admin_unit_code,
        operation_type="kiem_tra_du_lieu_lich_su",
    )
    current_ctx = LegalContext(
        mode="current_law",
        as_of_date=context.secondary_as_of_date,
        admin_unit_code=context.current_admin_unit_code,
        operation_type=context.operation_type,
    )

    return (
        resolve_rules(subject, historical_ctx),
        resolve_rules(subject, current_ctx),
    )
