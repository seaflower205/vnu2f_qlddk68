# -*- coding: utf-8 -*-
"""
Tab 1: Dự án & Bản vẽ
"""
import os
from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QComboBox,
    QMessageBox,
    QFileDialog,
    QLabel,
)
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsProject,
    QgsVectorFileWriter,
    QgsVectorLayer,
    QgsRasterLayer,
    QgsCoordinateTransformContext,
    QgsMapLayerProxyModel
)
from qgis.gui import QgsMapLayerComboBox

from ...common.vn2000_data import populate_crs_combo
from modules.common.ui_utils import (
    create_themed_button,
    create_centered_panel,
    create_form_group,
    create_growing_form,
    tune_form_controls,
)
from ...common.i18n import tr


class LayerTab(QWidget):
    def __init__(self, iface, parent=None, on_crs_changed=None):
        super().__init__(parent)
        self.iface = iface
        self.parent_dialog = parent
        self.on_crs_changed = on_crs_changed
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 18, 10, 18)
        layout.setSpacing(16)

        panel, panel_layout = create_centered_panel(self, layout, panel_spacing=18)

        # 2.1 Đặt CRS dự án
        self.grp_set_project, grp_proj_layout = create_form_group(
            tr("layer.group.project_crs"), self, minimum_height=230
        )

        g_proj = create_growing_form(horizontal_spacing=18, vertical_spacing=14)
        self.cmb_project_crs = QComboBox(self.grp_set_project)
        self.cmb_project_crs.setMinimumWidth(280)
        populate_crs_combo(self.cmb_project_crs)
        g_proj.addRow(tr("layer.label.project_crs"), self.cmb_project_crs)
        grp_proj_layout.addLayout(g_proj)

        self.btn_set_project = create_themed_button(
            tr("layer.button.apply_project"), theme="primary", parent=self.grp_set_project
        )
        self.btn_set_project.setObjectName("btn_primary")
        self.btn_set_project.clicked.connect(self._on_set_project_crs)
        grp_proj_layout.addWidget(self.btn_set_project)
        panel_layout.addWidget(self.grp_set_project)

        # 2.2 Reproject & Export Layer
        self.grp_reproject, grp_rep_layout = create_form_group(
            tr("layer.group.reproject"), self, minimum_height=300
        )

        g_rep = create_growing_form(horizontal_spacing=18, vertical_spacing=14)
        self.cmb_vector_layer = QgsMapLayerComboBox(self.grp_reproject)
        self.cmb_vector_layer.setFilters(QgsMapLayerProxyModel.VectorLayer)
        g_rep.addRow(tr("layer.label.layer"), self.cmb_vector_layer)

        self.cmb_target_crs = QComboBox(self.grp_reproject)
        self.cmb_target_crs.setMinimumWidth(280)
        populate_crs_combo(self.cmb_target_crs)
        g_rep.addRow(tr("layer.label.target_crs"), self.cmb_target_crs)
        grp_rep_layout.addLayout(g_rep)

        self.btn_export = create_themed_button(
            tr("layer.button.export_shp"), theme="success", parent=self.grp_reproject
        )
        self.btn_export.setObjectName("btn_success")
        self.btn_export.clicked.connect(self._on_reproject_layer)
        grp_rep_layout.addWidget(self.btn_export)
        panel_layout.addWidget(self.grp_reproject)

        # 2.3 Bản đồ nền địa lý nhanh
        self.grp_basemaps, grp_base_layout = create_form_group(
            tr("layer.group.basemaps"), self, minimum_height=200
        )

        g_base = create_growing_form(horizontal_spacing=18, vertical_spacing=14)
        self.cmb_basemap = QComboBox(self.grp_basemaps)
        self.cmb_basemap.addItem("Google Satellite", "type=xyz&url=https://mt1.google.com/vt/lyrs%3Ds%26x%3D%7Bx%7D%26y%3D%7By%7D%26z%3D%7Bz%7D")
        self.cmb_basemap.addItem("Google Hybrid", "type=xyz&url=https://mt1.google.com/vt/lyrs%3Dy%26x%3D%7Bx%7D%26y%3D%7By%7D%26z%3D%7Bz%7D")
        self.cmb_basemap.addItem("Google Road", "type=xyz&url=https://mt1.google.com/vt/lyrs%3Dm%26x%3D%7Bx%7D%26y%3D%7By%7D%26z%3D%7Bz%7D")
        self.cmb_basemap.addItem("OpenStreetMap", "type=xyz&url=https://tile.openstreetmap.org/%7Bz%7D/%7Bx%7D/%7By%7D.png")
        self.cmb_basemap.addItem("Esri World Imagery", "type=xyz&url=https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/%7Bz%7D/%7By%7D/%7Bx%7D")
        g_base.addRow(tr("layer.label.basemap"), self.cmb_basemap)
        grp_base_layout.addLayout(g_base)

        self.btn_add_basemap = create_themed_button(
            tr("layer.button.add_basemap"), theme="primary", parent=self.grp_basemaps
        )
        self.btn_add_basemap.clicked.connect(self._on_add_basemap)
        grp_base_layout.addWidget(self.btn_add_basemap)
        panel_layout.addWidget(self.grp_basemaps)

        # Nhãn cảnh báo độ chính xác khi chọn hệ tọa độ HN-72
        self.lbl_warning_hn72 = QLabel(self)
        self.lbl_warning_hn72.setWordWrap(True)
        self.lbl_warning_hn72.setStyleSheet("color: #ff9800; font-weight: bold; padding: 8px; border: 1px solid #ff9800; border-radius: 4px; background-color: rgba(255, 152, 0, 0.05); margin-top: 8px;")
        self.lbl_warning_hn72.setText("⚠️ Cảnh báo trắc địa: HN-72 sang VN-2000 là phép chuyển đổi gần đúng toàn quốc (sai số ~5-10m). Đối với bản đồ địa chính tỷ lệ lớn, hãy kiểm nghiệm và hiệu chỉnh lại bằng điểm khống chế tọa độ địa phương.")
        self.lbl_warning_hn72.hide()
        panel_layout.addWidget(self.lbl_warning_hn72)

        self.cmb_project_crs.currentIndexChanged.connect(self._check_hn72_warning)
        self.cmb_target_crs.currentIndexChanged.connect(self._check_hn72_warning)

        layout.addStretch()
        tune_form_controls(self)

        # Restore project CRS and target CRS settings using QSettings
        from qgis.PyQt.QtCore import QSettings
        settings = QSettings()
        last_proj = settings.value("vnu2f_qlddk68/layer_project_crs", "")
        if last_proj:
            idx = self.cmb_project_crs.findData(last_proj)
            if idx >= 0:
                self.cmb_project_crs.setCurrentIndex(idx)
        
        last_target = settings.value("vnu2f_qlddk68/layer_target_crs", "")
        if last_target:
            idx = self.cmb_target_crs.findData(last_target)
            if idx >= 0:
                self.cmb_target_crs.setCurrentIndex(idx)

        # Connect signals to save immediately on change
        self.cmb_project_crs.currentIndexChanged.connect(
            lambda idx: QSettings().setValue("vnu2f_qlddk68/layer_project_crs", self.cmb_project_crs.itemData(idx))
        )
        self.cmb_target_crs.currentIndexChanged.connect(
            lambda idx: QSettings().setValue("vnu2f_qlddk68/layer_target_crs", self.cmb_target_crs.itemData(idx))
        )

    def _check_hn72_warning(self):
        crs_proj = self.cmb_project_crs.currentData() or ""
        crs_target = self.cmb_target_crs.currentData() or ""
        if "900101" in crs_proj or "900102" in crs_proj or "900103" in crs_proj or \
           "900101" in crs_target or "900102" in crs_target or "900103" in crs_target:
            self.lbl_warning_hn72.show()
        else:
            self.lbl_warning_hn72.hide()

    def _on_set_project_crs(self):
        if not self.iface:
            return
        code = self.cmb_project_crs.currentData()
        crs = QgsCoordinateReferenceSystem(code)
        if not crs.isValid():
            QMessageBox.warning(self, tr("common.error"), tr("layer.msg.invalid_crs", code=code))
            return
        QgsProject.instance().setCrs(crs)
        if self.on_crs_changed:
            self.on_crs_changed()
        self.iface.messageBar().pushSuccess(
            "VNU2F", tr("layer.msg.project_applied", authid=crs.authid())
        )

    def _on_reproject_layer(self):
        if not self.iface:
            return
        layer = self.cmb_vector_layer.currentLayer()
        if not layer:
            QMessageBox.warning(self, tr("common.warning"), tr("layer.msg.need_layer"))
            return
        code = self.cmb_target_crs.currentData()
        target_crs = QgsCoordinateReferenceSystem(code)
        if not target_crs.isValid():
            QMessageBox.warning(self, tr("common.error"), tr("layer.msg.invalid_target_crs", code=code))
            return
        from qgis.PyQt.QtCore import QSettings
        settings = QSettings()
        start_dir = settings.value("vnu2f_qlddk68/last_working_dir", "")
        path, _ = QFileDialog.getSaveFileName(
            self, tr("layer.dialog.save_shp"), start_dir, "Shapefile (*.shp)"
        )
        if not path:
            return
        settings.setValue("vnu2f_qlddk68/last_working_dir", os.path.dirname(path))
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "ESRI Shapefile"
        options.fileEncoding = "UTF-8"
        ctx = QgsCoordinateTransformContext()
        ctx.addCoordinateOperation(layer.crs(), target_crs, "")
        error = QgsVectorFileWriter.writeAsVectorFormatV3(layer, path, ctx, options)
        if error[0] == QgsVectorFileWriter.NoError:
            new_layer = QgsVectorLayer(path, os.path.basename(path), "ogr")
            if new_layer.isValid():
                QgsProject.instance().addMapLayer(new_layer)
            QMessageBox.information(
                self, tr("layer.dialog.convert_success"),
                tr("layer.msg.export_success", filename=os.path.basename(path), authid=target_crs.authid())
            )
        else:
            QMessageBox.critical(
                self,
                tr("layer.dialog.export_error"),
                tr("layer.msg.export_error", code=error[0], detail=error[1]),
            )

    def _on_add_basemap(self):
        if not self.iface:
            return
        name = self.cmb_basemap.currentText()
        url = self.cmb_basemap.currentData()
        
        # Tạo lớp raster XYZ
        layer = QgsRasterLayer(url, name, "wms")
        if layer.isValid():
            QgsProject.instance().addMapLayer(layer)
            self.iface.messageBar().pushSuccess(
                "VNU2F", tr("layer.msg.basemap_added", name=name)
            )
        else:
            QMessageBox.critical(
                self, tr("common.error"), f"Không thể tải bản đồ nền: {name}"
            )

    def reset(self):
        """Reset các combobox về vị trí mặc định."""
        self.cmb_project_crs.setCurrentIndex(0)
        self.cmb_target_crs.setCurrentIndex(0)
        self.cmb_basemap.setCurrentIndex(0)
