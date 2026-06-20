"""
Safety Net — CRS Validation + Backup/Restore.

Đây là bước đầu tiên bắt buộc trước mọi quy trình QA.
Nhiệm vụ:
1. Validate CRS theo TT26/2024 (VN-2000, múi 3°, k₀=0.9999)
2. Tạo backup layer trước khi thao tác
3. Restore từ backup khi cần

Không auto-fix. Chỉ highlight + PASS/WARNING/BLOCK.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from .compat import require_qgis4
from .legal_resolver import LegalContext, ResolvedRules, resolve_rules
from .lookup_tables.crs_profiles import resolve_crs_profiles
from .preflight_backup import create_backup, restore_from_backup
from .preflight_crs_parser import extract_wkt_params as _extract_wkt_params

logger = logging.getLogger(__name__)

# ============================================================
# CRS Validation
# ============================================================

# VN-2000 EPSG code ranges
# 3° zones: 9210-9213 (official EPSG for VN-2000 3° TM)
# 6° zones: 3405-3408 (VN-2000 UTM 6°)
# Geographic: 4756 (VN-2000 geographic)
_VN2000_3DEG_EPSG = set(range(9210, 9214))
_VN2000_6DEG_EPSG = {3405, 3406, 3407, 3408}
_VN2000_GEOGRAPHIC = {4756}


@dataclass
class CRSCheckResult:
    """Kết quả kiểm tra CRS.

    Mapping rõ ràng — UI không phải đoán:
    - PASS    / can_continue=True  → VN-2000 3° đúng, legal VERIFIED
    - WARNING / can_continue=True  → CRS OK nhưng legal UNVERIFIED,
                                     hoặc custom WKT, hoặc 6° legacy,
                                     hoặc nhiều KTT sau sáp nhập
    - BLOCK   / can_continue=False → Không phải VN-2000, hoặc 6° chính thức
    """

    status: Literal["PASS", "WARNING", "BLOCK"]
    can_continue: bool
    zone_width: int | None = None
    central_meridian: float | None = None
    scale_factor: float | None = None
    matched_province: str | None = None
    reason: str | None = None
    legal_rule_id: str | None = None
    # Propagate legal context
    legal_warnings: list[str] = field(default_factory=list)
    source_integrity: str | None = None


def _parse_epsg_code(auth_id: str) -> int | None:
    """Extract EPSG code number from auth_id string."""
    if not auth_id or not auth_id.startswith("EPSG:"):
        return None
    try:
        return int(auth_id.split(":")[1])
    except (ValueError, IndexError):
        return None


def _validate_by_epsg(
    epsg_code: int,
    crs_rules: ResolvedRules,
) -> CRSCheckResult:
    """Validate CRS bằng EPSG code."""
    legal_rule_id = None
    if crs_rules.rules:
        legal_rule_id = crs_rules.rules[0].rule_id

    if epsg_code in _VN2000_3DEG_EPSG:
        return CRSCheckResult(
            status="PASS",
            can_continue=True,
            zone_width=3,
            reason="VN-2000 múi 3° (EPSG chính thức).",
            legal_rule_id=legal_rule_id,
        )

    if epsg_code in _VN2000_6DEG_EPSG:
        return CRSCheckResult(
            status="BLOCK",
            can_continue=False,
            zone_width=6,
            reason=(
                f"VN-2000 múi 6° (EPSG:{epsg_code}). "
                "TT26/2024 yêu cầu múi 3° cho BĐĐC chính thức. "
                "Múi 6° chỉ chấp nhận cho layer legacy/reference."
            ),
            legal_rule_id=legal_rule_id,
        )

    if epsg_code in _VN2000_GEOGRAPHIC:
        return CRSCheckResult(
            status="WARNING",
            can_continue=True,
            reason=(
                "VN-2000 geographic (EPSG:4756). "
                "Chưa có phép chiếu — cần chuyển đổi sang "
                "VN-2000 3° TM trước khi tính diện tích."
            ),
            legal_rule_id=legal_rule_id,
        )

    # WGS84 và các CRS khác → BLOCK
    return CRSCheckResult(
        status="BLOCK",
        can_continue=False,
        reason=(
            f"CRS EPSG:{epsg_code} không phải VN-2000. "
            "TT26/2024 yêu cầu VN-2000, múi 3°, k₀=0.9999."
        ),
        legal_rule_id=legal_rule_id,
    )


def _validate_by_wkt(
    wkt: str,
    crs_rules: ResolvedRules,
) -> CRSCheckResult:
    """Validate CRS qua WKT khi không có EPSG."""
    legal_rule_id = None
    if crs_rules.rules:
        legal_rule_id = crs_rules.rules[0].rule_id

    params = _extract_wkt_params(wkt)

    # Check datum
    datum = params.get("datum", "")
    if "VN-2000" not in datum and "VN_2000" not in datum:
        return CRSCheckResult(
            status="BLOCK",
            can_continue=False,
            reason=(
                f"Datum '{datum}' không phải VN-2000. "
                "TT26/2024 yêu cầu VN-2000."
            ),
            legal_rule_id=legal_rule_id,
        )

    # Check scale factor
    sf = params.get("scale_factor")
    if sf is not None and abs(sf - 0.9999) > 1e-6:
        return CRSCheckResult(
            status="WARNING",
            can_continue=True,
            scale_factor=sf,
            reason=(
                f"Scale factor = {sf}, khác 0.9999. "
                "TT26/2024 yêu cầu k₀ = 0.9999."
            ),
            legal_rule_id=legal_rule_id,
        )

    # Check central meridian → infer zone width
    cm = params.get("central_meridian")

    return CRSCheckResult(
        status="WARNING",
        can_continue=True,
        central_meridian=cm,
        scale_factor=sf,
        reason=(
            "VN-2000 custom WKT (không có EPSG chính thức). "
            "KS cần xác nhận thông số chiếu."
        ),
        legal_rule_id=legal_rule_id,
    )


def check_crs(
    layer,
    legal_context: LegalContext,
    admin_code: str | None = None,
    legacy_admin_code: str | None = None,
) -> CRSCheckResult:
    """Validate CRS cho BĐĐC.

    TT26/2024 Điều 3: VN-2000, múi 3°, k₀=0.9999,
    kinh tuyến trục theo tỉnh/thành phố.

    Hỗ trợ old province context qua legacy_admin_code.
    Dùng crs_profiles.py — nếu resolve ra nhiều profiles → WARNING.

    Propagate legal warnings + source integrity.
    """
    require_qgis4("step0_preflight")

    crs_rules = resolve_rules("crs", legal_context)

    crs = layer.crs()
    epsg = crs.authid()
    epsg_code = _parse_epsg_code(epsg)

    # Validate CRS
    if epsg_code is not None:
        result = _validate_by_epsg(epsg_code, crs_rules)
    else:
        result = _validate_by_wkt(crs.toWkt(), crs_rules)

    # Propagate legal context warnings + source integrity
    result.legal_warnings = list(crs_rules.warnings)
    result.source_integrity = crs_rules.source_integrity

    # CRS kỹ thuật OK nhưng legal source UNVERIFIED → downgrade
    if (
        result.status == "PASS"
        and crs_rules.source_integrity != "VERIFIED"
    ):
        result.status = "WARNING"
        result.reason = (
            (result.reason or "")
            + " CRS kỹ thuật hợp lệ, nhưng nguồn rule pháp lý "
            "chưa verified."
        ).strip()

    # Ambiguous legal rules → WARNING
    if crs_rules.is_ambiguous:
        result.status = "WARNING"
        result.legal_warnings.append(
            "Rule CRS không xác định duy nhất. KS cần xác nhận."
        )

    # Validate kinh tuyến trục nếu có admin context
    if result.can_continue and (admin_code or legacy_admin_code):
        profiles = resolve_crs_profiles(
            admin_code or "",
            legal_context.as_of_date,
            legacy_admin_code,
        )
        if len(profiles) == 0:
            result.status = "WARNING"
            result.reason = (
                "Không tìm thấy CRS profile cho ĐVHC này. "
                "KS cần xác nhận kinh tuyến trục."
            )
        elif len(profiles) > 1:
            meridians = ", ".join(
                str(p.central_meridian) for p in profiles
            )
            result.status = "WARNING"
            result.reason = (
                f"Nhiều kinh tuyến trục hợp lệ ({meridians}) do ĐVHC "
                f"sau sáp nhập. KS cần chọn old province context."
            )
        else:
            profile = profiles[0]
            result.central_meridian = profile.central_meridian
            result.matched_province = profile.admin_unit_code
            # Validate central meridian matches CRS
            if (
                result.central_meridian is not None
                and hasattr(result, "central_meridian")
                and profile.central_meridian
            ):
                wkt_params = _extract_wkt_params(crs.toWkt())
                wkt_cm = wkt_params.get("central_meridian")
                if (
                    wkt_cm is not None
                    and abs(wkt_cm - profile.central_meridian) > 0.01
                ):
                    result.status = "WARNING"
                    result.reason = (
                        f"Kinh tuyến trục CRS ({wkt_cm}°) khác với "
                        f"kinh tuyến trục ĐVHC "
                        f"({profile.central_meridian}°)."
                    )

    return result
