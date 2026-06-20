# -*- coding: utf-8 -*-
"""
Vertical tab for MBTiles Creator.
Styled according to Zinc UI guidelines and fully compatible with Qt6 / PyQt6.
"""

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
from .mbtiles_export_mixin import MbtilesExportMixin
ALIGN_CENTER = Qt.AlignmentFlag.AlignCenter

STANDARD_SCALES = [
    500, 1000, 2000, 2500, 5000, 10000, 15000,
    20000, 25000, 50000, 100000, 250000, 500000, 1000000,
]


class MBTilesTab(MbtilesExportMixin, MbtilesPreviewMixin, MbtilesUiMixin, QWidget):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self._stroke_color = QColor("#55ff00")
        self._fill_color = QColor("#ffff00")
        self._font_color = QColor("#00ffff")
        self._buf_color = QColor("#ffffff")
        self._bg_color = QColor("#ffaa00")
        self._num_checks = {}
        self._den_checks = {}
        self._num_order = []
        self._den_order = []
        self._setup_ui()
        self._refresh_layers()


    def _pick_theme_color(self, target, btn):
        cur = getattr(self, f"_{target}_color")
        c = QColorDialog.getColor(cur, self)
        if c.isValid():
            setattr(self, f"_{target}_color", c)
            btn.setText(c.name())
            btn.setStyleSheet(f"background-color: {c.name()}; color: {'white' if c.lightness() < 128 else 'black'};")
            self._update_preview()

    def _refresh_layers(self):
        try:
            from vnu2f_qlddk68.modules.common.ui_utils import populate_layers_to_combo
        except ImportError:
            from modules.common.ui_utils import populate_layers_to_combo
        populate_layers_to_combo(self.cbo_layer, polygon_only=False)
        if self.cbo_layer.count() == 0:
            self._on_layer_changed()

    def _on_layer_changed(self):
        lyrid = self.cbo_layer.currentData()
        layer = QgsProject.instance().mapLayer(lyrid) if lyrid else None
        if not layer:
            return
        fields = [f.name() for f in layer.fields()]
        
        # Populate Numerator list
        while self.ly_num.count():
            w = self.ly_num.takeAt(0).widget()
            if w:
                w.deleteLater()
        self._num_checks.clear()
        self._num_order.clear()
        for f in fields:
            chk = QCheckBox(f)
            chk.stateChanged.connect(lambda state, name=f: self._on_field_toggled(state, name, self._num_order))
            self.ly_num.addWidget(chk)
            self._num_checks[f] = chk

        # Populate Denominator list
        while self.ly_den.count():
            w = self.ly_den.takeAt(0).widget()
            if w:
                w.deleteLater()
        self._den_checks.clear()
        self._den_order.clear()
        for f in fields:
            chk = QCheckBox(f)
            chk.stateChanged.connect(lambda state, name=f: self._on_field_toggled(state, name, self._den_order))
            self.ly_den.addWidget(chk)
            self._den_checks[f] = chk

        self._update_preview()

    def _on_field_toggled(self, state, field_name, order_list):
        if state == 2:  # Checked
            if field_name not in order_list:
                order_list.append(field_name)
        else:
            if field_name in order_list:
                order_list.remove(field_name)
        self._update_preview()

    def _build_expression(self):
        num_f = [f for f in self._num_order if self._num_checks[f].isChecked()]
        den_f = [f for f in self._den_order if self._den_checks[f].isChecked()]
        if not num_f and not den_f:
            return ""

        num_parts = [f"coalesce(\"{f}\", '')" for f in num_f]
        num_expr = " || '-' || ".join(num_parts) if num_parts else "''"
        
        if not den_f:
            return num_expr

        den_parts = [f"coalesce(round(\"{f}\", 1), '')" for f in den_f]
        den_expr = " || '-' || ".join(den_parts) if den_parts else "''"

        # QGIS Fraction Style label with underline
        expr = f"({num_expr}) || '\\n' || '________' || '\\n\\n' || ({den_expr})"
        return expr


    def _draw_extent(self):
        from qgis.gui import QgsMapToolExtent
        self._extent_tool = QgsMapToolExtent(self.iface.mapCanvas())
        self._extent_tool.extentChanged.connect(self._on_extent_drawn)
        self.iface.mapCanvas().setMapTool(self._extent_tool)
        if self.parent_dialog():
            self.parent_dialog().hide()

    def _on_extent_drawn(self, extent):
        self._current_extent = extent
        self.lbl_extent_status.setText(
            f"Đã vẽ: {extent.xMinimum():.1f}, {extent.yMinimum():.1f} → {extent.xMaximum():.1f}, {extent.yMaximum():.1f}"
        )
        self.iface.mapCanvas().unsetMapTool(self._extent_tool)
        if self.parent_dialog():
            self.parent_dialog().show()
            self.parent_dialog().raise_()

    def parent_dialog(self):
        curr = self.parent()
        while curr:
            if isinstance(curr, QDialog):
                return curr
            curr = curr.parent()
        return None

    def _apply_to_layer(self):
        lyrid = self.cbo_layer.currentData()
        layer = QgsProject.instance().mapLayer(lyrid) if lyrid else None
        if not layer:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn lớp bản đồ.")
            return

        self.progress.setVisible(True)
        self.progress.setValue(20)
        QApplication.processEvents()

        # Simple single renderer styling
        sym = QgsFillSymbol.createSimple({})
        sl = sym.symbolLayer(0)
        sl.setStrokeColor(self._stroke_color)
        sl.setStrokeWidth(1.0)
        fc = QColor(self._fill_color.red(), self._fill_color.green(), self._fill_color.blue(), int(self.spn_fill_op.value() * 2.55))
        sl.setFillColor(fc)
        layer.setRenderer(QgsSingleSymbolRenderer(sym))

        self.progress.setValue(60)
        QApplication.processEvents()

        # Setup fraction labels
        expr = self._build_expression()
        if expr:
            s = QgsPalLayerSettings()
            s.fieldName = expr
            s.isExpression = True
            s.scaleVisibility = True
            s.maximumScale = self.spn_zoom_in.currentData()
            s.minimumScale = self.spn_zoom_out.currentData()

            fmt = QgsTextFormat()
            font = QFont(self.cbo_font.currentText())
            font.setPointSize(self.spn_fsize.value())
            fmt.setFont(font)
            fmt.setColor(self._font_color)
            
            # Text buffer settings (always white outline for visibility)
            buf = QgsTextBufferSettings()
            buf.setEnabled(True)
            buf.setSize(1.0)
            buf.setColor(QColor(255, 255, 255))
            fmt.setBuffer(buf)

            s.setFormat(fmt)
            layer.setLabeling(QgsVectorLayerSimpleLabeling(s))
            layer.setLabelsEnabled(True)

        self.progress.setValue(90)
        QApplication.processEvents()
        
        layer.triggerRepaint()
        self.iface.mapCanvas().refresh()
        self.progress.setValue(100)
        self.progress.setVisible(False)
        self.iface.messageBar().pushSuccess("VNU2F", "Đã cấu hình kiểu dáng và nhãn lô phân số thành công!")


    def reset(self):
        self._stroke_color = QColor("#55ff00")
        self._fill_color = QColor("#ffff00")
        self._font_color = QColor("#00ffff")
        self._buf_color = QColor("#ffffff")
        self._bg_color = QColor("#ffaa00")
        self._refresh_layers()

    def hideEvent(self, event):
        """Hủy map tool vẽ nếu tab bị ẩn."""
        self.cleanup()
        if event:
            super().hideEvent(event)

    def cleanup(self):
        """Unset map tool vẽ nếu đang active."""
        if hasattr(self, "_extent_tool") and self._extent_tool and self.iface:
            canvas = self.iface.mapCanvas()
            if canvas and canvas.mapTool() == self._extent_tool:
                try:
                    canvas.unsetMapTool(self._extent_tool)
                except Exception:  # noqa: BLE001 — intentional suppress
                    pass
