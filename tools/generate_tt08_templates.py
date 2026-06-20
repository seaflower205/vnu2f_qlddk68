# -*- coding: utf-8 -*-
"""Reproducibly build the four TT08 print-layout templates with QGIS API."""

from __future__ import annotations

import os
import sys

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor, QFont
from qgis.PyQt.QtXml import QDomDocument
from qgis.core import (
    QgsApplication,
    QgsFillSymbol,
    QgsLayoutItemLabel,
    QgsLayoutItemLegend,
    QgsLayoutItemMap,
    QgsLayoutItemMapGrid,
    QgsLayoutItemPicture,
    QgsLayoutItemScaleBar,
    QgsLayoutItemShape,
    QgsLayoutPoint,
    QgsLayoutSize,
    QgsPrintLayout,
    QgsProject,
    QgsReadWriteContext,
    QgsUnitTypes,
)


MM = QgsUnitTypes.LayoutMillimeters
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(ROOT, "templates")
PROFILES = {
    "commune": ("TT08_HTSDD_commune.qpt", "CẤP XÃ", 2),
    "district": ("TT08_HTSDD_district.qpt", "CẤP HUYỆN", 3),
    "province": ("TT08_HTSDD_province.qpt", "CẤP TỈNH", 3),
    "region_country": ("TT08_HTSDD_region_country.qpt", "VÙNG KINH TẾ - XÃ HỘI VÀ CẢ NƯỚC", 5),
}


def add_label(layout, item_id, text, x, y, width, height, size=9, bold=False, centered=False):
    label = QgsLayoutItemLabel(layout)
    label.setId(item_id)
    label.setText(text)
    text_format = label.textFormat()
    text_format.setFont(QFont("Times New Roman", size, QFont.Weight.Bold if bold else QFont.Weight.Normal))
    text_format.setSize(size)
    text_format.setSizeUnit(QgsUnitTypes.RenderPoints)
    label.setTextFormat(text_format)
    if centered:
        label.setHAlign(Qt.AlignmentFlag.AlignHCenter)
        label.setVAlign(Qt.AlignmentFlag.AlignVCenter)
    layout.addLayoutItem(label)
    label.attemptMove(QgsLayoutPoint(x, y, MM), False)
    label.attemptResize(QgsLayoutSize(width, height, MM))
    return label


def add_rect(layout, item_id, x, y, width, height, outline="#18181b", line_width=0.25):
    shape = QgsLayoutItemShape(layout)
    shape.setId(item_id)
    shape.setShapeType(QgsLayoutItemShape.Shape.Rectangle)
    shape.setSymbol(QgsFillSymbol.createSimple({
        "color": "255,255,255,0",
        "outline_color": outline,
        "outline_width": str(line_width),
    }))
    layout.addLayoutItem(shape)
    shape.attemptMove(QgsLayoutPoint(x, y, MM), False)
    shape.attemptResize(QgsLayoutSize(width, height, MM))
    return shape


def add_signature_block(layout, level_label):
    x, y, width, height = 884, 666, 269, 150
    add_rect(layout, "SignatureBlock", x, y, width, height, line_width=0.55)
    add_rect(layout, "SignatureLeft", x, y + 30, width / 2, height - 30, line_width=0.3)
    add_rect(layout, "SignatureRight", x + width / 2, y + 30, width / 2, height - 30, line_width=0.3)
    add_label(layout, "SignatureTitle", "KÝ XÁC NHẬN BẢN ĐỒ", x, y + 2, width, 24, 13, True, True)
    add_label(layout, "SignatureAuthority", "CƠ QUAN CÓ CHỨC NĂNG\nQUẢN LÝ ĐẤT ĐAI", x + 4, y + 34, width / 2 - 8, 32, 10, True, True)
    add_label(layout, "SignatureCommittee", f"UBND {level_label}", x + width / 2 + 4, y + 34, width / 2 - 8, 32, 11, True, True)
    add_label(layout, "SignatureDateLeft", "Ngày ..... tháng ..... năm .....\nKý, ghi rõ họ và tên", x + 4, y + 69, width / 2 - 8, 34, 9, False, True)
    add_label(layout, "SignatureDateRight", "Ngày ..... tháng ..... năm .....\nKý, ghi rõ họ và tên, đóng dấu", x + width / 2 + 4, y + 69, width / 2 - 8, 34, 9, False, True)


