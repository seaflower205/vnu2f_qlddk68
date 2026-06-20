"""Mechanically extracted responsibilities from font_tab.py."""

import os
import traceback
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QComboBox,
    QProgressBar,
    QTextEdit,
    QMessageBox,
    QFileDialog,
    QApplication,
)
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsProject,
    QgsVectorLayer,
    QgsVectorFileWriter,
    QgsCoordinateTransform,
    QgsFeature,
    QgsField,
    QgsCoordinateTransformContext
)
from qgis.gui import QgsMapLayerComboBox
from ...common.vn2000_data import populate_crs_combo
from modules.common.ui_utils import (
    create_themed_button,
    create_file_browser_row,
    create_bottom_action_bar,
    create_centered_panel,
    create_form_group,
    create_growing_form,
    create_solid_primary_button,
    tune_form_controls,
)
from ...common.i18n import tr
from ..font_utils import convert_text_by_mode, postprocess_tab
from .font_file_export_mixin import FontFileExportMixin
from .font_layer_export_mixin import FontLayerExportMixin


class FontTabUiMixin:
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 18, 10, 18)
        layout.setSpacing(16)

        panel, panel_layout = create_centered_panel(self, layout, panel_spacing=16)

        # Hộp cấu hình chính
        self.grp_font_config, grp_font_layout = create_form_group(
            tr("font.group.config"),
            self,
            minimum_height=560,
            margins=(36, 32, 36, 32),
            spacing=18,
        )

        form = create_growing_form(horizontal_spacing=24, vertical_spacing=18)

        # 1. Nguồn dữ liệu
        self.cmb_font_source_type = QComboBox(self.grp_font_config)
        self.cmb_font_source_type.addItems([
            tr("font.option.qgis_layer"),
            tr("font.option.shp_file"),
        ])
        form.addRow(tr("font.label.source"), self.cmb_font_source_type)

        # 2. Lớp bản đồ đang mở trong QGIS
        self.cmb_font_layer = QgsMapLayerComboBox(self.grp_font_config)
        form.addRow(tr("font.label.layer"), self.cmb_font_layer)
        self.row_font_layer_label = form.labelForField(self.cmb_font_layer)

        # 3. Tệp đầu vào trên đĩa (ẩn mặc định)
        self.lbl_font_file_in = QLabel(tr("font.label.file_in"))
        self.lbl_font_file_in.setVisible(False)
        
        file_in_layout, self.txt_font_file_in, self.btn_font_browse_in = create_file_browser_row(
            placeholder=tr("font.placeholder.file_in"), parent=self.grp_font_config
        )
        self.txt_font_file_in.setVisible(False)
        self.btn_font_browse_in.setVisible(False)
        form.addRow(self.lbl_font_file_in, file_in_layout)

        # 4. Tệp đầu ra trên đĩa (ẩn mặc định)
        self.lbl_font_file_out = QLabel(tr("font.label.file_out"))
        self.lbl_font_file_out.setVisible(False)
        
        file_out_layout, self.txt_font_file_out, self.btn_font_browse_out = create_file_browser_row(
            placeholder=tr("font.placeholder.file_out"), parent=self.grp_font_config
        )
        self.txt_font_file_out.setVisible(False)
        self.btn_font_browse_out.setVisible(False)
        form.addRow(self.lbl_font_file_out, file_out_layout)

        # 5. Phương thức chuyển đổi
        self.cmb_font_conversion = QComboBox(self.grp_font_config)
        self.cmb_font_conversion.addItems([
            tr("font.option.tcvn3_unicode"),
            tr("font.option.vni_unicode"),
            tr("font.option.unicode_tcvn3"),
            tr("font.option.no_convert"),
        ])
        form.addRow(tr("font.label.conversion"), self.cmb_font_conversion)

        # 6. Định dạng đầu ra
        self.cmb_font_format = QComboBox(self.grp_font_config)
        self.cmb_font_format.addItems([
            tr("font.option.shapefile"),
            tr("font.option.mapinfo"),
        ])
        form.addRow(tr("font.label.format"), self.cmb_font_format)
        self.row_font_format_label = form.labelForField(self.cmb_font_format)

        # 7. Hệ tọa độ đầu ra (CRS)
        self.cmb_font_crs = QComboBox(self.grp_font_config)
        self.cmb_font_crs.setMinimumWidth(280)
        from qgis.PyQt.QtCore import QTimer
        QTimer.singleShot(0, lambda: populate_crs_combo(self.cmb_font_crs))
        form.addRow(tr("font.label.target_crs"), self.cmb_font_crs)

        grp_font_layout.addLayout(form)

        self.btn_font_convert = create_solid_primary_button(
            tr("font.button.convert_export"), self.grp_font_config, object_name="fontConvertPrimary"
        )
        self.btn_font_convert.clicked.connect(self._on_font_convert_clicked)
        grp_font_layout.addWidget(self.btn_font_convert)

        panel_layout.addWidget(self.grp_font_config)

        # Kết nối sự kiện tương tác nguồn dữ liệu
        self.cmb_font_source_type.currentIndexChanged.connect(self._on_font_source_type_changed)
        self.btn_font_browse_in.clicked.connect(self._on_font_browse_in)
        self.btn_font_browse_out.clicked.connect(self._on_font_browse_out)

        # Khung tiến trình và Log kết quả
        self.progress_font = QProgressBar(self)
        self.progress_font.setVisible(False)
        panel_layout.addWidget(self.progress_font)

        self.grp_font_log, log_layout = create_form_group(
            tr("font.group.log"),
            self,
            margins=(12, 18, 12, 12),
            spacing=12,
        )
        self.log_font = QTextEdit(self.grp_font_log)
        self.log_font.setReadOnly(True)
        self.log_font.setMinimumHeight(150)
        self.log_font.setMaximumHeight(220)
        log_layout.addWidget(self.log_font)
        self.grp_font_log.setVisible(False)
        panel_layout.addWidget(self.grp_font_log)

        layout.addStretch(1)

        # Các nút hành động phụ
        action_bar, act_row = create_bottom_action_bar(self)
        
        self.btn_font_help = create_themed_button(tr("common.help"), parent=action_bar)
        self.btn_font_help.setMinimumWidth(180)
        self.btn_font_help.clicked.connect(self._on_font_help_clicked)
        act_row.addWidget(self.btn_font_help)

        layout.addWidget(action_bar)
        tune_form_controls(self)
