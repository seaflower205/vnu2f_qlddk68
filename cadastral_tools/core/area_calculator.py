# -*- coding: utf-8 -*-
"""
Trình tính toán Diện tích (Area Calculator).
Tính toán diện tích các thửa đất dựa trên hệ tọa độ CRS của Layer bằng QgsDistanceArea.
"""

from qgis.PyQt.QtCore import QVariant
from qgis.core import (
    QgsVectorLayer, QgsField, QgsDistanceArea, QgsProject, QgsUnitTypes, QgsMapLayerType
)

def recalculate_layer_area(
    layer: QgsVectorLayer, 
    field_name: str, 
    create_new: bool, 
    unit: str = "m2"
) -> int:
    """
    Tính lại diện tích của tất cả đối tượng trong Layer và ghi vào trường đã chọn.
    - layer: Layer vector polygon cần tính.
    - field_name: Tên trường cần ghi dữ liệu vào.
    - create_new: Nếu True, bỏ qua field_name và tạo trường mới DIENTICH.
    - unit: 'm2' hoặc 'ha'.
    Trả về số lượng đối tượng đã được cập nhật thành công.
    """
    if not layer or layer.type() != QgsMapLayerType.VectorLayer:
        return 0

    target_field_name = "DIENTICH" if create_new else field_name
    if not target_field_name:
        target_field_name = "DIENTICH"

    # 1. Đảm bảo trường tồn tại trong layer
    fields = layer.fields()
    field_idx = fields.indexOf(target_field_name)

    if field_idx == -1:
        # Tạo trường mới kiểu số thực (Double)
        new_field = QgsField(target_field_name, QVariant.Double, "Double", 12, 3)
        layer.startEditing()
        layer.addAttribute(new_field)
        layer.commitChanges()
        # Lấy lại index mới sau khi thêm trường
        fields = layer.fields()
        field_idx = fields.indexOf(target_field_name)

    if field_idx == -1:
        return 0

    # 2. Khởi tạo QgsDistanceArea
    da = QgsDistanceArea()
    da.setSourceCrs(layer.crs(), QgsProject.instance().transformContext())
    
    if layer.crs().isGeographic():
        da.setEllipsoid("WGS84")
    else:
        ellipsoid = QgsProject.instance().ellipsoid()
        if not ellipsoid or ellipsoid == "NONE":
            ellipsoid = "WGS84"
        da.setEllipsoid(ellipsoid)

    # 3. Duyệt đối tượng và cập nhật diện tích
    layer.startEditing()
    updated_count = 0
    
    for feature in layer.getFeatures():
        geom = feature.geometry()
        if geom.isEmpty():
            continue

        # Tính diện tích (trả về m²)
        area_m2 = da.measureArea(geom)
        
        # Quy đổi đơn vị
        final_area = area_m2 / 10000.0 if unit == "ha" else area_m2

        # Thay đổi giá trị thuộc tính
        layer.changeAttributeValue(feature.id(), field_idx, final_area)
        updated_count += 1

    # Lưu thay đổi
    layer.commitChanges()
    return updated_count
