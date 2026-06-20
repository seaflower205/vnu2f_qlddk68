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

ALIGN_CENTER = Qt.AlignmentFlag.AlignCenter
STANDARD_SCALES = [
    500, 1000, 2000, 2500, 5000, 10000, 15000,
    20000, 25000, 50000, 100000, 250000, 500000, 1000000,
]


class MbtilesUiMixin:
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        scroll, content, content_ly = make_scroll_area(self, spacing=12, margins=(0, 0, 0, 0))

        # 1. Layer & Basic styling
        self.grp_basic, basic_ly = create_layout_form_group("1. Thiết lập Lớp & Màu sắc", self)
        g_form = create_growing_form()
        
        self.cbo_layer = QComboBox(self)
        self.cbo_layer.currentIndexChanged.connect(self._on_layer_changed)
        g_form.addRow("Lớp vector:", self.cbo_layer)

        # Stroke + Fill colors
        color_ly = QHBoxLayout()
        self.btn_stroke = QPushButton("#55ff00")
        self.btn_stroke.setMinimumHeight(38)
        self.btn_stroke.setStyleSheet("background-color: #55ff00; color: black;")
        self.btn_stroke.clicked.connect(lambda: self._pick_theme_color("stroke", self.btn_stroke))
        color_ly.addWidget(self.btn_stroke)

        self.btn_fill = QPushButton("#ffff00")
        self.btn_fill.setMinimumHeight(38)
        self.btn_fill.setStyleSheet("background-color: #ffff00; color: black;")
        self.btn_fill.clicked.connect(lambda: self._pick_theme_color("fill", self.btn_fill))
        color_ly.addWidget(self.btn_fill)
        g_form.addRow("Màu viền / nền:", color_ly)

        self.spn_fill_op = QSpinBox()
        self.spn_fill_op.setRange(0, 100)
        self.spn_fill_op.setValue(5)
        self.spn_fill_op.setSuffix(" %")
        self.spn_fill_op.valueChanged.connect(self._update_preview)
        g_form.addRow("Độ mờ nền:", self.spn_fill_op)

        basic_ly.addLayout(g_form)
        content_ly.addWidget(self.grp_basic)

        # 2. Plot label numerator / denominator
        self.grp_label, label_ly = create_layout_form_group("2. Nhãn phân số lô rừng", self)
        
        # Grid of fields selection
        fields_ly = QHBoxLayout()
        
        # Numerator
        num_container = QGroupBox("▲ Tử số (Mã lô, loại đất...)")
        num_box = QVBoxLayout(num_container)
        self.scroll_num, self.w_num, self.ly_num = make_scroll_area(num_container, spacing=6, margins=(9, 9, 9, 9))
        num_box.addWidget(self.scroll_num)
        fields_ly.addWidget(num_container)

        # Denominator
        den_container = QGroupBox("▼ Mẫu số (Diện tích...)")
        den_box = QVBoxLayout(den_container)
        self.scroll_den, self.w_den, self.ly_den = make_scroll_area(den_container, spacing=6, margins=(9, 9, 9, 9))
        den_box.addWidget(self.scroll_den)
        fields_ly.addWidget(den_container)

        label_ly.addLayout(fields_ly)

        # Text properties
        label_form = create_growing_form()
        
        self.cbo_font = QComboBox(self)
        self.cbo_font.addItems(["Arial", "Times New Roman", "Courier New", "Verdana", "Tahoma", "Georgia", "Comic Sans MS", "Trebuchet MS", "Impact"])
        self.cbo_font.setCurrentText("Arial")
        label_form.addRow("Phông chữ:", self.cbo_font)

        self.spn_fsize = QSpinBox()
        self.spn_fsize.setRange(6, 72)
        self.spn_fsize.setValue(10)
        self.spn_fsize.valueChanged.connect(self._update_preview)
        label_form.addRow("Cỡ chữ:", self.spn_fsize)

        self.btn_fcolor = QPushButton("#00ffff")
        self.btn_fcolor.setMinimumHeight(38)
        self.btn_fcolor.setStyleSheet("background-color: #00ffff; color: black;")
        self.btn_fcolor.clicked.connect(lambda: self._pick_theme_color("font", self.btn_fcolor))
        label_form.addRow("Màu chữ:", self.btn_fcolor)

        self.spn_zoom_in = QComboBox(self)
        self.spn_zoom_out = QComboBox(self)
        for s in STANDARD_SCALES:
            self.spn_zoom_in.addItem(f"1:{s:,}".replace(",", "."), s)
            self.spn_zoom_out.addItem(f"1:{s:,}".replace(",", "."), s)
        self.spn_zoom_in.setCurrentIndex(1)
        self.spn_zoom_out.setCurrentIndex(5)
        label_form.addRow("Tỷ lệ hiển thị tối đa:", self.spn_zoom_in)
        label_form.addRow("Tỷ lệ hiển thị tối thiểu:", self.spn_zoom_out)

        label_ly.addLayout(label_form)
        content_ly.addWidget(self.grp_label)

        # 3. Preview Box
        self.grp_preview = QGroupBox("Xem trước nhãn lô", self)
        prev_ly = QVBoxLayout(self.grp_preview)
        self.lbl_preview = QLabel(self)
        self.lbl_preview.setMinimumHeight(100)
        self.lbl_preview.setAlignment(ALIGN_CENTER)
        self.lbl_preview.setStyleSheet("background-color: #09090b; border: 1px solid #27272a; border-radius: 6px;")
        prev_ly.addWidget(self.lbl_preview)
        content_ly.addWidget(self.grp_preview)

        # 4. Extent & Zoom settings
        self.grp_extent, ext_ly = create_layout_form_group("3. Phạm vi xuất MBTiles", self)
        ext_form = create_growing_form()
        
        self.btn_draw = create_themed_button("Vẽ phạm vi trên bản đồ", theme=None, parent=self)
        self.btn_draw.clicked.connect(self._draw_extent)
        ext_form.addRow("Phạm vi xuất:", self.btn_draw)

        self.lbl_extent_status = QLabel("Chưa chọn (mặc định lấy toàn bộ lớp)")
        ext_form.addRow("Trạng thái:", self.lbl_extent_status)

        self.spn_minz = QSpinBox()
        self.spn_minz.setRange(0, 22)
        self.spn_minz.setValue(12)
        ext_form.addRow("Zoom tối thiểu:", self.spn_minz)

        self.spn_maxz = QSpinBox()
        self.spn_maxz.setRange(0, 22)
        self.spn_maxz.setValue(18)
        ext_form.addRow("Zoom tối đa:", self.spn_maxz)

        self.chk_basemap = QCheckBox("Xuất kèm nền bản đồ đang bật (Basemap)")
        self.chk_basemap.setChecked(True)
        ext_form.addRow("", self.chk_basemap)

        ext_ly.addLayout(ext_form)
        content_ly.addWidget(self.grp_extent)

        # Progress bar
        self.progress = QProgressBar(self)
        self.progress.setVisible(False)
        grp_action_ly = QHBoxLayout()
        self.btn_apply = create_themed_button("Áp dụng kiểu nhãn", theme="primary", parent=self)
        self.btn_apply.setObjectName("btn_primary")
        self.btn_apply.clicked.connect(self._apply_to_layer)
        grp_action_ly.addWidget(self.btn_apply)

        self.btn_export = create_themed_button("Xuất file MBTiles", theme="success", parent=self)
        self.btn_export.setObjectName("btn_success")
        self.btn_export.clicked.connect(self._export_mbtiles)
        grp_action_ly.addWidget(self.btn_export)
        
        content_ly.addLayout(grp_action_ly)
        content_ly.addWidget(self.progress)

        layout.addWidget(scroll)
        tune_form_controls(self)
