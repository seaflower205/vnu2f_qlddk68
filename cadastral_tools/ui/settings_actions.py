"""CRS, area, and print-layout actions for ``SettingsTab``."""
from qgis.PyQt.QtGui import QFont
from qgis.PyQt.QtWidgets import QInputDialog, QMessageBox, QPushButton
from qgis.core import (
    Qgis, QgsCoordinateReferenceSystem, QgsLayoutItemLabel, QgsLayoutItemLegend,
    QgsLayoutItemMap, QgsLayoutItemPicture, QgsLayoutItemScaleBar, QgsLayoutPoint,
    QgsLayoutSize, QgsPrintLayout, QgsProject, QgsUnitTypes,
)
from qgis.utils import iface

from ..core import area_calculator, crs_helper


class SettingsActionsMixin:
    def check_layer_crs_status(self):
        layer_id = self.plugin_state.active_layer_id
        if not layer_id:
            self.lbl_crs_status.setText("Chưa chọn lớp ranh thửa đất nào.")
            self.lbl_crs_status.setStyleSheet("color: #71717a;")
            return
        layer = QgsProject.instance().mapLayer(layer_id)
        if not layer:
            return
        crs = layer.crs()
        auth_id = crs.authid()
        if crs_helper.check_crs_is_valid(crs):
            self.lbl_crs_status.setText(f"CRS: {auth_id} ({crs.description()}) - Hợp lệ")
            self.lbl_crs_status.setStyleSheet("color: #22c55e; font-weight: bold;")
        else:
            self.lbl_crs_status.setText(f"CRS không chuẩn: {auth_id} ({crs.description()})")
            self.lbl_crs_status.setStyleSheet("color: #ef4444; font-weight: bold;")
            self._show_qgis_crs_warning_bar(auth_id)

    def _show_qgis_crs_warning_bar(self, auth_id):
        if not iface:
            return
        from qgis.gui import QgsMessageBarItem
        iface.messageBar().clearWidgets()
        widget = QgsMessageBarItem(
            "Hệ tọa độ không chuẩn",
            f"Lớp hiện tại đang dùng CRS '{auth_id}' không chuẩn địa chính Việt Nam. Hãy thực hiện chiếu lại.",
            Qgis.Warning,
        )
        button = QPushButton("Chiếu lại...", widget)
        button.clicked.connect(self.open_reproject_dialog)
        widget.layout().addWidget(button)
        iface.messageBar().pushWidget(widget)

    def open_reproject_dialog(self):
        layer = QgsProject.instance().mapLayer(self.plugin_state.active_layer_id)
        if not layer:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn lớp ranh thửa cần chiếu lại.")
            return
        choices = {
            "EPSG:3405 - VN-2000 / UTM zone 48N (Múi 6 độ Miền Bắc)": "EPSG:3405",
            "EPSG:3406 - VN-2000 / UTM zone 49N (Múi 6 độ Miền Nam)": "EPSG:3406",
            "EPSG:4756 - VN-2000 / Hệ tọa độ 3D Quốc gia": "EPSG:4756",
            "EPSG:9210 - VN-2000 / Múi 3 độ kinh tuyến 102 (Lai Châu,...)": "EPSG:9210",
            "EPSG:9211 - VN-2000 / Múi 3 độ kinh tuyến 105 (Hà Nội, Hà Tây,...)": "EPSG:9211",
            "EPSG:9212 - VN-2000 / Múi 3 độ kinh tuyến 108 (Đà Nẵng, Quảng Nam,...)": "EPSG:9212",
            "EPSG:9213 - VN-2000 / Múi 3 độ kinh tuyến 111 (TP.HCM, Đồng Nai,...)": "EPSG:9213",
        }
        choice, ok = QInputDialog.getItem(
            self, "Chiếu lại hệ tọa độ VN-2000", "Chọn CRS VN-2000 mục tiêu:",
            list(choices), 0, False,
        )
        if not ok or not choice:
            return
        methods = [
            "Chiếu lại trực tiếp trên lớp (In-place, có Rollback)",
            "Chiếu lại sang Lớp dữ liệu mới (Memory layer)",
        ]
        method, ok = QInputDialog.getItem(
            self, "Phương thức chiếu lại", "Chọn cách lưu trữ dữ liệu chiếu lại:",
            methods, 0, False,
        )
        if not ok or not method:
            return
        epsg = choices[choice]
        try:
            if "trực tiếp" in method:
                result = crs_helper.reproject_layer_in_place(
                    layer, QgsCoordinateReferenceSystem(epsg)
                )
                if result:
                    self.check_layer_crs_status()
            else:
                result = crs_helper.reproject_layer_to_new(
                    layer, QgsCoordinateReferenceSystem(epsg)
                )
                if result:
                    self.plugin_state.active_layer_id = result.id()
            if result and iface:
                iface.messageBar().pushMessage(
                    "Địa chính", f"Đã chuyển đổi tọa độ sang {epsg}.",
                    level=Qgis.Success, duration=4,
                )
        except Exception as error:  # noqa: BLE001
            QMessageBox.critical(self, "Lỗi chiếu lại", f"Không thể chiếu lại hệ tọa độ: {error}")

    def recalculate_area(self):
        layer = QgsProject.instance().mapLayer(self.plugin_state.active_layer_id)
        if not layer:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn lớp ranh thửa đất.")
            return
        field_name = self.cbo_area_field.currentData()
        unit = "ha" if self.rad_ha.isChecked() else "m2"
        try:
            count = area_calculator.recalculate_layer_area(
                layer=layer, field_name="" if field_name == "__NEW__" else field_name,
                create_new=field_name == "__NEW__", unit=unit,
            )
            self.populate_fields()
            if iface:
                iface.messageBar().pushMessage(
                    "Thành công", f"Đã cập nhật diện tích ({'ha' if unit == 'ha' else 'm²'}) cho {count} thửa đất thành công.",
                    level=Qgis.Success, duration=5,
                )
        except Exception as error:  # noqa: BLE001
            QMessageBox.critical(self, "Lỗi", f"Không thể tính toán diện tích: {error}")

    def create_default_print_layout(self):
        project = QgsProject.instance()
        name = "Bản đồ Ranh thửa địa chính A4"
        manager = project.layoutManager()
        existing = manager.layoutByName(name)
        if existing:
            manager.removeLayout(existing)
        layout = QgsPrintLayout(project)
        layout.initializeDefaults()
        layout.setName(name)
        layout.pageCollection().pages()[0].setPageSize(
            "A4", layout.pageCollection().pages()[0].Orientation.Landscape
        )
        title = QgsLayoutItemLabel(layout)
        title.setText("BẢN ĐỒ CHI TIẾT RANH THỬA ĐẤT ĐỊA CHÍNH")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setHtmlState(False)
        layout.addLayoutItem(title)
        title.attemptMove(QgsLayoutPoint(15, 10, QgsUnitTypes.LayoutMillimeters))
        title.attemptResize(QgsLayoutSize(180, 10, QgsUnitTypes.LayoutMillimeters))
        map_item = QgsLayoutItemMap(layout)
        layer = project.mapLayer(self.plugin_state.active_layer_id)
        if layer:
            map_item.setExtent(layer.extent())
        layout.addLayoutItem(map_item)
        map_item.attemptMove(QgsLayoutPoint(15, 22, QgsUnitTypes.LayoutMillimeters))
        map_item.attemptResize(QgsLayoutSize(180, 130, QgsUnitTypes.LayoutMillimeters))
        legend = QgsLayoutItemLegend(layout)
        legend.setTitle("CHÚ GIẢI LOẠI ĐẤT")
        legend.setTitleFont(QFont("Arial", 10, QFont.Bold))
        legend.setItemFont(QFont("Arial", 8))
        layout.addLayoutItem(legend)
        legend.attemptMove(QgsLayoutPoint(205, 22, QgsUnitTypes.LayoutMillimeters))
        legend.attemptResize(QgsLayoutSize(75, 90, QgsUnitTypes.LayoutMillimeters))
        scale = QgsLayoutItemScaleBar(layout)
        scale.setLinkedMap(map_item)
        scale.setUnits(QgsUnitTypes.DistanceMeters)
        scale.setNumberOfSegments(2)
        scale.setUnitsAsHtml(True)
        scale.setUnitLabel("m")
        layout.addLayoutItem(scale)
        scale.attemptMove(QgsLayoutPoint(15, 160, QgsUnitTypes.LayoutMillimeters))
        scale.attemptResize(QgsLayoutSize(50, 12, QgsUnitTypes.LayoutMillimeters))
        north = QgsLayoutItemPicture(layout)
        north.setPicturePath("images/themes/default/arrows/NorthArrow_01.svg")
        layout.addLayoutItem(north)
        north.attemptMove(QgsLayoutPoint(232, 125, QgsUnitTypes.LayoutMillimeters))
        north.attemptResize(QgsLayoutSize(20, 20, QgsUnitTypes.LayoutMillimeters))
        manager.addLayout(layout)
        if iface:
            iface.showLayoutDesignerView(layout)
            iface.messageBar().pushMessage(
                "In ấn", f"Đã khởi tạo và mở trình thiết kế bố cục in '{name}'.",
                level=Qgis.Success, duration=5,
            )
