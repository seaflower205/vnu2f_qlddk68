# -*- coding: utf-8 -*-
"""Theme detection and assembled Zinc dialog stylesheet."""

from qgis.PyQt.QtGui import QPalette
from qgis.PyQt.QtWidgets import QApplication
from .style_qss_base import QSS_BASE
from .style_qss_controls import QSS_CONTROLS
from .style_qss_navigation import QSS_NAVIGATION
from .style_tokens import DARK_TOKENS, LIGHT_TOKENS

_QSS_TEMPLATE = QSS_BASE + QSS_CONTROLS + QSS_NAVIGATION
_QSS_CACHE = {}

def is_dark_mode() -> bool:
    """Kiểm tra xem QGIS hiện tại có đang ở chế độ nền tối (Dark Mode) hay không."""
    palette = QApplication.palette()
    try:
        # PyQt6 / Qt6
        bg_color = palette.color(QPalette.ColorRole.Window)
    except AttributeError:
        # PyQt5 / Qt5
        bg_color = palette.color(QPalette.Window)
    # Độ sáng từ 0 đến 255. Nếu < 128 nghĩa là nền tối.
    return bg_color.value() < 128

def get_dialog_stylesheet() -> str:
    """Trả về chuỗi Qt Stylesheet (QSS) phù hợp với chế độ nền hiện tại."""
    dark = is_dark_mode()
    cache_key = "dark" if dark else "light"
    if cache_key in _QSS_CACHE:
        return _QSS_CACHE[cache_key]

    tokens = DARK_TOKENS.copy() if dark else LIGHT_TOKENS.copy()

    # Generate SVG files dynamically based on theme to avoid QSS data-uri rendering bugs in Qt on Windows
    import os
    plugin_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    resources_dir = os.path.join(plugin_dir, "resources")
    try:
        os.makedirs(resources_dir, exist_ok=True)
    except Exception:  # noqa: BLE001 — intentional suppress
        pass

    stroke_color = "#fafafa" if dark else "#18181b"
    stroke_disabled = "#71717a" if dark else "#a1a1aa"

    up_svg_path = os.path.join(resources_dir, "spin_up.svg")
    down_svg_path = os.path.join(resources_dir, "spin_down.svg")
    up_dis_svg_path = os.path.join(resources_dir, "spin_up_disabled.svg")
    down_dis_svg_path = os.path.join(resources_dir, "spin_down_disabled.svg")

    def write_svg(path, is_up, stroke):
        d = "M1 5L5 1L9 5" if is_up else "M1 1L5 5L9 1"
        content = f"""<svg xmlns="http://www.w3.org/2000/svg" width="10" height="6" viewBox="0 0 10 6">
  <path d="{d}" stroke="{stroke}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
</svg>"""
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception:  # noqa: BLE001 — intentional suppress
            pass

    write_svg(up_svg_path, True, stroke_color)
    write_svg(down_svg_path, False, stroke_color)
    write_svg(up_dis_svg_path, True, stroke_disabled)
    write_svg(down_dis_svg_path, False, stroke_disabled)

    tokens['up_arrow_url'] = up_svg_path.replace("\\", "/")
    tokens['down_arrow_url'] = down_svg_path.replace("\\", "/")
    tokens['up_arrow_disabled_url'] = up_dis_svg_path.replace("\\", "/")
    tokens['down_arrow_disabled_url'] = down_dis_svg_path.replace("\\", "/")

    stylesheet = _QSS_TEMPLATE.format(**tokens)
    _QSS_CACHE[cache_key] = stylesheet
    return stylesheet
