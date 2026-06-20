"""Mechanically extracted responsibilities from font_tab.py."""

import os
import traceback
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QComboBox,
    QProgressBar,
    QTextEdit,
    QMessageBox,
    QFileDialog,
    QApplication,
)
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsProject,
    QgsVectorLayer,
    QgsVectorFileWriter,
    QgsCoordinateTransform,
    QgsFeature,
    QgsField,
    QgsCoordinateTransformContext
)
from qgis.gui import QgsMapLayerComboBox
from ...common.vn2000_data import populate_crs_combo
from modules.common.ui_utils import (
    create_themed_button,
    create_file_browser_row,
    create_bottom_action_bar,
    create_centered_panel,
    create_form_group,
    create_growing_form,
    create_solid_primary_button,
    tune_form_controls,
)
from ...common.i18n import tr
from ..font_utils import convert_text_by_mode, postprocess_tab


class FontFileExportMixin:
    def _export_font_file(self, in_path, out_path, mode, target_crs):
        """Dịch trực tiếp file Shapefile trên đĩa dùng thư viện GDAL/OGR nhúng trong QGIS."""
        from osgeo import ogr, gdal
        
        if not os.path.exists(in_path):
            raise FileNotFoundError(f"Không tìm thấy file nguồn: {in_path}")
            
        driver = ogr.GetDriverByName("ESRI Shapefile")
        if os.path.exists(out_path):
            driver.DeleteDataSource(out_path)
            
        gdal.SetConfigOption('SHAPE_ENCODING', 'ISO-8859-1')
        in_ds = driver.Open(in_path, 0)
        if in_ds is None:
            raise Exception(f"Không thể mở file Shapefile nguồn: {in_path}")
            
        in_layer = in_ds.GetLayer()
        in_defn = in_layer.GetLayerDefn()
        total = in_layer.GetFeatureCount()
        self.progress_font.setMaximum(total + 5)
        
        fields_list = []
        for i in range(in_defn.GetFieldCount()):
            f_defn = in_defn.GetFieldDefn(i)
            if f_defn.GetType() == ogr.OFTString:
                fields_list.append(f_defn.GetName())
                
        self.log_font.append(f"📋 File nguồn: {os.path.basename(in_path)} — {total} đối tượng")
        self.log_font.append(f"🔤 Các cột chữ: {len(fields_list)} ({', '.join(fields_list[:5])})")
        
        gdal.SetConfigOption('SHAPE_ENCODING', 'UTF-8')
        out_ds = driver.CreateDataSource(out_path)
        if out_ds is None:
            in_ds = None
            raise Exception(f"Không thể tạo file Shapefile kết quả: {out_path}")
            
        src_srs = in_layer.GetSpatialRef()
        out_srs = target_crs if target_crs.isValid() else src_srs
        
        out_layer = out_ds.CreateLayer(
            os.path.splitext(os.path.basename(out_path))[0],
            srs=out_srs,
            geom_type=in_layer.GetGeomType()
        )
        
        for i in range(in_defn.GetFieldCount()):
            f_defn = in_defn.GetFieldDefn(i)
            if f_defn.GetType() == ogr.OFTString:
                out_defn = ogr.FieldDefn(f_defn.GetName(), f_defn.GetType())
                out_defn.SetWidth(self._expanded_text_width(f_defn.GetWidth(), mode))
                out_defn.SetPrecision(f_defn.GetPrecision())
                out_layer.CreateField(out_defn)
            else:
                out_layer.CreateField(f_defn)
            
        transform = None
        if src_srs and out_srs and not src_srs.IsSame(out_srs):
            from osgeo import osr
            transform = osr.CoordinateTransformation(src_srs, out_srs)
            self.log_font.append("🌐 Thiết lập chuyển đổi hệ tọa độ...")
            
        converted_count = 0
        for idx in range(total):
            self.progress_font.setValue(idx + 1)
            if idx % 50 == 0:
                QApplication.processEvents()
                
            feat = in_layer.GetFeature(idx)
            out_feat = ogr.Feature(out_layer.GetLayerDefn())
            
            geom = feat.GetGeometryRef()
            if geom:
                if transform:
                    geom.Transform(transform)
                out_feat.SetGeometry(geom)
                
            for i in range(in_defn.GetFieldCount()):
                f_defn = in_defn.GetFieldDefn(i)
                f_name = f_defn.GetName()
                val = feat.GetField(f_name)
                
                if isinstance(val, str) and val and mode < 3:
                    new_val = convert_text_by_mode(val, mode)
                    out_feat.SetField(f_name, new_val)
                    if new_val != val:
                        converted_count += 1
                else:
                    out_feat.SetField(f_name, val)
                    
            out_layer.CreateFeature(out_feat)
            
        in_ds = None
        out_ds = None
        
        self.log_font.append(f"🔤 Đã dịch hoàn tất: {converted_count} chuỗi ký tự")
        self.progress_font.setValue(total + 2)
        QApplication.processEvents()
        
        cpg_path = os.path.splitext(out_path)[0] + ".cpg"
        try:
            with open(cpg_path, 'w') as f:
                f.write("UTF-8")
            self.log_font.append(f"📄 Đã tạo tệp {os.path.basename(cpg_path)} (UTF-8)")
        except Exception as e:  # noqa: BLE001 — intentional suppress
            self.log_font.append(f"⚠️ Không thể tạo file .cpg: {e}")
            
        try:
            result_layer = QgsVectorLayer(out_path, os.path.splitext(os.path.basename(out_path))[0], 'ogr')
            if result_layer.isValid():
                QgsProject.instance().addMapLayer(result_layer)
                self.log_font.append(f"✅ Đã nạp lớp kết quả vào QGIS: {result_layer.name()}")
        except Exception as e:  # noqa: BLE001 — intentional suppress
            self.log_font.append(f"⚠️ Lỗi nạp lớp: {e}")
            
        self.progress_font.setValue(total + 5)
        self.log_font.append("\n🎉 HOÀN THÀNH CHUYỂN ĐỔI FILE!")
        
        QMessageBox.information(
            self, "Thành công",
            f"Đã chuyển đổi thành công tệp:\n{os.path.basename(out_path)}"
        )
