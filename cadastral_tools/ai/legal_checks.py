"""Mechanically extracted functions from step3_legal_audit.py."""
from __future__ import annotations

import logging
from typing import Any

from qgis.core import QgsGeometry

from .legal_resolver import LegalContext
from .qa_models import FeatureSnapshot, LayerSnapshot, QAIssue
from .lookup_tables.admin_units import normalize_admin_code, resolve_admin_unit, resolve_province
from .lookup_tables.min_area_rules import get_min_area_rule, MinAreaRuleResult

logger = logging.getLogger(__name__)

def check_duplicate_parcel_numbers(
    snapshot: LayerSnapshot,
    legal_context: LegalContext,
    default_commune_code: str | None = None,
    is_cancelled: Any | None = None,
) -> tuple[list[QAIssue], bool]:
    issues: list[QAIssue] = []
    
    # 1. Normalize default commune code
    default_commune_code_valid = None
    if default_commune_code:
        norm_default = normalize_admin_code(default_commune_code, expected_level="commune")
        if norm_default:
            unit = resolve_admin_unit(norm_default, legal_context.as_of_date)
            if unit and unit.level == "commune":
                default_commune_code_valid = unit.code
    
    # 2. Build frequency map
    # tuple: (commune_code, SoTo, SoThua) -> list[FeatureSnapshot]
    freq_map: dict[tuple[str, int, int], list[FeatureSnapshot]] = {}
    feature_warnings: list[tuple[FeatureSnapshot, str]] = []
    
    for feature in snapshot.features:
        if is_cancelled and is_cancelled():
            return issues, True
            
        raw_admin = feature.attrs.get("MaDVHC")  # Hoặc lấy từ field mapping nếu có
        admin_code = normalize_admin_code(raw_admin, expected_level="commune")
        unit = resolve_admin_unit(admin_code, legal_context.as_of_date) if admin_code else None
        
        commune_code = None
        warning_msg = None
        
        if unit is None or unit.level != "commune":
            if default_commune_code_valid:
                commune_code = default_commune_code_valid
                warning_msg = "default commune code used"
            else:
                issues.append(
                    QAIssue(
                        rule_id="DUP-002",
                        severity="WARNING",
                        feature_id=feature.fid,
                        layer_id=snapshot.layer_id,
                        geometry_ref=None,
                        bbox=feature.bbox,
                        description="Thiếu hoặc không xác định được mã ĐVHC cấp xã; không đủ căn cứ kết luận trùng số tờ/số thửa.",
                        confidence="deterministic"
                    )
                )
                continue
        else:
            commune_code = unit.code
            
        raw_so_to = feature.attrs.get("SoTo")
        raw_so_thua = feature.attrs.get("SoThua")
        
        try:
            so_to = int(raw_so_to) if raw_so_to is not None else 0
            so_thua = int(raw_so_thua) if raw_so_thua is not None else 0
        except ValueError:
            continue
            
        if so_to <= 0 or so_thua <= 0:
            continue
            
        key = (commune_code, so_to, so_thua)
        if key not in freq_map:
            freq_map[key] = []
        freq_map[key].append(feature)
        if warning_msg:
            feature_warnings.append((feature, warning_msg))
            
    # 3. Detect duplicates
    for key, feats in freq_map.items():
        if len(feats) > 1:
            for feat in feats:
                # Tìm xem feature này có warning default code used không
                warn = [w for f, w in feature_warnings if f.fid == feat.fid]
                desc = f"Trùng lặp Số tờ={key[1]}, Số thửa={key[2]} trong cùng ĐVHC cấp xã ({key[0]})."
                if warn:
                    desc += f" (Cảnh báo: {warn[0]})"
                    
                issues.append(
                    QAIssue(
                        rule_id="DUP-001",
                        severity="ERROR",
                        feature_id=feat.fid,
                        layer_id=snapshot.layer_id,
                        geometry_ref=None,
                        bbox=feat.bbox,
                        description=desc,
                        confidence="deterministic"
                    )
                )
                
    return issues, False

