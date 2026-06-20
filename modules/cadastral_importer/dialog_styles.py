"""Zinc stylesheet fragment for the cadastral import dialog."""

from modules.common.ui_utils import is_dark_mode


def dialog_stylesheet() -> str:
    if is_dark_mode():
        muted, title, surface, border = "#a1a1aa", "#fafafa", "#18181b", "#27272a"
    else:
        muted, title, surface, border = "#71717a", "#09090b", "#ffffff", "#e4e4e7"
    return f"""
    QDialog#cadastralImportDialog QLabel#dialogTitle {{
        color: {title}; font-size: 18px; font-weight: 600;
    }}
    QDialog#cadastralImportDialog QLabel#dialogSubtitle {{
        color: {muted}; font-size: 12px;
    }}
    QDialog#cadastralImportDialog QLabel#sectionLabel {{
        color: {muted}; font-size: 12px; font-weight: 600; padding-left: 2px;
    }}
    QDialog#cadastralImportDialog QGroupBox {{
        background-color: {surface}; border: 1px solid {border};
    }}
    QDialog#cadastralImportDialog QTextEdit#processingLog {{ min-height: 60px; }}
    """
