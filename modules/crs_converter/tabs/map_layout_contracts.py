# -*- coding: utf-8 -*-
"""Stable contracts and validation for automated map layouts."""

from dataclasses import dataclass
from datetime import date

STANDARD_SCALES = (500, 1000, 2000, 2500, 5000, 10000, 15000, 20000, 25000, 50000, 100000, 250000, 500000, 1000000)
TT08_TEMPLATES = {"commune": "TT08_HTSDD_commune.qpt", "district": "TT08_HTSDD_district.qpt", "province": "TT08_HTSDD_province.qpt", "region": "TT08_HTSDD_region_country.qpt", "country": "TT08_HTSDD_region_country.qpt"}


@dataclass
class MapLayoutRequest:
    coverage_layer: object
    parent_layer: object | None = None
    land_use_layer: object | None = None
    profile: str = "tt08"
    admin_level: str = "commune"
    atlas_enabled: bool = False
    selected_only: bool = False
    paper: str = "A3"
    auto_orientation: bool = True
    portrait: bool = False
    scale: int | None = None
    main_margin: float = 10.0
    inset_margin: float = 5.0
    title: str = ""
    organization: str = ""
    study_area: str = ""
    author: str = ""
    map_date: str = ""
    name_field: str = ""
    code_field: str = ""
    parent_code_field: str = ""
    parent_lookup_field: str = ""
    land_code_field: str = ""
    area_field: str = ""
    chart_enabled: bool = True
    signatures_enabled: bool = True
    legal_date: date = date.today()


@dataclass(frozen=True)
class LayoutResult:
    layout: object
    warnings: tuple[str, ...]


class LayoutValidationError(ValueError):
    pass


def unique_layout_name(manager, base):
    name, suffix = base, 1
    while manager.layoutByName(name):
        name, suffix = f"{base}_{suffix}", suffix + 1
    return name


def nice_grid_interval(extent_width, target_lines=6):
    import math
    raw = max(float(extent_width), 1.0) / max(int(target_lines), 1)
    magnitude = 10 ** math.floor(math.log10(raw))
    normalized = raw / magnitude
    step = 1 if normalized <= 1 else 2 if normalized <= 2 else 5 if normalized <= 5 else 10
    return step * magnitude


def validate_request(request):
    layer = request.coverage_layer
    if layer is None or not layer.isValid():
        raise LayoutValidationError("Hãy chọn một layer ranh giới polygon hợp lệ.")
    if request.profile == "tt08" and request.admin_level not in TT08_TEMPLATES:
        raise LayoutValidationError("Cấp bản đồ TT08 không hợp lệ.")
    if not request.atlas_enabled and len(layer.selectedFeatureIds()) != 1:
        raise LayoutValidationError("Chế độ một bản đồ yêu cầu chọn đúng một đối tượng ranh giới.")
    if request.profile == "tt08" and not request.legal_date:
        raise LayoutValidationError("Hồ sơ TT08 bắt buộc có ngày áp dụng pháp lý.")
