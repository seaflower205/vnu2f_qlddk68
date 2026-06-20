"""
UI thuần của QA Tab. Không chứa logic xử lý (Controller-View separation).
Áp dụng phong cách Zinc (Shadcn/Cal.com) — Flat, clean.
"""
from __future__ import annotations

from qgis.PyQt.QtCore import Qt, QAbstractTableModel, QModelIndex, QVariant
from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QCheckBox, QComboBox, QTableView, QHeaderView,
    QProgressBar, QGroupBox, QScrollArea, QFrame, QAbstractItemView
)

class QAResultTableModel(QAbstractTableModel):
    def __init__(self, issues=None):
        super().__init__()
        self._data = issues or []
        self._headers = ["Mức độ", "FID", "Chi tiết", "Hình học/Vị trí"]

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return QVariant()
        
        if role == Qt.ItemDataRole.DisplayRole:
            issue = self._data[index.row()]
            if index.column() == 0:
                return issue.severity
            elif index.column() == 1:
                return str(issue.feature_id)
            elif index.column() == 2:
                return issue.description
            elif index.column() == 3:
                return str(issue.geometry_ref)
        
        # Có thể thêm role màu sắc (ERROR = đỏ, WARNING = vàng) nếu cần
        return QVariant()

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self._headers)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self._headers[section]
        return QVariant()

    def update_data(self, new_data):
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()

    def get_issue_at(self, row):
        if 0 <= row < len(self._data):
            return self._data[row]
        return None


