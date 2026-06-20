# -*- coding: utf-8 -*-
"""
Trình quản lý Nhãn (Label Manager).
Thực hiện cấu hình QgsPalLayerSettings và áp dụng gắn nhãn lên Layer bản đồ.
"""

from qgis.PyQt.QtGui import QColor, QFont
from qgis.core import (
    QgsPalLayerSettings,
    QgsVectorLayerSimpleLabeling,
    QgsTextFormat,
    QgsTextBufferSettings,
    QgsVectorLayer,
    QgsProject,
    QgsMapLayerType
)

def build_label_settings(config: dict) -> QgsPalLayerSettings:
    """
    Xây dựng cấu hình QgsPalLayerSettings từ cấu hình từ điển.
    - config: Chứa các thuộc tính font_family, font_size_pt, color, expression_template, scale_limit, v.v.
    """
    settings = QgsPalLayerSettings()
    
    # 1. Biểu thức gán nhãn
    expression = config.get("expression", "")
    settings.fieldName = expression
    settings.isExpression = True

    # 2. Định dạng chữ (QgsTextFormat)
    text_format = QgsTextFormat()
    
    font_family = config.get("font_family", "Arial")
    font = QFont(font_family)
    text_format.setFont(font)
    
    size_pt = float(config.get("font_size_pt", 9.0))
    text_format.setSize(size_pt)
    
    color_hex = config.get("color", "#000000")
    text_format.setColor(QColor(color_hex))

    # 3. Viền chữ (Buffer)
    if config.get("buffer_enabled", False):
        buffer_settings = QgsTextBufferSettings()
        buffer_settings.setEnabled(True)
        buffer_settings.setColor(QColor(config.get("buffer_color", "#FFFFFF")))
        buffer_settings.setSize(float(config.get("buffer_size", 1.0)))
        text_format.setBuffer(buffer_settings)

    settings.setFormat(text_format)

    # 4. Giới hạn tỷ lệ bản đồ (Scale limit)
    scale_limit = float(config.get("scale_limit", 2000))
    if scale_limit > 0:
        settings.scaleVisibility = True
        settings.minimumScale = scale_limit  # Trong QGIS, minimumScale tương ứng mẫu số lớn nhất (tức là khi thu nhỏ)
        settings.maximumScale = 0.0          # Không giới hạn khi phóng to
    else:
        settings.scaleVisibility = False

    # 5. Vị trí đặt nhãn (Placement)
    # Mặc định đặt nhãn ở trọng tâm đối tượng (Horizontal = 4)
    placement_mode = config.get("placement_mode", 4)
    if isinstance(placement_mode, int):
        try:
            from qgis.core import Qgis
            settings.placement = Qgis.LabelPlacement(placement_mode)
        except Exception:  # noqa: BLE001 — intentional suppress
            settings.placement = placement_mode
    else:
        settings.placement = placement_mode

    # 6. Tránh đè nhãn (Conflict Resolution / Obstacle)
    conflict_res = config.get("conflict_resolution", True)
    if hasattr(settings, 'obstacle'):
        settings.obstacle = conflict_res
    else:
        settings.obstacleSettings().setObstacle(conflict_res)

    return settings

def apply_to_layer(layer: QgsVectorLayer, config: dict) -> None:
    """
    Áp dụng cấu hình nhãn lên Layer vector.
    """
    if not layer or layer.type() != QgsMapLayerType.VectorLayer:
        return

    # Xây dựng settings từ config
    settings = build_label_settings(config)
    
    # Gán đối tượng nhãn cho layer
    labeling = QgsVectorLayerSimpleLabeling(settings)
    layer.setLabeling(labeling)
    layer.setLabelsEnabled(True)
    
    # Vẽ lại layer
    layer.triggerRepaint()

def disable_labels(layer: QgsVectorLayer) -> None:
    """
    Tắt hiển thị nhãn của Layer.
    """
    if not layer or layer.type() != QgsMapLayerType.VectorLayer:
        return

    layer.setLabelsEnabled(False)
    layer.triggerRepaint()
