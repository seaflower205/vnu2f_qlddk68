"""Mechanically extracted responsibilities from map_layout_overview.py."""

from __future__ import annotations
from .map_overview_geometry import expanded_extent, extent_is_broader
from dataclasses import dataclass


class OverviewUpdateMixin:
    def update_for_feature(self, feature):
        if feature is None or not feature.hasGeometry():
            return False
        context_source = self.resolution.layer
        if context_source is None:
            return False
        parent_value = None
        if self.request.parent_code_field:
            try:
                parent_value = feature[self.request.parent_code_field]
            except (KeyError, TypeError):
                parent_value = None
        lookup_field = self.request.parent_lookup_field
        if context_source is self.request.coverage_layer and not lookup_field:
            lookup_field = self.request.parent_code_field
        self.inset_map.setKeepLayerSet(True)
        self.inset_map.setKeepLayerStyles(True)
        layers = [self.request.coverage_layer]
        if context_source is not self.request.coverage_layer:
            layers.append(context_source)
        self.inset_map.setLayers(layers)
        overrides = {
            self.request.coverage_layer.id(): self._coverage_style(
                self.request.coverage_layer, feature.id()
            )
        }
        if context_source is not self.request.coverage_layer:
            overrides[context_source.id()] = self._context_style(context_source)
        self.inset_map.setLayerStyleOverrides(overrides)
        self.inset_map.setCrs(context_source.crs())
        inset_margin = self.request.inset_margin
        if (
            self.request.admin_level == "country"
            and context_source is self.request.coverage_layer
        ):
            # TT08 permits the national boundary itself as the last-resort
            # context. Give it enough surrounding space to remain a true inset.
            inset_margin = max(inset_margin, self.request.main_margin + 10.0)
        context_extent = expanded_extent(
            self._context_extent(context_source, lookup_field, parent_value),
            inset_margin,
        )
        main_extent = self.main_map.extent()
        if self.main_map.crs() != context_source.crs():
            try:
                from qgis.core import QgsCoordinateTransform, QgsProject

                transform = QgsCoordinateTransform(
                    self.main_map.crs(), context_source.crs(), QgsProject.instance().transformContext()
                )
                main_extent = transform.transformBoundingBox(main_extent)
            except Exception:  # noqa: BLE001 - CRS providers may reject exotic project CRS
                return False
        if not extent_is_broader(context_extent, main_extent):
            from qgis.core import QgsRectangle

            combined = QgsRectangle(context_extent)
            combined.combineExtentWith(main_extent)
            context_extent = expanded_extent(combined, max(inset_margin, 2.0))
            if not extent_is_broader(context_extent, main_extent):
                return False
        self.inset_map.zoomToExtent(context_extent)
        self.inset_map.refresh()
        return True
