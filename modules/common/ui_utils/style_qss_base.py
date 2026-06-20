# -*- coding: utf-8 -*-
"""Base Zinc QSS fragment."""

QSS_BASE = """
QDialog {{
    background-color: {bg_primary};
    color: {text_primary};
    font-family: 'Segoe UI', 'Inter', 'Roboto', 'Helvetica Neue', sans-serif;
    font-size: 12px;
}}
QGroupBox {{
    font-weight: 600;
    font-size: 13px;
    border: 1px solid {border_color};
    border-radius: 8px;
    margin-top: 16px;
    padding-top: 24px;
    padding-left: 16px;
    padding-right: 16px;
    padding-bottom: 16px;
    background-color: {bg_surface};
    color: {text_primary};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 16px;
    top: 6px;
    padding: 0px 4px;
    color: {text_primary};
    background-color: transparent;
}}
QLabel {{
    color: {text_primary};
    font-size: 12px;
}}
QLineEdit {{
    padding: 6px 12px;
    border: 1px solid {border_color};
    border-radius: 6px;
    background-color: {bg_input};
    color: {text_highlight};
    selection-background-color: {selection_bg};
    selection-color: {selection_text};
    min-height: 24px;
}}
QTextEdit, QPlainTextEdit {{
    padding: 6px 12px;
    border: 1px solid {border_color};
    border-radius: 6px;
    background-color: {bg_input};
    color: {text_highlight};
    selection-background-color: {selection_bg};
    selection-color: {selection_text};
    min-height: 80px;
}}
QSpinBox, QDoubleSpinBox {{
    border: 1px solid {border_color};
    border-radius: 6px;
    background-color: {bg_input};
    color: {text_highlight};
    min-height: 36px;
    padding-left: 12px;
    padding-right: 20px;
}}
QSpinBox QLineEdit, QDoubleSpinBox QLineEdit {{
    padding: 0px;
    background-color: transparent;
    border: none;
    color: {text_highlight};
    selection-background-color: {selection_bg};
    selection-color: {selection_text};
}}
QLineEdit::placeholder, QTextEdit::placeholder, QPlainTextEdit::placeholder, QComboBox::placeholder {{
    color: {text_secondary};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {accent};
}}
QDialog QSpinBox:focus, QDialog QDoubleSpinBox:focus {{
    border: 1px solid {accent};
}}
QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
    background-color: {bg_input_disabled};
    color: {text_disabled};
    border: 1px solid {border_disabled};
}}
/* Padding is handled directly on QSpinBox/QDoubleSpinBox */
QDialog QSpinBox::up-button, QDialog QDoubleSpinBox::up-button {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 18px;
    border-left: 1px solid {border_color};
    background-color: transparent;
    border-top-right-radius: 5px;
}}
QDialog QSpinBox::up-button:hover, QDialog QDoubleSpinBox::up-button:hover {{
    background-color: {btn_secondary_hover};
}}
QDialog QSpinBox::up-arrow, QDialog QDoubleSpinBox::up-arrow {{
    image: url("{up_arrow_url}");
    width: 10px;
    height: 6px;
}}
QDialog QSpinBox::up-arrow:disabled, QDialog QDoubleSpinBox::up-arrow:disabled {{
    image: url("{up_arrow_disabled_url}");
}}
QDialog QSpinBox::down-button, QDialog QDoubleSpinBox::down-button {{
    subcontrol-origin: padding;
    subcontrol-position: bottom right;
    width: 18px;
    border-left: 1px solid {border_color};
    border-top: 1px solid {border_color};
    background-color: transparent;
    border-bottom-right-radius: 5px;
}}
QDialog QSpinBox::down-button:hover, QDialog QDoubleSpinBox::down-button:hover {{
    background-color: {btn_secondary_hover};
}}
QDialog QSpinBox::down-arrow, QDialog QDoubleSpinBox::down-arrow {{
    image: url("{down_arrow_url}");
    width: 10px;
    height: 6px;
}}
QDialog QSpinBox::down-arrow:disabled, QDialog QDoubleSpinBox::down-arrow:disabled {{
    image: url("{down_arrow_disabled_url}");
}}
QComboBox {{
    padding: 6px 12px;
    border: 1px solid {border_color};
    border-radius: 6px;
    background-color: {bg_input};
    color: {text_highlight};
    min-height: 24px;
"""
