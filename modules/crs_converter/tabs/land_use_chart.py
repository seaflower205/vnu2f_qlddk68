# -*- coding: utf-8 -*-
"""Land-use structure aggregation and native QGIS layout chart rendering."""

from __future__ import annotations

import math
from dataclasses import dataclass


GROUP_ORDER = ("NNN", "PNN", "CSD")
GROUP_LABELS = {
    "NNN": "ĐẤT NÔNG NGHIỆP",
    "PNN": "ĐẤT PHI NÔNG NGHIỆP",
    "CSD": "ĐẤT CHƯA SỬ DỤNG",
}
GROUP_COLORS = {
    "NNN": "#facc15",
    "PNN": "#f0abfc",
    "CSD": "#d4d4d8",
}


@dataclass(frozen=True)
class LandUseChartData:
    areas: dict[str, float]

    @property
    def total(self) -> float:
        return sum(self.areas.values())

    def percent(self, group: str) -> float:
        return 0.0 if self.total <= 0 else self.areas.get(group, 0.0) * 100.0 / self.total


def _legal_group(code: object) -> str | None:
    """Resolve a TT08 land-use code to one of the three headline groups."""
    value = str(code or "").strip().upper()
    if value in GROUP_ORDER:
        return value
    try:
        from cadastral_tools.ai.lookup_tables.land_use_codes import LAND_USE_CODES

        entry = LAND_USE_CODES.get(value)
        if entry:
            return entry.group
    except (ImportError, AttributeError):
        pass
    if value in {"BCS", "DCS", "NCS", "CSD"}:
        return "CSD"
    return None


def aggregate_land_use(features, code_field: str, area_field: str = "") -> LandUseChartData:
    """Aggregate feature area without modifying feature or layer state."""
    totals = {group: 0.0 for group in GROUP_ORDER}
    for feature in features:
        group = _legal_group(feature[code_field])
        if group is None:
            continue
        value = feature[area_field] if area_field else None
        try:
            area = float(value) if value not in (None, "") else float(feature.geometry().area())
        except (TypeError, ValueError, AttributeError):
            area = 0.0
        if area > 0:
            totals[group] += area
    return LandUseChartData(totals)


def _pie_polygon(cx: float, cy: float, radius: float, start: float, span: float):
    from qgis.PyQt.QtCore import QPointF
    from qgis.PyQt.QtGui import QPolygonF

    points = [QPointF(cx, cy)]
    steps = max(4, int(abs(span) / 7.5))
    for index in range(steps + 1):
        angle = math.radians(start + span * index / steps)
        points.append(QPointF(cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    points.append(QPointF(cx, cy))
    return QPolygonF(points)


def add_land_use_chart(layout, data: LandUseChartData, *, x: float, y: float, size: float = 42.0):
    """Draw a compact pie chart with native vector layout items."""
    if data.total <= 0:
        return []

    from qgis.core import (
        QgsFillSymbol,
        QgsLayoutItemLabel,
        QgsLayoutItemPolygon,
        QgsLayoutPoint,
        QgsLayoutSize,
        QgsUnitTypes,
    )
    from qgis.PyQt.QtGui import QFont

    mm = QgsUnitTypes.LayoutMillimeters
    created = []
    angle = -90.0
    center_x = x + size / 2.0
    center_y = y + size / 2.0
    radius = size / 2.0
    for group in GROUP_ORDER:
        span = 360.0 * data.percent(group) / 100.0
        if span <= 0:
            continue
        polygon = QgsLayoutItemPolygon(
            _pie_polygon(center_x, center_y, radius, angle, span), layout
        )
        polygon.setId(f"Chart_{group}")
        polygon.setSymbol(QgsFillSymbol.createSimple({
            "color": GROUP_COLORS[group],
            "outline_color": "#3f3f46",
            "outline_width": "0.20",
        }))
        layout.addLayoutItem(polygon)
        created.append(polygon)
        angle += span

    title = QgsLayoutItemLabel(layout)
    title.setId("ChartTitle")
    title.setText("DIỆN TÍCH, CƠ CẤU SỬ DỤNG ĐẤT")
    title_format = title.textFormat()
    title_format.setFont(QFont("Times New Roman", 12, QFont.Weight.Bold))
    title_format.setSize(12)
    title_format.setSizeUnit(QgsUnitTypes.RenderPoints)
    title.setTextFormat(title_format)
    layout.addLayoutItem(title)
    title.attemptMove(QgsLayoutPoint(x, y - 18, mm), False)
    title.attemptResize(QgsLayoutSize(size * 3.1, 14, mm))
    created.append(title)

    for index, group in enumerate(GROUP_ORDER):
        label = QgsLayoutItemLabel(layout)
        label.setId(f"ChartLabel_{group}")
        label.setText(
            f"{GROUP_LABELS[group]}: {data.areas[group] / 10000.0:,.2f} ha "
            f"({data.percent(group):.2f}%)"
        )
        label_format = label.textFormat()
        label_format.setFont(QFont("Times New Roman", 9))
        label_format.setSize(9)
        label_format.setSizeUnit(QgsUnitTypes.RenderPoints)
        label.setTextFormat(label_format)
        layout.addLayoutItem(label)
        label.attemptMove(QgsLayoutPoint(x + size + 10, y + 8 + index * 22, mm), False)
        label.attemptResize(QgsLayoutSize(size * 1.65, 16, mm))
        created.append(label)
    return created


def features_inside_boundary(land_layer, boundary_feature, boundary_layer):
    """Yield land features intersecting the current administrative boundary."""
    from qgis.core import QgsCoordinateTransform, QgsFeatureRequest, QgsGeometry, QgsProject

    geometry = boundary_feature.geometry()
    if boundary_layer.crs() != land_layer.crs():
        geometry = QgsGeometry(geometry)
        transform = QgsCoordinateTransform(
            boundary_layer.crs(), land_layer.crs(), QgsProject.instance().transformContext()
        )
        geometry.transform(transform)
    request = QgsFeatureRequest().setFilterRect(geometry.boundingBox())
    for feature in land_layer.getFeatures(request):
        if feature.hasGeometry() and feature.geometry().intersects(geometry):
            yield feature


class LandUseChartController:
    """Rebuild chart content when an Atlas switches its coverage feature."""

    def __init__(self, layout, boundary_layer, land_layer, code_field, area_field, x, y, size):
        self.layout = layout
        self.boundary_layer = boundary_layer
        self.land_layer = land_layer
        self.code_field = code_field
        self.area_field = area_field
        self.x, self.y, self.size = x, y, size
        self._items = []

    def update_for_feature(self, feature):
        for item in self._items:
            self.layout.removeLayoutItem(item)
        features = features_inside_boundary(
            self.land_layer, feature, self.boundary_layer
        )
        data = aggregate_land_use(features, self.code_field, self.area_field)
        self._items = add_land_use_chart(
            self.layout, data, x=self.x, y=self.y, size=self.size
        )
        return bool(self._items)

    def connect_atlas(self, atlas):
        atlas.featureChanged.connect(self.update_for_feature)
