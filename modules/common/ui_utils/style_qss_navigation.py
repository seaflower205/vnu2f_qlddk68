# -*- coding: utf-8 -*-
"""Navigation and feedback Zinc QSS fragment."""

QSS_NAVIGATION = """
    border: none;
    border-bottom: 1px solid {border_color};
    font-weight: 600;
}}
QHeaderView::section:horizontal {{
    border-right: 1px solid {table_grid};
}}
QTabWidget::pane {{
    border: 1px solid {border_color};
    background-color: {bg_surface};
    border-radius: 8px;
    top: -1px;
}}
QTabBar::tab {{
    background-color: {bg_input_disabled};
    color: {text_secondary};
    border: 1px solid {border_color};
    padding: 6px 16px;
    border-radius: 6px;
    min-width: 90px;
    font-weight: 500;
    margin-right: 4px;
}}
QTabBar::tab:selected {{
    background-color: {btn_primary_bg};
    color: {btn_primary_text};
    border: 1px solid {btn_primary_bg};
    font-weight: 600;
}}
QTabBar::tab:hover:!selected {{
    background-color: {btn_secondary_hover};
    color: {text_primary};
}}
QProgressBar {{
    border: 1px solid {border_color};
    border-radius: 6px;
    text-align: center;
    background-color: {bg_input_disabled};
    color: {text_primary};
    font-weight: 600;
    height: 18px;
}}
QProgressBar::chunk {{
    background-color: {accent};
    border-radius: 5px;
}}
QCheckBox, QRadioButton {{
    color: {text_primary};
    spacing: 8px;
}}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {border_color};
    border-radius: 3px;
    background-color: {bg_input};
}}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
    border-color: {accent};
}}
QCheckBox::indicator:checked {{
    background-color: {checkbox_checked_bg};
    border-color: {checkbox_checked_border};
    image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='{checkbox_check_color}' stroke-width='4' stroke-linecap='round' stroke-linejoin='round'><polyline points='20 6 9 17 4 12'></polyline></svg>");
}}
QRadioButton::indicator {{
    border-radius: 8px;
}}
QRadioButton::indicator:checked {{
    background-color: {bg_input};
    border-color: {checkbox_checked_border};
    image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><circle cx='12' cy='12' r='5' fill='{checkbox_checked_bg}'/></svg>");
}}
QScrollBar:vertical {{
    border: none;
    background: {scrollbar_bg};
    width: 12px;
    margin: 0px;
    border-radius: 6px;
}}
QScrollBar::handle:vertical {{
    background: {scrollbar_handle};
    min-height: 24px;
    border-radius: 6px;
}}
QScrollBar::handle:vertical:hover {{
    background: {scrollbar_handle_hover};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QStatusBar {{
    background-color: {bg_primary};
    color: {text_secondary};
    border-top: 1px solid {border_color};
    font-size: 11px;
}}
QListWidget#sidebar {{
    background-color: {bg_sidebar};
    border: none;
    border-right: 1px solid {border_color};
    border-radius: 0px;
    padding: 16px 8px;
    outline: none;
}}
QListWidget#sidebar QScrollBar:horizontal {{
    height: 0px;
    background: transparent;
}}
QListWidget#sidebar::item {{
    padding: 8px 12px;
    border-radius: 6px;
    color: {text_primary};
    font-weight: 500;
    margin-bottom: 4px;
}}
QListWidget#sidebar::item:hover {{
    background-color: {btn_secondary_hover};
    color: {text_primary};
}}
QListWidget#sidebar::item:selected {{
    background-color: {sidebar_selected_bg};
    color: {sidebar_selected_text};
    font-weight: 600;
}}
"""

