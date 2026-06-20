"""
Bảng mã ký hiệu loại đất — Source of Truth.

Nguồn: TT08/2024/TT-BTNMT, sửa đổi bởi TT23/2025/TT-BNNMT.
Văn bản hợp nhất: VBHN 37/VBHN-BNNMT (ban hành 11/08/2025).

QUAN TRỌNG: as_of là REQUIRED trong hàm core is_valid_code().
Không fallback date.today() im lặng. UI wrapper tách riêng.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

LEGAL_DATA_VERSION = "2026-06-verified"
SOURCE = "TT08/2024 as amended by TT23/2025, VBHN 37/VBHN-BNNMT"
EFFECTIVE_FROM = date(2024, 8, 1)


@dataclass(frozen=True)
class LandUseCode:
    """Mã ký hiệu loại đất."""

    code: str
    label: str
    group: str  # NNN (Nông nghiệp) | PNN (Phi nông nghiệp) | CSD (Chưa sử dụng)
    legal_basis: str
    effective_from: date
    effective_to: date | None  # None = còn hiệu lực


# ============================================================
# LAND USE CODES DATA
# Source: VBHN 37/VBHN-BNNMT
# TODO: Populate đầy đủ từ VBHN 37 trước production deploy.
# ============================================================

LAND_USE_CODES: dict[str, LandUseCode] = {
    # --- Đất nông nghiệp (NNN) ---
    "LUC": LandUseCode(
        "LUC", "Đất chuyên trồng lúa nước", "NNN",
        "TT08/2024, Phụ lục", date(2024, 8, 1), None,
    ),
    "LUK": LandUseCode(
        "LUK", "Đất trồng lúa nước còn lại", "NNN",
        "TT08/2024, Phụ lục", date(2024, 8, 1), None,
    ),
    "LUN": LandUseCode(
        "LUN", "Đất trồng lúa nương", "NNN",
        "TT08/2024, Phụ lục", date(2024, 8, 1), None,
    ),
    "CLN": LandUseCode(
        "CLN", "Đất trồng cây lâu năm", "NNN",
        "TT08/2024, Phụ lục", date(2024, 8, 1), None,
    ),
    "CHN": LandUseCode(
        "CHN", "Đất trồng cây hàng năm khác", "NNN",
        "TT08/2024, Phụ lục", date(2024, 8, 1), None,
    ),
    "RSX": LandUseCode(
        "RSX", "Đất rừng sản xuất", "NNN",
        "TT08/2024, Phụ lục", date(2024, 8, 1), None,
    ),
    "RPH": LandUseCode(
        "RPH", "Đất rừng phòng hộ", "NNN",
        "TT08/2024, Phụ lục", date(2024, 8, 1), None,
    ),
    "RDD": LandUseCode(
        "RDD", "Đất rừng đặc dụng", "NNN",
        "TT08/2024, Phụ lục", date(2024, 8, 1), None,
    ),
    "NTS": LandUseCode(
        "NTS", "Đất nuôi trồng thủy sản", "NNN",
        "TT08/2024, Phụ lục", date(2024, 8, 1), None,
    ),
    "LMU": LandUseCode(
        "LMU", "Đất làm muối", "NNN",
        "TT08/2024, Phụ lục", date(2024, 8, 1), None,
    ),
    "NKH": LandUseCode(
        "NKH", "Đất nông nghiệp khác", "NNN",
        "TT08/2024, Phụ lục", date(2024, 8, 1), None,
    ),
    # --- Đất phi nông nghiệp (PNN) ---
    "ONT": LandUseCode(
        "ONT", "Đất ở tại nông thôn", "PNN",
        "TT08/2024, Phụ lục", date(2024, 8, 1), None,
    ),
    "ODT": LandUseCode(
        "ODT", "Đất ở tại đô thị", "PNN",
        "TT08/2024, Phụ lục", date(2024, 8, 1), None,
    ),
    "TSC": LandUseCode(
        "TSC", "Đất trụ sở cơ quan", "PNN",
        "TT08/2024, Phụ lục", date(2024, 8, 1), None,
    ),
    "DGD": LandUseCode(
        "DGD", "Đất giáo dục", "PNN",
        "TT08/2024, Phụ lục", date(2024, 8, 1), None,
    ),
    "DYT": LandUseCode(
        "DYT", "Đất y tế", "PNN",
        "TT08/2024, Phụ lục", date(2024, 8, 1), None,
    ),
    "SKC": LandUseCode(
        "SKC", "Đất sản xuất kinh doanh", "PNN",
        "TT08/2024, Phụ lục", date(2024, 8, 1), None,
    ),
    "DGT": LandUseCode(
        "DGT", "Đất giao thông", "PNN",
        "TT08/2024, Phụ lục", date(2024, 8, 1), None,
    ),
    "DTL": LandUseCode(
        "DTL", "Đất thủy lợi", "PNN",
        "TT08/2024, Phụ lục", date(2024, 8, 1), None,
    ),
    "TON": LandUseCode(
        "TON", "Đất tôn giáo", "PNN",
        "TT08/2024, Phụ lục", date(2024, 8, 1), None,
    ),
    "TIN": LandUseCode(
        "TIN", "Đất tín ngưỡng", "PNN",
        "TT08/2024, Phụ lục", date(2024, 8, 1), None,
    ),
    "NTD": LandUseCode(
        "NTD", "Đất nghĩa trang, nghĩa địa", "PNN",
        "TT08/2024, Phụ lục", date(2024, 8, 1), None,
    ),
    "SMN": LandUseCode(
        "SMN", "Đất có mặt nước chuyên dùng", "PNN",
        "TT08/2024, Phụ lục", date(2024, 8, 1), None,
    ),
    "PNK": LandUseCode(
        "PNK", "Đất phi nông nghiệp khác", "PNN",
        "TT08/2024, Phụ lục", date(2024, 8, 1), None,
    ),
    # --- Đất chưa sử dụng (CSD) ---
    "BCS": LandUseCode(
        "BCS", "Đất bằng chưa sử dụng", "CSD",
        "TT08/2024, Phụ lục", date(2024, 8, 1), None,
    ),
    "DCS": LandUseCode(
        "DCS", "Đất đồi núi chưa sử dụng", "CSD",
        "TT08/2024, Phụ lục", date(2024, 8, 1), None,
    ),
    "NCS": LandUseCode(
        "NCS", "Núi đá không có rừng cây", "CSD",
        "TT08/2024, Phụ lục", date(2024, 8, 1), None,
    ),
    # TODO: Populate đầy đủ mã con (BHK, DRA, DSH, etc.) từ VBHN 37
}


# ============================================================
# CORE FUNCTION: as_of BẮT BUỘC
# ============================================================

def is_valid_code(code: str, as_of: date) -> bool:
    """Kiểm tra mã đất hợp lệ tại thời điểm as_of.

    Args:
        code: Mã ký hiệu loại đất (VD: "ONT", "CLN").
        as_of: Ngày áp dụng pháp lý. REQUIRED — TypeError nếu thiếu.

    Returns:
        True nếu mã hợp lệ tại thời điểm as_of.
    """
    entry = LAND_USE_CODES.get(code)
    if entry is None:
        return False
    if as_of < entry.effective_from:
        return False
    if entry.effective_to is not None and as_of > entry.effective_to:
        return False
    return True


def get_code_info(code: str, as_of: date) -> LandUseCode | None:
    """Lấy thông tin chi tiết mã đất nếu hợp lệ tại as_of."""
    if is_valid_code(code, as_of):
        return LAND_USE_CODES.get(code)
    return None


# ============================================================
# UI WRAPPER — chỉ dùng cho giao diện, KHÔNG dùng trong QA pipeline
# ============================================================

def is_valid_code_for_ui(code: str) -> bool:
    """UI-only convenience. QA pipeline PHẢI dùng is_valid_code(code, as_of)."""
    return is_valid_code(code, date.today())
