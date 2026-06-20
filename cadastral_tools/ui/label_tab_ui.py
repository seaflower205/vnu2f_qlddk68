# -*- coding: utf-8 -*-
from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QTextEdit, QLabel
)
from vnu2f_qlddk68.cadastral_tools.ui.color_row_widget import ColorSwatchButton
from vnu2f_qlddk68.modules.common.ui_utils import (
    create_themed_button,
    create_form_group,
    tune_form_controls,
    create_growing_form
)
from vnu2f_qlddk68.modules.common.scroll_utils import make_scroll_area

class LabelTabUi:
    def setup_ui(self, parent: QWidget):
        self.parent = parent
        scroll, container, layout = make_scroll_area(parent, spacing=10, margins=(12, 12, 12, 12))
        
        main_layout = QVBoxLayout(parent)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

        # 1. Chọn Layer hoạt động
        layer_layout = QHBoxLayout()
        layer_layout.addWidget(QLabel("Lớp ranh thửa:", container))
        self.cbo_layer = QComboBox(container)
        self.cbo_layer.setPlaceholderText("--- Chọn lớp ranh thửa ---")
        layer_layout.addWidget(self.cbo_layer, 1)
        layout.addLayout(layer_layout)

        # 2. Chọn Preset
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Preset mẫu nhãn:", container))
        self.cbo_preset = QComboBox(container)
        preset_layout.addWidget(self.cbo_preset, 1)
        layout.addLayout(preset_layout)

        # 3. Form Group: Khớp trường thuộc tính
        grp_fields, fields_layout = create_form_group("Khớp trường thuộc tính", container, spacing=10)
        form_fields = create_growing_form()
        
        self.cbo_f_sothua = QComboBox(container)
        self.cbo_f_ma_dat = QComboBox(container)
        self.cbo_f_dientich = QComboBox(container)
        self.cbo_f_to_ban_do = QComboBox(container)
        
        form_fields.addRow("Số thửa đất (*):", self.cbo_f_sothua)
        form_fields.addRow("Mã loại đất (*):", self.cbo_f_ma_dat)
        form_fields.addRow("Diện tích (*):", self.cbo_f_dientich)
        form_fields.addRow("Số tờ bản đồ:", self.cbo_f_to_ban_do)
        
        fields_layout.addLayout(form_fields)
        layout.addWidget(grp_fields)

        # 4. Xem trước biểu thức
        grp_preview, preview_layout = create_form_group("Biểu thức nhãn QGIS", container, spacing=6)
        self.txt_expr_preview = QTextEdit(container)
        self.txt_expr_preview.setReadOnly(True)
        self.txt_expr_preview.setMinimumHeight(65)
        self.txt_expr_preview.setMaximumHeight(100)
        self.txt_expr_preview.setStyleSheet("font-family: Courier New; font-size: 11px;")
        preview_layout.addWidget(self.txt_expr_preview)
        layout.addWidget(grp_preview)

        # 5. Form Group: Thiết lập hiển thị
        grp_visual, visual_layout = create_form_group("Cấu hình kiểu hiển thị", container, spacing=8)
        form_visual = create_growing_form()

        # Font chữ và cỡ chữ
        font_layout = QHBoxLayout()
        self.cbo_font = QComboBox(container)
        self.cbo_font.addItems(["Arial", "Times New Roman", "Courier New", "Verdana", "Tahoma", "Georgia", "Comic Sans MS", "Trebuchet MS", "Impact"])
        self.cbo_font.setCurrentText("Arial")
        self.sp_font_size = QSpinBox(container)
        self.sp_font_size.setRange(4, 72)
        self.sp_font_size.setValue(9)
        font_layout.addWidget(self.cbo_font, 3)
        font_layout.addWidget(self.sp_font_size, 1)
        form_visual.addRow("Phông & cỡ chữ:", font_layout)

        # Màu chữ
        self.btn_color = ColorSwatchButton("#000000", container)
        form_visual.addRow("Màu sắc chữ:", self.btn_color)

        # Viền chữ
        buffer_layout = QHBoxLayout()
        self.chk_buffer = QCheckBox("Bật viền chữ", container)
        self.chk_buffer.setChecked(True)
        self.btn_buffer_color = ColorSwatchButton("#FFFFFF", container)
        self.sp_buffer_size = QDoubleSpinBox(container)
        self.sp_buffer_size.setRange(0.1, 10.0)
        self.sp_buffer_size.setSingleStep(0.2)
        self.sp_buffer_size.setValue(1.0)
        
        buffer_layout.addWidget(self.chk_buffer)
        buffer_layout.addWidget(self.btn_buffer_color)
        buffer_layout.addWidget(self.sp_buffer_size)
        form_visual.addRow("Viền bóng chữ:", buffer_layout)

        # Tỷ lệ giới hạn hiển thị
        self.cbo_scale_limit = QComboBox(container)
        self.cbo_scale_limit.addItem("Hiện ở mọi tỷ lệ", 0)
        self.cbo_scale_limit.addItem("Chỉ hiện từ 1:1.000", 1000)
        self.cbo_scale_limit.addItem("Chỉ hiện từ 1:2.000", 2000)
        self.cbo_scale_limit.addItem("Chỉ hiện từ 1:5.000", 5000)
        self.cbo_scale_limit.addItem("Chỉ hiện từ 1:10.000", 10000)
        form_visual.addRow("Tỷ lệ giới hạn nhãn:", self.cbo_scale_limit)

        # Vị trí đặt nhãn & Tránh chồng đè
        self.cbo_placement = QComboBox(container)
        self.cbo_placement.addItem("Trọng tâm thửa đất (Nằm ngang)", 4)
        self.cbo_placement.addItem("Xung quanh thửa", 0)
        self.cbo_placement.addItem("Tự do trong thửa", 5)
        self.cbo_placement.addItem("Bám theo ranh giới thửa", 7)
        form_visual.addRow("Vị trí đặt nhãn:", self.cbo_placement)

        self.chk_conflict = QCheckBox("Tự động giải quyết chồng đè nhãn", container)
        self.chk_conflict.setChecked(True)
        form_visual.addRow("Chống đè nhãn:", self.chk_conflict)

        visual_layout.addLayout(form_visual)
        layout.addWidget(grp_visual)

        # 6. Bottom Action Bar
        action_bar = QWidget(container)
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(6)

        self.btn_apply = create_themed_button("Áp dụng nhãn", "primary", action_bar)
        self.btn_apply.setMinimumHeight(38)
        self.btn_disable = create_themed_button("Tắt nhãn", "danger", action_bar)
        self.btn_disable.setMinimumHeight(38)
        self.btn_save_preset = create_themed_button("Lưu preset...", None, action_bar)
        self.btn_save_preset.setMinimumHeight(38)
        
        self.btn_import = create_themed_button("↓ Nhập preset", None, action_bar)
        self.btn_import.setMinimumHeight(38)
        self.btn_export = create_themed_button("↑ Xuất preset", None, action_bar)
        self.btn_export.setMinimumHeight(38)

        action_layout.addWidget(self.btn_apply)
        action_layout.addWidget(self.btn_disable)
        action_layout.addWidget(self.btn_save_preset)
        action_layout.addStretch()
        action_layout.addWidget(self.btn_import)
        action_layout.addWidget(self.btn_export)
        
        layout.addWidget(action_bar)
        
        tune_form_controls(container)
