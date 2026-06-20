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


class MbtilesPreviewMixin:
    def _update_preview(self):
        num_f = [f for f in self._num_order if self._num_checks.get(f) and self._num_checks[f].isChecked()]
        den_f = [f for f in self._den_order if self._den_checks.get(f) and self._den_checks[f].isChecked()]
        
        num_t = "-".join(num_f) if num_f else "12a"
        den_t = "-".join(den_f) if den_f else "3.2"

        pw = self.lbl_preview.width() or 300
        ph = self.lbl_preview.height() or 100
        pix = QPixmap(max(pw, 100), max(ph, 100))
        pix.fill(QColor("#09090b"))

        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing if hasattr(QPainter, 'RenderHint') else QPainter.Antialiasing)

        # Draw simulated forest boundary rectangle
        pen = QPen(self._stroke_color)
        pen.setWidthF(1.5)
        p.setPen(pen)
        p.setBrush(QBrush(QColor(self._fill_color.red(), self._fill_color.green(), self._fill_color.blue(), 25)))
        p.drawRect(20, 10, pw - 40, ph - 20)

        # Draw label
        font = QFont(self.cbo_font.currentText())
        font.setPointSize(self.spn_fsize.value())
        p.setFont(font)
        p.setPen(QPen(self._font_color))

        # Underline buffer effect
        fm = p.fontMetrics()
        cx = pw // 2
        cy = ph // 2
        line_h = fm.height()

        p.drawText(cx - fm.horizontalAdvance(num_t)//2, cy - 6, num_t)
        p.drawText(cx - fm.horizontalAdvance("________")//2, cy + 2, "________")
        p.drawText(cx - fm.horizontalAdvance(den_t)//2, cy + line_h + 4, den_t)

        p.end()
        self.lbl_preview.setPixmap(pix)
