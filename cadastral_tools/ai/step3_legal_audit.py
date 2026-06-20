"""
Phase 3: Legal & Business Logic Validation

Kiểm tra nghiệp vụ địa chính:
1. Trùng lặp Số tờ + Số thửa (cấp xã)
2. Diện tích tách thửa tối thiểu (cấp tỉnh)
"""
from __future__ import annotations

import logging
from typing import Any

from qgis.core import QgsGeometry

from .legal_resolver import LegalContext
from .qa_models import FeatureSnapshot, LayerSnapshot, QAIssue
from .lookup_tables.admin_units import normalize_admin_code, resolve_admin_unit, resolve_province
from .lookup_tables.min_area_rules import get_min_area_rule, MinAreaRuleResult

logger = logging.getLogger(__name__)


def run_legal_audit_checks(
    snapshot: LayerSnapshot,
    legal_context: LegalContext,
    operation_type: str,
    default_commune_code: str | None = None,
    default_province_code: str | None = None,
    progress_callback: Any | None = None,
    is_cancelled: Any | None = None,
) -> tuple[list[QAIssue], bool]:
    """Chạy toàn bộ các bước Legal Audit trên LayerSnapshot.
    
    Returns:
        (issues, is_cancelled)
    """
    issues: list[QAIssue] = []
    
    # Check Duplicate
    if progress_callback:
        progress_callback(10, "Kiểm tra trùng lặp Số tờ/Số thửa...")
        
    dup_issues, cancelled = check_duplicate_parcel_numbers(
        snapshot=snapshot,
        legal_context=legal_context,
        default_commune_code=default_commune_code,
        is_cancelled=is_cancelled,
    )
    issues.extend(dup_issues)
    if cancelled:
        return issues, True
        
    # Check Minimum Area
    if progress_callback:
        progress_callback(50, "Kiểm tra diện tích tách thửa tối thiểu...")
        
    area_issues, cancelled = check_minimum_area(
        snapshot=snapshot,
        legal_context=legal_context,
        operation_type=operation_type,
        default_commune_code=default_commune_code,
        default_province_code=default_province_code,
        is_cancelled=is_cancelled,
    )
    issues.extend(area_issues)
    if cancelled:
        return issues, True
        
    return issues, False

from .legal_checks import check_duplicate_parcel_numbers, check_minimum_area
