"""Mechanically extracted responsibilities from map_packager_tab.py."""

import os
import shutil
from .map_package_helpers import _collect_symbol_paths, _get_source_info, _is_in_dir, _set_path
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


class MapPackageRunMixin:
    def _run(self):
        project = QgsProject.instance()
        if not project.fileName():
            QMessageBox.warning(self, "Cảnh báo", "Dự án hiện tại chưa được lưu. Vui lòng lưu dự án trước khi đóng gói.")
            return
        if project.isDirty():
            QMessageBox.warning(self, "Cảnh báo", "Dự án hiện có thay đổi chưa lưu. Vui lòng nhấn Ctrl+S để lưu trước.")
            return
        if not self.txt_outdir.text():
            self._browse()
        if not self.txt_outdir.text():
            return

        outdir = os.path.join(self.txt_outdir.text(), project.baseName())
        home = project.homePath()
        if home and _is_in_dir(home, outdir):
            QMessageBox.warning(self, "Lỗi", "Thư mục đích không được nằm trong thư mục gốc của dự án!")
            return

        if os.path.exists(outdir):
            res = QMessageBox.question(
                self, "Xác nhận",
                f"Thư mục '{outdir}' đã tồn tại.\nDữ liệu cũ sẽ bị xóa sạch để đóng gói mới. Tiếp tục?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if res != QMessageBox.StandardButton.Yes:
                return
            try:
                shutil.rmtree(outdir)
            except Exception as e:  # noqa: BLE001 — intentional suppress
                QMessageBox.critical(self, "Lỗi", f"Không thể xóa thư mục cũ: {e}")
                return

        if self.radio_gpkg.isChecked():
            self._run_gpkg_package(project, outdir)
            return

        # Regular packaging
        src_map = {}
        for lyr in project.mapLayers().values():
            info = _get_source_info(lyr)
            if info:
                src_map[lyr] = info

        if not src_map:
            QMessageBox.information(self, "Thông tin", "Không tìm thấy lớp bản đồ dạng tệp nào trong dự án.")
            return

        context = QgsRenderContext.fromMapSettings(self.iface.mapCanvas().mapSettings())
        sym_map = _collect_symbol_paths(project, context)

        all_paths = [path for path, _, _ in src_map.values()]
        all_paths.extend(sym_map.values())
        paths_set = list(set(all_paths))

        dirs_set = list(set(os.path.dirname(p) for p in paths_set))
        names = [project.baseName() + '.qgz']
        for d in dirs_set:
            name = os.path.basename(d)
            if name in names:
                suffix = 1
                while f"{name}_{suffix}" in names:
                    suffix += 1
                name = f"{name}_{suffix}"
            names.append(name)
        del names[0]
        dir_map = dict(zip(dirs_set, names))
        path_map = {p: dir_map[os.path.dirname(p)] for p in paths_set}

        self.progress.setVisible(True)
        self.progress.setRange(0, len(path_map) + 1)
        self.progress.setValue(0)
        self.progress.setFormat("Đang đóng gói... %p%")
        QCoreApplication.processEvents()

        orig_project = project.fileName()
        try:
            for i, path in enumerate(path_map):
                dstdir = os.path.join(outdir, path_map[path])
                os.makedirs(dstdir, exist_ok=True)
                if os.path.isdir(path):
                    file_list = [path]
                else:
                    try:
                        ds = gdal.OpenEx(path)
                        file_list = ds.GetFileList() if ds else [path]
                    except Exception:  # noqa: BLE001 — intentional suppress
                        file_list = [path]
                    finally:
                        ds = None

                for fpath in file_list:
                    QCoreApplication.processEvents()
                    try:
                        if os.path.isdir(fpath):
                            shutil.copytree(fpath, os.path.join(dstdir, os.path.basename(fpath)))
                        else:
                            shutil.copy2(fpath, dstdir)
                    except FileNotFoundError:
                        pass
                    except Exception:  # noqa: BLE001 — intentional suppress
                        try:
                            shutil.copytree(fpath, os.path.join(dstdir, os.path.basename(fpath)))
                        except Exception:
                            pass

                    if self.chk_vacuum.isChecked():
                        self._try_vacuum(os.path.join(dstdir, os.path.basename(fpath)))

                self.progress.setValue(i + 1)

            reg = QgsProviderRegistry.instance()
            for lyr, src in src_map.items():
                path, _, _ = src
                dp = lyr.dataProvider()
                encoding = dp.encoding() if isinstance(dp, QgsVectorDataProvider) else None
                parts = reg.decodeUri(dp.name(), lyr.source())
                parts['path'] = QDir(os.path.join(outdir, path_map[path], os.path.basename(path))).absolutePath()
                new_source = reg.encodeUri(dp.name(), parts)
                lyr.setDataSource(new_source, lyr.name(), lyr.providerType(), QgsDataProvider.ProviderOptions())
                if encoding is not None:
                    lyr.dataProvider().setEncoding(encoding)

            for slyr, path in sym_map.items():
                new_path = QDir(os.path.join(outdir, path_map[path], os.path.basename(path))).absolutePath()
                if isinstance(slyr, QgsLayoutItemPicture):
                    fmt = QgsLayoutItemPicture.FormatSVG if new_path.endswith(('.svg', '.svgz')) else QgsLayoutItemPicture.FormatRaster
                    slyr.setPicturePath(new_path, fmt)
                else:
                    _set_path(slyr, new_path)

            self.progress.setValue(self.progress.maximum())
            QCoreApplication.processEvents()

            project.setPresetHomePath('')
            project.writeEntryBool('Paths', '/Absolute', False)
            qgz_path = QDir(os.path.join(outdir, project.baseName())).absolutePath() + '.qgz'
            result = project.write(qgz_path)
        except Exception as e:  # noqa: BLE001 — intentional suppress
            QMessageBox.critical(self, "Lỗi", f"Lỗi đóng gói: {e}")
            return
        finally:
            self.progress.setVisible(False)
            project.read(orig_project)

        if result:
            self.iface.messageBar().pushSuccess("VNU2F", f"Đóng gói bản đồ thành công tại: {outdir}")
        else:
            QMessageBox.warning(self, "Lỗi", "Lưu dự án đóng gói thất bại!")
