# -*- coding: utf-8 -*-
"""
Factory tạo widget giao diện chuẩn.

Cung cấp các hàm tạo nhanh QPushButton themed, QGroupBox, file browser row…
để loại bỏ code inline stylesheet lặp đi lặp lại trong các dialog.
"""

from qgis.PyQt.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)


def _text_width(widget, text):
    metrics = widget.fontMetrics()
    if hasattr(metrics, "horizontalAdvance"):
        return metrics.horizontalAdvance(text)
    return metrics.width(text)


def create_themed_button(text, theme=None, parent=None):
    """Tạo QPushButton với theme property — QSS sẽ tự render đúng màu.

    Không dùng inline stylesheet. Chỉ cần set property ``theme`` và
    để stylesheet ở ``ui_utils.get_dialog_stylesheet()`` xử lý.

    Parameters
    ----------
    text : str
        Nhãn hiển thị trên nút.
    theme : str or None
        Một trong: ``"primary"``, ``"success"``, ``"danger"``, hoặc ``None``
        (mặc định — nút thường).
    parent : QWidget or None
        Widget cha.

    Returns
    -------
    QPushButton
    """
    btn = QPushButton(text, parent)
    btn.setToolTip(text)
    btn.setMinimumWidth(_text_width(btn, text) + 56)
    if theme:
        btn.setProperty("theme", theme)
        btn.setObjectName(f"btn_{theme}")
    return btn


def create_form_group(title, parent=None, spacing=12):
    """Tạo QGroupBox chuẩn với margin/spacing thống nhất.

    Parameters
    ----------
    title : str
        Tiêu đề GroupBox.
    parent : QWidget or None
        Widget cha.
    spacing : int
        Khoảng cách giữa các widget con.

    Returns
    -------
    tuple[QGroupBox, QVBoxLayout]
        GroupBox và layout bên trong, sẵn sàng thêm widget.
    """
    group = QGroupBox(title, parent)
    layout = QVBoxLayout(group)
    layout.setContentsMargins(12, 16, 12, 12)
    layout.setSpacing(spacing)
    return group, layout


def create_file_browser_row(placeholder="", readonly=False, parent=None):
    """Tạo bộ [QLineEdit + QPushButton '...'] cho chọn file/thư mục.

    Parameters
    ----------
    placeholder : str
        Văn bản gợi ý trong ô nhập.
    readonly : bool
        Nếu ``True``, ô nhập chỉ đọc (người dùng phải dùng nút browse).
    parent : QWidget or None
        Widget cha.

    Returns
    -------
    tuple[QHBoxLayout, QLineEdit, QPushButton]
        Layout chứa cả hai widget, và tham chiếu trực tiếp đến LineEdit và Button.
    """
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
