# -*- coding: utf-8 -*-
"""
Vertical tab for KML Tools.
Styled according to Zinc UI guidelines and fully compatible with Qt6 / PyQt6.
"""

import os
from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QComboBox, QCheckBox, QLineEdit, QSpinBox, QPushButton, QMessageBox,
    QTableWidget, QTableWidgetItem, QFileDialog
)
from qgis.core import QgsProject, QgsVectorLayer

from modules.common.ui_utils import (
    create_themed_button,
    create_file_browser_row,
    create_form_group as create_layout_form_group,
    create_growing_form,
    tune_form_controls,
)
from .kml_tools import KmlBuilder, KmlToShpConverter, MergeKmlBuilder
from ...common.qt_compat import HeaderStretch
from ...common.scroll_utils import make_scroll_area
from .kml_tools_build_mixin import KmlToolsBuildMixin


class KmlToolsTab(KmlToolsBuildMixin, QWidget):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.parent_dialog = parent
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Tab Widget
        self.tabs = QTabWidget(self)
        
        self.tab_shp2kml = QWidget()
        self._build_shp2kml()
        self.tabs.addTab(self.tab_shp2kml, "SHP → KML")

        self.tab_kml2shp = QWidget()
        self._build_kml2shp()
        self.tabs.addTab(self.tab_kml2shp, "KML → SHP")

        self.tab_merge = QWidget()
        self._build_merge()
        self.tabs.addTab(self.tab_merge, "Gộp SHP → KML")

        layout.addWidget(self.tabs)
        tune_form_controls(self)

    # --- SHP -> KML Tab ---

    def _get_plugin_state(self):
        if hasattr(self, "parent_dialog") and self.parent_dialog and hasattr(self.parent_dialog, "_plugin_state"):
            return self.parent_dialog._plugin_state
        return None

    def _load_layers_to_combo(self, combo):
        try:
            from vnu2f_qlddk68.modules.common.ui_utils import populate_layers_to_combo
        except ImportError:
            from modules.common.ui_utils import populate_layers_to_combo
        populate_layers_to_combo(combo, polygon_only=False, plugin_state=self._get_plugin_state())
        if combo.count() == 0:
            self._on_layer_changed()

    def _on_layer_changed(self):
        lyrid = self.cbo_kml_layers.currentData()
        layer = QgsProject.instance().mapLayer(lyrid) if lyrid else None
        if not layer:
            return
        fields = [f.name() for f in layer.fields()]
        self.cbo_name1.clear()
        self.cbo_name1.addItems(fields)
        self.cbo_name2.clear()
        self.cbo_name2.addItems(fields)

    def _pick_color(self, btn):
        from qgis.PyQt.QtWidgets import QColorDialog
        from qgis.PyQt.QtGui import QColor
        c = QColorDialog.getColor(QColor(btn.text()))
        if c.isValid():
            btn.setText(c.name())
            btn.setStyleSheet(f"background-color: {c.name()}; color: {'white' if c.lightness() < 128 else 'black'};")

    def _get_shp2kml_config(self):
        # Build description fields mapping
        lyrid = self.cbo_kml_layers.currentData()
        layer = QgsProject.instance().mapLayer(lyrid) if lyrid else None
        df = []
        if layer:
            for i, f in enumerate(layer.fields()):
                df.append({'field': f.name(), 'alias': f.name(), 'suffix': '', 'enabled': True, 'order': i})

        return {
            'name_fields': {
                'field1': self.cbo_name1.currentText() if self.chk_f1.isChecked() else '',
                'field2': self.cbo_name2.currentText() if self.chk_f2.isChecked() else '',
                'field1_enabled': self.chk_f1.isChecked(),
                'field2_enabled': self.chk_f2.isChecked(),
                'separator': self.txt_sep.text(),
                'font_size': self.spn_name_size.value(),
                'font_color': self.btn_name_color.text(),
            },
            'polygon_style': {
                'border_color': self.btn_border.text(),
                'border_width': self.spn_border_w.value(),
                'fill_color': self.btn_fill.text(),
                'fill_opacity': self.spn_opacity.value(),
            },
            'description_fields': df,
            'header': {
                'title': 'Thông tin thuộc tính',
                'bg_color': '#18181b',
                'text_color': '#FFFFFF',
                'bold': True,
                'font_size': 14
            }
        }

    def _export_shp2kml(self):
        lyrid = self.cbo_kml_layers.currentData()
        layer = QgsProject.instance().mapLayer(lyrid) if lyrid else None
        if not layer:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn lớp dữ liệu vector cần xuất.")
            return
        
        path, _ = QFileDialog.getSaveFileName(self, "Save KML/KMZ", "", "KML (*.kml);;KMZ (*.kmz)")
        if not path:
            return

        cfg = self._get_shp2kml_config()
        builder = KmlBuilder(cfg)
        success, msg = builder.build(layer, path, 'kmz' if path.lower().endswith('.kmz') else 'kml')
        if success:
            self.iface.messageBar().pushSuccess("VNU2F", "Xuất file KML/KMZ thành công!")
        else:
            QMessageBox.critical(self, "Lỗi", f"Xuất KML thất bại:\n{msg}")

    # --- KML -> SHP Tab ---

    def _browse_kml(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn tệp KML/KMZ", "", "KML (*.kml);;KMZ (*.kmz)")
        if path:
            self.txt_kml_in.setText(path)

    def _scan_kml_fields(self):
        kpath = self.txt_kml_in.text()
        if not kpath or not os.path.exists(kpath):
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn tệp KML/KMZ hợp lệ trước khi quét.")
            return
        
        conv = KmlToShpConverter()
        meta = conv.discover_fields(kpath)
        if not meta:
            QMessageBox.warning(self, "Lỗi", "Không thể phân tích dữ liệu thuộc tính từ tệp KML này.")
            return

        self.tbl_kml_fields.setRowCount(0)
        for i, (fname, sample) in enumerate(meta['fields'].items()):
            self.tbl_kml_fields.insertRow(i)
            chk = QCheckBox()
            chk.setChecked(True)
            self.tbl_kml_fields.setCellWidget(i, 0, chk)
            self.tbl_kml_fields.setItem(i, 1, QTableWidgetItem(fname))
            self.tbl_kml_fields.setItem(i, 2, QTableWidgetItem(str(sample)))

        QMessageBox.information(
            self, "Thông tin quét",
            f"Quét hoàn tất!\nTìm thấy: {meta['total_features']} đối tượng, "
            f"Hình học: {', '.join(meta['geom_types'])}, Thư mục con: {meta['sub_layer_count']}."
        )

    def _kml_all(self):
        for i in range(self.tbl_kml_fields.rowCount()):
            chk = self.tbl_kml_fields.cellWidget(i, 0)
            if chk:
                chk.setChecked(True)

    def _kml_none(self):
        for i in range(self.tbl_kml_fields.rowCount()):
            chk = self.tbl_kml_fields.cellWidget(i, 0)
            if chk:
                chk.setChecked(False)

    def _convert_kml(self):
        kpath = self.txt_kml_in.text()
        if not kpath or not os.path.exists(kpath):
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn tệp KML/KMZ đầu vào.")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Lưu Shapefile kết quả", "", "Shapefile (*.shp)")
        if not path:
            return

        selected = []
        for i in range(self.tbl_kml_fields.rowCount()):
            chk = self.tbl_kml_fields.cellWidget(i, 0)
            if chk and chk.isChecked():
                selected.append(self.tbl_kml_fields.item(i, 1).text())

        conv = KmlToShpConverter()
        success, msg = conv.convert(kpath, path, self.txt_kml_crs.text(), selected if selected else None)
        if success:
            new_layer = QgsVectorLayer(path, os.path.basename(path), "ogr")
            if new_layer.isValid():
                QgsProject.instance().addMapLayer(new_layer)
            self.iface.messageBar().pushSuccess("VNU2F", f"Chuyển đổi hoàn thành: {msg}")
        else:
            QMessageBox.critical(self, "Lỗi", f"Chuyển đổi thất bại:\n{msg}")

    # --- Merge Tab ---
    def _build_merge(self):
        layout = QVBoxLayout(self.tab_merge)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        self.tbl_merge = QTableWidget(0, 2, self.tab_merge)
        self.tbl_merge.setHorizontalHeaderLabels(["Tệp nguồn (Shapefile)", "Đường dẫn"])
        self.tbl_merge.horizontalHeader().setSectionResizeMode(HeaderStretch)
        self.tbl_merge.setStyleSheet(
            "QTableWidget { border: 1px solid #27272a; gridline-color: transparent; }"
            "QTableWidget::item { border-bottom: 1px solid #27272a; height: 32px; }"
        )
        layout.addWidget(self.tbl_merge)

        btn_row = QHBoxLayout()
        self.btn_add_merge = create_themed_button("Thêm tệp", theme="primary", parent=self.tab_merge)
        self.btn_add_merge.setObjectName("btn_primary")
        self.btn_add_merge.clicked.connect(self._add_merge_file)
        btn_row.addWidget(self.btn_add_merge)

        self.btn_remove_merge = create_themed_button("Xóa tệp", theme="danger", parent=self.tab_merge)
        self.btn_remove_merge.setObjectName("btn_danger")
        self.btn_remove_merge.clicked.connect(self._remove_merge_file)
        btn_row.addWidget(self.btn_remove_merge)
        layout.addLayout(btn_row)

        self.btn_run_merge = create_themed_button("Gộp & Xuất KML/KMZ", theme="success", parent=self.tab_merge)
        self.btn_run_merge.setObjectName("btn_success")
        self.btn_run_merge.clicked.connect(self._run_merge)
        layout.addWidget(self.btn_run_merge)
        layout.addStretch()

    def _add_merge_file(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Chọn các tệp Shapefile", "", "Shapefile (*.shp)")
        for path in paths:
            row = self.tbl_merge.rowCount()
            self.tbl_merge.insertRow(row)
            self.tbl_merge.setItem(row, 0, QTableWidgetItem(os.path.basename(path)))
            self.tbl_merge.setItem(row, 1, QTableWidgetItem(path))

    def _remove_merge_file(self):
        self.tbl_merge.removeRow(self.tbl_merge.currentRow())

    def _run_merge(self):
        if self.tbl_merge.rowCount() == 0:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng thêm ít nhất một tệp Shapefile để gộp.")
            return

        out_path, _ = QFileDialog.getSaveFileName(self, "Lưu tệp gộp KML/KMZ", "", "KML (*.kml);;KMZ (*.kmz)")
        if not out_path:
            return

        layer_configs = []
        for i in range(self.tbl_merge.rowCount()):
            spath = self.tbl_merge.item(i, 1).text()
            layer_configs.append((spath, self._get_shp2kml_config()))

        builder = MergeKmlBuilder()
        success, msg = builder.build(layer_configs, out_path, 'kmz' if out_path.lower().endswith('.kmz') else 'kml')
        if success:
            self.iface.messageBar().pushSuccess("VNU2F", "Gộp và xuất KML/KMZ thành công!")
        else:
            QMessageBox.critical(self, "Lỗi", f"Gộp KML thất bại:\n{msg}")

    def reset(self):
        self.cbo_kml_layers.setCurrentIndex(0)
        self.txt_kml_in.clear()
        self.tbl_kml_fields.setRowCount(0)
        self.tbl_merge.setRowCount(0)
