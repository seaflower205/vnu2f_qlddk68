"""Mechanically extracted responsibilities from topology_tab.py."""

from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox, QMessageBox,
    QTableWidget, QTableWidgetItem
)
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry, QgsField, QgsFields,
    QgsMapLayerProxyModel
)
from qgis.gui import QgsMapLayerComboBox
from ...common.qt_compat import HeaderStretch
from ...common.scroll_utils import make_scroll_area
from modules.common.ui_utils import (
    create_themed_button,
    create_centered_panel,
    create_form_group,
    create_growing_form,
    tune_form_controls
)
from ...common.i18n import tr
from ...common.dep_installer import is_installed
from .tab_text import tab_text
from .topology_helpers import get_shapely as _get_shapely, tx
from .topology_ui_mixin import TopologyUiMixin


class TopologyBuildMixin:
    def _on_clean_lines(self):
        """Làm sạch lớp ranh và tạo lớp đường tạm thời."""
        if not self._require_deps():
            return
        layer = self.cmb_line_layer.currentLayer()
        if not layer:
            QMessageBox.warning(self, tr("common.warning"), tx("warn.need_line"))
            return
            
        tolerance = self.spin_tolerance.value()
        dangle_threshold = self.spin_dangle.value()
        
        loads = _get_shapely()
        from topology_tools import clean_lines

        # Load geometries
        shapely_lines = []
        for feat in layer.getFeatures():
            geom = feat.geometry()
            if geom and not geom.isEmpty():
                try:
                    shapely_lines.append(loads(geom.asWkt()))
                except Exception:  # noqa: BLE001 — intentional suppress
                    pass
                    
        if not shapely_lines:
            QMessageBox.warning(self, tr("common.error"), tx("error.no_lines"))
            return
            
        # Gọi thuật toán làm sạch
        cleaned_lines = clean_lines(shapely_lines, tolerance, dangle_threshold)
        
        # Tạo memory layer mới
        crs_auth = layer.crs().authid()
        mem_layer = QgsVectorLayer(f"LineString?crs={crs_auth}", f"[Đã làm sạch] {layer.name()}", "memory")
        prov = mem_layer.dataProvider()
        
        # Copy fields từ layer cũ
        prov.addAttributes(layer.fields())
        mem_layer.updateFields()
        
        # Ghi các line đã làm sạch
        features = []
        for idx, line in enumerate(cleaned_lines):
            feat = QgsFeature()
            feat.setGeometry(QgsGeometry.fromWkt(line.wkt))
            feat.setAttributes([None] * len(layer.fields()))
            features.append(feat)
            
        prov.addFeatures(features)
        mem_layer.updateExtents()
        
        # Nạp vào dự án
        QgsProject.instance().addMapLayer(mem_layer)
        self.cleaned_layer = mem_layer
        
        # Tự động chọn lớp mới cho bước 2
        self.cmb_clean_line_layer.setLayer(mem_layer)
        
        QMessageBox.information(
            self, tr("common.success"),
            tx(
                "success.clean",
                before_count=len(shapely_lines),
                after_count=len(cleaned_lines),
                layer_name=mem_layer.name(),
            )
        )
    def _on_polygonize(self):
        """Đóng vùng Line thành Polygon và gán nhãn."""
        if not self._require_deps():
            return
        line_layer = self.cmb_clean_line_layer.currentLayer()
        if not line_layer:
            QMessageBox.warning(self, tr("common.warning"), tx("warn.need_clean_line"))
            return
            
        label_layer = self.cmb_label_layer.currentLayer()
        
        loads = _get_shapely()
        from topology_tools import create_polygons, assign_labels

        # Load lines
        shapely_lines = []
        for feat in line_layer.getFeatures():
            geom = feat.geometry()
            if geom and not geom.isEmpty():
                try:
                    shapely_lines.append(loads(geom.asWkt()))
                except Exception:  # noqa: BLE001 — intentional suppress
                    pass
                    
        if not shapely_lines:
            QMessageBox.warning(self, tr("common.error"), tx("error.empty_lines"))
            return
            
        # Đóng vùng
        polygons = create_polygons(shapely_lines)
        if not polygons:
            QMessageBox.warning(self, tr("common.error"), tx("error.no_polygons"))
            return
            
        # Trích xuất nhãn từ điểm nhãn nếu có
        label_points = []
        fields = QgsFields()
        
        if label_layer:
            fields = label_layer.fields()
            for feat in label_layer.getFeatures():
                geom = feat.geometry()
                if geom and not geom.isEmpty():
                    try:
                        pt = loads(geom.asWkt())
                        attrs = {}
                        for field in fields:
                            attrs[field.name()] = feat[field.name()]
                        label_points.append({
                            'geometry': pt,
                            'attributes': attrs
                        })
                    except Exception:  # noqa: BLE001 — intentional suppress
                        pass
        else:
            # Nếu không có lớp nhãn, tạo cấu trúc trường mặc định chuẩn địa chính
            fields.append(QgsField("SOTHUA", QVariant.String, len=10))
            fields.append(QgsField("SOTO", QVariant.String, len=10))
            fields.append(QgsField("LOAIDAT", QVariant.String, len=10))
            fields.append(QgsField("TENCHU", QVariant.String, len=100))
            fields.append(QgsField("DIENTICH", QVariant.Double))
            
        # Thêm trường thông tin bổ sung và cảnh báo
        fields.append(QgsField("DIENTICH_HP", QVariant.Double))
        fields.append(QgsField("_warning", QVariant.String, len=100))
        
        # Gán nhãn
        parcels = assign_labels(polygons, label_points)
        
        # Tạo memory layer thửa đất
        crs_auth = line_layer.crs().authid()
        poly_layer = QgsVectorLayer(f"Polygon?crs={crs_auth}", f"[Thửa đất] {line_layer.name().replace('[Đã làm sạch] ', '')}", "memory")
        prov = poly_layer.dataProvider()
        prov.addAttributes(fields)
        poly_layer.updateFields()
        
        features = []
        for p in parcels:
            feat = QgsFeature(fields)
            feat.setGeometry(QgsGeometry.fromWkt(p['geometry'].wkt))
            
            # Gán giá trị thuộc tính
            attrs = []
            for field in fields:
                name = field.name()
                attrs.append(p['attributes'].get(name, None))
                
            feat.setAttributes(attrs)
            features.append(feat)
            
        prov.addFeatures(features)
        poly_layer.updateExtents()
        
        # Nạp vào QGIS
        QgsProject.instance().addMapLayer(poly_layer)
        self.polygon_layer = poly_layer
        
        # Tự động chọn lớp mới cho bước 3
        self.cmb_polygon_layer.setLayer(poly_layer)
        
        QMessageBox.information(
            self, tr("common.success"),
            tx("success.polygonize", polygon_count=len(polygons), layer_name=poly_layer.name())
        )
