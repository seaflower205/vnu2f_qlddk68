# -*- coding: utf-8 -*-
"""Regression tests for automatic layouts, TT08 contracts and inset resolution."""

from pathlib import Path
from xml.etree import ElementTree

import pytest

from modules.crs_converter.tabs.land_use_chart import aggregate_land_use
from modules.crs_converter.tabs.map_layout_overview import (
    extent_is_broader,
    resolve_context_layer,
)
from modules.crs_converter.tabs.map_layout_service import (
    LayoutValidationError,
    MapLayoutRequest,
    TT08_TEMPLATES,
    unique_layout_name,
    validate_request,
)


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_IDS = {
    "Map",
    "InsetMap",
    "InsetTitle",
    "Tên bản đồ",
    "Khu vực bản đồ",
    "Chú dẫn",
    "Scale mét",
    "SignatureBlock",
    "LegalMetadata",
}


@pytest.mark.parametrize("level,filename", TT08_TEMPLATES.items())
def test_tt08_template_contract(level, filename):
    root = ElementTree.parse(ROOT / "templates" / filename).getroot()
    ids = {node.attrib.get("id") for node in root.iter("LayoutItem")}
    assert REQUIRED_IDS <= ids, f"{level} thiếu {REQUIRED_IDS - ids}"
    map_items = [node for node in root.iter("LayoutItem") if node.attrib.get("type") == "65639"]
    assert len(map_items) == 2


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("TT08_HTSDD_commune.qpt", 2),
        ("TT08_HTSDD_district.qpt", 3),
        ("TT08_HTSDD_province.qpt", 3),
        ("TT08_HTSDD_region_country.qpt", 5),
    ],
)
def test_tt08_frame_count(filename, expected):
    root = ElementTree.parse(ROOT / "templates" / filename).getroot()
    ids = [node.attrib.get("id", "") for node in root.iter("LayoutItem")]
    assert sum(item.startswith("TT08_Frame_") for item in ids) == expected


class FakeRect:
    def __init__(self, xmin, ymin, xmax, ymax):
        self.values = xmin, ymin, xmax, ymax

    def isEmpty(self):
        return False

    def xMinimum(self):
        return self.values[0]

    def yMinimum(self):
        return self.values[1]

    def xMaximum(self):
        return self.values[2]

    def yMaximum(self):
        return self.values[3]

    def width(self):
        return self.values[2] - self.values[0]

    def height(self):
        return self.values[3] - self.values[1]


def test_inset_extent_must_contain_and_be_broader():
    main = FakeRect(2, 2, 8, 8)
    assert extent_is_broader(FakeRect(0, 0, 10, 10), main)
    assert not extent_is_broader(FakeRect(2, 2, 8, 8), main)
    assert not extent_is_broader(FakeRect(3, 3, 9, 9), main)


class FakeLayer:
    def __init__(self, name, *, count=2, marker="", selected=(1,)):
        self._name = name
        self._count = count
        self._marker = marker
        self._selected = list(selected)

    def isValid(self):
        return True

    def name(self):
        return self._name

    def featureCount(self):
        return self._count

    def customProperty(self, key, default=""):
        return self._marker if key == "vnu2f/admin_level" else default

    def selectedFeatureIds(self):
        return self._selected


class FakeProject:
    def __init__(self, layers):
        self._layers = layers

    def mapLayers(self):
        return {str(index): layer for index, layer in enumerate(self._layers)}


def test_overview_resolver_precedence_and_fallback():
    coverage = FakeLayer("Các xã")
    explicit = FakeLayer("Ranh huyện chỉ định")
    candidate = FakeLayer("Ranh giới huyện", marker="district")
    project = FakeProject([coverage, candidate])
    assert resolve_context_layer(project, coverage, "commune", explicit).source == "explicit"
    assert resolve_context_layer(project, coverage, "commune").layer is candidate
    assert resolve_context_layer(FakeProject([coverage]), coverage, "commune").source == "coverage"


def test_single_layout_requires_exactly_one_selection():
    request = MapLayoutRequest(FakeLayer("Xã", selected=()))
    with pytest.raises(LayoutValidationError, match="đúng một"):
        validate_request(request)
    request.coverage_layer = FakeLayer("Xã", selected=(1, 2))
    with pytest.raises(LayoutValidationError, match="đúng một"):
        validate_request(request)


class FakeGeometry:
    def __init__(self, area):
        self._area = area

    def area(self):
        return self._area


class FakeFeature:
    def __init__(self, code, area=None, geom_area=0):
        self.values = {"LoaiDat": code, "DienTich": area}
        self._geometry = FakeGeometry(geom_area)

    def __getitem__(self, key):
        return self.values[key]

    def geometry(self):
        return self._geometry


def test_land_use_chart_aggregation_uses_three_legal_groups():
    features = [
        FakeFeature("LUC", 100),
        FakeFeature("ODT", 200),
        FakeFeature("BCS", None, 50),
        FakeFeature("UNKNOWN", 999),
    ]
    data = aggregate_land_use(features, "LoaiDat", "DienTich")
    assert data.areas == {"NNN": 100.0, "PNN": 200.0, "CSD": 50.0}
    assert round(sum(data.percent(group) for group in data.areas), 8) == 100.0


