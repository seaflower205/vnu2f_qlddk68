# -*- coding: utf-8 -*-
"""Shared UI layout helpers for plugin dialogs and tabs."""

from qgis.PyQt.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QSpinBox,
    QDoubleSpinBox,
)

from .qt_compat import SizePolicyExpanding, SizePolicyFixed


def grow_form_fields(form: QFormLayout) -> None:
    """Let form fields use the available horizontal space."""
    if hasattr(QFormLayout, "FieldGrowthPolicy"):
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
    else:
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)


def create_centered_panel(
    parent,
    root_layout: QVBoxLayout,
    *,
    max_width: int = 1280,
    panel_spacing: int = 16,
    side_stretch: int = 1,
    panel_stretch: int = 36,
) -> tuple[QWidget, QVBoxLayout]:
    """Create a wide centered panel that still breathes on large dialogs."""
    panel = QWidget(parent)
    panel.setMaximumWidth(max_width)
    panel_policy = panel.sizePolicy()
    panel_policy.setHorizontalPolicy(SizePolicyExpanding)
    panel.setSizePolicy(panel_policy)

    panel_layout = QVBoxLayout(panel)
    panel_layout.setContentsMargins(0, 0, 0, 0)
    panel_layout.setSpacing(panel_spacing)

    center_row = QHBoxLayout()
    center_row.addStretch(side_stretch)
    center_row.addWidget(panel, panel_stretch)
    center_row.addStretch(side_stretch)
    root_layout.addLayout(center_row)
    return panel, panel_layout


def create_form_group(
    title: str,
    parent,
    *,
    minimum_height: int = 0,
    margins: tuple[int, int, int, int] = (32, 30, 32, 30),
    spacing: int = 18,
) -> tuple[QGroupBox, QVBoxLayout]:
    """Create the larger form group style used by the main tool tabs."""
    group = QGroupBox(title, parent)
    if minimum_height:
        group.setMinimumHeight(minimum_height)
    layout = QVBoxLayout(group)
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    return group, layout


def create_growing_form(*, horizontal_spacing: int = 18, vertical_spacing: int = 14) -> QFormLayout:
    form = QFormLayout()
    grow_form_fields(form)
    form.setHorizontalSpacing(horizontal_spacing)
    form.setVerticalSpacing(vertical_spacing)
    return form


def create_bottom_action_bar(parent) -> tuple[QWidget, QHBoxLayout]:
    action_bar = QWidget(parent)
    row = QHBoxLayout(action_bar)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(12)
    row.addStretch(1)
    return action_bar, row


def create_solid_primary_button(text: str, parent=None, *, object_name: str = "solidPrimaryButton") -> QPushButton:
    """Create a direct-styled primary button for QGIS themes that ignore dynamic properties."""
    from modules.common.ui_utils import is_dark_mode
    button = QPushButton(text, parent)
    button.setObjectName(object_name)
    button.setSizePolicy(SizePolicyExpanding, SizePolicyFixed)
    button.setMinimumHeight(42)
    button.setMinimumWidth(280)
    
    if is_dark_mode():
        bg = "#fafafa"
        color = "#18181b"
        hover = "#e4e4e7"
        pressed = "#fafafa"
        disabled_bg = "#18181b"
        disabled_text = "#71717a"
        border_disabled = "#27272a"
    else:
        bg = "#18181b"
        color = "#ffffff"
        hover = "#27272a"
        pressed = "#09090b"
        disabled_bg = "#f4f4f5"
        disabled_text = "#a1a1aa"
        border_disabled = "#e4e4e7"

    button.setStyleSheet(f"""
        QPushButton#{object_name} {{
            background-color: {bg};
            color: {color};
            border: 1px solid {bg};
            border-radius: 6px;
            padding: 8px 18px;
            font-weight: 600;
            font-size: 13px;
        }}
        QPushButton#{object_name}:hover {{
            background-color: {hover};
            border-color: {hover};
        }}
        QPushButton#{object_name}:pressed {{
            background-color: {pressed};
            border-color: {pressed};
        }}
        QPushButton#{object_name}:disabled {{
            background-color: {disabled_bg};
            color: {disabled_text};
            border: 1px solid {border_disabled};
        }}
    """)
    return button


def tune_form_controls(root, *, input_height: int = 38, button_height: int = 38) -> None:
    """Apply common sizing and tooltip behavior to form controls."""
    for label in root.findChildren(QLabel):
        label.setWordWrap(True)
        if label.text():
            label.setToolTip(label.text())

    for widget in root.findChildren((QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox)):
        # Skip internal QLineEdit child of QSpinBox/QDoubleSpinBox/QComboBox to prevent clipping
        if isinstance(widget, QLineEdit) and isinstance(widget.parent(), (QSpinBox, QDoubleSpinBox, QComboBox)):
            continue
        widget.setMinimumHeight(max(widget.minimumHeight(), input_height))
        widget.setSizePolicy(SizePolicyExpanding, SizePolicyFixed)

    for button in root.findChildren(QPushButton):
        if button.text():
            button.setToolTip(button.text())
        # Tránh ghi đè chiều cao của nút primary lớn hoặc nút duyệt file nhỏ
        if button.objectName() != "solidPrimaryButton" and button.objectName() != "btn_browse":
            button.setMinimumHeight(max(button.minimumHeight(), button_height))
        button.setSizePolicy(SizePolicyExpanding, SizePolicyFixed)

