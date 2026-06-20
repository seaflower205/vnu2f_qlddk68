"""Mechanically extracted responsibilities from map_layout_service.py."""

from __future__ import annotations
import os
from .map_layout_contracts import LayoutValidationError, STANDARD_SCALES, nice_grid_interval
from dataclasses import dataclass
from datetime import date
from .land_use_chart import LandUseChartController
from .map_layout_overview import (
    OverviewController,
    create_neighbor_label_items,
    expanded_extent,
    resolve_context_layer,
)


class MapLayoutConfigMixin:
    def _configure_main_map(self, layout, request, feature):
        from qgis.core import (
            QgsCoordinateTransform,
            QgsFeatureRequest,
            QgsGeometry,
            QgsLayoutItemMap,
            QgsProject,
            QgsRectangle,
        )

        item = layout.itemById("Map")
        if not isinstance(item, QgsLayoutItemMap):
            raise LayoutValidationError("Template thiếu map item ID 'Map'.")
        if feature and feature.hasGeometry():
            map_crs = request.coverage_layer.crs()
            if request.land_use_layer is not None and request.land_use_layer.isValid():
                map_crs = request.land_use_layer.crs()
            geometry = QgsGeometry(feature.geometry())
            if request.coverage_layer.crs() != map_crs:
                geometry.transform(QgsCoordinateTransform(
                    request.coverage_layer.crs(), map_crs, QgsProject.instance().transformContext()
                ))
            item.setCrs(map_crs)
            map_extent = geometry.boundingBox()
            if request.land_use_layer is not None and request.land_use_layer.isValid():
                land_extent = QgsRectangle()
                has_land = False
                query = QgsFeatureRequest().setFilterRect(map_extent)
                for land_feature in request.land_use_layer.getFeatures(query):
                    if land_feature.hasGeometry() and land_feature.geometry().intersects(geometry):
                        land_extent.combineExtentWith(land_feature.geometry().boundingBox())
                        has_land = True
                if has_land:
                    map_extent = land_extent
            item.zoomToExtent(expanded_extent(map_extent, request.main_margin))
        else:
            item.zoomToExtent(request.coverage_layer.extent())
        if request.scale:
            item.setScale(request.scale)
        elif request.profile == "tt08":
            current_scale = item.scale()
            standard_scale = next(
                (value for value in STANDARD_SCALES if value >= current_scale),
                STANDARD_SCALES[-1],
            )
            item.setScale(standard_scale)
        if item.grids().size():
            from qgis.PyQt.QtGui import QColor
            from qgis.core import QgsTextBufferSettings

            grid = item.grids().grid(0)
            interval = nice_grid_interval(item.extent().width())
            grid.setIntervalX(interval)
            grid.setIntervalY(interval)
            annotation_format = grid.annotationTextFormat()
            annotation_buffer = QgsTextBufferSettings()
            annotation_buffer.setEnabled(True)
            annotation_buffer.setSize(1.2)
            annotation_buffer.setColor(QColor("white"))
            annotation_format.setBuffer(annotation_buffer)
            grid.setAnnotationTextFormat(annotation_format)
            grid.setAnnotationFrameDistance(1.8)
        layers = list(self.iface.mapCanvas().layers())
        if request.coverage_layer is not request.land_use_layer:
            layers = [layer for layer in layers if layer.id() != request.coverage_layer.id()]
        item.setLayers(layers)
        item.setKeepLayerSet(True)
        item.setKeepLayerStyles(True)
        return item
    def _configure_legend_and_scale(self, layout, main_map, request):
        import math

        from qgis.PyQt.QtCore import Qt
        from qgis.PyQt.QtGui import QFont
        from qgis.core import (
            QgsLayerTreeLayer,
            QgsLayoutItemLabel,
            QgsLayoutItemLegend,
            QgsLayoutItemScaleBar,
            QgsLayoutPoint,
            QgsLayoutSize,
            QgsScaleBarSettings,
            QgsUnitTypes,
        )

        legend = layout.itemById("Chú dẫn")
        if isinstance(legend, QgsLayoutItemLegend) and request.land_use_layer is not None:
            legend.setAutoUpdateModel(False)
            root = legend.model().rootGroup()
            for child in list(root.children()):
                if isinstance(child, QgsLayerTreeLayer) and child.layerId() != request.land_use_layer.id():
                    root.removeChildNode(child)
            legend.updateLegend()

        scale = layout.itemById("Scale mét")
        if isinstance(scale, QgsLayoutItemScaleBar):
            target = main_map.scale() * 0.05
            magnitude = 10 ** math.floor(math.log10(max(target, 1.0)))
            normalized = target / magnitude
            step = next(value for value in (1, 2, 2.5, 5, 10) if normalized <= value + 1e-9)
            interval = step * magnitude
            scale.setLinkedMap(main_map)
            scale.setSegmentSizeMode(QgsScaleBarSettings.SegmentSizeMode.Fixed)
            scale.setNumberOfSegments(2)
            scale.setNumberOfSegmentsLeft(0)
            if interval >= 1000:
                scale.setUnits(QgsUnitTypes.DistanceKilometers)
                scale.setUnitLabel("km")
                scale.setUnitsPerSegment(interval / 1000.0)
            else:
                scale.setUnits(QgsUnitTypes.DistanceMeters)
                scale.setUnitLabel("m")
                scale.setUnitsPerSegment(interval)
            scale_format = scale.textFormat()
            scale_format.setFont(QFont("Times New Roman", 9))
            scale_format.setSize(9)
            scale.setTextFormat(scale_format)
            scale.setHeight(2.2)
            scale.applyDefaultSize()
            # QGIS applyDefaultSize may replace a boundary value (e.g. 250 m)
            # with the next "nice" value. Restore the explicitly chosen step.
            scale.setUnitsPerSegment(interval / 1000.0 if interval >= 1000 else interval)
            scale.attemptResize(scale.minimumSize())
            page_width = layout.pageCollection().page(0).pageSize().width()
            mm = QgsUnitTypes.LayoutMillimeters
            scale.attemptMove(QgsLayoutPoint((page_width - scale.sizeWithUnits().width()) / 2, 650, mm), False)
            scale.refresh()

            ratio = QgsLayoutItemLabel(layout)
            ratio.setId("Tỷ lệ số")
            denominator = f"{int(round(main_map.scale())):,}".replace(",", ".")
            ratio.setText(f"TỶ LỆ 1:{denominator}")
            ratio_format = ratio.textFormat()
            ratio_format.setFont(QFont("Times New Roman", 10, QFont.Weight.Bold))
            ratio_format.setSize(10)
            ratio.setTextFormat(ratio_format)
            ratio.setHAlign(Qt.AlignmentFlag.AlignHCenter)
            ratio.setVAlign(Qt.AlignmentFlag.AlignVCenter)
            layout.addLayoutItem(ratio)
            ratio.attemptMove(QgsLayoutPoint(page_width / 2 - 60, 660.5, mm), False)
            ratio.attemptResize(QgsLayoutSize(120, 5.2, mm))