class QATabUi:
    """Setup UI components cho QA Tab."""

    def __init__(self):
        # Các control chính
        self.layer_combo = QComboBox()
        self.layer_combo.setFixedHeight(38)
        
        self.boundary_combo = QComboBox()
        self.boundary_combo.setFixedHeight(38)
        
        self.date_picker = QComboBox() # Tạm dùng combo hoặc lineEdit cho as_of_date
        self.date_picker.setFixedHeight(38)

        self.chk_topology = QCheckBox("Kiểm tra chồng lấp, lỗi không gian (Topology) — Nặng")
        self.chk_topology.setChecked(True)
        
        self.chk_gaps = QCheckBox("Kiểm tra khoảng hở (Gaps) với Ranh giới")
        self.chk_gaps.setChecked(False)
        self.chk_gaps.setEnabled(False)  # Bật khi boundary được chọn
        
        # --- UI Pháp lý ---
        from qgis.PyQt.QtWidgets import QDateEdit, QLineEdit
        from qgis.PyQt.QtCore import QDate
        
        self.chk_legal = QCheckBox("Kiểm tra Nghiệp vụ & Pháp lý (Trùng lặp, Diện tích tách thửa)")
        self.chk_legal.setChecked(True)
        
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setFixedHeight(38)
        
        self.cbo_operation = QComboBox()
        self.cbo_operation.addItems([
            "Kiểm tra hiện trạng (kiem_tra_hien_trang)",
            "Tách thửa (tach_thua)",
            "Hợp thửa (hop_thua)",
            "Nghiệm thu (nghiem_thu)",
            "Cảnh báo chuyển đổi (migration_warning)"
        ])
        self.cbo_operation.setFixedHeight(38)
        
        self.txt_default_commune = QLineEdit()
        self.txt_default_commune.setPlaceholderText("VD: 00001")
        self.txt_default_commune.setFixedHeight(38)
        
        self.txt_default_province = QLineEdit()
        self.txt_default_province.setPlaceholderText("VD: 01")
        self.txt_default_province.setFixedHeight(38)

        self.btn_run = QPushButton("Chạy Kiểm Định")
        self.btn_run.setFixedHeight(38)
        self.btn_run.setObjectName("btn_run_qa")
        # Style tương tự nút Zinc Primary
        self.btn_run.setStyleSheet("""
            QPushButton#btn_run_qa {
                background-color: #18181b;
                color: #fafafa;
                border-radius: 6px;
                border: 1px solid #18181b;
                font-weight: bold;
            }
            QPushButton#btn_run_qa:hover { background-color: #27272a; }
            QPushButton#btn_run_qa:disabled { background-color: #e4e4e7; color: #a1a1aa; border: 1px solid #e4e4e7; }
        """)

        self.btn_cancel = QPushButton("Hủy")
        self.btn_cancel.setFixedHeight(38)
        self.btn_cancel.setEnabled(False)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        
        self.lbl_status = QLabel("Sẵn sàng.")

        # Table View
        self.table_view = QTableView()
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.verticalHeader().setVisible(False)
        
        # Flat Table Style (Zinc)
        self.table_view.setStyleSheet("""
            QTableView {
                border: 1px solid #e4e4e7;
                background-color: #ffffff;
                gridline-color: transparent;
            }
            QTableView::item {
                border-bottom: 1px solid #f4f4f5;
                padding: 4px;
            }
            QHeaderView::section {
                background-color: #fafafa;
                border: none;
                border-bottom: 1px solid #e4e4e7;
                font-weight: bold;
                padding: 4px;
            }
        """)

    def setup_ui(self, parent_widget: QWidget):
        main_layout = QVBoxLayout(parent_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # 1. Config Group
        cfg_group = QGroupBox("Cấu hình kiểm định")
        cfg_layout = QVBoxLayout(cfg_group)
        cfg_layout.setSpacing(12)

        row1 = QHBoxLayout()
        lbl_layer = QLabel("Lớp thửa đất:")
        lbl_layer.setFixedWidth(100)
        row1.addWidget(lbl_layer)
        row1.addWidget(self.layer_combo)
        cfg_layout.addLayout(row1)

        row2 = QHBoxLayout()
        lbl_bound = QLabel("Lớp ranh giới:")
        lbl_bound.setFixedWidth(100)
        row2.addWidget(lbl_bound)
        row2.addWidget(self.boundary_combo)
        cfg_layout.addLayout(row2)

        cfg_layout.addWidget(self.chk_topology)
        cfg_layout.addWidget(self.chk_gaps)
        
        cfg_layout.addWidget(self.chk_legal)
        
        row_date = QHBoxLayout()
        lbl_date = QLabel("Ngày áp dụng pháp lý:")
        lbl_date.setFixedWidth(120)
        row_date.addWidget(lbl_date)
        row_date.addWidget(self.date_edit)
        cfg_layout.addLayout(row_date)
        
        row_op = QHBoxLayout()
        lbl_op = QLabel("Loại nghiệp vụ:")
        lbl_op.setFixedWidth(120)
        row_op.addWidget(lbl_op)
        row_op.addWidget(self.cbo_operation)
        cfg_layout.addLayout(row_op)
        
        row_default_com = QHBoxLayout()
        lbl_default_com = QLabel("Mã xã mặc định:")
        lbl_default_com.setFixedWidth(120)
        row_default_com.addWidget(lbl_default_com)
        row_default_com.addWidget(self.txt_default_commune)
        cfg_layout.addLayout(row_default_com)
        
        row_default_prov = QHBoxLayout()
        lbl_default_prov = QLabel("Mã tỉnh mặc định:")
        lbl_default_prov.setFixedWidth(120)
        row_default_prov.addWidget(lbl_default_prov)
        row_default_prov.addWidget(self.txt_default_province)
        cfg_layout.addLayout(row_default_prov)

        main_layout.addWidget(cfg_group)

        # 2. Status & Actions
        action_layout = QHBoxLayout()
        action_layout.addWidget(self.btn_run)
        action_layout.addWidget(self.btn_cancel)
        main_layout.addLayout(action_layout)

        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.lbl_status)

        # 3. Results Table
        lbl_res = QLabel("Danh sách lỗi phát hiện (Nhấp đúp để Zoom):")
        lbl_res.setStyleSheet("font-weight: bold; margin-top: 8px;")
        main_layout.addWidget(lbl_res)

        main_layout.addWidget(self.table_view)

        # Căn chỉnh cột table
        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # Mức độ
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) # FID
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)          # Mô tả
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents) # Vị trí
