# -*- coding: utf-8 -*-
"""Business service for automated QGIS print layouts and TT08 profiles."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date

from .land_use_chart import LandUseChartController
from .map_layout_overview import (
    OverviewController,
    create_neighbor_label_items,
    expanded_extent,
    resolve_context_layer,
)
from .map_layout_config_mixin import MapLayoutConfigMixin
from .map_layout_create_mixin import MapLayoutCreateMixin


PAPER_SIZES = {
    "A5": (210, 148),
    "A4": (297, 210),
    "A3": (420, 297),
    "A2": (594, 420),
    "A1": (841, 594),
    "A0": (1189, 841),
}
STANDARD_SCALES = (500, 1000, 2000, 2500, 5000, 10000, 15000, 20000, 25000, 50000, 100000, 250000, 500000, 1000000)
TT08_TEMPLATES = {
    "commune": "TT08_HTSDD_commune.qpt",
    "district": "TT08_HTSDD_district.qpt",
    "province": "TT08_HTSDD_province.qpt",
    "region": "TT08_HTSDD_region_country.qpt",
    "country": "TT08_HTSDD_region_country.qpt",
}


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


def plugin_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def unique_layout_name(manager, base: str) -> str:
    name, suffix = base, 1
    while manager.layoutByName(name):
        name = f"{base}_{suffix}"
        suffix += 1
    return name


def nice_grid_interval(extent_width: float, target_lines: int = 6) -> float:
    """Return a readable 1/2/5 grid interval for the current map extent."""
    import math

    raw = max(float(extent_width), 1.0) / max(int(target_lines), 1)
    magnitude = 10 ** math.floor(math.log10(raw))
    normalized = raw / magnitude
    step = 1 if normalized <= 1 else 2 if normalized <= 2 else 5 if normalized <= 5 else 10
    return step * magnitude


def validate_request(request: MapLayoutRequest):
    layer = request.coverage_layer
    if layer is None or not layer.isValid():
        raise LayoutValidationError("Hãy chọn một layer ranh giới polygon hợp lệ.")
    if request.profile == "tt08" and request.admin_level not in TT08_TEMPLATES:
        raise LayoutValidationError("Cấp bản đồ TT08 không hợp lệ.")
    if not request.atlas_enabled and len(layer.selectedFeatureIds()) != 1:
        raise LayoutValidationError("Chế độ một bản đồ yêu cầu chọn đúng một đối tượng ranh giới.")
    if request.profile == "tt08" and not request.legal_date:
        raise LayoutValidationError("Hồ sơ TT08 bắt buộc có ngày áp dụng pháp lý.")


# Re-export the cycle-free contracts used by the implementation mixins.
from .map_layout_contracts import (  # noqa: E402,F401
    LayoutResult, LayoutValidationError, MapLayoutRequest, STANDARD_SCALES,
    TT08_TEMPLATES, nice_grid_interval, unique_layout_name, validate_request,
)


class MapLayoutService(MapLayoutCreateMixin, MapLayoutConfigMixin):
    def __init__(self, iface, project=None):
        from qgis.core import QgsProject

        self.iface = iface
        self.project = project or QgsProject.instance()
        self._controllers = []

    def _template_path(self, request):
        if request.profile == "tt08":
            name = TT08_TEMPLATES[request.admin_level]
        elif request.profile == "slide":
            name = "Khung_Slide.qpt"
        else:
            name = "Khung LVT2601_print_27Apr2026_VN.qpt"
        return os.path.join(plugin_root(), "templates", name)

    def _load_layout(self, request):
        from qgis.PyQt.QtXml import QDomDocument
        from qgis.core import QgsPrintLayout, QgsReadWriteContext

        path = self._template_path(request)
        if not os.path.exists(path):
            raise LayoutValidationError(f"Không tìm thấy template: {path}")
        document = QDomDocument()
        with open(path, "r", encoding="utf-8") as stream:
            ok, message, line, _ = document.setContent(stream.read())
        if not ok:
            raise LayoutValidationError(f"QPT lỗi dòng {line}: {message}")
        layout = QgsPrintLayout(self.project)
        _, loaded = layout.loadFromTemplate(document, QgsReadWriteContext())
        if not loaded:
            raise LayoutValidationError("QGIS không thể nạp template bố cục.")
        north = layout.itemById("NorthArrow")
        if north is not None and hasattr(north, "setPicturePath"):
            north.setPicturePath(os.path.join(plugin_root(), "templates", "north_arrow_tt08.svg"))
        return layout

    def _target_feature(self, request):
        if request.atlas_enabled:
            ids = request.coverage_layer.selectedFeatureIds() if request.selected_only else []
            if ids:
                from qgis.core import QgsFeatureRequest
                return next(request.coverage_layer.getFeatures(QgsFeatureRequest(ids[0])), None)
            return next(request.coverage_layer.getFeatures(), None)
        return next(iter(request.coverage_layer.selectedFeatures()), None)

    def _set_page(self, layout, request, feature):
        from qgis.core import QgsLayoutItemLabel, QgsLayoutItemPage, QgsLayoutPoint, QgsLayoutSize, QgsUnitTypes

        page = layout.pageCollection().page(0)
        old_size = page.pageSize()
        width, height = PAPER_SIZES.get(request.paper, PAPER_SIZES["A3"])
        if request.auto_orientation and feature and feature.hasGeometry():
            bounds = feature.geometry().boundingBox()
            request.portrait = bounds.height() > bounds.width()
        if request.portrait:
            width, height = height, width
        sx, sy = width / old_size.width(), height / old_size.height()
        for item in layout.items():
            if isinstance(item, QgsLayoutItemPage) or not hasattr(item, "positionWithUnits"):
                continue
            position = item.positionWithUnits()
            size = item.sizeWithUnits()
            item.attemptMove(QgsLayoutPoint(position.x() * sx, position.y() * sy, QgsUnitTypes.LayoutMillimeters), False)
            item.attemptResize(QgsLayoutSize(size.width() * sx, size.height() * sy, QgsUnitTypes.LayoutMillimeters))
            if isinstance(item, QgsLayoutItemLabel):
                text_format = item.textFormat()
                if text_format.size() > 0:
                    text_format.setSize(max(5.0, text_format.size() * min(sx, sy)))
                    item.setTextFormat(text_format)
        page.setPageSize(QgsLayoutSize(width, height, QgsUnitTypes.LayoutMillimeters))

    def _update_label(self, layout, item_id, value):
        from qgis.core import QgsLayoutItemLabel

        item = layout.itemById(item_id)
        if isinstance(item, QgsLayoutItemLabel):
            item.setText(value)
            item.refresh()

    def _configure_labels(self, layout, request, feature):
        title = request.title or f"BẢN ĐỒ HIỆN TRẠNG SỬ DỤNG ĐẤT {request.study_area}".strip()
        study = request.study_area
        if not study and feature is not None and request.name_field:
            study = str(feature[request.name_field] or "")
        values = {
            "Tên bản đồ": title.upper(),
            "Khu vực bản đồ": study.upper(),
            "Tên đv xd bản đồ": request.organization or "ĐƠN VỊ XÂY DỰNG BẢN ĐỒ",
            "Người lập": f"Người lập: {request.author}",
            "Ngày lập": f"Ngày lập: {request.map_date}",
            "InsetTitle": "SƠ ĐỒ VỊ TRÍ",
            "LegalMetadata": f"TT08/2024 + TT23/2025 | ngày áp dụng {request.legal_date:%d/%m/%Y}",
        }
        for item_id, value in values.items():
            self._update_label(layout, item_id, value)



    def _add_grid_crs_note(self, layout, main_map):
        from qgis.PyQt.QtCore import Qt
        from qgis.PyQt.QtGui import QFont
        from qgis.core import QgsLayoutItemLabel, QgsLayoutPoint, QgsLayoutSize, QgsUnitTypes

        label = QgsLayoutItemLabel(layout)
        label.setId("GridCrsNote")
        label.setText("LƯỚI TỌA ĐỘ VN-2000 — ĐƠN VỊ: MÉT")
        text_format = label.textFormat()
        text_format.setFont(QFont("Times New Roman", 9, QFont.Weight.Bold))
        text_format.setSize(9)
        label.setTextFormat(text_format)
        label.setHAlign(Qt.AlignmentFlag.AlignRight)
        label.setVAlign(Qt.AlignmentFlag.AlignVCenter)
        layout.addLayoutItem(label)
        position = main_map.positionWithUnits()
        size = main_map.sizeWithUnits()
        mm = QgsUnitTypes.LayoutMillimeters
        label.attemptMove(QgsLayoutPoint(position.x() + size.width() - 205, position.y() + size.height() + 3, mm), False)
        label.attemptResize(QgsLayoutSize(200, 10, mm))

    def _configure_atlas(self, layout, main_map, request):
        atlas = layout.atlas()
        atlas.setCoverageLayer(request.coverage_layer)
        atlas.setEnabled(True)
        atlas.setHideCoverage(False)
        if request.selected_only:
            ids = request.coverage_layer.selectedFeatureIds()
            atlas.setFilterFeatures(True)
            atlas.setFilterExpression(f"$id IN ({','.join(map(str, ids))})" if ids else "FALSE")
        if request.name_field:
            atlas.setPageNameExpression(f'attribute(@atlas_feature, \'{request.name_field}\')')
            atlas.setFilenameExpression(f'attribute(@atlas_feature, \'{request.name_field}\')')
        main_map.setAtlasDriven(True)
        main_map.setAtlasScalingMode(main_map.AtlasScalingMode.Auto)
        main_map.setAtlasMargin(request.main_margin / 100.0)
        atlas.updateFeatures()
        return atlas

    def _configure_chart(self, layout, request, feature):
        source = request.land_use_layer
        if not request.chart_enabled or source is None or not request.land_code_field:
            return None
        page_size = layout.pageCollection().page(0).pageSize()
        controller = LandUseChartController(
            layout,
            request.coverage_layer,
            source,
            request.land_code_field,
            request.area_field,
            x=page_size.width() * 0.44,
            y=page_size.height() * 0.82,
            size=min(page_size.width(), page_size.height()) * 0.105,
        )
        controller.update_for_feature(feature)
        self._controllers.append(controller)
        return controller

    def _configure_signatures(self, layout, enabled):
        ids = (
            "SignatureBlock", "SignatureLeft", "SignatureRight", "SignatureTitle",
            "SignatureAuthority", "SignatureCommittee", "SignatureDateLeft", "SignatureDateRight",
        )
        for item_id in ids:
            item = layout.itemById(item_id)
            if item:
                item.setVisibility(enabled)

