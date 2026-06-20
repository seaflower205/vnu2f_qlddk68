"""Mechanically extracted responsibilities from mbtiles_tab.py."""

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor, QFont, QBrush, QPen, QPainter, QPixmap
from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QSpinBox, QGroupBox, QProgressBar, QMessageBox,
    QFileDialog, QColorDialog, QDialog, QApplication, QCheckBox
)
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsFillSymbol, QgsSingleSymbolRenderer,
    QgsPalLayerSettings, QgsVectorLayerSimpleLabeling, QgsTextFormat, QgsTextBufferSettings
)
from modules.common.ui_utils import (
    create_themed_button,
    create_form_group as create_layout_form_group,
    create_growing_form,
    tune_form_controls,
)
from ...common.scroll_utils import make_scroll_area
from .mbtiles_ui_mixin import MbtilesUiMixin
from .mbtiles_preview_mixin import MbtilesPreviewMixin


class MbtilesExportMixin:
    def _export_mbtiles(self):
        lyrid = self.cbo_layer.currentData()
        layer = QgsProject.instance().mapLayer(lyrid) if lyrid else None
        if not layer:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn lớp bản đồ.")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Xuất MBTiles", "", "MBTiles (*.mbtiles)")
        if not path:
            return

        import processing
        extent = getattr(self, '_current_extent', layer.extent())
        ext_str = f"{extent.xMinimum()},{extent.xMaximum()},{extent.yMinimum()},{extent.yMaximum()} [{layer.crs().authid()}]"

        self.progress.setVisible(True)
        self.progress.setValue(20)
        self.progress.setFormat("Đang xuất MBTiles... %p%")
        QApplication.processEvents()

        try:
            alg_name = None
            for name in ['native:tilesxyzmbtiles', 'qgis:tilesxyzmbtiles']:
                try:
                    processing.algorithmHelp(name)
                    alg_name = name
                    break
                except Exception:  # noqa: BLE001 — intentional suppress
                    continue

            if not alg_name:
                raise RuntimeError("Không tìm thấy thuật toán xuất MBTiles trên phiên bản QGIS này.")

            hidden_layers = []
            if not self.chk_basemap.isChecked():
                root = QgsProject.instance().layerTreeRoot()
                for node in root.findLayers():
                    lyr = node.layer()
                    if lyr and node.isVisible() and lyr.id() != layer.id() and not isinstance(lyr, QgsVectorLayer):
                        node.setItemVisibilityChecked(False)
                        hidden_layers.append(node)
                self.iface.mapCanvas().refresh()
                QApplication.processEvents()

            self.progress.setValue(40)
            QApplication.processEvents()

            try:
                processing.run(alg_name, {
                    'EXTENT': ext_str,
                    'ZOOM_MIN': self.spn_minz.value(),
                    'ZOOM_MAX': self.spn_maxz.value(),
                    'DPI': 96,
                    'BACKGROUND_COLOR': QColor(255, 255, 255, 0),
                    'TILE_FORMAT': 0,
                    'QUALITY': 75,
                    'METATILESIZE': 4,
                    'OUTPUT_FILE': path,
                    'OUTPUT_HTML': '',
                })
            finally:
                for node in hidden_layers:
                    node.setItemVisibilityChecked(True)
                if hidden_layers:
                    self.iface.mapCanvas().refresh()

            self.progress.setValue(100)
            QApplication.processEvents()
            QMessageBox.information(self, "Thành công", f"Đã xuất tệp MBTiles thành công tại:\n{path}")
        except Exception as e:  # noqa: BLE001 — intentional suppress
            QMessageBox.critical(self, "Lỗi", f"Xuất MBTiles thất bại:\n{e}")
        finally:
            self.progress.setVisible(False)
