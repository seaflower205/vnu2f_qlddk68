# -*- coding: utf-8 -*-
from qgis.PyQt.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QComboBox, QTableWidget, 
    QCheckBox, QProgressBar, QLineEdit, QWidget
)
from modules.common.ui_utils import (
    create_themed_button,
    tune_form_controls
)
from modules.common.qt_compat import (
    HeaderResizeToContents,
    HeaderStretch,
    NoEditTriggers,
    SelectRows,
)
from modules.common.scroll_utils import make_scroll_area

class StatsTabUi:
    def setup_ui(self, parent: QWidget):
        self.parent = parent
        scroll, container, layout = make_scroll_area(parent, spacing=10, margins=(12, 12, 12, 12))
        
        main_layout = QVBoxLayout(parent)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

        # 1. Bộ chọn Layer & Field
        selectors_layout = QHBoxLayout()
        selectors_layout.setSpacing(6)
        
        self.cbo_layer = QComboBox(container)
        self.cbo_layer.setPlaceholderText("--- Chọn lớp ranh thửa ---")
        
        self.cbo_field_code = QComboBox(container)
        self.cbo_field_code.setPlaceholderText("--- Trường mã loại đất ---")
        
        self.cbo_field_area = QComboBox(container)
        self.cbo_field_area.setPlaceholderText("--- Trường diện tích (Tính hình học nếu trống) ---")
        
        selectors_layout.addWidget(self.cbo_layer, 2)
        selectors_layout.addWidget(self.cbo_field_code, 2)
        selectors_layout.addWidget(self.cbo_field_area, 2)
        layout.addLayout(selectors_layout)

        # 2. Checkbox tự động cập nhật & Thanh tiến trình ngầm
        options_layout = QHBoxLayout()
        self.chk_auto_update = QCheckBox("Tự động cập nhật khi layer thay đổi", container)
        self.chk_auto_update.setChecked(False)
        options_layout.addWidget(self.chk_auto_update)
        options_layout.addStretch()
        layout.addLayout(options_layout)

        # Progress bar cho QgsTask tính toán ngầm
        self.progress_bar = QProgressBar(container)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(14)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #27272a;
                border-radius: 4px;
                text-align: center;
                background-color: #18181b;
                color: #fafafa;
            }
            QProgressBar::chunk {
                background-color: #22c55e;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # 2.5. Hộp tìm kiếm nhanh loại đất thống kê (Filter Bar)
        self.txt_search = QLineEdit(container)
        self.txt_search.setPlaceholderText("Tìm kiếm nhanh loại đất thống kê...")
        self.txt_search.setClearButtonEnabled(True)
        self.txt_search.setMinimumHeight(34)
        layout.addWidget(self.txt_search)

        # 3. Bảng kết quả thống kê QTableWidget
        self.table = QTableWidget(container)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Mã", "Tên loại đất", "Số thửa", "Tổng DT (m²)", "Tổng DT (ha)", "Tỷ lệ (%)"
        ])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, HeaderResizeToContents)
        header.setSectionResizeMode(1, HeaderStretch)
        for i in range(2, 6):
            header.setSectionResizeMode(i, HeaderResizeToContents)
            
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(SelectRows)
        self.table.setEditTriggers(NoEditTriggers)
        self.table.setMinimumHeight(280)
        
        layout.addWidget(self.table)

        # 4. Action Buttons Bar
        action_bar = QWidget(container)
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(6)

        self.btn_refresh = create_themed_button("Làm mới", "primary", action_bar)
        self.btn_refresh.setMinimumHeight(38)
        self.btn_csv = create_themed_button("Xuất CSV...", None, action_bar)
        self.btn_csv.setMinimumHeight(38)
        self.btn_excel = create_themed_button("Xuất Excel (.xlsx)...", None, action_bar)
        self.btn_excel.setMinimumHeight(38)

        action_layout.addWidget(self.btn_refresh)
        action_layout.addStretch()
        action_layout.addWidget(self.btn_csv)
        action_layout.addWidget(self.btn_excel)
        
        layout.addWidget(action_bar)
        
        tune_form_controls(container)
