"""Mechanically extracted responsibilities from plot_tab.py."""

import os
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QTableWidget,
    QTableWidgetItem,
    QGridLayout,
    QMessageBox,
    QFileDialog,
    QPushButton
)
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsProject,
    QgsVectorLayer,
    QgsCoordinateTransform,
    QgsFeature,
    QgsField,
    QgsPointXY,
    QgsGeometry,
    QgsMapLayerProxyModel
)
from qgis.gui import QgsMapLayerComboBox
from ...common.vn2000_data import populate_crs_combo
from modules.common.ui_utils import create_themed_button, create_file_browser_row
from ...common.qt_compat import (
    MessageBoxNo,
    MessageBoxYes,
    NoEditTriggers,
    SizePolicyExpanding,
    SizePolicyFixed,
)
from ...common.scroll_utils import make_scroll_area
from ..plot_utils import parse_coordinate_file, list_excel_sheets, suggest_column_mappings
from .plot_tab_ui_mixin import PlotTabUiMixin
from .plot_labeling_mixin import PlotLabelingMixin


class PlotExecutionMixin(PlotLabelingMixin):
    def _on_plot_execute_clicked(self):
        path = self.txt_plot_file.text().strip()
        if not path or not hasattr(self, '_plot_all_data') or not self._plot_all_data:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn tệp dữ liệu hợp lệ và kiểm tra preview.")
            return

        col_name = self.cmb_col_name.currentText()
        col_x = self.cmb_col_x.currentText()
        col_y = self.cmb_col_y.currentText()
        col_z = self.cmb_col_z.currentData() if self.cmb_col_z.currentIndex() == 0 else self.cmb_col_z.currentText()
        col_note = self.cmb_col_note.currentData() if self.cmb_col_note.currentIndex() == 0 else self.cmb_col_note.currentText()

        if not col_name or not col_x or not col_y:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng ánh xạ đầy đủ 3 cột chính: Tên điểm, Tọa độ X và Tọa độ Y.")
            return

        if col_x == col_y:
            QMessageBox.warning(self, "Cảnh báo", "Cột tọa độ X và cột tọa độ Y phải khác nhau.")
            return

        src_crs_code = self.cmb_plot_src_crs.currentData()
        src_crs = QgsCoordinateReferenceSystem(src_crs_code)
        if not src_crs.isValid():
            QMessageBox.warning(self, "Cảnh báo", "Hệ tọa độ nguồn không hợp lệ.")
            return

        project_crs = QgsProject.instance().crs()
        target_type = self.cmb_plot_target_type.currentIndex()
        is_existing = (target_type == 1)

        if is_existing:
            pt_layer = self.cmb_plot_target_layer.currentLayer()
            if not pt_layer:
                reply = QMessageBox.question(
                    self, 
                    "Không tìm thấy lớp Point",
                    "Chưa chọn lớp Point đích để ghi dữ liệu. Bạn có muốn tạo một lớp ảo mới (Memory Layer) để rải điểm không?",
                    MessageBoxYes | MessageBoxNo,
                    MessageBoxYes
                )
                if reply == MessageBoxYes:
                    is_existing = False
                    self.cmb_plot_target_type.setCurrentIndex(0)
                    dest_crs = project_crs if project_crs.isValid() else QgsCoordinateReferenceSystem("EPSG:4326")
                else:
                    return
            else:
                dest_crs = pt_layer.crs()
        else:
            dest_crs = project_crs if project_crs.isValid() else QgsCoordinateReferenceSystem("EPSG:4326")

        # Thiết lập biến đổi hệ tọa độ
        transform = None
        if src_crs.isValid() and dest_crs.isValid() and src_crs != dest_crs:
            try:
                transform = QgsCoordinateTransform(src_crs, dest_crs, QgsProject.instance())
            except Exception as e:  # noqa: BLE001 — intentional suppress
                QMessageBox.critical(
                    self, "Lỗi thiết lập CRS", 
                    f"Không thể khởi tạo phép biến đổi hệ tọa độ từ '{src_crs.authid()}' sang '{dest_crs.authid()}': {e}"
                )
                return

        # Chuẩn bị layer
        base_name = os.path.splitext(os.path.basename(path))[0]
        if not is_existing:
            pt_layer = QgsVectorLayer(f"Point?crs={dest_crs.authid()}", f"Rải điểm: {base_name}", "memory")
            pt_provider = pt_layer.dataProvider()
            pt_provider.addAttributes([
                QgsField("name", QVariant.String),
                QgsField("x", QVariant.Double),
                QgsField("y", QVariant.Double),
                QgsField("z", QVariant.Double),
                QgsField("note", QVariant.String)
            ])
            pt_layer.updateFields()
        else:
            if not pt_layer.isEditable():
                if not pt_layer.startEditing():
                    QMessageBox.critical(self, "Lỗi", "Không thể chỉnh sửa lớp Point đã chọn.")
                    return
            pt_provider = pt_layer.dataProvider()

        fields = pt_layer.fields()
        idx_name = fields.indexOf("name") if fields.indexOf("name") >= 0 else fields.indexOf("ten")
        idx_x = fields.indexOf("x")
        idx_y = fields.indexOf("y")
        idx_z = fields.indexOf("z") if fields.indexOf("z") >= 0 else fields.indexOf("h")
        idx_note = fields.indexOf("note") if fields.indexOf("note") >= 0 else fields.indexOf("ghi_chu")

        features = []
        valid_points = []
        skip_count = 0

        for idx, row in enumerate(self._plot_all_data):
            try:
                pt_name = str(row.get(col_name, "")).strip()
                if not pt_name or pt_name == "None":
                    pt_name = f"D_{idx+1}"

                raw_x = row.get(col_x)
                raw_y = row.get(col_y)
                if raw_x is None or raw_y is None:
                    skip_count += 1
                    continue

                x = float(str(raw_x).replace(",", "").strip())
                y = float(str(raw_y).replace(",", "").strip())

                z = 0.0
                if col_z:
                    raw_z = row.get(col_z)
                    if raw_z is not None and str(raw_z).strip() != "" and str(raw_z).lower() != "none":
                        try:
                            z = float(str(raw_z).replace(",", "").strip())
                        except ValueError:
                            pass

                note = ""
                if col_note:
                    raw_note = row.get(col_note)
                    if raw_note is not None and str(raw_note).lower() != "none":
                        note = str(raw_note).strip()

                pt_src = QgsPointXY(x, y)
                if transform:
                    pt_dst = transform.transform(pt_src)
                else:
                    pt_dst = pt_src

                feat = QgsFeature(fields)
                feat.setGeometry(QgsGeometry.fromPointXY(pt_dst))

                if not is_existing:
                    feat.setAttributes([pt_name, x, y, z, note])
                else:
                    attrs = [None] * len(fields)
                    if idx_name >= 0:
                        attrs[idx_name] = pt_name
                    if idx_x >= 0:
                        attrs[idx_x] = x
                    if idx_y >= 0:
                        attrs[idx_y] = y
                    if idx_z >= 0:
                        attrs[idx_z] = z
                    if idx_note >= 0:
                        attrs[idx_note] = note
                    feat.setAttributes(attrs)

                features.append(feat)
                valid_points.append(pt_dst)

            except Exception:  # noqa: BLE001 — intentional suppress
                skip_count += 1
                continue

        if not features:
            QMessageBox.warning(self, "Cảnh báo", "Không rải được điểm nào. Vui lòng kiểm tra lại định dạng tọa độ số thực.")
            return

        if not is_existing:
            pt_provider.addFeatures(features)
            pt_layer.updateExtents()
            
            show_name = self.chk_label_name.isChecked()
            show_z = self.chk_label_z.isChecked()
            color_hex = self.cmb_label_color.currentData()
            self._enable_layer_labeling(pt_layer, show_name, show_z, color_hex)
            
            QgsProject.instance().addMapLayer(pt_layer)
        else:
            pt_layer.addFeatures(features)
            pt_layer.updateExtents()
            pt_layer.triggerRepaint()

        # Nối điểm thành đường/vùng nếu được yêu cầu
        if self.chk_connect_lines.isChecked() and len(valid_points) >= 2:
            if self.chk_close_polygon.isEnabled() and self.chk_close_polygon.isChecked() and len(valid_points) >= 3:
                geom_layer = QgsVectorLayer(f"Polygon?crs={dest_crs.authid()}", f"Vùng nối: {base_name}", "memory")
                geom_provider = geom_layer.dataProvider()
                geom_provider.addAttributes([QgsField("name", QVariant.String)])
                geom_layer.updateFields()

                poly_points = list(valid_points) + [valid_points[0]]
                geom = QgsGeometry.fromPolygonXY([poly_points])
                feat = QgsFeature(geom_layer.fields())
                feat.setGeometry(geom)
                feat.setAttributes([f"Vùng {base_name}"])
                geom_provider.addFeatures([feat])
            else:
                geom_layer = QgsVectorLayer(f"LineString?crs={dest_crs.authid()}", f"Đường nối: {base_name}", "memory")
                geom_provider = geom_layer.dataProvider()
                geom_provider.addAttributes([QgsField("name", QVariant.String)])
                geom_layer.updateFields()

                geom = QgsGeometry.fromPolylineXY(valid_points)
                feat = QgsFeature(geom_layer.fields())
                feat.setGeometry(geom)
                feat.setAttributes([f"Đường {base_name}"])
                geom_provider.addFeatures([feat])

            geom_layer.updateExtents()
            QgsProject.instance().addMapLayer(geom_layer)

        # Phóng tới nhóm điểm vừa rải
        if self.canvas and valid_points:
            from qgis.core import QgsRectangle
            rect = QgsRectangle()
            rect.setMinimal()
            for pt in valid_points:
                rect.combineExtentWith(pt)
            
            rect.grow(10.0 if not rect.isEmpty() else 100.0)
            self.canvas.setExtent(rect)
            self.canvas.refresh()

        success_msg = f"Đã rải thành công {len(features)} điểm lên bản đồ."
        if skip_count > 0:
            success_msg += f"\n(Bỏ qua {skip_count} dòng dữ liệu lỗi không phân tích được)"
        if self.iface:
            self.iface.messageBar().pushSuccess("VNU2F", success_msg)
        else:
            QMessageBox.information(self, "Thành công", success_msg)
