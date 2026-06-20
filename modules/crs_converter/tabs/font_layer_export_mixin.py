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
from .font_file_export_mixin import FontFileExportMixin


class FontLayerExportMixin:
    def _export_font_layer(self, layer, path, driver, ext, mode, target_crs):
        """Chuyển đổi bảng mã thuộc tính và xuất lớp bản đồ."""
        from qgis.core import QgsWkbTypes
        
        fields = layer.fields()
        features = list(layer.getFeatures())
        total = len(features)
        self.progress_font.setMaximum(total + 5)

        mode_labels = [
            "TCVN3 → Unicode", "VNI → Unicode",
            "Unicode → TCVN3", "Không chuyển đổi"
        ]
        self.log_font.append(f"📋 Lớp nguồn: {layer.name()} — {total} đối tượng")
        self.log_font.append(f"🔄 Phương thức: {mode_labels[mode]}")
        self.log_font.append(f"💾 Định dạng xuất: {driver}")
        QApplication.processEvents()

        # Xác định encoding xuất
        if driver == "MapInfo File":
            if mode == 2:
                write_enc = "ISO-8859-1"
                self.log_font.append("📝 Encoding xuất: ISO-8859-1 (TCVN3 raw bytes)")
            else:
                write_enc = "windows-1258"
                self.log_font.append("📝 Encoding xuất: windows-1258 (Unicode -> WindowsVietnamese)")
        else:
            write_enc = "UTF-8"
            self.log_font.append("📝 Encoding xuất: UTF-8")

        # 1. Tạo một lớp ảo (memory layer) tạm thời để thực hiện chuyển đổi
        geom_type = layer.wkbType()
        geom_name = QgsWkbTypes.displayString(geom_type)
        
        src_crs = layer.crs()
        mem_crs = target_crs if target_crs.isValid() else src_crs
        
        mem_layer = QgsVectorLayer(f"{geom_name}?crs={mem_crs.authid()}", "temp_mem", "memory")
        mem_provider = mem_layer.dataProvider()
        
        # Sao chép định nghĩa các thuộc tính
        mem_provider.addAttributes(self._expanded_qgs_fields(fields, mode))
        mem_layer.updateFields()
        
        # Thiết lập biến đổi hệ tọa độ nếu cần
        transform = None
        if src_crs.isValid() and mem_crs.isValid() and src_crs != mem_crs:
            transform = QgsCoordinateTransform(src_crs, mem_crs, QgsProject.instance())
            self.log_font.append("🌐 Thiết lập chuyển đổi hệ tọa độ...")
            
        self.log_font.append("✍️ Đang chuyển đổi bảng mã các đối tượng trong bộ nhớ...")
        
        new_features = []
        converted_count = 0
        
        for idx, feat in enumerate(features):
            self.progress_font.setValue(idx + 1)
            if idx % 50 == 0:
                QApplication.processEvents()
                
            new_feat = QgsFeature(mem_layer.fields())
            
            # Xử lý hình học (và reproject nếu cần)
            if feat.hasGeometry():
                geom = feat.geometry()
                if transform:
                    geom.transform(transform)
                new_feat.setGeometry(geom)
                
            # Xử lý thuộc tính
            attrs = []
            for field in fields:
                val = feat[field.name()]
                if isinstance(val, str) and val and mode < 3:
                    new_val = convert_text_by_mode(val, mode)
                    attrs.append(new_val)
                    if new_val != val:
                        converted_count += 1
                else:
                    attrs.append(val)
            new_feat.setAttributes(attrs)
            new_features.append(new_feat)
            
        mem_provider.addFeatures(new_features)
        mem_layer.updateExtents()
        
        self.log_font.append(f"🔤 Số giá trị chữ đã dịch: {converted_count}")
        self.progress_font.setValue(total + 2)
        QApplication.processEvents()

        # 2. Ghi lớp ảo ra tệp đích dùng QgsVectorFileWriter
        self.log_font.append("💾 Đang ghi dữ liệu ra tệp...")
        save_options = QgsVectorFileWriter.SaveVectorOptions()
        save_options.driverName = driver
        save_options.fileEncoding = write_enc
        
        ctx = QgsCoordinateTransformContext()
        
        err = QgsVectorFileWriter.writeAsVectorFormatV3(
            mem_layer, path, ctx, save_options
        )

        if err[0] != QgsVectorFileWriter.NoError:
            self.log_font.append(f"❌ Lỗi ghi file: {err[1]}")
            QMessageBox.critical(self, "Lỗi ghi file", err[1])
            return

        self.progress_font.setValue(total + 3)
        QApplication.processEvents()

        # 3. Hậu xử lý (post-process) MapInfo TAB nếu cần
        if driver == "MapInfo File":
            postprocess_tab(path, lambda msg: self.log_font.append(msg))

        if driver == "ESRI Shapefile":
            cpg_path = os.path.splitext(path)[0] + ".cpg"
            try:
                with open(cpg_path, 'w') as f:
                    f.write("UTF-8")
                self.log_font.append(f"📄 Đã tạo tệp {os.path.basename(cpg_path)} (UTF-8)")
            except Exception as e:  # noqa: BLE001 — intentional suppress
                self.log_font.append(f"⚠️ Không thể tạo tệp .cpg: {e}")

        # 4. Nạp lớp kết quả vào giao diện QGIS
        load_enc = 'System' if driver == 'MapInfo File' else 'UTF-8'
        try:
            result_layer = QgsVectorLayer(path, os.path.basename(path).replace(ext, ''), 'ogr')
            if result_layer.isValid():
                result_layer.setProviderEncoding('System')
                result_layer.dataProvider().setEncoding(load_enc)
                QgsProject.instance().addMapLayer(result_layer)
                self.log_font.append(f"✅ Đã nạp lớp kết quả vào QGIS: {result_layer.name()}")
        except Exception as e:  # noqa: BLE001 — intentional suppress
            self.log_font.append(f"⚠️ Lỗi nạp lớp: {e}")

        self.progress_font.setValue(total + 5)
        self.log_font.append("\n🎉 HOÀN THÀNH CHUYỂN ĐỔI LỚP BẢN ĐỒ!")

        QMessageBox.information(
            self, "Thành công",
            f"Đã xuất và dịch thành công {total} đối tượng sang file:\n{os.path.basename(path)}"
        )
