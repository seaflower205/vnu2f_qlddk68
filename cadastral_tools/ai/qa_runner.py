"""
Core QA Orchestrator.
Chạy độc lập với UI. Nhận đầu vào là dữ liệu snapshot.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from .legal_resolver import LegalContext
from .qa_models import FeatureSnapshot, LayerSnapshot, QAIssue

logger = logging.getLogger(__name__)


@dataclass
class QARunConfig:
    """Cấu hình chạy QA."""
    legal_context: LegalContext
    run_topology: bool = True
    run_attributes: bool = True
    run_legal_audit: bool = True
    operation_type: str = "kiem_tra_hien_trang"
    run_gaps: bool = False
    gap_area_threshold_m2: float = 0.1
    max_features_before_confirm: int = 5000
    
    default_commune_code: str | None = None
    default_province_code: str | None = None
    require_verified_legal_rules: bool = False
    
    boundary_layer_snapshot: LayerSnapshot | None = None
    main_layer_snapshot: LayerSnapshot | None = None
    
    # Callback để báo cáo tiến độ về Task
    progress_callback: Any | None = None
    is_cancelled: Any | None = None


@dataclass
class QAResult:
    """Kết quả chạy QA."""
    issues: list[QAIssue] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    preflight_hash: str | None = None
    elapsed_ms: int = 0
    cancelled: bool = False


class QARunner:
    """Bộ điều phối QA Core."""

    def __init__(self, config: QARunConfig):
        self.config = config
        self.result = QAResult(
            preflight_hash=config.main_layer_snapshot.preflight_hash if config.main_layer_snapshot else None
        )

    def run(self) -> QAResult:
        """Thực thi chuỗi QA trên dữ liệu snapshot."""
        start_time = time.time()
        
        try:
            if not self.config.main_layer_snapshot:
                self.result.errors.append("Không có dữ liệu snapshot để chạy QA.")
                return self.result

            if self._is_cancelled():
                self.result.cancelled = True
                return self._finalize(start_time)

            # 1. Topology Checks
            if self.config.run_topology:
                self._report_progress(10, "Đang kiểm tra không gian (Topology)...")
                
                from .step1_topology import run_topology_checks
                topo_issues, topo_cancelled = run_topology_checks(
                    self.config.main_layer_snapshot,
                    boundary_snapshot=self.config.boundary_layer_snapshot if self.config.run_gaps else None,
                    progress_callback=self._make_sub_progress_callback(10, 40),
                    is_cancelled=self.config.is_cancelled,
                )
                self.result.issues.extend(topo_issues)
                
                if topo_cancelled or self._is_cancelled():
                    self.result.cancelled = True
                    return self._finalize(start_time)

            # 2. Attribute Checks
            if self.config.run_attributes:
                self._report_progress(40, "Đang kiểm tra thuộc tính cơ bản...")
                
                from .step2_attributes import run_attribute_checks
                attr_issues, attr_cancelled = run_attribute_checks(
                    self.config.main_layer_snapshot,
                    self.config.legal_context,
                    progress_callback=self._make_sub_progress_callback(40, 70),
                    is_cancelled=self.config.is_cancelled,
                )
                self.result.issues.extend(attr_issues)
                
                if attr_cancelled or self._is_cancelled():
                    self.result.cancelled = True
                    return self._finalize(start_time)

            # 3. Legal Audit Checks
            if self.config.run_legal_audit:
                self._report_progress(70, "Đang kiểm tra nghiệp vụ và pháp lý...")
                
                from .step3_legal_audit import run_legal_audit_checks
                legal_issues, legal_cancelled = run_legal_audit_checks(
                    snapshot=self.config.main_layer_snapshot,
                    legal_context=self.config.legal_context,
                    operation_type=self.config.operation_type,
                    default_commune_code=self.config.default_commune_code,
                    default_province_code=self.config.default_province_code,
                    progress_callback=self._make_sub_progress_callback(70, 95),
                    is_cancelled=self.config.is_cancelled,
                )
                self.result.issues.extend(legal_issues)
                
                if legal_cancelled or self._is_cancelled():
                    self.result.cancelled = True
                    return self._finalize(start_time)

            self._report_progress(100, "Hoàn tất kiểm định.")

        except Exception as e:
            logger.exception("Lỗi nghiêm trọng khi chạy QA: %s", e)
            self.result.errors.append(f"Lỗi nghiêm trọng: {str(e)}")

        return self._finalize(start_time)

    def _finalize(self, start_time: float) -> QAResult:
        self.result.elapsed_ms = int((time.time() - start_time) * 1000)
        return self.result

    def _is_cancelled(self) -> bool:
        if self.config.is_cancelled and self.config.is_cancelled():
            return True
        return False

    def _report_progress(self, percent: float, msg: str) -> None:
        if self.config.progress_callback:
            self.config.progress_callback(percent, msg)

    def _make_sub_progress_callback(self, start_pct: float, end_pct: float):
        """Tạo callback map % local sang % global."""
        def callback(local_pct: float, msg: str) -> None:
            if self.config.progress_callback:
                global_pct = start_pct + (local_pct / 100.0) * (end_pct - start_pct)
                self.config.progress_callback(global_pct, msg)
        return callback
