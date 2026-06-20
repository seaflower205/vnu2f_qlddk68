"""
Kiểm tra thuộc tính dựa trên snapshot data. (Thread-safe)
"""
from __future__ import annotations

import logging
from typing import Any

from .qa_models import LayerSnapshot, QAIssue
from .legal_resolver import LegalContext
from .lookup_tables.field_mapping import resolve_fields
from .lookup_tables.land_use_codes import is_valid_code

logger = logging.getLogger(__name__)

REQUIRED_CANONICAL_FIELDS = ["so_to", "so_thua", "dien_tich", "loai_dat"]

def run_attribute_checks(
    main_snapshot: LayerSnapshot,
    legal_context: LegalContext,
    progress_callback: Any | None = None,
    is_cancelled: Any | None = None,
) -> tuple[list[QAIssue], bool]:
    """
    Chạy chuỗi kiểm tra thuộc tính an toàn.
    Trả về: (danh sách lỗi, cờ bị huỷ hay không)
    """
    issues: list[QAIssue] = []
    features = main_snapshot.features
    total_features = len(features)
    
    if total_features == 0:
        return issues, False

    def check_cancel() -> bool:
        return is_cancelled() if is_cancelled else False

    # 1. Xác định mapping trường
    field_map = resolve_fields(main_snapshot.fields, REQUIRED_CANONICAL_FIELDS)
    
    missing_fields = [c for c, a in field_map.items() if a is None]
    if missing_fields:
        issues.append(
            QAIssue(
                rule_id="ATTR-MISSING-001",
                severity="ERROR",
                feature_id=None,
                layer_id=main_snapshot.layer_id,
                geometry_ref="Cấu trúc Layer",
                bbox=None,
                description=f"Thiếu các cột bắt buộc: {', '.join(missing_fields)}. Vui lòng kiểm tra field mapping.",
            )
        )
    
    actual_so_to = field_map.get("so_to")
    actual_so_thua = field_map.get("so_thua")
    actual_dien_tich = field_map.get("dien_tich")
    actual_loai_dat = field_map.get("loai_dat")

    from qgis.core import QgsGeometry

    # 2. Kiểm tra NULL, Code, Area
    for i, feat in enumerate(features):
        if i % 1000 == 0:
            if check_cancel():
                return issues, True
            if progress_callback:
                progress_callback(100.0 * i / total_features, f"Kiểm tra Thuộc tính ({i}/{total_features})...")
                
        attrs = feat.attrs
        fid = feat.fid
        
        # Check NULLs
        if actual_so_to and attrs.get(actual_so_to) in (None, "", "NULL"):
            issues.append(
                QAIssue(
                    rule_id="ATTR-NULL-001",
                    severity="ERROR",
                    feature_id=fid,
                    layer_id=main_snapshot.layer_id,
                    geometry_ref=None,
                    bbox=feat.bbox,
                    description=f"Trường {actual_so_to} bị trống (NULL).",
                )
            )
            
        if actual_so_thua and attrs.get(actual_so_thua) in (None, "", "NULL"):
            issues.append(
                QAIssue(
                    rule_id="ATTR-NULL-002",
                    severity="ERROR",
                    feature_id=fid,
                    layer_id=main_snapshot.layer_id,
                    geometry_ref=None,
                    bbox=feat.bbox,
                    description=f"Trường {actual_so_thua} bị trống (NULL).",
                )
            )

        # Check Loai Dat
        if actual_loai_dat:
            ma_dat = attrs.get(actual_loai_dat)
            if ma_dat in (None, "", "NULL"):
                issues.append(
                    QAIssue(
                        rule_id="ATTR-NULL-003",
                        severity="ERROR",
                        feature_id=fid,
                        layer_id=main_snapshot.layer_id,
                        geometry_ref=None,
                        bbox=feat.bbox,
                        description=f"Trường {actual_loai_dat} bị trống (NULL).",
                    )
                )
            else:
                ma_dat_str = str(ma_dat).strip().upper()
                sub_codes = [c.strip() for c in ma_dat_str.replace(",", "+").split("+") if c.strip()]
                for code in sub_codes:
                    if not is_valid_code(code, legal_context.as_of_date):
                        issues.append(
                            QAIssue(
                                rule_id="ATTR-LEGAL-001",
                                severity="ERROR",
                                feature_id=fid,
                                layer_id=main_snapshot.layer_id,
                                geometry_ref=None,
                                bbox=feat.bbox,
                                description=f"Mã loại đất '{code}' không hợp lệ tại thời điểm {legal_context.as_of_date}.",
                            )
                        )

        # Compare Area
        if actual_dien_tich:
            dt_attr_raw = attrs.get(actual_dien_tich)
            if dt_attr_raw in (None, "", "NULL"):
                issues.append(
                    QAIssue(
                        rule_id="ATTR-NULL-004",
                        severity="ERROR",
                        feature_id=fid,
                        layer_id=main_snapshot.layer_id,
                        geometry_ref=None,
                        bbox=feat.bbox,
                        description=f"Trường {actual_dien_tich} bị trống (NULL).",
                    )
                )
            else:
                try:
                    dt_attr = float(dt_attr_raw)
                    geom = QgsGeometry()
                    geom.fromWkb(feat.wkb)
                    if not geom.isNull() and not geom.isEmpty():
                        dt_geom = geom.area()
                        if abs(dt_attr - dt_geom) > 0.1:
                            issues.append(
                                QAIssue(
                                    rule_id="ATTR-AREA-001",
                                    severity="WARNING",
                                    feature_id=fid,
                                    layer_id=main_snapshot.layer_id,
                                    geometry_ref=None,
                                    bbox=feat.bbox,
                                    description=f"Diện tích lệch: Ghi sổ {dt_attr:.2f} m² vs Hình học {dt_geom:.2f} m².",
                                )
                            )
                except (ValueError, TypeError):
                    issues.append(
                        QAIssue(
                            rule_id="ATTR-FORMAT-001",
                            severity="ERROR",
                            feature_id=fid,
                            layer_id=main_snapshot.layer_id,
                            geometry_ref=None,
                            bbox=feat.bbox,
                            description=f"Diện tích '{dt_attr_raw}' sai định dạng số.",
                        )
                    )

    return issues, False
