# -*- coding: utf-8 -*-
"""Control Zinc QSS fragment."""

QSS_CONTROLS = """
    combobox-popup: 0;
}}
QComboBox:focus {{
    border: 1px solid {accent};
}}
QComboBox QLineEdit {{
    color: {text_highlight};
    background-color: transparent;
    border: none;
    padding: 0px;
}}
QComboBox QLineEdit:disabled {{
    color: {text_disabled};
}}
QComboBox QAbstractItemView {{
    background-color: {bg_input};
    color: {text_primary};
    selection-background-color: {combo_popup_selected_bg};
    selection-color: {combo_popup_selected_text};
    border: 1px solid {border_color};
    border-radius: 6px;
    outline: 0px;
}}
QComboBox QAbstractItemView::item, QListView::item {{
    padding: 6px 10px;
    font-size: 12px;
}}
QComboBox QAbstractItemView::item:hover, QListView::item:hover {{
    background-color: {combo_popup_selected_bg};
    color: {combo_popup_selected_text};
}}
QPushButton {{
    padding: 6px 14px;
    border: 1px solid {btn_secondary_border};
    border-radius: 6px;
    background-color: {btn_secondary_bg};
    color: {btn_secondary_text};
    font-weight: 500;
    font-size: 12px;
    outline: none;
}}
QPushButton#btn_browse {{
    padding: 0px;
    font-size: 14px;
    font-weight: bold;
    background-color: {btn_secondary_bg};
    border: 1px solid {btn_secondary_border};
    border-radius: 6px;
}}
QPushButton:hover {{
    background-color: {btn_secondary_hover};
    border-color: {border_color};
}}
QPushButton:pressed {{
    background-color: {btn_secondary_pressed};
}}
QPushButton:disabled {{
    background-color: {bg_input_disabled};
    color: {text_disabled};
    border: 1px solid {border_disabled};
}}
QPushButton#btn_primary, QPushButton[theme="primary"], QPushButton#primaryAction, QPushButton#fontConvertPrimary {{
    background-color: {btn_primary_bg};
    color: {btn_primary_text};
    border: 1px solid {btn_primary_bg};
    font-weight: 600;
}}
QPushButton#btn_primary:hover, QPushButton[theme="primary"]:hover, QPushButton#primaryAction:hover, QPushButton#fontConvertPrimary:hover {{
    background-color: {btn_primary_hover};
    border-color: {btn_primary_hover};
}}
QPushButton#btn_primary:pressed, QPushButton[theme="primary"]:pressed, QPushButton#primaryAction:pressed, QPushButton#fontConvertPrimary:pressed {{
    background-color: {btn_primary_pressed};
    border-color: {btn_primary_pressed};
}}
QPushButton#btn_primary:disabled, QPushButton[theme="primary"]:disabled, QPushButton#primaryAction:disabled, QPushButton#fontConvertPrimary:disabled {{
    background-color: {bg_input_disabled};
    color: {text_disabled};
    border: 1px solid {border_disabled};
}}
QPushButton#btn_success, QPushButton[theme="success"] {{
    background-color: {btn_success_bg};
    color: {btn_success_text};
    border: 1px solid {btn_success_bg};
    font-weight: 600;
}}
QPushButton#btn_success:hover, QPushButton[theme="success"]:hover {{
    background-color: {btn_success_hover};
    border-color: {btn_success_hover};
}}
QPushButton#btn_success:pressed, QPushButton[theme="success"]:pressed {{
    background-color: {btn_success_pressed};
    border-color: {btn_success_pressed};
}}
QPushButton#btn_success:disabled, QPushButton[theme="success"]:disabled {{
    background-color: {bg_input_disabled};
    color: {text_disabled};
    border: 1px solid {border_disabled};
}}
QPushButton#btn_danger, QPushButton[theme="danger"] {{
    background-color: {btn_danger_bg};
    color: {btn_danger_text};
    border: 1px solid {btn_danger_bg};
    font-weight: 600;
}}
QPushButton#btn_danger:hover, QPushButton[theme="danger"]:hover {{
    background-color: {btn_danger_hover};
    border-color: {btn_danger_hover};
}}
QPushButton#btn_danger:pressed, QPushButton[theme="danger"]:pressed {{
    background-color: {btn_danger_pressed};
    border-color: {btn_danger_pressed};
}}
QPushButton#btn_danger:disabled, QPushButton[theme="danger"]:disabled {{
    background-color: {bg_input_disabled};
    color: {text_disabled};
    border: 1px solid {border_disabled};
}}
QTableWidget, QTableView {{
    background-color: {bg_surface};
    color: {text_primary};
    gridline-color: {table_grid};
    border: 1px solid {border_color};
    border-radius: 6px;
    outline: none;
}}
QHeaderView::section {{
    background-color: {bg_surface};
    color: {text_secondary};
    padding: 8px;
"""

