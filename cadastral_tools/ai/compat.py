"""
Version compatibility helpers & runtime policy flags.

Module này chứa:
- require_qgis4(): Runtime version guard (KHÔNG assert ở import-time)
- Production policy config (TODO: chuyển sang settings.py khi refactor)
"""
from __future__ import annotations

import warnings


def require_qgis4(module_name: str) -> None:
    """Kiểm tra QGIS >= 4.0 tại runtime.

    Gọi trong runtime function, KHÔNG gọi ở import-time.
    Tránh crash test/headless environment.
    """
    try:
        from qgis.core import Qgis

        if Qgis.QGIS_VERSION_INT < 40000:
            raise RuntimeError(
                f"{module_name} yêu cầu QGIS >= 4.0. "
                f"Phiên bản hiện tại: {Qgis.QGIS_VERSION}"
            )
    except ImportError:
        warnings.warn(
            f"{module_name}: Không thể kiểm tra phiên bản QGIS "
            "(chạy ngoài môi trường QGIS).",
            stacklevel=2,
        )


# ---------------------------------------------------------------------------
# Production policy config
# TODO: Chuyển sang settings.py hoặc config_repository khi refactor.
# Đây là runtime policy, không phải compatibility.
# Tạm đặt ở đây cho checkpoint đầu.
# ---------------------------------------------------------------------------
REQUIRE_VERIFIED_LEGAL_SOURCES_FOR_OFFICIAL_REPORT: bool = True
"""
Nếu True: audit_report_generator BLOCK báo cáo nghiệm thu chính thức
khi source_integrity != "VERIFIED".
Trong dev/demo có thể set False để chạy với warning.
"""
