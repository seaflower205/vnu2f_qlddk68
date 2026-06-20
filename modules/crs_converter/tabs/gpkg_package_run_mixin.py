"""Mechanically extracted responsibilities from map_packager_tab.py."""

import os
from .map_package_helpers import _get_source_info
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


class GpkgPackageRunMixin:
    def _run_gpkg_package(self, project, outdir):
        import processing
        os.makedirs(outdir, exist_ok=True)
        gpkg_path = os.path.join(outdir, f"{project.baseName()}.gpkg")
        qgz_path = os.path.join(outdir, f"{project.baseName()}.qgz")
        raster_dir = os.path.join(outdir, "raster")
        orig_project = project.fileName()

        all_layers = list(project.mapLayers().values())
        vectors = []
        rasters = []
        online = []
        _ONLINE_PROVIDERS = {'wms', 'wfs', 'arcgismapserver', 'arcgisfeatureserver', 'vectortile', 'xyztiles', 'wcs'}

        for lyr in all_layers:
            if not lyr.isValid():
                continue
            prov = lyr.providerType().lower() if lyr.providerType() else ''
            if prov in _ONLINE_PROVIDERS:
                online.append(lyr)
            elif isinstance(lyr, QgsVectorLayer):
                vectors.append(lyr)
            elif isinstance(lyr, QgsRasterLayer):
                info = _get_source_info(lyr)
                if info and os.path.isfile(info[0]):
                    rasters.append(lyr)
                else:
                    online.append(lyr)

        if not vectors and not rasters:
            QMessageBox.warning(self, "Cảnh báo", "Không có lớp dữ liệu tệp nào để đóng gói GeoPackage.")
            return

        self.progress.setVisible(True)
        self.progress.setRange(0, len(rasters) + 3)
        self.progress.setValue(0)
        self.progress.setFormat("Đang đóng gói GPKG... %p%")
        QCoreApplication.processEvents()

        try:
            step = 0
            if vectors:
                params = {
                    'LAYERS': vectors,
                    'OUTPUT': gpkg_path,
                    'OVERWRITE': True,
                    'SAVE_STYLES': True,
                    'SAVE_METADATA': True,
                    'SELECTED_FEATURES_ONLY': False,
                }
                processing.run("native:package", params)
            step += 1
            self.progress.setValue(step)
            QCoreApplication.processEvents()

            if rasters:
                os.makedirs(raster_dir, exist_ok=True)
            raster_path_map = {}
            for rlyr in rasters:
                info = _get_source_info(rlyr)
                if not info:
                    continue
                src_path = info[0]
                try:
                    ds = gdal.OpenEx(src_path)
                    file_list = ds.GetFileList() if ds else [src_path]
                except Exception:  # noqa: BLE001 — intentional suppress
                    file_list = [src_path]
                finally:
                    ds = None

                for fpath in (file_list or [src_path]):
                    if os.path.isfile(fpath):
                        dst = os.path.join(raster_dir, os.path.basename(fpath))
                        try:
                            shutil.copy2(fpath, dst)
                        except Exception:  # noqa: BLE001 — intentional suppress
                            pass
                raster_path_map[rlyr.id()] = os.path.join("raster", os.path.basename(src_path))
                step += 1
                self.progress.setValue(step)
                QCoreApplication.processEvents()

            reg = QgsProviderRegistry.instance()
            for vlyr in vectors:
                dp = vlyr.dataProvider()
                if not dp:
                    continue
                parts = reg.decodeUri(dp.name(), vlyr.source())
                parts['path'] = QDir(gpkg_path).absolutePath()
                new_source = reg.encodeUri(dp.name(), parts)
                encoding = dp.encoding() if isinstance(dp, QgsVectorDataProvider) else None
                vlyr.setDataSource(new_source, vlyr.name(), vlyr.providerType(), QgsDataProvider.ProviderOptions())
                if encoding:
                    vlyr.dataProvider().setEncoding(encoding)

            for rlyr in rasters:
                rel_path = raster_path_map.get(rlyr.id())
                if not rel_path:
                    continue
                abs_path = QDir(os.path.join(outdir, rel_path)).absolutePath()
                rlyr.setDataSource(abs_path, rlyr.name(), rlyr.providerType(), QgsDataProvider.ProviderOptions())

            project.setPresetHomePath('')
            project.writeEntryBool('Paths', '/Absolute', False)
            project.write(qgz_path)

            step += 1
            self.progress.setValue(self.progress.maximum())
            QCoreApplication.processEvents()
            result = True
        except Exception as e:  # noqa: BLE001 — intentional suppress
            QMessageBox.critical(self, "Lỗi", f"Lỗi đóng gói GPKG: {e}")
            result = False
        finally:
            self.progress.setVisible(False)
            project.read(orig_project)

        if result:
            self.iface.messageBar().pushSuccess("VNU2F", f"Đóng gói GPKG thành công tại: {outdir}")
