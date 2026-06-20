"""Mechanically extracted responsibilities from map_layout_service.py."""

from __future__ import annotations
import os
from .map_layout_contracts import LayoutResult, LayoutValidationError, MapLayoutRequest, unique_layout_name, validate_request
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


class MapLayoutCreateMixin:
    def create(self, request: MapLayoutRequest) -> LayoutResult:
        validate_request(request)
        warnings = []
        layout_controllers = []
        resolution = resolve_context_layer(
            self.project, request.coverage_layer, request.admin_level, request.parent_layer
        )
        if resolution.warning:
            warnings.append(resolution.warning)
        if request.profile == "tt08" and resolution.layer is None:
            raise LayoutValidationError(resolution.warning)

        feature = self._target_feature(request)
        if feature is None:
            raise LayoutValidationError("Layer không có đối tượng phù hợp để tạo layout.")
        layout = self._load_layout(request)
        self._set_page(layout, request, feature)
        self._configure_labels(layout, request, feature)
        main_map = self._configure_main_map(layout, request, feature)
        create_neighbor_label_items(layout, request, feature, main_map)
        self._add_grid_crs_note(layout, main_map)
        self._configure_legend_and_scale(layout, main_map, request)

        from qgis.core import QgsLayoutItemMap
        inset = layout.itemById("InsetMap")
        if isinstance(inset, QgsLayoutItemMap) and resolution.layer is not None:
            controller = OverviewController(layout, main_map, inset, request, resolution)
            if not controller.update_for_feature(feature):
                message = "Phạm vi sơ đồ vị trí không rộng hơn và bao chứa bản đồ chính."
                if request.profile == "tt08":
                    raise LayoutValidationError(message)
                warnings.append(message)
            self._controllers.append(controller)
            layout_controllers.append(controller)
        elif request.profile == "tt08":
            raise LayoutValidationError("Template TT08 thiếu map item ID 'InsetMap'.")

        atlas = None
        if request.atlas_enabled:
            atlas = self._configure_atlas(layout, main_map, request)
            for controller in layout_controllers:
                controller.connect_atlas(atlas)
        chart_controller = self._configure_chart(layout, request, feature)
        if chart_controller is not None:
            layout_controllers.append(chart_controller)
        if atlas is not None and chart_controller is not None:
            chart_controller.connect_atlas(atlas)
        # Qt signal connections alone do not reliably retain Python receivers.
        # Keep per-layout controllers alive for as long as the designer/layout.
        layout._vnu2f_controllers = layout_controllers
        self._configure_signatures(layout, request.signatures_enabled)

        base = f"HTSDD_{request.admin_level}_{date.today():%Y%m%d}" if request.profile == "tt08" else f"Ban_do_{date.today():%Y%m%d}"
        layout.setName(unique_layout_name(self.project.layoutManager(), base))
        layout.setCustomProperty("vnu2f/legal_basis", "TT08/2024 + TT23/2025")
        layout.setCustomProperty("vnu2f/legal_as_of", request.legal_date.isoformat())
        self.project.layoutManager().addLayout(layout)
        self.iface.openLayoutDesigner(layout)
        return LayoutResult(layout, tuple(warnings))
