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
from .topology_build_mixin import TopologyBuildMixin


class TopologyValidateMixin:
    def _on_validate_topo(self):
        """Kiểm tra lỗi topo chồng đè giữa các thửa đất."""
        if not self._require_deps():
            return
        layer = self.cmb_polygon_layer.currentLayer()
        if not layer:
            QMessageBox.warning(self, tr("common.warning"), tx("warn.need_polygon"))
            return
            
        loads = _get_shapely()
        from topology_tools import check_topology_errors

        polygons = []
        feat_ids = []
        
        for feat in layer.getFeatures():
            geom = feat.geometry()
            if geom and not geom.isEmpty():
                try:
                    polygons.append(loads(geom.asWkt()))
                    feat_ids.append(feat.id())
                except Exception:  # noqa: BLE001 — intentional suppress
                    pass
                    
        if not polygons:
            QMessageBox.warning(self, tr("common.error"), tx("error.no_valid_polygon"))
            return
            
        # Chạy kiểm tra chồng đè
        overlap_errors = check_topology_errors(polygons)
        
        # Cập nhật bảng kết quả
        self.tbl_errors.setRowCount(0)
        if not overlap_errors:
            QMessageBox.information(self, tr("common.success"), tx("success.no_overlap"))
            return
            
        # Tạo memory layer lưu vết lỗi chồng đè để trực quan hóa màu đỏ
        crs_auth = layer.crs().authid()
        err_layer = QgsVectorLayer(f"Polygon?crs={crs_auth}", f"[Lỗi topo] {layer.name()}", "memory")
        prov = err_layer.dataProvider()
        prov.addAttributes([
            QgsField("thua_a", QVariant.Int),
            QgsField("thua_b", QVariant.Int),
            QgsField("dientich", QVariant.Double)
        ])
        err_layer.updateFields()
        
        err_features = []
        self.tbl_errors.setRowCount(len(overlap_errors))
        for idx, err in enumerate(overlap_errors):
            id_a = feat_ids[err['idx_a']]
            id_b = feat_ids[err['idx_b']]
            area = err['overlap_area']
            
            # Thêm dòng vào bảng
            self.tbl_errors.setItem(idx, 0, QTableWidgetItem(str(id_a)))
            self.tbl_errors.setItem(idx, 1, QTableWidgetItem(str(id_b)))
            self.tbl_errors.setItem(idx, 2, QTableWidgetItem(str(area)))
            
            # Thêm đối tượng lỗi không gian
            feat = QgsFeature(err_layer.fields())
            feat.setGeometry(QgsGeometry.fromWkt(err['overlap_geometry'].wkt))
            feat.setAttributes([id_a, id_b, area])
            err_features.append(feat)
            
        prov.addFeatures(err_features)
        err_layer.updateExtents()
        QgsProject.instance().addMapLayer(err_layer)
        
        QMessageBox.warning(
            self, tr("common.warning"),
            tx("warn.overlap", error_count=len(overlap_errors), layer_name=err_layer.name())
        )
    def _on_repair_geom(self):
        """Sửa lỗi hình học tự động cho lớp polygon đang chọn."""
        if not self._require_deps():
            return
        layer = self.cmb_polygon_layer.currentLayer()
        if not layer:
            QMessageBox.warning(self, tr("common.warning"), tx("warn.need_repair_layer"))
            return
            
        loads = _get_shapely()
        from topology_tools import validate_and_repair

        # Bắt đầu chỉnh sửa
        layer.startEditing()
        
        invalid_count = 0
        repaired_count = 0
        
        for feat in layer.getFeatures():
            geom = feat.geometry()
            if not geom:
                continue
                
            try:
                poly = loads(geom.asWkt())
                check = validate_and_repair(poly)
                
                if not check['is_valid']:
                    invalid_count += 1
                    repaired_geom = check['repaired_geometry']
                    
                    if repaired_geom and not repaired_geom.is_empty:
                        # Ghi đè geometry đã sửa
                        qgs_geom = QgsGeometry.fromWkt(repaired_geom.wkt)
                        layer.changeGeometry(feat.id(), qgs_geom)
                        repaired_count += 1
            except Exception:  # noqa: BLE001 — intentional suppress
                pass
                
        # Lưu thay đổi
        layer.commitChanges()
        
        if invalid_count > 0:
            QMessageBox.information(
                self, tr("common.success"),
                tx("success.repair", invalid_count=invalid_count, repaired_count=repaired_count)
            )
        else:
            QMessageBox.information(self, tr("common.success"), tx("success.no_repair"))