def test_unique_layout_name_is_deterministic():
    class Manager:
        def layoutByName(self, name):
            return name in {"Bản đồ", "Bản đồ_1"}

    assert unique_layout_name(Manager(), "Bản đồ") == "Bản đồ_2"


def _polygon_layer(name, polygons, fields):
    from qgis.PyQt.QtCore import QVariant
    from qgis.core import QgsFeature, QgsField, QgsGeometry, QgsVectorLayer

    layer = QgsVectorLayer("Polygon?crs=EPSG:3405", name, "memory")
    layer.dataProvider().addAttributes([QgsField(field, QVariant.String) for field in fields])
    layer.updateFields()
    features = []
    for wkt, values in polygons:
        feature = QgsFeature(layer.fields())
        feature.setGeometry(QgsGeometry.fromWkt(wkt))
        feature.setAttributes(values)
        features.append(feature)
    layer.dataProvider().addFeatures(features)
    layer.updateExtents()
    return layer


def test_qgis_layout_builds_real_inset_without_mutating_source(qgis_app):
    from unittest.mock import MagicMock

    from qgis.core import QgsProject
    from modules.crs_converter.tabs.map_layout_service import MapLayoutService

    project = QgsProject.instance()
    coverage = _polygon_layer(
        "Ranh giới xã",
        [
            ("POLYGON((0 0,10 0,10 10,0 10,0 0))", ["Xã A", "01", "H01"]),
            ("POLYGON((10 0,20 0,20 10,10 10,10 0))", ["Xã B", "02", "H01"]),
        ],
        ["TenDVHC", "MaDVHC", "MaCapTren"],
    )
    parent = _polygon_layer(
        "Ranh giới huyện",
        [("POLYGON((-5 -5,25 -5,25 15,-5 15,-5 -5))", ["H01"])],
        ["MaDVHC"],
    )
    project.addMapLayers([coverage, parent], False)
    coverage.selectByIds([next(coverage.getFeatures()).id()])
    renderer_dump = coverage.renderer().dump()

    iface = MagicMock()
    iface.mapCanvas().layers.return_value = [coverage, parent]
    request = MapLayoutRequest(
        coverage_layer=coverage,
        parent_layer=parent,
        admin_level="commune",
        name_field="TenDVHC",
        parent_code_field="MaCapTren",
        parent_lookup_field="MaDVHC",
        chart_enabled=False,
    )
    result = MapLayoutService(iface, project).create(request)
    try:
        main_map = result.layout.itemById("Map")
        inset = result.layout.itemById("InsetMap")
        assert main_map is not None and inset is not None
        assert len(inset.layers()) == 2
        assert inset.overviews().size() == 1
        assert inset.overviews().overview(0).linkedMap() is main_map
        assert coverage.renderer().dump() == renderer_dump
        assert coverage.selectedFeatureCount() == 1
        iface.openLayoutDesigner.assert_called_once_with(result.layout)
    finally:
        project.layoutManager().removeLayout(result.layout)
        project.removeMapLayers([coverage.id(), parent.id()])


def test_qgis_atlas_refreshes_inset_for_each_feature(qgis_app):
    from unittest.mock import MagicMock

    from qgis.core import QgsProject
    from modules.crs_converter.tabs.map_layout_service import MapLayoutService

    project = QgsProject.instance()
    coverage = _polygon_layer(
        "Ranh giới xã Atlas",
        [
            ("POLYGON((0 0,10 0,10 10,0 10,0 0))", ["Xã A", "01", "H01"]),
            ("POLYGON((20 0,30 0,30 10,20 10,20 0))", ["Xã B", "02", "H02"]),
        ],
        ["TenDVHC", "MaDVHC", "MaCapTren"],
    )
    parent = _polygon_layer(
        "Ranh giới huyện Atlas",
        [
            ("POLYGON((-5 -5,15 -5,15 15,-5 15,-5 -5))", ["H01"]),
            ("POLYGON((15 -5,35 -5,35 15,15 15,15 -5))", ["H02"]),
        ],
        ["MaDVHC"],
    )
    project.addMapLayers([coverage, parent], False)
    renderer_dump = coverage.renderer().dump()
    iface = MagicMock()
    iface.mapCanvas().layers.return_value = [coverage, parent]
    request = MapLayoutRequest(
        coverage_layer=coverage,
        parent_layer=parent,
        admin_level="commune",
        atlas_enabled=True,
        name_field="TenDVHC",
        parent_code_field="MaCapTren",
        parent_lookup_field="MaDVHC",
        chart_enabled=False,
    )
    result = MapLayoutService(iface, project).create(request)
    atlas = result.layout.atlas()
    inset = result.layout.itemById("InsetMap")
    try:
        assert atlas.enabled() and atlas.count() == 2
        atlas.beginRender()
        assert atlas.first()
        first_extent = inset.extent()
        first_styles = inset.layerStyleOverrides()
        assert atlas.next()
        second_extent = inset.extent()
        second_styles = inset.layerStyleOverrides()
        assert first_extent.center().x() != second_extent.center().x()
        assert first_styles[coverage.id()] != second_styles[coverage.id()]
        assert coverage.renderer().dump() == renderer_dump
        assert coverage.selectedFeatureCount() == 0
    finally:
        atlas.endRender()
        project.layoutManager().removeLayout(result.layout)
        project.removeMapLayers([coverage.id(), parent.id()])
