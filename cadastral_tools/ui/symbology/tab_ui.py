# -*- coding: utf-8 -*-
"""Zinc UI builder for the cadastral symbology tab."""

from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)
from qgis.core import QgsMapLayerProxyModel
from qgis.gui import QgsFilterLineEdit, QgsMapLayerComboBox

from modules.common.qt_compat import (
    CustomContextMenu,
    ExtendedSelection,
    HeaderResizeToContents,
    HeaderStretch,
    HeaderInteractive,
    SelectRows,
)
from modules.common.scroll_utils import make_scroll_area
from modules.common.ui_utils import create_themed_button, tune_form_controls

from ..symbology_delegate import SymbologyDelegate


class SymbologyTabUi:
    """Build widgets only; the owner remains responsible for behavior."""

    def setup_ui(self, owner):
        scroll, container, content = make_scroll_area(
            owner,
            spacing=10,
            margins=(12, 12, 12, 12),
        )

        main_layout = QVBoxLayout(owner)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)

        owner.cbo_layer = QgsMapLayerComboBox(container)
        owner.cbo_layer.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        owner.cbo_layer.setAllowEmptyLayer(True)
        owner.cbo_layer.setMinimumHeight(38)

        from qgis.PyQt.QtWidgets import QComboBox

        owner.cbo_field = QComboBox(container)
        owner.cbo_field.setPlaceholderText("--- Chọn trường mã đất ---")
        owner.cbo_field.setMinimumHeight(38)

        owner.btn_scan = create_themed_button("Tải mã từ layer", parent=container)
        owner.btn_scan.setMinimumHeight(38)

        top_bar.addWidget(owner.cbo_layer, 2)
        top_bar.addWidget(owner.cbo_field, 2)
        top_bar.addWidget(owner.btn_scan, 1)
        content.addLayout(top_bar)

        owner.txt_search = QgsFilterLineEdit(container)
        owner.txt_search.setPlaceholderText("Tìm kiếm nhanh mã hoặc tên loại đất...")
        owner.txt_search.setShowSearchIcon(True)
        owner.txt_search.setMinimumHeight(38)
        content.addWidget(owner.txt_search)

        owner.table = QTableWidget(container)
        owner.table.setColumnCount(8)
        owner.table.setHorizontalHeaderLabels(
            [
                "#",
                "Mã",
                "Tên loại đất",
                "Màu nền",
                "Màu viền",
                "Nét viền (mm)",
                "Kiểu fill",
                "Độ mờ (%)",
            ]
        )
        header = owner.table.horizontalHeader()
        header.setSectionResizeMode(0, HeaderResizeToContents)
        header.setSectionResizeMode(1, HeaderResizeToContents)
        header.setSectionResizeMode(2, HeaderStretch)
        for column in (3, 4, 5, 7):
            header.setSectionResizeMode(column, HeaderResizeToContents)
        header.setSectionResizeMode(6, HeaderInteractive)
        owner.table.setColumnWidth(6, 150)

        owner.table.verticalHeader().setVisible(False)
        owner.table.verticalHeader().setDefaultSectionSize(32)
        owner.table.setSelectionBehavior(SelectRows)
        owner.table.setSelectionMode(ExtendedSelection)
        owner.table.setContextMenuPolicy(CustomContextMenu)
        owner.table.setShowGrid(False)
        owner.table.setMinimumHeight(300)
        owner.table.setItemDelegate(SymbologyDelegate(
            owner,
            patterns_provider=lambda: owner.current_pattern_map.keys()
        ))
        content.addWidget(owner.table)

        options = QHBoxLayout()
        owner.chk_add_to_legend = QCheckBox("Thêm vào legend", container)
        owner.chk_add_to_legend.setChecked(True)
        owner.chk_highlight_unmatched = QCheckBox("Hiện giá trị không khớp", container)
        owner.chk_highlight_unmatched.setChecked(True)
        options.addWidget(owner.chk_add_to_legend)
        options.addWidget(owner.chk_highlight_unmatched)
        options.addStretch()
        content.addLayout(options)

        action_bar = QWidget(container)
        actions = QHBoxLayout(action_bar)
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(8)

        owner.btn_apply = create_themed_button("Áp dụng", "primary", action_bar)
        owner.btn_apply.setObjectName("btn_primary")
        owner.btn_reset = create_themed_button("Reset mặc định", parent=action_bar)
        owner.btn_import = create_themed_button("↓ Nhập JSON", parent=action_bar)
        owner.btn_export = create_themed_button("↑ Xuất JSON", parent=action_bar)
        owner.btn_export_qml = create_themed_button("↑ Xuất QML", parent=action_bar)
        for button in (
            owner.btn_apply,
            owner.btn_reset,
            owner.btn_import,
            owner.btn_export,
            owner.btn_export_qml,
        ):
            button.setMinimumHeight(38)

        actions.addWidget(owner.btn_apply)
        actions.addWidget(owner.btn_reset)
        actions.addStretch()
        actions.addWidget(owner.btn_import)
        actions.addWidget(owner.btn_export)
        actions.addWidget(owner.btn_export_qml)
        content.addWidget(action_bar)

        tune_form_controls(container)
