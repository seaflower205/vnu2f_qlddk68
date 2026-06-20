# -*- coding: utf-8 -*-
"""
Vertical tab for Map Packaging.
Styled according to Zinc UI guidelines and fully compatible with Qt6 / PyQt6.
"""

import os
import shutil
from qgis.PyQt.QtCore import QDir, QCoreApplication
from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGroupBox, QRadioButton, QCheckBox,
    QProgressBar, QMessageBox, QFileDialog
)
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsRasterLayer, QgsProviderRegistry, QgsDataProvider,
    QgsVectorDataProvider, QgsRenderContext, QgsLayoutItemPicture, QgsSymbolLayerUtils
)
from osgeo import gdal

from modules.common.ui_utils import (
    create_themed_button,
    create_file_browser_row,
    create_centered_panel,
    create_form_group as create_layout_form_group,
    create_growing_form,
    tune_form_controls,
)
from .map_package_run_mixin import MapPackageRunMixin
from .gpkg_package_run_mixin import GpkgPackageRunMixin

# Stock SVG paths shipped with QGIS (lazy loaded to prevent blocking import)
_cached_stock_svgs = None

def _get_stock_svgs():
    global _cached_stock_svgs
    if _cached_stock_svgs is None:
        _cached_stock_svgs = list(
            map(lambda x: QDir(x).canonicalPath(), QgsSymbolLayerUtils.listSvgFiles())
        )
    return _cached_stock_svgs

def _symbol_layers_from_symbol(symbol):
    slyrs = []
    for slyr in symbol.symbolLayers():
        sub = slyr.subSymbol()
        if sub:
            slyrs.extend(_symbol_layers_from_symbol(sub))
        slyrs.append(slyr)
    return slyrs

def _get_path(slyr):
    for getter in ('path', 'svgFilePath', 'imageFilePath'):
        try:
            return getattr(slyr, getter)()
        except AttributeError:
            pass
    return None

def _set_path(slyr, new_path):
    for setter in ('setPath', 'setSvgFilePath', 'setImageFilePath'):
        try:
            getattr(slyr, setter)(new_path)
            return
        except AttributeError:
            pass

def _collect_symbol_paths(project, context):
    result = {}
    stock_svgs = _get_stock_svgs()
    for lyr in project.mapLayers().values():
        try:
            syms = lyr.renderer().symbols(context)
        except AttributeError:
            continue
        for sym in syms:
            for slyr in _symbol_layers_from_symbol(sym):
                raw = _get_path(slyr)
                path = QDir(raw).canonicalPath() if raw else ''
                if path and os.path.exists(path) and path not in stock_svgs:
                    result[slyr] = path

    for layout in project.layoutManager().printLayouts():
        model = layout.itemsModel()
        for row in range(model.rowCount()):
            item = model.itemFromIndex(model.index(row, 0))
            if isinstance(item, QgsLayoutItemPicture):
                raw = item.picturePath()
                path = QDir(raw).canonicalPath() if raw else ''
                if path and os.path.exists(path) and path not in stock_svgs:
                    result[item] = path
            else:
                try:
                    sym = item.symbol()
                except AttributeError:
                    continue
                for slyr in _symbol_layers_from_symbol(sym):
                    raw = _get_path(slyr)
                    path = QDir(raw).canonicalPath() if raw else ''
                    if path and os.path.exists(path) and path not in stock_svgs:
                        result[slyr] = path
    return result

def _is_in_dir(parent, child):
    parent = os.path.abspath(parent)
    child = os.path.abspath(child)
    try:
        return os.path.commonpath([parent, child]) == parent
    except ValueError:
        return False

def _get_source_info(layer):
    dp = layer.dataProvider()
    if dp is None:
        return None
    reg = QgsProviderRegistry.instance()
    parts = reg.decodeUri(dp.name(), layer.source())
    path = parts.get('path')
    if path:
        path = QDir(path).canonicalPath()
    if not path:
        return None
    layer_name = parts.get('layerName')
    return path, layer_name, None


class MapPackagerTab(GpkgPackageRunMixin, MapPackageRunMixin, QWidget):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 18, 10, 18)
        layout.setSpacing(16)

        panel, panel_layout = create_centered_panel(self, layout, panel_spacing=18)

        # Form Group
        self.grp_pack, grp_layout = create_layout_form_group(
            "Đóng gói Dự án bản đồ", self, minimum_height=350
        )

        desc = QLabel(
            "Đóng gói project QGIS hiện tại thành thư mục di động.\n"
            "Toàn bộ dữ liệu, style, nhãn, layout được copy — mở trên máy khác hiển thị đúng."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #71717a; margin-bottom: 8px;")
        grp_layout.addWidget(desc)

        # Output folder row
        browse_layout, self.txt_outdir, btn_browse = create_file_browser_row(
            placeholder="Chọn thư mục đích đóng gói...", readonly=True, parent=self
        )
        btn_browse.clicked.connect(self._browse)
        g_form = create_growing_form(horizontal_spacing=18, vertical_spacing=14)
        g_form.addRow("Thư mục đích:", browse_layout)
        grp_layout.addLayout(g_form)

        # Radio option
        opt_group = QGroupBox("Tùy chọn đóng gói", self)
        opt_layout = QVBoxLayout(opt_group)
        self.radio_copy = QRadioButton("Copy dữ liệu gốc (giữ nguyên định dạng)")
        self.radio_copy.setChecked(True)
        self.radio_gpkg = QRadioButton("Đóng gói vào một file GeoPackage (.gpkg)")
        self.chk_vacuum = QCheckBox("Vacuum file SQLite sau khi copy")
        self.chk_vacuum.setChecked(True)

        opt_layout.addWidget(self.radio_copy)
        opt_layout.addWidget(self.radio_gpkg)
        opt_layout.addWidget(self.chk_vacuum)
        grp_layout.addWidget(opt_group)

        # Progress bar
        self.progress = QProgressBar(self)
        self.progress.setVisible(False)
        self.progress.setTextVisible(True)
        grp_layout.addWidget(self.progress)

        # Action button
        self.btn_run = create_themed_button("Đóng gói bản đồ", theme="primary", parent=self)
        self.btn_run.setObjectName("btn_primary")
        self.btn_run.clicked.connect(self._run)
        grp_layout.addWidget(self.btn_run)

        panel_layout.addWidget(self.grp_pack)
        layout.addStretch()
        tune_form_controls(self)

    def _browse(self):
        path = QFileDialog.getExistingDirectory(self, "Chọn thư mục đích", self.txt_outdir.text())
        if path:
            self.txt_outdir.setText(path)



    def _try_vacuum(self, filepath):
        import sqlite3
        from contextlib import closing
        try:
            with open(filepath, 'rb') as f:
                header = f.read(16)
            if header == b'SQLite format 3\x00':
                with closing(sqlite3.connect(filepath)) as conn:
                    conn.execute('VACUUM')
        except Exception:  # noqa: BLE001 — intentional suppress
            pass

    def reset(self):
        self.txt_outdir.clear()
        self.progress.setVisible(False)
