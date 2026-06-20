# -*- coding: utf-8 -*-
"""Helper class for loading default symbology configurations."""

import json
import os
from qgis.core import Qgis

class ConfigLoader:
    @staticmethod
    def load_defaults(plugin_dir: str, iface=None) -> list[dict]:
        """Tải cấu hình bảng mặc định từ file land_use_codes.json."""
        json_path = os.path.join(plugin_dir, "data", "land_use_codes.json")
        if not os.path.exists(json_path):
            if iface:
                iface.messageBar().pushMessage(
                    "Lỗi", "Không tìm thấy file mẫu cấu hình mặc định land_use_codes.json",
                    level=Qgis.Critical, duration=5
                )
            return []

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                codes_dict = json.load(f)
            
            # Chuyển đổi sang list[dict]
            configs = []
            for code, data in codes_dict.items():
                cfg = data.copy()
                cfg["code"] = code
                configs.append(cfg)
            return configs
        except Exception as e:
            if iface:
                iface.messageBar().pushMessage(
                    "Lỗi", f"Không thể đọc cấu hình mặc định: {str(e)}",
                    level=Qgis.Critical, duration=5
                )
            return []

    @staticmethod
    def get_land_use_codes_dict(plugin_dir: str) -> dict:
        """Tải bộ từ điển land_use_codes mặc định để map nếu có"""
        json_path = os.path.join(plugin_dir, "data", "land_use_codes.json")
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