def build_template(project, key, filename, level_label, frame_count):
    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    layout.setName(f"TT08_{key}")
    layout.pageCollection().page(0).setPageSize(QgsLayoutSize(1189, 841, MM))

    for index in range(frame_count):
        offset = 12 + index * 2.4
        add_rect(
            layout,
            f"TT08_Frame_{index + 1}",
            offset,
            offset,
            1189 - 2 * offset,
            841 - 2 * offset,
            line_width=1.0 if index == 0 else 0.45,
        )

    add_label(layout, "Tên bản đồ", "BẢN ĐỒ HIỆN TRẠNG SỬ DỤNG ĐẤT", 95, 13, 999, 34, 36, True, True)
    add_label(layout, "Khu vực bản đồ", level_label, 95, 49, 999, 18, 20, True, True)

    main_map = QgsLayoutItemMap(layout)
    main_map.setId("Map")
    layout.addLayoutItem(main_map)
    main_map.attemptMove(QgsLayoutPoint(28, 74, MM), False)
    main_map.attemptResize(QgsLayoutSize(1133, 568, MM))
    main_map.setFrameEnabled(True)

    grid = QgsLayoutItemMapGrid("Lưới tọa độ", main_map)
    grid.setEnabled(True)
    grid.setIntervalX(1000)
    grid.setIntervalY(1000)
    grid.setAnnotationEnabled(True)
    grid.setAnnotationPrecision(0)
    main_map.grids().addItem(grid)
    main_map.update()

    inset = QgsLayoutItemMap(layout)
    inset.setId("InsetMap")
    layout.addLayoutItem(inset)
    inset.attemptMove(QgsLayoutPoint(48, 105, MM), False)
    inset.attemptResize(QgsLayoutSize(240, 170, MM))
    inset.setFrameEnabled(True)
    inset_title = add_label(layout, "InsetTitle", "SƠ ĐỒ VỊ TRÍ", 48, 105, 240, 18, 13, True, True)
    inset_title.setBackgroundEnabled(True)
    inset_title.setBackgroundColor(QColor("white"))

    add_rect(layout, "LegendBlock", 244, 666, 255, 150, line_width=0.55)
    add_rect(layout, "ChartBlock", 510, 666, 360, 150, line_width=0.55)

    legend = QgsLayoutItemLegend(layout)
    legend.setId("Chú dẫn")
    legend.setTitle("CHÚ DẪN")
    legend.setLinkedMap(main_map)
    layout.addLayoutItem(legend)
    legend.attemptMove(QgsLayoutPoint(252, 674, MM), False)
    legend.attemptResize(QgsLayoutSize(239, 134, MM))

    scale = QgsLayoutItemScaleBar(layout)
    scale.setId("Scale mét")
    scale.setLinkedMap(main_map)
    scale.setStyle("Double Box")
    scale.setNumberOfSegments(3)
    scale.setNumberOfSegmentsLeft(0)
    scale.setUnits(QgsUnitTypes.DistanceKilometers)
    scale.setUnitLabel("km")
    scale.applyDefaultSize()
    layout.addLayoutItem(scale)
    scale.attemptMove(QgsLayoutPoint(500, 646, MM), False)

    north = QgsLayoutItemPicture(layout)
    north.setId("NorthArrow")
    north.setPicturePath(os.path.join(TEMPLATE_DIR, "north_arrow_tt08.svg"))
    layout.addLayoutItem(north)
    north.attemptMove(QgsLayoutPoint(1076, 90, MM), False)
    north.attemptResize(QgsLayoutSize(48, 122, MM))

    add_rect(layout, "SourceBlock", 28, 666, 200, 150, line_width=0.55)
    add_label(layout, "Viện dẫn", "NGUỒN TÀI LIỆU", 34, 672, 188, 18, 12, True, True)
    add_label(layout, "Dữ liệu bản đồ", "Dữ liệu xây dựng bản đồ:\n................................................", 38, 697, 180, 42, 10)
    add_label(layout, "Tên đv xd bản đồ", "ĐƠN VỊ XÂY DỰNG BẢN ĐỒ", 38, 746, 180, 18, 11, True, True)
    add_label(layout, "Người lập", "Người lập:", 38, 771, 180, 14, 9)
    add_label(layout, "Ngày lập", "Ngày lập:", 38, 790, 180, 14, 9)
    add_label(layout, "LegalMetadata", "TT08/2024 + TT23/2025", 510, 806, 360, 10, 8, False, True)
    add_signature_block(layout, level_label)

    path = os.path.join(TEMPLATE_DIR, filename)
    if not layout.saveAsTemplate(path, QgsReadWriteContext()):
        raise RuntimeError(f"Không thể ghi {path}")
    return path


def upgrade_generic_template(project):
    path = os.path.join(TEMPLATE_DIR, "Khung LVT2601_print_27Apr2026_VN.qpt")
    document = QDomDocument()
    with open(path, "r", encoding="utf-8") as stream:
        ok, message, line, _ = document.setContent(stream.read())
    if not ok:
        raise RuntimeError(f"QPT chung lỗi dòng {line}: {message}")
    layout = QgsPrintLayout(project)
    _, loaded = layout.loadFromTemplate(document, QgsReadWriteContext())
    if not loaded:
        raise RuntimeError("Không thể nạp QPT chung")
    if layout.itemById("InsetMap") is None:
        add_label(layout, "InsetTitle", "SƠ ĐỒ VỊ TRÍ", 143, 22, 56, 6, 7, True, True)
        inset = QgsLayoutItemMap(layout)
        inset.setId("InsetMap")
        layout.addLayoutItem(inset)
        inset.attemptMove(QgsLayoutPoint(143, 29, MM), False)
        inset.attemptResize(QgsLayoutSize(56, 42, MM))
        inset.setFrameEnabled(True)
    if layout.itemById("LegalMetadata") is None:
        add_label(layout, "LegalMetadata", "", 7, 277, 125, 5, 5)
    if not layout.saveAsTemplate(path, QgsReadWriteContext()):
        raise RuntimeError("Không thể cập nhật QPT chung")
    return path


def main():
    app = QgsApplication([arg.encode("utf-8") for arg in sys.argv], False)
    app.initQgis()
    try:
        project = QgsProject.instance()
        for key, (filename, label, frames) in PROFILES.items():
            print(build_template(project, key, filename, label, frames))
        print(upgrade_generic_template(project))
    finally:
        app.exitQgis()


if __name__ == "__main__":
    main()
