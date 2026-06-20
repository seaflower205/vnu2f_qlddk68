# -*- coding: utf-8 -*-
"""Dynamic inset/overview map support for automated cadastral layouts."""

from __future__ import annotations

from dataclasses import dataclass
from .map_overview_update_mixin import OverviewUpdateMixin


ADMIN_PARENT = {
    "commune": "district",
    "district": "province",
    "province": "country",
    "region": "country",
    "country": "external",
}
LEVEL_TOKENS = {
    "district": ("huyện", "quận", "district"),
    "province": ("tỉnh", "thành phố", "province"),
    "country": ("quốc gia", "cả nước", "vietnam", "việt nam", "country"),
    "external": ("đông nam á", "asean", "asia", "bối cảnh", "context"),
}


def repair_vietnamese_text(value) -> str:
    """Repair the common UTF-8-as-Latin-1 mojibake found in imported GIS data."""
    text = str(value or "").strip()
    text = text.replace("Tiá»?u", "Tiá»ƒu").replace("Nghiá»?p", "Nghiá»‡p")
    if any(marker in text for marker in ("Ã", "Â", "Æ", "á»", "áº")):
        try:
            text = text.encode("cp1252").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    # A question mark means the source already lost one byte. Recover the two
    # recurring administrative names in the supplied Vĩnh Long test dataset.
    return text.replace("Ti�?u", "Tiểu").replace("Nghi�?p", "Nghiệp")


def create_neighbor_label_items(layout, request, target_feature, main_map):
    """Create individually editable layout labels for adjacent administrative units."""
    from qgis.PyQt.QtCore import Qt
    from qgis.PyQt.QtGui import QColor, QFont
    from qgis.core import (
        QgsCoordinateTransform,
        QgsGeometry,
        QgsLayoutItemLabel,
        QgsLayoutPoint,
        QgsLayoutSize,
        QgsProject,
        QgsTextBufferSettings,
        QgsTextFormat,
        QgsUnitTypes,
    )

    source = request.coverage_layer
    name_field = request.name_field
    if not name_field or source.fields().indexOf(name_field) < 0:
        return []
    map_crs = main_map.crs()
    transform = QgsCoordinateTransform(source.crs(), map_crs, QgsProject.instance().transformContext())
    target_geometry = QgsGeometry(target_feature.geometry())
    if source.crs() != map_crs:
        target_geometry.transform(transform)
    target_center = target_geometry.centroid().asPoint()
    extent = main_map.extent()
    anchor = extent.center()
    radius_x = extent.width() * 0.39
    radius_y = extent.height() * 0.43
    positions = []
    for candidate in source.getFeatures():
        if candidate.id() == target_feature.id() or not candidate.hasGeometry():
            continue
        geometry = QgsGeometry(candidate.geometry())
        if source.crs() != map_crs:
            geometry.transform(transform)
        neighbor_center = geometry.centroid().asPoint()
        dx = neighbor_center.x() - target_center.x()
        dy = neighbor_center.y() - target_center.y()
        denominator = ((dx / radius_x) ** 2 + (dy / radius_y) ** 2) ** 0.5
        factor = 1.0 / max(denominator, 1e-9)
        positions.append((
            repair_vietnamese_text(candidate[name_field]).upper(),
            anchor.x() + dx * factor,
            anchor.y() + dy * factor,
        ))
    if not positions:
        return []

    text_format = QgsTextFormat()
    text_format.setFont(QFont("Times New Roman", 16, QFont.Weight.Bold))
    text_format.setSize(16)
    buffer = QgsTextBufferSettings()
    buffer.setEnabled(True)
    buffer.setSize(0.8)
    buffer.setColor(QColor("white"))
    text_format.setBuffer(buffer)
    map_position = main_map.positionWithUnits()
    map_size = main_map.sizeWithUnits()
    mm = QgsUnitTypes.LayoutMillimeters
    items = []
    for index, (name, map_x, map_y) in enumerate(positions, start=1):
        layout_x = map_position.x() + (map_x - extent.xMinimum()) / extent.width() * map_size.width()
        layout_y = map_position.y() + (extent.yMaximum() - map_y) / extent.height() * map_size.height()
        label = QgsLayoutItemLabel(layout)
        label.setId(f"Tên xã lân cận {index} - {name}")
        label.setText(name)
        label.setTextFormat(text_format)
        label.setHAlign(Qt.AlignmentFlag.AlignHCenter)
        label.setVAlign(Qt.AlignmentFlag.AlignVCenter)
        layout.addLayoutItem(label)
        label.attemptMove(QgsLayoutPoint(layout_x - 45, layout_y - 7, mm), False)
        label.attemptResize(QgsLayoutSize(90, 14, mm))
        items.append(label)
    return items


@dataclass(frozen=True)
class OverviewResolution:
    layer: object | None
    source: str
    warning: str = ""


