# -*- coding: utf-8 -*-
"""Zinc UI controller for automatic map layouts with dynamic overview maps."""

from __future__ import annotations

from datetime import date

from qgis.PyQt.QtCore import QDate
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QLineEdit,
    QMessageBox,
    QWidget,
    QVBoxLayout,
)
from qgis.core import Qgis
from qgis.gui import QgsFieldComboBox, QgsMapLayerComboBox

from modules.common.scroll_utils import make_scroll_area
from modules.common.ui_utils import (
    create_form_group,
    create_growing_form,
    create_themed_button,
    tune_form_controls,
)
from .map_layout_service import (
    MapLayoutRequest,
    MapLayoutService,
    PAPER_SIZES,
    STANDARD_SCALES,
    LayoutValidationError,
)


PROFILE_ITEMS = (
    ("Hiện trạng sử dụng đất — TT08", "tt08"),
    ("Khung bản đồ chung", "general"),
    ("Khung trình chiếu", "slide"),
)
LEVEL_ITEMS = (
    ("Cấp xã", "commune"),
    ("Cấp huyện", "district"),
    ("Cấp tỉnh", "province"),
    ("Vùng kinh tế - xã hội", "region"),
    ("Cả nước", "country"),
)


class MapLayoutTab(QWidget):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self._service = MapLayoutService(iface)
        self._setup_ui()
        self._connect_data_sources()

    def _combo_with_data(self, items):
        combo = QComboBox(self)
        for label, value in items:
            combo.addItem(label, value)
        return combo

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(12)
        scroll, _, content = make_scroll_area(self, spacing=12, margins=(0, 0, 0, 0))

        group, group_layout = create_form_group("1. Hồ sơ và đầu ra", self)
        form = create_growing_form()
        self.cmb_profile = self._combo_with_data(PROFILE_ITEMS)
        self.cmb_level = self._combo_with_data(LEVEL_ITEMS)
        self.cmb_paper = self._combo_with_data(tuple((key, key) for key in PAPER_SIZES))
        self.cmb_paper.setCurrentIndex(self.cmb_paper.findData("A0"))
        self.cmb_scale = QComboBox(self)
        self.cmb_scale.addItem("Tự động theo đối tượng", None)
        for scale in STANDARD_SCALES:
            self.cmb_scale.addItem(f"1:{scale:,}".replace(",", "."), scale)
        self.chk_auto_orientation = QCheckBox("Tự chọn ngang/dọc theo hình dạng ranh giới", self)
        self.chk_auto_orientation.setChecked(True)
        self.chk_atlas = QCheckBox("Tạo Atlas hàng loạt", self)
        self.chk_selected_only = QCheckBox("Atlas chỉ dùng các đối tượng đang chọn", self)
        form.addRow("Hồ sơ:", self.cmb_profile)
        form.addRow("Cấp bản đồ:", self.cmb_level)
        form.addRow("Khổ giấy:", self.cmb_paper)
        form.addRow("Tỷ lệ:", self.cmb_scale)
        form.addRow("Hướng giấy:", self.chk_auto_orientation)
        form.addRow("Chế độ:", self.chk_atlas)
        form.addRow("Phạm vi Atlas:", self.chk_selected_only)
        group_layout.addLayout(form)
        content.addWidget(group)

        group, group_layout = create_form_group("2. Dữ liệu bản đồ và sơ đồ vị trí", self)
        form = create_growing_form()
        self.cmb_boundary = QgsMapLayerComboBox(self)
        self.cmb_boundary.setFilters(Qgis.LayerFilter.PolygonLayer)
        self.cmb_parent = QgsMapLayerComboBox(self)
        self.cmb_parent.setFilters(Qgis.LayerFilter.PolygonLayer)
        self.cmb_parent.setAllowEmptyLayer(True)
        self.cmb_land = QgsMapLayerComboBox(self)
        self.cmb_land.setFilters(Qgis.LayerFilter.PolygonLayer)
        self.cmb_land.setAllowEmptyLayer(True)
        self.fld_name = QgsFieldComboBox(self)
        self.fld_code = QgsFieldComboBox(self)
        self.fld_parent_code = QgsFieldComboBox(self)
        self.fld_parent_lookup = QgsFieldComboBox(self)
        self.fld_land_code = QgsFieldComboBox(self)
        self.fld_area = QgsFieldComboBox(self)
        form.addRow("Layer ranh giới:", self.cmb_boundary)
        form.addRow("Layer cấp trên (tự tìm nếu trống):", self.cmb_parent)
        form.addRow("Layer hiện trạng đất:", self.cmb_land)
        form.addRow("Trường tên ĐVHC:", self.fld_name)
        form.addRow("Trường mã ĐVHC:", self.fld_code)
        form.addRow("Mã cấp trên trên layer chính:", self.fld_parent_code)
        form.addRow("Mã tra cứu trên layer cấp trên:", self.fld_parent_lookup)
        form.addRow("Trường mã loại đất:", self.fld_land_code)
        form.addRow("Trường diện tích (tùy chọn):", self.fld_area)
        group_layout.addLayout(form)
        content.addWidget(group)

        group, group_layout = create_form_group("3. Nội dung và quy cách", self)
        form = create_growing_form()
        self.txt_title = QLineEdit(self)
        self.txt_title.setPlaceholderText("BẢN ĐỒ HIỆN TRẠNG SỬ DỤNG ĐẤT NĂM 2026")
        self.txt_study = QLineEdit(self)
        self.txt_study.setPlaceholderText("Tự lấy từ trường tên nếu để trống")
        self.txt_org = QLineEdit(self)
        self.txt_author = QLineEdit(self)
        self.date_legal = QDateEdit(QDate.currentDate(), self)
        self.date_legal.setCalendarPopup(True)
        self.date_map = QDateEdit(QDate.currentDate(), self)
        self.date_map.setCalendarPopup(True)
        self.spn_main_margin = QDoubleSpinBox(self)
        self.spn_main_margin.setRange(0, 30)
        self.spn_main_margin.setValue(10)
        self.spn_main_margin.setSuffix(" %")
        self.spn_inset_margin = QDoubleSpinBox(self)
        self.spn_inset_margin.setRange(0, 30)
        self.spn_inset_margin.setValue(5)
        self.spn_inset_margin.setSuffix(" %")
        self.chk_chart = QCheckBox("Tự tính biểu đồ cơ cấu sử dụng đất", self)
        self.chk_chart.setChecked(True)
        self.chk_signatures = QCheckBox("Tạo khối ký xác nhận", self)
        self.chk_signatures.setChecked(True)
        form.addRow("Tiêu đề:", self.txt_title)
        form.addRow("Khu vực:", self.txt_study)
        form.addRow("Đơn vị xây dựng:", self.txt_org)
        form.addRow("Người lập:", self.txt_author)
        form.addRow("Ngày áp dụng pháp lý:", self.date_legal)
        form.addRow("Ngày lập bản đồ:", self.date_map)
        form.addRow("Lề bản đồ chính:", self.spn_main_margin)
        form.addRow("Lề sơ đồ vị trí:", self.spn_inset_margin)
        form.addRow("Biểu đồ:", self.chk_chart)
        form.addRow("Ký duyệt:", self.chk_signatures)
        group_layout.addLayout(form)
        content.addWidget(group)

        self.btn_create = create_themed_button("Tạo khung bản đồ", theme="success", parent=self)
        self.btn_create.clicked.connect(self._create_layout)
        content.addWidget(self.btn_create)
        root.addWidget(scroll)
        tune_form_controls(self)

    def _connect_data_sources(self):
        self.cmb_boundary.layerChanged.connect(self._on_boundary_changed)
        self.cmb_parent.layerChanged.connect(self.fld_parent_lookup.setLayer)
        self.cmb_land.layerChanged.connect(self._on_land_changed)
        self.cmb_profile.currentIndexChanged.connect(self._on_profile_changed)
        self.chk_atlas.toggled.connect(self.chk_selected_only.setEnabled)
        self._on_boundary_changed(self.cmb_boundary.currentLayer())
        self._on_land_changed(self.cmb_land.currentLayer())
        self._on_profile_changed()

    def _set_preferred_field(self, combo, aliases):
        for alias in aliases:
            index = combo.findText(alias)
            if index >= 0:
                combo.setCurrentIndex(index)
                return

    def _on_boundary_changed(self, layer):
        for combo in (self.fld_name, self.fld_code, self.fld_parent_code):
            combo.setLayer(layer)
        self._set_preferred_field(self.fld_name, ("TenDVHC", "tenXa", "TENXA", "TEN", "Name"))
        self._set_preferred_field(self.fld_code, ("MaDVHC", "maXa", "MAXA", "MADVHC", "Code"))
        self._set_preferred_field(self.fld_parent_code, ("MaCapTren", "PARENT_CODE"))

    def _on_land_changed(self, layer):
        self.fld_land_code.setLayer(layer)
        self.fld_area.setLayer(layer)
        self._set_preferred_field(self.fld_land_code, ("KHLOAIDAT", "MALOAIDAT", "LoaiDat", "LOAIDAT", "MaLoaiDat"))
        self._set_preferred_field(self.fld_area, ("DienTich", "DIENTICH", "Shape_Area"))

    def _on_profile_changed(self, *_):
        strict = self.cmb_profile.currentData() == "tt08"
        self.cmb_level.setEnabled(strict)
        self.date_legal.setEnabled(strict)

    def _request(self):
        legal_qdate = self.date_legal.date()
        map_qdate = self.date_map.date()
        return MapLayoutRequest(
            coverage_layer=self.cmb_boundary.currentLayer(),
            parent_layer=self.cmb_parent.currentLayer(),
            land_use_layer=self.cmb_land.currentLayer(),
            profile=self.cmb_profile.currentData(),
            admin_level=self.cmb_level.currentData(),
            atlas_enabled=self.chk_atlas.isChecked(),
            selected_only=self.chk_selected_only.isChecked(),
            paper=self.cmb_paper.currentData(),
            auto_orientation=self.chk_auto_orientation.isChecked(),
            scale=self.cmb_scale.currentData(),
            main_margin=self.spn_main_margin.value(),
            inset_margin=self.spn_inset_margin.value(),
            title=self.txt_title.text().strip(),
            organization=self.txt_org.text().strip(),
            study_area=self.txt_study.text().strip(),
            author=self.txt_author.text().strip(),
            map_date=map_qdate.toString("dd/MM/yyyy"),
            name_field=self.fld_name.currentField(),
            code_field=self.fld_code.currentField(),
            parent_code_field=self.fld_parent_code.currentField(),
            parent_lookup_field=self.fld_parent_lookup.currentField(),
            land_code_field=self.fld_land_code.currentField(),
            area_field=self.fld_area.currentField(),
            chart_enabled=self.chk_chart.isChecked(),
            signatures_enabled=self.chk_signatures.isChecked(),
            legal_date=date(legal_qdate.year(), legal_qdate.month(), legal_qdate.day()),
        )

    def _create_layout(self):
        try:
            result = self._service.create(self._request())
        except LayoutValidationError as exc:
            QMessageBox.warning(self, "Không thể tạo khung bản đồ", str(exc))
            return
        except Exception as exc:  # noqa: BLE001 - QGIS runtime boundary
            QMessageBox.critical(self, "Lỗi tạo khung bản đồ", str(exc))
            return
        if result.warnings:
            self.iface.messageBar().pushWarning("VNU2F", " ".join(result.warnings))
        self.iface.messageBar().pushSuccess("VNU2F", f"Đã tạo: {result.layout.name()}")

    def reset(self):
        self.cmb_profile.setCurrentIndex(0)
        self.cmb_level.setCurrentIndex(0)
        self.cmb_paper.setCurrentIndex(self.cmb_paper.findData("A0"))
        self.cmb_scale.setCurrentIndex(0)
        self.chk_auto_orientation.setChecked(True)
        self.chk_atlas.setChecked(False)
        self.chk_selected_only.setChecked(False)
        self.txt_title.clear()
        self.txt_study.clear()
        self.txt_org.clear()
        self.txt_author.clear()
        self.date_legal.setDate(QDate.currentDate())
        self.date_map.setDate(QDate.currentDate())
        self.spn_main_margin.setValue(10)
        self.spn_inset_margin.setValue(5)
        self.chk_chart.setChecked(True)
        self.chk_signatures.setChecked(True)

    def parent_dialog(self):
        current = self.parent()
        while current:
            if isinstance(current, QDialog):
                return current
            current = current.parent()
        return None
