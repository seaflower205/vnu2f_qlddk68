# -*- coding: utf-8 -*-
"""
Giao diện phân hệ xử lý DXF địa chính nâng cao (Advanced DXF Tab).
"""

import os
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QMessageBox,
    QLineEdit, QFileDialog
)
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry, QgsField, QgsFields,
    QgsMapLayerProxyModel
)
from qgis.gui import QgsMapLayerComboBox

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
from ...report_generator.field_mapper import auto_detect_mapping
from .tab_text import tab_text
from .dxf_advanced_ui_mixin import DxfAdvancedUiMixin


def tx(key, **kwargs):
    return tab_text("dxf", key, **kwargs)

class DxfAdvancedTab(DxfAdvancedUiMixin, QWidget):
    """Giao diện xuất nhập DXF địa chính nâng cao sử dụng thư viện ezdxf."""

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.parent_dialog = parent
        self.lbl_warn = None
        
        self._build_ui()


    def _deps_ready(self):
        return is_installed("ezdxf") and is_installed("shapely")

    def showEvent(self, event):
        """Khi tab được kích hoạt, tự động kiểm tra lại dependency xem đã cài đặt xong chưa."""
        super().showEvent(event)
        now_ok = self._deps_ready()
        if now_ok != self.deps_ok:
            self.deps_ok = now_ok
            self._set_dependency_controls(now_ok)

    def _set_dependency_controls(self, enabled: bool):
        for widget in (self.btn_import, self.btn_export, self.btn_browse_in):
            widget.setEnabled(enabled)
        if self.lbl_warn:
            self.lbl_warn.setVisible(not enabled)

    def _on_browse_in(self):
        path, _ = QFileDialog.getOpenFileName(self, tx("dialog.open"), "", "AutoCAD Drawing Exchange (*.dxf)")
        if path:
            self.txt_dxf_in.setText(path)

    def _on_import_dxf(self):
        if not self._deps_ready():
            QMessageBox.warning(self, tr("common.warning"), tx("missing.import"))
            return
        filepath = self.txt_dxf_in.text().strip()
        if not filepath or not os.path.exists(filepath):
            QMessageBox.warning(self, tr("common.warning"), tx("warn.need_file"))
            return

        from ...dxf_engine.dxf_reader import read_dxf_data, match_parcels_with_attributes
            
        # Đọc dữ liệu từ DXF
        dxf_data = read_dxf_data(filepath)
        
        # Tách riêng các đối tượng hình học đa giác khép kín và nhãn
        dxf_polygons = []
        dxf_lines = []
        
        for poly in dxf_data["polylines"]:
            geom = poly["geometry"]
            if geom.geom_type == "Polygon":
                dxf_polygons.append(geom)
            else:
                dxf_lines.append(geom)
                
        if not dxf_polygons:
            QMessageBox.warning(
                self, tr("common.error"),
                tx("warn.no_polygons")
            )
            return
            
        # Ghép ranh thửa với nhãn
        parcels = match_parcels_with_attributes(
            dxf_polygons,
            dxf_data["blocks"],
            dxf_data["texts"]
        )
        
        # Tạo lớp thửa đất tạm thời trong QGIS
        # Lấy CRS mặc định của dự án hoặc WGS84
        crs = QgsProject.instance().crs()
        crs_auth = crs.authid() if crs.isValid() else "EPSG:32648" # Mặc định múi 48N nếu chưa lập
        
        layer_name = f"[Import DXF] {os.path.basename(filepath)}"
        mem_layer = QgsVectorLayer(f"Polygon?crs={crs_auth}", layer_name, "memory")
        prov = mem_layer.dataProvider()
        
        # Định nghĩa cấu trúc trường dữ liệu
        fields = QgsFields()
        fields.append(QgsField("SOTHUA", QVariant.String, len=10))
        fields.append(QgsField("SOTO", QVariant.String, len=10))
        fields.append(QgsField("LOAIDAT", QVariant.String, len=10))
        fields.append(QgsField("DIENTICH", QVariant.Double))
        fields.append(QgsField("_text_notes", QVariant.String, len=254))
        
        prov.addAttributes(fields)
        mem_layer.updateFields()
        
        # Thêm features
        features = []
        for p in parcels:
            feat = QgsFeature(fields)
            feat.setGeometry(QgsGeometry.fromWkt(p["geometry"].wkt))
            
            attrs = p["attributes"]
            feat.setAttributes([
                attrs.get("SOTHUA", ""),
                attrs.get("SOTO", ""),
                attrs.get("LOAIDAT", "Khac"),
                attrs.get("DIENTICH", 0.0),
                attrs.get("_notes_text", "")
            ])
            features.append(feat)
            
        prov.addFeatures(features)
        mem_layer.updateExtents()
        
        # Nạp vào project
        QgsProject.instance().addMapLayer(mem_layer)
        
        QMessageBox.information(
            self, tr("common.success"),
            tx(
                "success.import",
                parcel_count=len(parcels),
                text_count=len(dxf_data["texts"]),
                block_count=len(dxf_data["blocks"]),
                layer_name=mem_layer.name(),
            )
        )

    def _on_layer_changed(self):
        """Tự động quét trường khi thay đổi lớp thửa đất."""
        layer = self.cmb_poly_layer.currentLayer()
        if not layer:
            for cmb in [self.cmb_f_sothua, self.cmb_f_soto, self.cmb_f_loaidat, self.cmb_f_dientich]:
                cmb.clear()
            return
            
        fields = [""] + [f.name() for f in layer.fields()]
        
        for cmb in [self.cmb_f_sothua, self.cmb_f_soto, self.cmb_f_loaidat, self.cmb_f_dientich]:
            cmb.clear()
            cmb.addItems(fields)
            
        # Ánh xạ trường tự động phát hiện được
        detected = auto_detect_mapping(layer.fields())
        
        if detected.get("sothua") in fields:
            self.cmb_f_sothua.setCurrentText(detected["sothua"])
        if detected.get("soto") in fields:
            self.cmb_f_soto.setCurrentText(detected["soto"])
        if detected.get("loaidat") in fields:
            self.cmb_f_loaidat.setCurrentText(detected["loaidat"])
        if detected.get("dientich") in fields:
            self.cmb_f_dientich.setCurrentText(detected["dientich"])

    def _on_export_dxf(self):
        if not self._deps_ready():
            QMessageBox.warning(self, tr("common.warning"), tx("missing.export"))
            return
        layer = self.cmb_poly_layer.currentLayer()
        if not layer:
            QMessageBox.warning(self, tr("common.warning"), tx("warn.need_layer"))
            return
            
        mapping = {
            "sothua": self.cmb_f_sothua.currentText(),
            "soto": self.cmb_f_soto.currentText(),
            "loaidat": self.cmb_f_loaidat.currentText(),
            "dientich": self.cmb_f_dientich.currentText()
        }
        
        if not mapping["sothua"]:
            QMessageBox.warning(self, tr("common.warning"), tx("warn.need_sothua"))
            return
            
        # Chọn đường lưu tệp tin DXF
        save_path, _ = QFileDialog.getSaveFileName(self, tx("dialog.save"), "", "AutoCAD Drawing Exchange (*.dxf)")
        if not save_path:
            return
            
        # Đọc dữ liệu thửa đất
        features = []
        for feat in layer.getFeatures():
            geom = feat.geometry()
            if geom and not geom.isEmpty():
                # Gửi WKT và tất cả thuộc tính
                attrs = {}
                for field in layer.fields():
                    attrs[field.name()] = feat[field.name()]
                    
                features.append({
                    "wkt": geom.asWkt(),
                    "attributes": attrs
                })
                
        if not features:
            QMessageBox.warning(self, tr("common.warning"), tx("warn.empty_layer"))
            return

        from ...dxf_engine.dxf_writer import export_features_to_dxf
            
        # Thực hiện xuất DXF
        success = export_features_to_dxf(
            features,
            save_path,
            mapping=mapping,
            boundary_layer="RANH_THUA",
            label_layer="NHAN_THUA"
        )
        
        if success:
            QMessageBox.information(
                self, tx("success.export_title"),
                tx("success.export", feature_count=len(features), path=save_path)
            )
        else:
            QMessageBox.critical(self, tr("common.error"), tx("error.export"))

    def reset(self):
        """Đặt lại các combo box."""
        self.txt_dxf_in.clear()
        self.cmb_poly_layer.setCurrentIndex(0)
        self._on_layer_changed()
