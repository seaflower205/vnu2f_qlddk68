"""User-facing plugin actions kept separate from plugin lifecycle wiring."""

from __future__ import annotations

import os
import traceback

from qgis.PyQt.QtWidgets import QInputDialog
from qgis.core import QgsMapLayerType, QgsMessageLog, QgsProject, QgsWkbTypes, Qgis

try:
    from PyQt6.sip import isdeleted
except ImportError:
    try:
        from PyQt5.sip import isdeleted
    except ImportError:
        import sip

        isdeleted = sip.isdeleted

try:
    from .cadastral_importer.dialog import CadastralImportDialog
    from .webgis_launcher import WebGISLauncher
except ImportError:
    from modules.cadastral_importer.dialog import CadastralImportDialog
    from modules.webgis_launcher import WebGISLauncher


class PluginActionsMixin:
    """Open plugin tools and resolve the WebGIS source layer."""

    def _open_crs_converter(self) -> None:
        try:
            try:
                from .crs_converter.crs_dialog import CRSConverterDialog
            except ImportError:
                from modules.crs_converter.crs_dialog import CRSConverterDialog

            if not self._crs_dialog or isdeleted(self._crs_dialog):
                self._crs_dialog = CRSConverterDialog(parent=self.iface.mainWindow())
            self._crs_dialog.show()
            self._crs_dialog.raise_()
            self._crs_dialog.activateWindow()
        except Exception as error:  # noqa: BLE001
            self._crs_dialog = None
            QgsMessageLog.logMessage(
                f"Lỗi khi hiển thị hộp thoại CRS Converter: {error}\n{traceback.format_exc()}",
                self.PLUGIN_NAME,
                Qgis.Critical,
            )
            self.iface.messageBar().pushMessage(
                self.PLUGIN_NAME,
                f"Không thể mở hộp thoại chuyển đổi hệ tọa độ: {error}",
                level=Qgis.Critical,
                duration=8,
            )

    def _open_cadastral_importer(self) -> None:
        try:
            if not self._cadastral_import_dialog or isdeleted(self._cadastral_import_dialog):
                self._cadastral_import_dialog = CadastralImportDialog(parent=self.iface.mainWindow())
            self._cadastral_import_dialog.show()
            self._cadastral_import_dialog.raise_()
            self._cadastral_import_dialog.activateWindow()
        except Exception as error:  # noqa: BLE001
            self._log_action_error(
                f"Lỗi khi hiển thị hộp thoại nhập dữ liệu địa chính: {error}",
                "Không thể mở hộp thoại nhập dữ liệu địa chính. Kiểm tra Log QGIS để biết chi tiết.",
            )

    def _open_webgis(self) -> None:
        try:
            launcher = self._get_webgis_launcher()
            layer = self._choose_webgis_layer()
            if layer:
                launcher.open(layer)
        except Exception as error:  # noqa: BLE001
            self._log_action_error(
                f"Lỗi khi mở WebGIS quản lý thửa đất: {error}",
                "Không thể mở WebGIS quản lý thửa đất. Kiểm tra Log QGIS để biết chi tiết.",
            )

    def _share_webgis(self) -> None:
        try:
            self._get_webgis_launcher().show_share_dialog()
        except Exception as error:  # noqa: BLE001
            self._log_action_error(
                f"Lỗi khi mở giao diện chia sẻ WebGIS: {error}",
                "Không thể mở giao diện chia sẻ WebGIS. Kiểm tra Log QGIS để biết chi tiết.",
            )

    def _get_webgis_launcher(self):
        if not self._webgis_launcher:
            self._webgis_launcher = WebGISLauncher(self.plugin_dir, self.iface, self.PLUGIN_NAME)
        return self._webgis_launcher

    def _log_action_error(self, log_message: str, user_message: str) -> None:
        QgsMessageLog.logMessage(log_message, self.PLUGIN_NAME, Qgis.Critical)
        self.iface.messageBar().pushMessage(
            self.PLUGIN_NAME,
            user_message,
            level=Qgis.Critical,
            duration=5,
        )

    def _choose_webgis_layer(self):
        polygon_layers = [
            layer
            for layer in QgsProject.instance().mapLayers().values()
            if self._is_polygon_vector_layer(layer)
        ]
        if not polygon_layers:
            self.iface.messageBar().pushMessage(
                self.PLUGIN_NAME,
                "Không có layer polygon trong project. Hãy nạp/chọn lớp ranh thửa trước khi mở WebGIS.",
                level=Qgis.Warning,
                duration=8,
            )
            return None

        current_layer = self._selected_webgis_layer()
        current_index = 0
        items: list[str] = []
        item_to_layer = {}
        for index, layer in enumerate(polygon_layers):
            crs = layer.crs()
            crs_label = crs.authid() if crs and crs.isValid() else "CRS không xác định"
            source_name = os.path.basename(str(layer.source()).split("|")[0])
            label = f"{layer.name()} | {layer.featureCount()} đối tượng | {crs_label} | {source_name}"
            items.append(label)
            item_to_layer[label] = layer
            if current_layer and layer.id() == current_layer.id():
                current_index = index

        selected_label, accepted = QInputDialog.getItem(
            self.iface.mainWindow(),
            "Chọn layer WebGIS",
            "Chọn layer polygon/ranh thửa để xuất sang WebGIS:",
            items,
            current_index,
            False,
        )
        return item_to_layer.get(selected_label) if accepted else None

    def _selected_webgis_layer(self):
        candidates = self._layer_tree_candidate_layers()
        for layer in candidates:
            if self._is_polygon_vector_layer(layer):
                return layer
        if candidates:
            return candidates[0]
        active_layer = self.iface.activeLayer()
        return active_layer

    def _layer_tree_candidate_layers(self) -> list:
        try:
            layer_tree = self.iface.layerTreeView()
            if not layer_tree:
                return []
            layers = []
            current_layer = layer_tree.currentLayer()
            if current_layer:
                layers.append(current_layer)
            for layer in layer_tree.selectedLayers():
                if layer and layer not in layers:
                    layers.append(layer)
            return layers
        except Exception:  # noqa: BLE001
            return []

    @staticmethod
    def _is_polygon_vector_layer(layer) -> bool:
        if not layer:
            return False
        try:
            return (
                layer.type() == QgsMapLayerType.VectorLayer
                and QgsWkbTypes.geometryType(layer.wkbType()) == QgsWkbTypes.PolygonGeometry
            )
        except Exception:  # noqa: BLE001
            return False
