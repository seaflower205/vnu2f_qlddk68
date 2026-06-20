"""Mechanically extracted responsibilities from plot_execution_mixin.py."""

import os
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QTableWidget,
    QTableWidgetItem,
    QGridLayout,
    QMessageBox,
    QFileDialog,
    QPushButton
)
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsProject,
    QgsVectorLayer,
    QgsCoordinateTransform,
    QgsFeature,
    QgsField,
    QgsPointXY,
    QgsGeometry,
    QgsMapLayerProxyModel
)
from qgis.gui import QgsMapLayerComboBox
from ...common.vn2000_data import populate_crs_combo
from modules.common.ui_utils import create_themed_button, create_file_browser_row
from ...common.qt_compat import (
    MessageBoxNo,
    MessageBoxYes,
    NoEditTriggers,
    SizePolicyExpanding,
    SizePolicyFixed,
)
from ...common.scroll_utils import make_scroll_area
from ..plot_utils import parse_coordinate_file, list_excel_sheets, suggest_column_mappings
from .plot_tab_ui_mixin import PlotTabUiMixin


class PlotLabelingMixin:
    def _enable_layer_labeling(self, layer, show_name, show_z, color_hex, size=9):
        if not (show_name or show_z):
            return

        from qgis.core import (
            QgsPalLayerSettings, QgsVectorLayerSimpleLabeling, QgsTextFormat, QgsTextBufferSettings
        )
        from qgis.PyQt.QtGui import QColor

        if show_name and show_z:
            expr = '"name" || \'\\n\' || "z"'
        elif show_name:
            expr = '"name"'
        else:
            expr = '"z"'

        settings = QgsPalLayerSettings()
        settings.isExpression = True
        settings.fieldName = expr

        text_format = QgsTextFormat()
        text_format.setSize(size)
        text_format.setColor(QColor(color_hex))

        buffer = QgsTextBufferSettings()
        buffer.setEnabled(True)
        buffer.setSize(1.5)
        buffer.setColor(QColor("#ffffff"))
        text_format.setBuffer(buffer)

        settings.setFormat(text_format)

        settings.placement = QgsPalLayerSettings.Placement.OverPoint
        settings.quadrant = QgsPalLayerSettings.QuadrantPosition.QuadrantAboveRight
        settings.distance = 3.0

        layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
        layer.setLabelsEnabled(True)