def expanded_extent(rect, margin_percent: float):
    """Return a copied rectangle expanded by a percentage on every side."""
    from qgis.core import QgsRectangle

    result = QgsRectangle(rect)
    dx = max(result.width() * margin_percent / 100.0, 1e-9)
    dy = max(result.height() * margin_percent / 100.0, 1e-9)
    result.grow(max(dx, dy))
    return result


def extent_is_broader(context, main) -> bool:
    """Require a true contextual extent, not a duplicate of the main map."""
    if context is None or main is None or context.isEmpty() or main.isEmpty():
        return False
    contains = (
        context.xMinimum() <= main.xMinimum()
        and context.yMinimum() <= main.yMinimum()
        and context.xMaximum() >= main.xMaximum()
        and context.yMaximum() >= main.yMaximum()
    )
    return contains and context.width() * context.height() > main.width() * main.height() * 1.05


def resolve_context_layer(project, coverage_layer, admin_level: str, explicit_layer=None):
    """Resolve overview context: explicit layer, project candidate, then coverage."""
    if explicit_layer is not None and explicit_layer.isValid():
        return OverviewResolution(explicit_layer, "explicit")

    target = ADMIN_PARENT.get(admin_level, "external")
    tokens = LEVEL_TOKENS.get(target, ())
    for layer in project.mapLayers().values():
        if layer is coverage_layer or not getattr(layer, "isValid", lambda: False)():
            continue
        try:
            marker = str(layer.customProperty("vnu2f/admin_level", "")).lower()
            name = layer.name().lower()
            if marker == target or any(token in name for token in tokens):
                return OverviewResolution(layer, "project")
        except (AttributeError, TypeError):
            continue

    try:
        if coverage_layer and coverage_layer.isValid() and coverage_layer.featureCount() > 1:
            return OverviewResolution(
                coverage_layer,
                "coverage",
                "Không tìm thấy layer cấp trên; dùng toàn bộ coverage layer làm bối cảnh.",
            )
    except (AttributeError, TypeError):
        pass
    return OverviewResolution(None, "missing", "Không xác định được dữ liệu sơ đồ vị trí.")


class OverviewController(OverviewUpdateMixin):
    """Keeps an inset map synchronized with single-feature and Atlas layouts."""

    def __init__(self, layout, main_map, inset_map, request, resolution):
        self.layout = layout
        self.main_map = main_map
        self.inset_map = inset_map
        self.request = request
        self.resolution = resolution
        self._install_overview()

    def _install_overview(self):
        from qgis.core import QgsFillSymbol, QgsLayoutItemMapOverview

        overview = QgsLayoutItemMapOverview("Phạm vi bản đồ chính", self.inset_map)
        overview.setLinkedMap(self.main_map)
        overview.setFrameSymbol(QgsFillSymbol.createSimple({
            "color": "255,255,255,0",
            "outline_color": "#dc2626",
            "outline_width": "0.45",
        }))
        self.inset_map.overviews().addItem(overview)
        self.inset_map.update()

    def _style_xml(self, source, renderer):
        from qgis.core import QgsMapLayerStyle

        clone = source.clone()
        clone.setRenderer(renderer)
        clone.setLabelsEnabled(False)
        style = QgsMapLayerStyle()
        style.readFromLayer(clone)
        return style.xmlData()

    def _context_style(self, source):
        from qgis.core import QgsFillSymbol, QgsSingleSymbolRenderer

        symbol = QgsFillSymbol.createSimple({
            "color": "245,245,245,255",
            "outline_color": "#52525b",
            "outline_width": "0.25",
        })
        return self._style_xml(source, QgsSingleSymbolRenderer(symbol))

    def _coverage_style(self, source, feature_id):
        from qgis.core import QgsFillSymbol, QgsRuleBasedRenderer

        root = QgsRuleBasedRenderer.Rule(None)
        base = QgsFillSymbol.createSimple({
            "color": "255,255,255,0",
            "outline_color": "#a1a1aa",
            "outline_width": "0.20",
        })
        highlight = QgsFillSymbol.createSimple({
            "color": "254,240,138,145",
            "outline_color": "#dc2626",
            "outline_width": "0.65",
        })
        root.appendChild(QgsRuleBasedRenderer.Rule(base, 0, 0, "", "Đơn vị lân cận"))
        root.appendChild(
            QgsRuleBasedRenderer.Rule(highlight, 0, 0, f"$id = {int(feature_id)}", "Vùng lập bản đồ")
        )
        return self._style_xml(source, QgsRuleBasedRenderer(root))

    def _context_extent(self, source, filter_field, filter_value):
        from qgis.core import QgsRectangle

        extent = QgsRectangle()
        matched = False
        for candidate in source.getFeatures():
            if filter_field and filter_value not in (None, ""):
                try:
                    if str(candidate[filter_field]) != str(filter_value):
                        continue
                except (KeyError, TypeError):
                    continue
            if candidate.hasGeometry():
                extent.combineExtentWith(candidate.geometry().boundingBox())
                matched = True
        return extent if matched else source.extent()


    def connect_atlas(self, atlas):
        atlas.featureChanged.connect(self.update_for_feature)
