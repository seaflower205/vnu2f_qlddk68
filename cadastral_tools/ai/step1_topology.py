"""
Kiểm tra Topology dựa trên snapshot data. (Thread-safe)
"""
from __future__ import annotations

import logging
from typing import Any

from .qa_models import LayerSnapshot, FeatureSnapshot, QAIssue
from .compat import require_qgis4

logger = logging.getLogger(__name__)

def run_topology_checks(
    main_snapshot: LayerSnapshot,
    boundary_snapshot: LayerSnapshot | None = None,
    progress_callback: Any | None = None,
    is_cancelled: Any | None = None,
) -> tuple[list[QAIssue], bool]:
    """
    Chạy chuỗi kiểm tra topology an toàn bằng WKB.
    Trả về: (danh sách lỗi, cờ bị huỷ hay không)
    """
    require_qgis4("step1_topology")
    
    issues: list[QAIssue] = []
    features = main_snapshot.features
    total_features = len(features)
    
    if total_features == 0:
        return issues, False

    from qgis.core import QgsGeometry, QgsSpatialIndex, QgsFeature

    def check_cancel() -> bool:
        return is_cancelled() if is_cancelled else False

    def report_prog(pct: float, msg: str):
        if progress_callback:
            progress_callback(pct, msg)

    valid_geometries: dict[int, QgsGeometry] = {}
    valid_features: list[FeatureSnapshot] = []

    # 1. Null/Empty & Invalid/Self-Intersection
    report_prog(0, "Kiểm tra hình học Null / Invalid...")
    for i, feat in enumerate(features):
        if i % 1000 == 0 and check_cancel():
            return issues, True
            
        geom = QgsGeometry()
        geom.fromWkb(feat.wkb)
        
        if geom.isNull() or geom.isEmpty():
            issues.append(
                QAIssue(
                    rule_id="TOPO-NULL-001",
                    severity="ERROR",
                    feature_id=feat.fid,
                    layer_id=main_snapshot.layer_id,
                    geometry_ref="Không xác định",
                    bbox=feat.bbox,
                    description="Hình học Null hoặc rỗng.",
                )
            )
            continue
            
        if not geom.isGeosValid():
            error_msg = geom.lastError() or "Lỗi hình học (Self-intersection, v.v.)"
            issues.append(
                QAIssue(
                    rule_id="TOPO-INVALID-001",
                    severity="ERROR",
                    feature_id=feat.fid,
                    layer_id=main_snapshot.layer_id,
                    geometry_ref="Toàn bộ hình",
                    bbox=feat.bbox,
                    description=f"Hình học không hợp lệ: {error_msg}.",
                )
            )
            continue
            
        valid_geometries[feat.fid] = geom
        valid_features.append(feat)

    if not valid_features:
        return issues, False
        
    if check_cancel():
        return issues, True

    # 2. Xây dựng Spatial Index từ các feature hợp lệ
    report_prog(15, "Đang xây dựng Spatial Index...")
    index = QgsSpatialIndex()
    for feat in valid_features:
        geom = valid_geometries[feat.fid]
        qgs_feat = QgsFeature(feat.fid)
        qgs_feat.setGeometry(geom)
        index.addFeature(qgs_feat)

    if check_cancel():
        return issues, True

    # 3. Detect Overlaps
    seen_pairs = set()
    total_valid = len(valid_features)
    for i, feat in enumerate(valid_features):
        if i % 500 == 0:
            if check_cancel():
                return issues, True
            pct = 15.0 + 50.0 * (i / total_valid)
            report_prog(pct, f"Kiểm tra chồng lấp ({i}/{total_valid})...")

        geom = valid_geometries[feat.fid]
        candidate_fids = index.intersects(geom.boundingBox())
        
        for cand_fid in candidate_fids:
            if cand_fid == feat.fid:
                continue
                
            pair = tuple(sorted((feat.fid, cand_fid)))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            
            cand_geom = valid_geometries.get(cand_fid)
            if cand_geom:
                try:
                    if geom.intersects(cand_geom):
                        intersection = geom.intersection(cand_geom)
                        if intersection.type() == 2 and intersection.area() > 0.001:
                            issues.append(
                                QAIssue(
                                    rule_id="TOPO-OVERLAP-001",
                                    severity="ERROR",
                                    feature_id=feat.fid,
                                    layer_id=main_snapshot.layer_id,
                                    geometry_ref=f"Giao với thửa ID: {cand_fid}",
                                    bbox=feat.bbox,
                                    description=f"Chồng lấn {intersection.area():.2f} m² với thửa ID {cand_fid}.",
                                )
                            )
                except Exception as e:
                    logger.warning(f"Lỗi khi check intersection {feat.fid} & {cand_fid}: {e}")

    if check_cancel():
        return issues, True

    # 4. Detect Gaps
    if boundary_snapshot:
        report_prog(80, "Kiểm tra khoảng hở (Gaps) với ranh giới...")
        
        try:
            # Thuật toán chuẩn xác cần tạo unary union
            geoms = list(valid_geometries.values())
            combined_geom = QgsGeometry.unaryUnion(geoms) if geoms else None
            
            if combined_geom:
                for b_feat in boundary_snapshot.features:
                    b_geom = QgsGeometry()
                    b_geom.fromWkb(b_feat.wkb)
                    if b_geom.isNull() or b_geom.isEmpty() or not b_geom.isGeosValid():
                        continue
                        
                    diff = b_geom.difference(combined_geom)
                    if diff and not diff.isEmpty() and diff.area() > 0.1: # Threshold
                        issues.append(
                            QAIssue(
                                rule_id="TOPO-GAP-001",
                                severity="WARNING",
                                feature_id=-1,
                                layer_id=main_snapshot.layer_id,
                                geometry_ref=f"Ranh vùng ID: {b_feat.fid}",
                                bbox=b_feat.bbox,
                                description=f"Phát hiện khoảng hở bên trong ranh giới tổng, diện tích hở: {diff.area():.2f} m².",
                            )
                        )
        except Exception as e:
            logger.warning(f"Lỗi khi check gap: {e}")
            
    if check_cancel():
        return issues, True

    # 5. Detect Slivers
    report_prog(90, "Đang quét các mảnh vụn (Slivers)...")
    for feat in valid_features:
        geom = valid_geometries[feat.fid]
        area = geom.area()
        if 0 < area < 1.0: # Diện tích dưới 1m2
            issues.append(
                QAIssue(
                    rule_id="TOPO-SLIVER-001",
                    severity="WARNING",
                    feature_id=feat.fid,
                    layer_id=main_snapshot.layer_id,
                    geometry_ref=f"S={area:.2f} m²",
                    bbox=feat.bbox,
                    description=f"Thửa đất quá nhỏ ({area:.2f} m²), nghi ngờ mảnh vụn (sliver).",
                )
            )

    return issues, False
