"""Widget construction for the settings tab."""
from qgis.PyQt.QtWidgets import (
    QButtonGroup, QComboBox, QHBoxLayout, QLabel, QRadioButton, QVBoxLayout, QWidget,
)

from modules.common.scroll_utils import make_scroll_area
from modules.common.ui_utils import (
    create_form_group, create_growing_form, create_themed_button, tune_form_controls,
)


def setup_settings_ui(parent):
    scroll, container, layout = make_scroll_area(
        parent, spacing=12, margins=(12, 12, 12, 12)
    )
    root = QVBoxLayout(parent)
    root.setContentsMargins(0, 0, 0, 0)
    root.addWidget(scroll)
    crs_group, crs_layout = create_form_group(
        "Kiểm tra Hệ tọa độ bản đồ", container, spacing=8
    )
    parent.lbl_crs_status = QLabel("CRS hiện tại của Layer: Chưa xác định", container)
    parent.lbl_crs_status.setWordWrap(True)
    parent.lbl_crs_status.setStyleSheet("font-weight: bold; color: #71717a;")
    crs_layout.addWidget(parent.lbl_crs_status)
    parent.btn_reproject = create_themed_button(
        "Chiếu lại về VN-2000...", "primary", container
    )
    parent.btn_reproject.setMinimumHeight(38)
    crs_layout.addWidget(parent.btn_reproject)
    layout.addWidget(crs_group)

    area_group, area_layout = create_form_group(
        "Tính toán lại diện tích thửa đất", container, spacing=10
    )
    form = create_growing_form()
    parent.cbo_area_field = QComboBox(container)
    form.addRow("Trường ghi diện tích:", parent.cbo_area_field)
    unit_widget = QWidget(container)
    unit_layout = QHBoxLayout(unit_widget)
    unit_layout.setContentsMargins(0, 0, 0, 0)
    unit_layout.setSpacing(12)
    parent.rad_m2 = QRadioButton("Mét vuông (m²)", unit_widget)
    parent.rad_m2.setChecked(True)
    parent.rad_ha = QRadioButton("Héc-ta (ha)", unit_widget)
    parent.unit_group = QButtonGroup(container)
    parent.unit_group.addButton(parent.rad_m2)
    parent.unit_group.addButton(parent.rad_ha)
    unit_layout.addWidget(parent.rad_m2)
    unit_layout.addWidget(parent.rad_ha)
    form.addRow("Đơn vị tính toán:", unit_widget)
    area_layout.addLayout(form)
    parent.btn_calc_area = create_themed_button("Tính lại diện tích", None, container)
    parent.btn_calc_area.setMinimumHeight(38)
    area_layout.addWidget(parent.btn_calc_area)
    layout.addWidget(area_group)

    print_group, print_layout = create_form_group(
        "Mẫu in & Xuất hồ sơ bản đồ", container, spacing=8
    )
    info = QLabel(
        "Tự động thiết lập layout in A4 ngang với bản đồ chính, chú giải và thanh tỷ lệ.",
        container,
    )
    info.setWordWrap(True)
    print_layout.addWidget(info)
    parent.btn_create_layout = create_themed_button("Tạo bố cục in mẫu", None, container)
    parent.btn_create_layout.setMinimumHeight(38)
    print_layout.addWidget(parent.btn_create_layout)
    layout.addWidget(print_group)

    profile_group, profile_layout = create_form_group(
        "Sao lưu cấu hình plugin", container, spacing=8
    )
    buttons = QHBoxLayout()
    parent.btn_import_profile = create_themed_button("↓ Nhập profile...", None, container)
    parent.btn_export_profile = create_themed_button("↑ Xuất profile...", None, container)
    for button in (parent.btn_import_profile, parent.btn_export_profile):
        button.setMinimumHeight(38)
        buttons.addWidget(button)
    profile_layout.addLayout(buttons)
    layout.addWidget(profile_group)
    tune_form_controls(container)
