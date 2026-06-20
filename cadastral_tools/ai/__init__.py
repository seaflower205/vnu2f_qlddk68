"""
AI Cadastral QA Framework.

Rule engine deterministic là core QA. LLM chỉ là optional assistant.
Hệ thống không tự "phán luật" nếu thiếu căn cứ.

Public API:
    - LegalContext, ResolvedRules: Ngữ cảnh pháp lý
    - resolve_rules, resolve_migration_rules: Resolve bộ quy định
    - LegalRule: Một quy định pháp lý
    - require_qgis4: Version guard
"""
from .compat import require_qgis4
from .legal_registry import LegalRule
from .legal_resolver import (
    EvaluationMode,
    LegalContext,
    ResolvedRules,
    ResolutionStatus,
    resolve_migration_rules,
    resolve_rules,
)

__all__ = [
    "EvaluationMode",
    "LegalContext",
    "LegalRule",
    "ResolvedRules",
    "ResolutionStatus",
    "require_qgis4",
    "resolve_migration_rules",
    "resolve_rules",
]
