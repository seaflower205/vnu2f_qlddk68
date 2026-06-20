"""
Legal Registry — Lưu trữ quy định pháp lý dưới dạng dữ liệu có version.

Theo tinh thần Luật Ban hành VBQPPL 2025 (64/2025/QH15, hiệu lực
01/04/2025, sửa đổi bởi Luật 87/2025/QH15, hiệu lực 01/07/2025):
hiệu lực, sửa đổi/thay thế, và điều khoản chuyển tiếp là dữ liệu
bắt buộc, không phải comment trong code.

Mỗi LegalRule có:
- effective_from / effective_to: thời gian hiệu lực
- amended_by / replaced_by: quan hệ sửa đổi/thay thế
- transition_notes: điều khoản chuyển tiếp
- source_sha256: hash file PDF nguồn (bắt buộc trước production)
- priority: mức ưu tiên (higher = more specific)
- jurisdiction: "national" hoặc mã ĐVHC cấp tỉnh

matches_admin_unit() leo cây cha: xã → huyện → tỉnh.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class LegalRule:
    """Một quy định pháp lý có version."""

    rule_id: str
    source_doc: str
    legal_basis: str
    jurisdiction: str  # "national" | mã ĐVHC cấp tỉnh
    subject: str  # "crs" | "land_use_code" | "min_area" | ...
    priority: int  # Higher = more specific
    effective_from: date
    effective_to: date | None
    amended_by: str | None
    replaced_by: str | None
    transition_notes: str | None
    verified_at: date
    verified_by: str | None = None
    source_url: str | None = None
    source_filename: str | None = None
    source_downloaded_at: date | None = None
    source_sha256: str | None = None
    content: dict | None = None

    def is_effective_at(self, as_of: date) -> bool:
        """Kiểm tra rule có hiệu lực tại thời điểm as_of."""
        if as_of < self.effective_from:
            return False
        if self.effective_to is not None and as_of > self.effective_to:
            return False
        return True

    def matches_admin_unit(
        self, admin_code: str | None, as_of: date
    ) -> bool:
        """Kiểm tra rule có áp dụng cho ĐVHC admin_code tại as_of.

        - national rule → luôn match
        - non-national + admin_code=None → return False (caller emit WARNING)
        - non-national + admin_code → leo cây cha để match

        Dữ liệu layer thường lưu MaDVHC cấp xã, nhưng rule tách thửa
        là cấp tỉnh. Cần traverse: xã → huyện → tỉnh.
        """
        if self.jurisdiction == "national":
            return True

        if admin_code is None:
            return False

        from .lookup_tables.admin_units import resolve_admin_unit

        unit = resolve_admin_unit(admin_code, as_of)
        while unit is not None:
            if unit.code == self.jurisdiction:
                return True
            if unit.parent_code is None:
                break
            unit = resolve_admin_unit(unit.parent_code, as_of)

        return False

    @property
    def source_verified(self) -> bool:
        """Kiểm tra source_sha256 có hay không."""
        return self.source_sha256 is not None


# ============================================================
# REGISTRY DATA — verified 2026-06
# Populate đầy đủ trước production deploy.
# ============================================================

LEGAL_RULES: list[LegalRule] = [
    # ----- CRS -----
    LegalRule(
        rule_id="CRS-001",
        source_doc="TT26/2024/TT-BTNMT",
        legal_basis="Điều 3",
        jurisdiction="national",
        subject="crs",
        priority=100,
        effective_from=date(2025, 1, 15),
        effective_to=None,
        amended_by=None,
        replaced_by=None,
        transition_notes=(
            "Thay thế TT25/2014. Dữ liệu lập trước 15/01/2025 "
            "đánh giá theo TT25/2014 trong historical-law mode."
        ),
        verified_at=date(2026, 6, 19),
        source_url=(
            "https://datafiles.chinhphu.vn/cpp/files/vbpq/2025/01/"
            "26-btnmt.pdf"
        ),
        content={
            "projection": "Transverse Mercator",
            "zone_width_deg": 3,
            "scale_factor": 0.9999,
            "datum": "VN-2000",
        },
    ),
    LegalRule(
        rule_id="CRS-LEGACY-001",
        source_doc="TT25/2014/TT-BTNMT",
        legal_basis="Chương II",
        jurisdiction="national",
        subject="crs",
        priority=100,
        effective_from=date(2014, 7, 1),
        effective_to=date(2025, 1, 14),
        amended_by=None,
        replaced_by="CRS-001",
        transition_notes=None,
        verified_at=date(2026, 6, 19),
        content={
            "projection": "Transverse Mercator",
            "zone_width_deg": 3,
            "scale_factor": 0.9999,
            "datum": "VN-2000",
        },
    ),
    # ----- Land Use Codes -----
    LegalRule(
        rule_id="LAND-CODE-001",
        source_doc=(
            "TT08/2024/TT-BTNMT + TT23/2025/TT-BNNMT (VBHN 37)"
        ),
        legal_basis="Phụ lục mã ký hiệu loại đất",
        jurisdiction="national",
        subject="land_use_code",
        priority=100,
        effective_from=date(2024, 8, 1),
        effective_to=None,
        amended_by="TT23/2025/TT-BNNMT",
        replaced_by=None,
        transition_notes=(
            "Thay thế TT27/2018. Mã đất cũ theo TT27 valid "
            "cho historical-law mode."
        ),
        verified_at=date(2026, 6, 19),
        source_url=(
            "https://datafiles.chinhphu.vn/cpp/files/vbpq/2025/8/"
            "37-vbhn-bnnmt.pdf"
        ),
    ),
    LegalRule(
        rule_id="LAND-CODE-LEGACY-001",
        source_doc="TT27/2018/TT-BTNMT",
        legal_basis="Phụ lục danh mục mã đất",
        jurisdiction="national",
        subject="land_use_code",
        priority=100,
        effective_from=date(2018, 1, 1),
        effective_to=date(2024, 7, 31),
        amended_by=None,
        replaced_by="LAND-CODE-001",
        transition_notes=None,
        verified_at=date(2026, 6, 19),
    ),
    LegalRule(
        rule_id="LAND-CODE-LEGACY-002",
        source_doc="TT09/2007/TT-BTNMT",
        legal_basis="Danh mục mã loại đất",
        jurisdiction="national",
        subject="land_use_code",
        priority=50,  # Thấp hơn TT27
        effective_from=date(2007, 1, 1),
        effective_to=None,  # Quan hệ thay thế CHƯA verify
        amended_by=None,
        replaced_by=None,  # KHÔNG ghi "thay bởi TT08/2024" — chưa verify
        transition_notes=(
            "Văn bản legacy về lập/chỉnh lý/quản lý hồ sơ địa chính. "
            "Quan hệ thay thế trực tiếp chưa verify đầy đủ. "
            "Chỉ dùng historical-law nếu registry xác định đúng phạm vi."
        ),
        verified_at=date(2026, 6, 19),
    ),
    # TODO: Thêm rule cho min_area, map_technique, etc.
]
