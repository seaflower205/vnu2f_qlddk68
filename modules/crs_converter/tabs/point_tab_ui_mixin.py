"""Mechanically extracted responsibilities from point_tab.py."""

from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QGridLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QMessageBox,
    QApplication,
    QPushButton
)
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
    QgsPointXY,
    QgsVectorLayer,
    QgsField,
    QgsFeature,
    QgsGeometry
)
from qgis.gui import QgsVertexMarker
from ...common.vn2000_data import VN2000_PROVINCES
from modules.common.ui_utils import create_themed_button
from ...common.qt_compat import SizePolicyExpanding, SizePolicyFixed
from ..crs_utils import CoordinateTransformer


class PointTabUiMixin:
    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 12, 14, 12)
        main_layout.setSpacing(16)

        split_layout = QHBoxLayout()
        split_layout.setSpacing(16)
        main_layout.addLayout(split_layout)

        # LEFT COL: Input
        left_col = QVBoxLayout()
        left_col.setSpacing(10)
        split_layout.addLayout(left_col, 1)

        # 3.1 WGS84 input
        self.grp_dms_in = QGroupBox("Nhập tọa độ WGS84 (DMS / Thập phân)", self)
        self.grp_dms_in.setMinimumHeight(190)
        g_dms = QGridLayout(self.grp_dms_in)
        g_dms.setContentsMargins(18, 20, 18, 18)
        g_dms.setHorizontalSpacing(12)
        g_dms.setVerticalSpacing(12)
        g_dms.setColumnStretch(1, 1)

        g_dms.addWidget(QLabel("Vĩ độ (Lat):"), 0, 0)
        self.txt_lat_dms = QLineEdit(self.grp_dms_in)
        self.txt_lat_dms.setPlaceholderText("21°14'05\" hoặc 21.2347")
        g_dms.addWidget(self.txt_lat_dms, 0, 1)

        g_dms.addWidget(QLabel("Kinh độ (Lon):"), 1, 0)
        self.txt_lon_dms = QLineEdit(self.grp_dms_in)
        self.txt_lon_dms.setPlaceholderText("105°22'20\" hoặc 105.3722")
        g_dms.addWidget(self.txt_lon_dms, 1, 1)

        self.btn_convert_dms = create_themed_button("Chuyển sang Thập phân và VN-2000", theme="primary", parent=self.grp_dms_in)
        self.btn_convert_dms.setObjectName("btn_primary")
        self.btn_convert_dms.clicked.connect(self._on_convert_dms)
        g_dms.addWidget(self.btn_convert_dms, 2, 0, 1, 2)
        left_col.addWidget(self.grp_dms_in)

        # 3.2 VN-2000 input
        self.grp_metric_in = QGroupBox("Nhập tọa độ VN-2000 (Mét)", self)
        self.grp_metric_in.setMinimumHeight(245)
        g_met = QGridLayout(self.grp_metric_in)
        g_met.setContentsMargins(18, 20, 18, 18)
        g_met.setHorizontalSpacing(12)
        g_met.setVerticalSpacing(12)
        g_met.setColumnStretch(1, 1)

        g_met.addWidget(QLabel("Tỉnh thành:"), 0, 0)
        self.cmb_prov_crs = QComboBox(self.grp_metric_in)
        for prov_name, crs_code in VN2000_PROVINCES:
            self.cmb_prov_crs.addItem(prov_name, crs_code)
        g_met.addWidget(self.cmb_prov_crs, 0, 1)

        # Restore selected province using QSettings with migration logic
        from qgis.PyQt.QtCore import QSettings
        settings = QSettings()
        last_prov = settings.value("vnu2f_qlddk68/crs_last_province", "")
        if not last_prov:
            last_prov = settings.value("vnu2f_qlddk68/point_prov_crs", "")
            if last_prov:
                settings.setValue("vnu2f_qlddk68/crs_last_province", last_prov)
                settings.remove("vnu2f_qlddk68/point_prov_crs")
        if last_prov:
            idx = self.cmb_prov_crs.findData(last_prov)
            if idx >= 0:
                self.cmb_prov_crs.setCurrentIndex(idx)

        # Connect signal to save immediately on change
        self.cmb_prov_crs.currentIndexChanged.connect(
            lambda idx: QSettings().setValue("vnu2f_qlddk68/crs_last_province", self.cmb_prov_crs.itemData(idx))
        )

        g_met.addWidget(QLabel("Tọa độ X (m):"), 1, 0)
        self.txt_x = QLineEdit(self.grp_metric_in)
        self.txt_x.setPlaceholderText("Ví dụ: 585250.34")
        g_met.addWidget(self.txt_x, 1, 1)

        g_met.addWidget(QLabel("Tọa độ Y (m):"), 2, 0)
        self.txt_y = QLineEdit(self.grp_metric_in)
        self.txt_y.setPlaceholderText("Ví dụ: 2324560.12")
        g_met.addWidget(self.txt_y, 2, 1)

        self.btn_convert_met = create_themed_button("Chuyển sang WGS84", theme="primary", parent=self.grp_metric_in)
        self.btn_convert_met.setObjectName("btn_primary")
        self.btn_convert_met.clicked.connect(self._on_convert_metric)
        g_met.addWidget(self.btn_convert_met, 3, 0, 1, 2)
        left_col.addWidget(self.grp_metric_in)

        left_col.addStretch()

        # RIGHT COL: Results + Actions
        right_col = QVBoxLayout()
        right_col.setSpacing(10)
        split_layout.addLayout(right_col, 1)

        # 3.3 Results
        self.grp_result = QGroupBox("Kết quả tính toán", self)
        self.grp_result.setMinimumHeight(315)
        g_res = QGridLayout(self.grp_result)
        g_res.setContentsMargins(18, 20, 18, 18)
        g_res.setHorizontalSpacing(12)
        g_res.setVerticalSpacing(12)
        g_res.setColumnStretch(1, 1)

        g_res.addWidget(QLabel("Vĩ độ Lat:"), 0, 0)
        self.txt_res_lat = QLineEdit(self.grp_result)
        self.txt_res_lat.setReadOnly(True)
        g_res.addWidget(self.txt_res_lat, 0, 1)

        g_res.addWidget(QLabel("Kinh độ Lon:"), 1, 0)
        self.txt_res_lon = QLineEdit(self.grp_result)
        self.txt_res_lon.setReadOnly(True)
        g_res.addWidget(self.txt_res_lon, 1, 1)

        g_res.addWidget(QLabel("Dạng DMS:"), 2, 0)
        self.txt_res_dms = QLineEdit(self.grp_result)
        self.txt_res_dms.setReadOnly(True)
        g_res.addWidget(self.txt_res_dms, 2, 1)

        g_res.addWidget(QLabel("VN-2000 X (m):"), 3, 0)
        self.txt_res_x = QLineEdit(self.grp_result)
        self.txt_res_x.setReadOnly(True)
        g_res.addWidget(self.txt_res_x, 3, 1)

        g_res.addWidget(QLabel("VN-2000 Y (m):"), 4, 0)
        self.txt_res_y = QLineEdit(self.grp_result)
        self.txt_res_y.setReadOnly(True)
        g_res.addWidget(self.txt_res_y, 4, 1)
        right_col.addWidget(self.grp_result)

        # 3.4 Actions
        self.grp_actions = QGroupBox("Thao tác với điểm", self)
        self.grp_actions.setMinimumHeight(225)
        grp_act_layout = QVBoxLayout(self.grp_actions)
        grp_act_layout.setContentsMargins(18, 22, 18, 18)
        grp_act_layout.setSpacing(12)

        self.txt_point_name = QLineEdit(self.grp_actions)
        self.txt_point_name.setPlaceholderText("Tên điểm (Ví dụ: Điểm 1)")
        grp_act_layout.addWidget(self.txt_point_name)

        act_layout = QGridLayout()
        act_layout.setHorizontalSpacing(10)
        act_layout.setVerticalSpacing(10)
        act_layout.setColumnStretch(0, 1)
        act_layout.setColumnStretch(1, 1)

        self.btn_copy = create_themed_button("Sao chép X,Y", parent=self.grp_actions)
        self.btn_copy.clicked.connect(self._on_copy)
        act_layout.addWidget(self.btn_copy, 0, 0)

        self.btn_zoom = create_themed_button("Phóng tới", parent=self.grp_actions)
        self.btn_zoom.clicked.connect(self._on_zoom)
        act_layout.addWidget(self.btn_zoom, 0, 1)

        self.btn_mark = create_themed_button("Vẽ Marker", parent=self.grp_actions)
        self.btn_mark.clicked.connect(self._on_mark)
        act_layout.addWidget(self.btn_mark, 1, 0)

        self.btn_add_layer = create_themed_button("Lưu vào Lớp", theme="success", parent=self.grp_actions)
        self.btn_add_layer.setObjectName("btn_success")
        self.btn_add_layer.clicked.connect(self._on_add_to_layer)
        act_layout.addWidget(self.btn_add_layer, 1, 1)

        grp_act_layout.addLayout(act_layout)
        right_col.addWidget(self.grp_actions)

        right_col.addStretch()
        self._tune_control_sizes()
