# -*- coding: utf-8 -*-
"""
Tab 3: Chuyển đổi Font chữ bản đồ
"""
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
from .font_layer_export_mixin import FontLayerExportMixin
from .font_tab_ui_mixin import FontTabUiMixin


class FontTab(FontTabUiMixin, FontLayerExportMixin, FontFileExportMixin, QWidget):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.parent_dialog = parent
        self._build_ui()


    def _show_log_panel(self):
        self.grp_font_log.setVisible(True)
        self.log_font.clear()

    def _expanded_text_width(self, width, mode):
        if mode >= 3:
            return width
        if not width or width < 1:
            return 254
        return min(254, max(width, width * 3))

    def _expanded_qgs_fields(self, fields, mode):
        output_fields = []
        for field in fields:
            new_field = QgsField(field)
            if new_field.type() == QVariant.String:
                new_field.setLength(self._expanded_text_width(new_field.length(), mode))
            output_fields.append(new_field)
        return output_fields

    def _on_font_source_type_changed(self, index):
        is_file = (index == 1)
        self.cmb_font_layer.setVisible(not is_file)
        if self.row_font_layer_label:
            self.row_font_layer_label.setVisible(not is_file)
            
        self.cmb_font_format.setVisible(not is_file)
        if self.row_font_format_label:
            self.row_font_format_label.setVisible(not is_file)
            
        self.txt_font_file_in.setVisible(is_file)
        self.btn_font_browse_in.setVisible(is_file)
        self.lbl_font_file_in.setVisible(is_file)
        self.txt_font_file_out.setVisible(is_file)
        self.btn_font_browse_out.setVisible(is_file)
        self.lbl_font_file_out.setVisible(is_file)

    def _on_font_browse_in(self):
        path, _ = QFileDialog.getOpenFileName(self, tr("font.dialog.open_shp"), "", "Shapefile (*.shp)")
        if path:
            self.txt_font_file_in.setText(path)
            base, ext = os.path.splitext(path)
            self.txt_font_file_out.setText(base + "_translated" + ext)

    def _on_font_browse_out(self):
        path, _ = QFileDialog.getSaveFileName(self, tr("font.dialog.save_shp"), "", "Shapefile (*.shp)")
        if path:
            self.txt_font_file_out.setText(path)

    def _on_font_help_clicked(self):
        QMessageBox.information(
            self,
            tr("font.help.title"),
            tr("font.help.body"),
        )

    def _on_font_convert_clicked(self):
        source_idx = self.cmb_font_source_type.currentIndex()
        is_file = (source_idx == 1)
        
        crs_code = self.cmb_font_crs.currentData()
        target_crs = QgsCoordinateReferenceSystem(crs_code) if crs_code else QgsCoordinateReferenceSystem()
        
        # Mode: 0=TCVN3→Uni, 1=VNI→Uni, 2=Uni→TCVN3, 3=none
        mode = self.cmb_font_conversion.currentIndex()

        try:
            if is_file:
                in_path = self.txt_font_file_in.text().strip()
                out_path = self.txt_font_file_out.text().strip()
                if not in_path or not os.path.exists(in_path):
                    QMessageBox.warning(self, tr("common.warning"), tr("font.msg.need_source_file"))
                    return
                if not out_path:
                    QMessageBox.warning(self, tr("common.warning"), tr("font.msg.need_output_file"))
                    return

                self._show_log_panel()
                self.progress_font.setVisible(True)
                self.btn_font_convert.setEnabled(False)
                QApplication.processEvents()
                self._export_font_file(in_path, out_path, mode, target_crs)
            else:
                layer = self.cmb_font_layer.currentLayer()
                if not layer:
                    QMessageBox.warning(self, tr("common.warning"), tr("font.msg.need_layer"))
                    return
                
                fmt_idx = self.cmb_font_format.currentIndex()
                if fmt_idx == 1:
                    filt = "MapInfo TAB (*.tab)"
                    driver = "MapInfo File"
                    ext = ".tab"
                else:
                    filt = "Shapefile (*.shp)"
                    driver = "ESRI Shapefile"
                    ext = ".shp"
                    
                path, _ = QFileDialog.getSaveFileName(self, tr("font.dialog.save_result"), "", filt)
                if not path:
                    return
                if not path.lower().endswith(ext):
                    path += ext

                self._show_log_panel()
                self.progress_font.setVisible(True)
                self.btn_font_convert.setEnabled(False)
                QApplication.processEvents()
                self._export_font_layer(layer, path, driver, ext, mode, target_crs)
        except Exception as e:
            self.grp_font_log.setVisible(True)
            self.log_font.append(f"❌ Lỗi ngoại lệ: {e}")
            self.log_font.append(traceback.format_exc())
            QMessageBox.critical(self, tr("common.error"), str(e))
        finally:
            self.btn_font_convert.setEnabled(True)
            self.progress_font.setVisible(False)



    def reset(self):
        """Xóa log, progress, và các trường file."""
        self.cmb_font_source_type.setCurrentIndex(0)
        self.cmb_font_conversion.setCurrentIndex(0)
        self.cmb_font_format.setCurrentIndex(0)
        self.cmb_font_crs.setCurrentIndex(0)
        self.txt_font_file_in.clear()
        self.txt_font_file_out.clear()
        self.log_font.clear()
        self.grp_font_log.setVisible(False)
        self.progress_font.setValue(0)
        self.progress_font.setVisible(False)
