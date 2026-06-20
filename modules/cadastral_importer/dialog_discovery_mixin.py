"""Mechanically extracted responsibilities from dialog_ui.py."""

import os
from qgis.PyQt.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from ..common.qt_compat import (
    NoEditTriggers,
    SelectRows,
    SizePolicyExpanding,
    SizePolicyFixed,
    FrameStyledPanel,
)
from modules.common.ui_utils import create_themed_button
from .dialog_styles import dialog_stylesheet
from .texts import cadastral_text as tx


class CadastralDiscoveryMixin:
    def update_discovery_card(self):
        if not self.owner.current_group:
            self.owner.lbl_discovery.setText("<i>Chưa chọn tệp tin hoặc thư mục nguồn.</i>")
            self.owner.zone_c.setCurrentWidget(self.owner.page_discovery)
            self.owner.zone_c.hide()
            return

        self.owner.zone_c.show()
        self.owner.zone_c.setCurrentWidget(self.owner.page_discovery)

        # Build HTML summary of discovered files
        html = f"<b>Bộ hồ sơ: {self.owner.current_group.display_name}</b><br/>"
        html += "<table width='100%' style='margin-top: 6px; border-collapse: collapse;'>"

        # Categorize: CAD, GTP, POL, SHP, XML
        categories = [
            ("Bản vẽ CAD", [".dwg", ".dgn", ".dxf"]),
            ("CSDL GTP", [".gtp"]),
            ("Tệp nhị phân POL", [".pol"]),
            ("Hình thể SHP", [".shp"]),
            ("Trao đổi XML", [".xml"])
        ]

        html += "<tr><th align='left' style='padding: 4px; border-bottom: 1px solid rgba(0,0,0,0.1);'>Loại tệp</th>"
        html += "<th align='left' style='padding: 4px; border-bottom: 1px solid rgba(0,0,0,0.1);'>Tên tệp</th>"
        html += "<th align='right' style='padding: 4px; border-bottom: 1px solid rgba(0,0,0,0.1);'>Trạng thái / Dung lượng</th></tr>"

        for label, exts in categories:
            found_ext = None
            for ext in exts:
                if self.owner.current_group.get(ext):
                    found_ext = ext
                    break

            if found_ext:
                path = self.owner.current_group.get(found_ext)
                fname = os.path.basename(path)
                size_str = "N/A"
                if os.path.exists(path):
                    size = os.path.getsize(path)
                    size_str = f"{size:,} byte" if size > 0 else "0 byte (Trống)"
                html += f"<tr><td style='padding: 4px; color: green;'><b>✅ {label} ({found_ext.upper()})</b></td>"
                html += f"<td style='padding: 4px;'>{fname}</td>"
                html += f"<td align='right' style='padding: 4px;'>{size_str}</td></tr>"
            else:
                html += f"<tr><td style='padding: 4px; color: gray;'>❌ {label}</td>"
                html += "<td style='padding: 4px; color: gray;'><i>Không phát hiện</i></td>"
                html += "<td align='right' style='padding: 4px; color: gray;'>-</td></tr>"

        html += "</table>"
        self.owner.lbl_discovery.setText(html)
