# -*- coding: utf-8 -*-
"""
Trình quản lý Thống kê (Statistics Manager).
Tính toán tổng diện tích, số lượng thửa và tỷ lệ theo từng loại đất chạy trên QgsTask nền.
"""

import os
import json
from qgis.PyQt.QtCore import QVariant
from qgis.core import (
    QgsDistanceArea,
    QgsFeatureRequest,
    QgsGeometry,
    QgsProject,
    QgsTask,
    QgsVectorLayer,
)

class ComputeStatsTask(QgsTask):
    """
    QgsTask chạy ngầm tính toán thống kê để tránh đơ giao diện QGIS với lớp dữ liệu lớn.
    """
    def __init__(self, description: str, layer: QgsVectorLayer, code_field: str, area_field: str = None, callback=None):
        super().__init__(description, QgsTask.CanCancel)
        self.code_field = code_field
        self.area_field = area_field
        self.callback = callback
        self.exception = None
        self.stats_result = []

        # Sao chép các thuộc tính và hình học sang đối tượng thô để chạy thread nền an toàn
        self.features_data = []
        if layer:
            fields = layer.fields()

            def get_field_idx(f_name):
                if not f_name:
                    return -1
                idx = fields.indexOf(f_name)
                if not isinstance(idx, int) or idx == -1:
                    try:
                        idx = int(fields.indexFromName(f_name))
                    except (TypeError, ValueError, AttributeError):
                        idx = -1
                return idx if isinstance(idx, int) else -1

            code_idx = get_field_idx(code_field)
            area_idx = get_field_idx(area_field)

            # Lưu CRS của layer và Ellipsoid của Project
            self.crs = layer.crs()
            self.ellipsoid = QgsProject.instance().ellipsoid()
            self.transform_context = QgsProject.instance().transformContext()

            attribute_indexes = [index for index in (code_idx, area_idx) if index >= 0]
            request = QgsFeatureRequest().setSubsetOfAttributes(attribute_indexes)
            needs_geometry = area_idx == -1
            if not needs_geometry:
                request.setFlags(QgsFeatureRequest.NoGeometry)

            for feature in layer.getFeatures(request):
                # Lấy mã loại đất
                code = ""
                if code_idx != -1:
                    val = feature.attribute(code_idx)
                    if val is not None and val != QVariant():
                        code = str(val).strip().upper()
                
                # Lấy giá trị diện tích có sẵn nếu có
                area_val = None
                if area_idx != -1:
                    val = feature.attribute(area_idx)
                    if val is not None and val != QVariant():
                        try:
                            area_val = float(val)
                        except ValueError:
                            pass
                
                geom = QgsGeometry(feature.geometry()) if needs_geometry else None
                self.features_data.append((code, area_val, geom))

    def run(self) -> bool:
        try:
            # 1. Đọc danh mục mã loại đất
            land_use_codes = {}
            plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            json_path = os.path.join(plugin_dir, "data", "land_use_codes.json")
            if os.path.exists(json_path):
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        land_use_codes = json.load(f)
                except Exception:  # noqa: BLE001 — intentional suppress
                    pass

            # 2. Khởi tạo QgsDistanceArea
            da = QgsDistanceArea()
            da.setSourceCrs(self.crs, self.transform_context)
            if self.crs.isGeographic():
                da.setEllipsoid("WGS84")
            else:
                ellipsoid = self.ellipsoid
                if not ellipsoid or ellipsoid == "NONE":
                    ellipsoid = "WGS84"
                da.setEllipsoid(ellipsoid)

            stats_map = {}
            total_area_m2 = 0.0
            total_count = 0
            
            total_features = len(self.features_data)

            for idx, (code, area_val, geom) in enumerate(self.features_data):
                if self.isCanceled():
                    return False

                if not code:
                    code = "CHƯA XÁC ĐỊNH"

                # Tính diện tích
                area_m2 = 0.0
                if area_val is not None:
                    area_m2 = area_val
                elif geom and not geom.isEmpty():
                    area_m2 = da.measureArea(geom)

                if code not in stats_map:
                    name_vi = "Chưa xác định"
                    color = "#a1a1aa"
                    if code in land_use_codes:
                        name_vi = land_use_codes[code].get("name_vi", name_vi)
                        color = land_use_codes[code].get("fill_color", color)
                    elif code == "CHƯA XÁC ĐỊNH":
                        name_vi = "Chưa xác định / Trống"
                    
                    stats_map[code] = {
                        "code": code,
                        "name_vi": name_vi,
                        "color": color,
                        "count": 0,
                        "area_m2": 0.0
                    }
                
                stats_map[code]["count"] += 1
                stats_map[code]["area_m2"] += area_m2
                total_area_m2 += area_m2
                total_count += 1
                
                # Cập nhật tiến trình chạy (2% một lần để giảm quá tải giao diện)
                if idx % max(1, total_features // 50) == 0:
                    self.setProgress(int((idx / total_features) * 100))

            # 3. Tính tỷ lệ %
            result = []
            for code, data in stats_map.items():
                area_m2 = data["area_m2"]
                area_ha = area_m2 / 10000.0
                pct = (area_m2 / total_area_m2 * 100.0) if total_area_m2 > 0 else 0.0
                
                result.append({
                    "code": code,
                    "name_vi": data["name_vi"],
                    "color": data["color"],
                    "count": data["count"],
                    "area_m2": area_m2,
                    "area_ha": area_ha,
                    "percentage": pct
                })
                
            self.stats_result = result
            return True
        except Exception as e:  # noqa: BLE001 — intentional suppress
            self.exception = e
            return False

    def finished(self, result: bool):
        if self.callback:
            self.callback(result, self.stats_result, self.exception)
