# -*- coding: utf-8 -*-
"""
Trình hỗ trợ Hệ tọa độ (CRS Helper).
Kiểm tra CRS hợp lệ cho địa chính Việt Nam và thực hiện chuyển đổi chiếu lại.
"""

from qgis.core import (
    QgsVectorLayer, QgsCoordinateTransform, QgsCoordinateReferenceSystem, 
    QgsProject, QgsMessageLog, Qgis, QgsMapLayerType
)

def check_crs_is_valid(crs: QgsCoordinateReferenceSystem) -> bool:
    """
    Kiểm tra hệ tọa độ có nằm trong các mã được chấp nhận của địa chính Việt Nam.
    Chấp nhận: EPSG 4756 (VN-2000), 3405-3408, 9210-9213, 32648, 32649.
    """
    if not crs or not crs.isValid():
        return False
        
    auth_id = crs.authid()
    if not auth_id.startswith("EPSG:"):
        return False
        
    try:
        code = int(auth_id.split(":")[1])
        valid_codes = [4756, 3405, 3406, 3407, 3408, 9210, 9211, 9212, 9213, 32648, 32649]
        return code in valid_codes
    except (ValueError, IndexError):
        return False

def reproject_layer_in_place(layer: QgsVectorLayer, target_crs: QgsCoordinateReferenceSystem) -> bool:
    """
    Chuyển đổi hệ tọa độ của Layer đang có trực tiếp (in-place) với khả năng rollback.
    """
    if not layer or layer.type() != QgsMapLayerType.VectorLayer:
        return False

    source_crs = layer.crs()
    if source_crs == target_crs:
        return True

    # Tạo phép chuyển đổi
    transform = QgsCoordinateTransform(source_crs, target_crs, QgsProject.instance())

    # Khởi động chế độ chỉnh sửa của Layer
    layer.startEditing()
    try:
        for feature in layer.getFeatures():
            geom = feature.geometry()
            if geom.isEmpty():
                continue
            
            # Chuyển đổi tọa độ hình học
            geom.transform(transform)
            # Cập nhật hình học mới
            layer.changeGeometry(feature.id(), geom)

        # Cập nhật lại CRS hiển thị của Layer
        layer.setCrs(target_crs)
        layer.commitChanges()
        layer.triggerRepaint()
        return True
    except Exception as e:
        layer.rollBack()
        QgsMessageLog.logMessage(f"Lỗi khi chiếu lại layer trực tiếp: {str(e)}", "CadastralTools", Qgis.Critical)
        raise e

def reproject_layer_to_new(layer: QgsVectorLayer, target_crs: QgsCoordinateReferenceSystem) -> QgsVectorLayer:
    """
    Chiếu lại Layer sang một Layer mới (memory layer) và thêm vào bản đồ.
    """
    if not layer or layer.type() != QgsMapLayerType.VectorLayer:
        return None

    import processing
    try:
        params = {
            'INPUT': layer,
            'TARGET_CRS': target_crs,
            'OUTPUT': 'memory:'
        }
        # Chạy thuật toán reproject của QGIS Processing
        res = processing.run("native:reprojectlayer", params)
        new_layer = res['OUTPUT']
        
        if new_layer and new_layer.isValid():
            new_layer.setName(f"{layer.name()}_VN2000")
            QgsProject.instance().addMapLayer(new_layer)
            return new_layer
    except Exception as e:
        QgsMessageLog.logMessage(f"Lỗi khi chiếu lại sang layer mới qua Processing: {str(e)}", "CadastralTools", Qgis.Critical)
        
    return None
