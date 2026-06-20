# -*- coding: utf-8 -*-
"""
Tab 2: Tọa độ điểm đo
"""
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QGridLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QMessageBox,
    QApplication,
    QPushButton
)
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
    QgsPointXY,
    QgsVectorLayer,
    QgsField,
    QgsFeature,
    QgsGeometry
)
from qgis.gui import QgsVertexMarker

from ...common.vn2000_data import VN2000_PROVINCES
from modules.common.ui_utils import create_themed_button
from ...common.qt_compat import SizePolicyExpanding, SizePolicyFixed
from ..crs_utils import CoordinateTransformer
from .point_tab_ui_mixin import PointTabUiMixin

class PointTab(PointTabUiMixin, QWidget):
    def __init__(self, iface, canvas, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.canvas = canvas
        self.parent_dialog = parent
        self._marker = None
        self._mem_layer = None
        self._build_ui()


    def _tune_control_sizes(self):
        for label in self.findChildren(QLabel):
            label.setWordWrap(True)
            if label.text():
                label.setToolTip(label.text())

        for widget in self.findChildren((QLineEdit, QComboBox)):
            widget.setMinimumHeight(38)
            widget.setSizePolicy(SizePolicyExpanding, SizePolicyFixed)

        for button in self.findChildren(QPushButton):
            if button.text():
                button.setToolTip(button.text())
            button.setMinimumHeight(38)
            button.setSizePolicy(SizePolicyExpanding, SizePolicyFixed)

    def _on_convert_dms(self):
        try:
            lat = CoordinateTransformer.parse_dms(self.txt_lat_dms.text())
            lon = CoordinateTransformer.parse_dms(self.txt_lon_dms.text())
        except Exception as e:  # noqa: BLE001 — intentional suppress
            QMessageBox.warning(self, "Lỗi dữ liệu", f"Tọa độ DMS nhập không đúng định dạng ({e}).")
            return
        
        self._show_point_results(lat, lon)

    def _on_convert_metric(self):
        crs_code = self.cmb_prov_crs.currentData()
        try:
            x = float(self.txt_x.text().replace(",", "").strip())
            y = float(self.txt_y.text().replace(",", "").strip())
        except ValueError:
            QMessageBox.warning(self, "Lỗi dữ liệu", "Tọa độ X và Y phải là số thực.")
            return

        src_crs = QgsCoordinateReferenceSystem(crs_code)
        dst_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        
        if not src_crs.isValid():
            QMessageBox.critical(
                self, "Lỗi CRS", 
                "CSDL chưa đăng ký hệ tọa độ VN-2000 cho tỉnh này.\n"
                "Hãy kiểm tra lại CSDL hệ tọa độ!"
            )
            return

        try:
            xform = QgsCoordinateTransform(src_crs, dst_crs, QgsProject.instance())
            pt = xform.transform(x, y)
            self._show_point_results(pt.y(), pt.x(), pre_x=x, pre_y=y)
        except Exception as e:  # noqa: BLE001 — intentional suppress
            QMessageBox.warning(self, "Lỗi tính toán", f"Không thể chuyển đổi tọa độ: {e}")

    def _show_point_results(self, lat, lon, pre_x=None, pre_y=None):
        self.txt_res_lat.setText(f"{lat:.8f}")
        self.txt_res_lon.setText(f"{lon:.8f}")
        self.txt_res_dms.setText(
            f"{CoordinateTransformer.dd_to_dms(lat, True)}  {CoordinateTransformer.dd_to_dms(lon, False)}"
        )

        # Tính VN-2000 dựa trên tỉnh đang chọn ở ComboBox
        crs_code = self.cmb_prov_crs.currentData()
        src_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        dst_crs = QgsCoordinateReferenceSystem(crs_code)
        
        if dst_crs.isValid():
            try:
                xform = QgsCoordinateTransform(src_crs, dst_crs, QgsProject.instance())
                pt = xform.transform(QgsPointXY(lon, lat))
                self.txt_res_x.setText(f"{pt.x():.3f}")
                self.txt_res_y.setText(f"{pt.y():.3f}")
            except Exception:  # noqa: BLE001 — intentional suppress
                self.txt_res_x.setText("Lỗi tính toán")
                self.txt_res_y.clear()
        else:
            self.txt_res_x.setText("Hệ CRS chưa đăng ký")
            self.txt_res_y.clear()

    def _get_active_point(self):
        try:
            lat = float(self.txt_res_lat.text())
            lon = float(self.txt_res_lon.text())
            return lat, lon
        except ValueError:
            # Thử tự động chạy tính toán nếu có đầu vào mà chưa bấm nút dịch
            if self.txt_lat_dms.text() and self.txt_lon_dms.text():
                self._on_convert_dms()
                return self._get_active_point()
            elif self.txt_x.text() and self.txt_y.text():
                self._on_convert_metric()
                return self._get_active_point()
        return None

    def _on_copy(self):
        pt = self._get_active_point()
        if not pt:
            QMessageBox.warning(self, "Cảnh báo", "Không có kết quả tọa độ để sao chép.")
            return
        
        x = self.txt_res_x.text()
        y = self.txt_res_y.text()
        text = f"X: {x}, Y: {y} | Lat: {pt[0]:.8f}, Lon: {pt[1]:.8f}"
        QApplication.clipboard().setText(text)
        if self.iface:
            self.iface.messageBar().pushSuccess("VNU2F", f"Đã sao chép: {text}")

    def _on_zoom(self):
        pt = self._get_active_point()
        if not pt or not self.canvas:
            return
        
        wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
        canvas_crs = self.canvas.mapSettings().destinationCrs()
        try:
            transform = QgsCoordinateTransform(wgs84, canvas_crs, QgsProject.instance())
            canvas_pt = transform.transform(QgsPointXY(pt[1], pt[0]))
        except Exception as e:  # noqa: BLE001 — intentional suppress
            QMessageBox.warning(self, "Lỗi chiếu bản đồ", f"Không thể chiếu tọa độ lên bản đồ: {e}")
            return

        self.canvas.setCenter(canvas_pt)
        self.canvas.zoomScale(2000)
        self.canvas.refresh()

    def _on_mark(self):
        pt = self._get_active_point()
        if not pt or not self.canvas:
            return

        self.cleanup()

        wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
        canvas_crs = self.canvas.mapSettings().destinationCrs()
        try:
            transform = QgsCoordinateTransform(wgs84, canvas_crs, QgsProject.instance())
            canvas_pt = transform.transform(QgsPointXY(pt[1], pt[0]))
        except Exception as e:  # noqa: BLE001 — intentional suppress
            QMessageBox.warning(self, "Lỗi chiếu bản đồ", f"Không thể chiếu tọa độ lên bản đồ: {e}")
            return

        marker = QgsVertexMarker(self.canvas)
        marker.setCenter(canvas_pt)
        marker.setColor(QColor(239, 68, 68)) # Màu đỏ tươi
        marker.setIconType(QgsVertexMarker.ICON_CROSS)
        marker.setIconSize(16)
        marker.setPenWidth(3)
        self._marker = marker

        self.canvas.setCenter(canvas_pt)
        self.canvas.zoomScale(2000)
        self.canvas.refresh()

    def _on_add_to_layer(self):
        pt = self._get_active_point()
        if not pt or not self.iface:
            return

        proj = QgsProject.instance()
        if not self._mem_layer or not proj.mapLayer(self._mem_layer.id()):
            # Tạo lớp ảo mới nếu chưa có
            self._mem_layer = QgsVectorLayer("Point?crs=EPSG:4326", "Điểm đo VNU2F", "memory")
            dp = self._mem_layer.dataProvider()
            dp.addAttributes([
                QgsField("name", QVariant.String),
                QgsField("lat", QVariant.Double),
                QgsField("lon", QVariant.Double),
                QgsField("x_vn2k", QVariant.Double),
                QgsField("y_vn2k", QVariant.Double)
            ])
            self._mem_layer.updateFields()
            QgsProject.instance().addMapLayer(self._mem_layer)

        feat = QgsFeature(self._mem_layer.fields())
        feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(pt[1], pt[0])))
        
        name = self.txt_point_name.text().strip()
        if not name:
            name = f"Điểm đo {self._mem_layer.featureCount() + 1}"
            
        try:
            x_vn = float(self.txt_res_x.text())
            y_vn = float(self.txt_res_y.text())
        except ValueError:
            x_vn, y_vn = 0.0, 0.0

        feat.setAttributes([
            name,
            round(pt[0], 8),
            round(pt[1], 8),
            round(x_vn, 3),
            round(y_vn, 3)
        ])
        
        self._mem_layer.dataProvider().addFeature(feat)
        self._mem_layer.updateExtents()
        self._mem_layer.triggerRepaint()
        
        self.iface.messageBar().pushSuccess("VNU2F", f"Đã thêm điểm '{name}' vào Lớp bản đồ.")

    def reset(self):
        """Xóa trắng các trường nhập và xóa Marker bản đồ."""
        self.txt_lat_dms.clear()
        self.txt_lon_dms.clear()
        self.txt_x.clear()
        self.txt_y.clear()
        self.txt_res_lat.clear()
        self.txt_res_lon.clear()
        self.txt_res_dms.clear()
        self.txt_res_x.clear()
        self.txt_res_y.clear()
        self.txt_point_name.clear()
        self.cleanup()

    def cleanup(self):
        """Dọn dẹp marker khỏi canvas nếu có."""
        if self._marker and self.canvas:
            try:
                self.canvas.scene().removeItem(self._marker)
            except Exception:  # noqa: BLE001 — intentional suppress
                pass
            self._marker = None

    def hideEvent(self, event):
        """Dọn dẹp marker khi tab bị ẩn."""
        self.cleanup()
        if event:
            super().hideEvent(event)