def check_minimum_area(
    snapshot: LayerSnapshot,
    legal_context: LegalContext,
    operation_type: str,
    default_commune_code: str | None = None,
    default_province_code: str | None = None,
    is_cancelled: Any | None = None,
) -> tuple[list[QAIssue], bool]:
    issues: list[QAIssue] = []
    
    # 1. Normalize defaults
    default_commune_code_valid = None
    if default_commune_code:
        norm_default = normalize_admin_code(default_commune_code, expected_level="commune")
        if norm_default:
            unit = resolve_admin_unit(norm_default, legal_context.as_of_date)
            if unit and unit.level == "commune":
                default_commune_code_valid = unit.code
                
    default_province_code_valid = None
    if default_province_code:
        norm_default = normalize_admin_code(default_province_code, expected_level="province")
        if norm_default:
            unit = resolve_admin_unit(norm_default, legal_context.as_of_date)
            if unit and unit.level == "province":
                default_province_code_valid = unit.code

    for feature in snapshot.features:
        if is_cancelled and is_cancelled():
            return issues, True
            
        # 2. Guard geometry
        geom = QgsGeometry()
        geom.fromWkb(feature.wkb)
        if geom.isNull() or geom.isEmpty() or not geom.isGeosValid():
            # Không tính diện tích, bỏ qua check min_area
            # Có thể báo warning/error hình học ở đây hoặc topology đã báo
            continue
            
        area_m2 = geom.area()
        
        # 3. Resolve Province
        raw_admin = feature.attrs.get("MaDVHC")
        admin_code = normalize_admin_code(raw_admin, expected_level="commune")
        
        province_unit = None
        if admin_code:
            province_unit = resolve_province(admin_code, legal_context.as_of_date)
            
        if not province_unit:
            if default_commune_code_valid:
                province_unit = resolve_province(default_commune_code_valid, legal_context.as_of_date)
                
        if not province_unit:
            if default_province_code_valid:
                province_unit = resolve_province(default_province_code_valid, legal_context.as_of_date)
                
        if not province_unit:
            issues.append(
                QAIssue(
                    rule_id="MINAREA-002",
                    severity="WARNING",
                    feature_id=feature.fid,
                    layer_id=snapshot.layer_id,
                    geometry_ref=None,
                    bbox=feature.bbox,
                    description="Không xác định được ĐVHC cấp tỉnh, bỏ qua kiểm tra diện tích tối thiểu.",
                    confidence="deterministic"
                )
            )
            continue
            
        # 4. Resolve Land Type
        land_type = feature.attrs.get("LoaiDat")
        if not land_type:
            continue
        land_type = str(land_type).strip()
            
        # 5. Look up rule
        rule_result = get_min_area_rule(
            admin_unit_code=province_unit.code,
            land_type=land_type,
            as_of=legal_context.as_of_date,
            zone_type=None,
        )
        
        if rule_result.status == "NO_MATCH":
            issues.append(
                QAIssue(
                    rule_id="MINAREA-003",
                    severity="WARNING",
                    feature_id=feature.fid,
                    layer_id=snapshot.layer_id,
                    geometry_ref=None,
                    bbox=feature.bbox,
                    description="Không tìm thấy quy định diện tích tối thiểu tách thửa cho loại đất này.",
                    confidence="deterministic"
                )
            )
            continue
            
        if rule_result.status == "AMBIGUOUS":
            issues.append(
                QAIssue(
                    rule_id="MINAREA-004",
                    severity="WARNING",
                    feature_id=feature.fid,
                    layer_id=snapshot.layer_id,
                    geometry_ref=None,
                    bbox=feature.bbox,
                    description="Xung đột quy định diện tích tối thiểu (nhiều hơn 1 quy định áp dụng).",
                    confidence="deterministic"
                )
            )
            continue
            
        rule = rule_result.rule
        if rule and rule.min_area_m2 is not None:
            if area_m2 < rule.min_area_m2:
                desc = f"Diện tích ({area_m2:.1f} m²) nhỏ hơn mức tối thiểu quy định ({rule.min_area_m2} m²)."
                
                if rule_result.status in ("MOCK", "UNVERIFIED"):
                    desc += f" (Cảnh báo: Rule diện tích tối thiểu là mock/unverified data, không dùng nghiệm thu chính thức)"
                
                issues.append(
                    QAIssue(
                        rule_id="MINAREA-001",
                        severity="WARNING",  # Luôn WARNING trong v1
                        feature_id=feature.fid,
                        layer_id=snapshot.layer_id,
                        geometry_ref=None,
                        bbox=feature.bbox,
                        description=desc,
                        confidence="deterministic"
                    )
                )
                
    return issues, False
