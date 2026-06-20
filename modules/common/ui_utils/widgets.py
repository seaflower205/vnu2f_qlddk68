# -*- coding: utf-8 -*-
import os
from qgis.PyQt.QtWidgets import (
    QPushButton, QGroupBox, QHBoxLayout, QLineEdit, QVBoxLayout, QWidget, 
    QFormLayout, QLabel, QComboBox, QSpinBox, QDoubleSpinBox
)
from modules.common.ui_builder import SizePolicyExpanding, SizePolicyFixed
from .styles import is_dark_mode

def _text_width(widget, text):
    metrics = widget.fontMetrics()
    if hasattr(metrics, "horizontalAdvance"):
        return metrics.horizontalAdvance(text)
    return metrics.width(text)



def create_themed_button(text, theme=None, parent=None):
    """Tạo QPushButton với theme property — QSS sẽ tự render đúng màu."""
    btn = QPushButton(text, parent)
    btn.setToolTip(text)
    btn.setMinimumWidth(_text_width(btn, text) + 56)
    if theme:
        btn.setProperty("theme", theme)
        btn.setObjectName(f"btn_{theme}")
    return btn



def create_form_group(
    title: str,
    parent=None,
    spacing: int = 12,
    *,
    minimum_height: int = 0,
    margins: tuple[int, int, int, int] = None,
) -> tuple[QGroupBox, QVBoxLayout]:
    """Tạo QGroupBox chuẩn với margin/spacing thống nhất."""
    group = QGroupBox(title, parent)
    if minimum_height:
        group.setMinimumHeight(minimum_height)
    layout = QVBoxLayout(group)
    if margins is None:
        if spacing >= 18:
            margins = (32, 30, 32, 30)
        else:
            margins = (12, 16, 12, 12)
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    return group, layout



def create_file_browser_row(placeholder="", readonly=False, parent=None):
    """Tạo bộ [QLineEdit + QPushButton '...'] cho chọn file/thư mục."""
    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(6)
    
    txt = QLineEdit(parent)
    txt.setPlaceholderText(placeholder)
    txt.setReadOnly(readonly)

    btn = QPushButton("...", parent)
    btn.setObjectName("btn_browse")
    btn.setFixedWidth(40)
    btn.setMinimumHeight(38)

    row.addWidget(txt)
    row.addWidget(btn)
    return row, txt, btn



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



def set_dialog_icon(dialog, icon_name):
    """Gán icon tiêu đề cửa sổ cho Dialog."""
    from qgis.PyQt.QtGui import QIcon
    import os
    plugin_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    icon_path = os.path.join(plugin_dir, icon_name)
    if os.path.exists(icon_path):
        dialog.setWindowIcon(QIcon(icon_path))

