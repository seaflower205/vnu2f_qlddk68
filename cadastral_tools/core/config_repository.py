# -*- coding: utf-8 -*-
"""
Kho l╞░u trß╗» cß║Ñu h├¼nh (Repository Pattern) cho Plugin.
Xß╗¡ l├╜ tß║¡p trung c├íc thao t├íc ─æß╗ìc/ghi file JSON vß╗¢i c╞í chß║┐ Cache tr├¬n RAM (Defensive Programming).
"""

import os
import json
import traceback
from qgis.core import QgsMessageLog, Qgis

class ConfigRepository:
    _plugin_dir = None
    _cache = {}

    @classmethod
    def set_plugin_dir(cls, dir_path: str):
        """Khß╗ƒi tß║ío ─æ╞░ß╗¥ng dß║½n plugin v├á x├│a cache c┼⌐ ─æß╗â ph├▓ng r├▓ rß╗ë (Memory/Stale Cache Leak)."""
        cls._plugin_dir = dir_path
        cls.clear_cache()  # Lß╗¢p ph├▓ng thß╗º: lu├┤n reset khi dir thay ─æß╗òi

    @classmethod
    def clear_cache(cls):
        """X├│a to├án bß╗Ö cache tr├¬n RAM."""
        cls._cache.clear()

    @classmethod
    def get_config(cls, config_name: str, default=None):
        """
        ─Éß╗ìc v├á cache file cß║Ñu h├¼nh JSON tß╗½ th╞░ mß╗Ñc data.
        
        Parameters
        ----------
        config_name : str
            T├¬n file (kh├┤ng c├│ ─æu├┤i .json), v├¡ dß╗Ñ: 'land_use_codes'.
        default : any, optional
            Gi├í trß╗ï trß║ú vß╗ü nß║┐u lß╗ùi (VD: [] cho List, {} cho Dict).
        """
        if cls._plugin_dir is None:
            QgsMessageLog.logMessage(
                "ConfigRepository ch╞░a ─æ╞░ß╗úc khß╗ƒi tß║ío! Gß╗ìi get_config tr╞░ß╗¢c set_plugin_dir.", 
                "VNU2F", 
                level=Qgis.Critical
            )
            return default

        # 1. Trß║ú vß╗ü Cache nß║┐u c├│
        if config_name in cls._cache:
            return cls._cache[config_name]

        # 2. ─Éß╗ìc ß╗ò cß╗⌐ng
        json_path = os.path.join(cls._plugin_dir, "data", f"{config_name}.json")
        if not os.path.exists(json_path):
            return default

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                cls._cache[config_name] = data
                return data
        except json.JSONDecodeError as e:
            QgsMessageLog.logMessage(
                f"Lß╗ùi c├║ ph├íp JSON khi ─æß╗ìc '{config_name}.json': {str(e)}", 
                "VNU2F", 
                level=Qgis.Critical
            )
            return default
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Lß╗ùi kh├┤ng x├íc ─æß╗ïnh khi ─æß╗ìc '{config_name}.json': {str(e)}\n{traceback.format_exc()}", 
                "VNU2F", 
                level=Qgis.Warning
            )
            return default

    @classmethod
    def save_config(cls, config_name: str, data) -> bool:
        """
        Ghi file cß║Ñu h├¼nh JSON v├á cß║¡p nhß║¡t lß║íi cache.
        
        Parameters
        ----------
        config_name : str
            T├¬n file (kh├┤ng c├│ ─æu├┤i .json).
        data : list or dict
            Dß╗» liß╗çu cß║ºn l╞░u.
        """
        if cls._plugin_dir is None:
            QgsMessageLog.logMessage(
                "ConfigRepository ch╞░a ─æ╞░ß╗úc khß╗ƒi tß║ío! Gß╗ìi save_config tr╞░ß╗¢c set_plugin_dir.", 
                "VNU2F", 
                level=Qgis.Critical
            )
            return False

        json_path = os.path.join(cls._plugin_dir, "data", f"{config_name}.json")
        
        # ─Éß║úm bß║úo th╞░ mß╗Ñc data tß╗ôn tß║íi
        os.makedirs(os.path.dirname(json_path), exist_ok=True)

        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            # Ghi ─æ├¿ cache ngay sau khi l╞░u ─æ─⌐a th├ánh c├┤ng
            cls._cache[config_name] = data
            return True
        except PermissionError as e:
            QgsMessageLog.logMessage(
                f"Lß╗ùi quyß╗ün truy cß║¡p khi ghi '{config_name}.json'. Dß╗» liß╗çu CH╞»A ─É╞»ß╗óC L╞»U: {str(e)}", 
                "VNU2F", 
                level=Qgis.Critical
            )
            return False
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Lß╗ùi kh├┤ng x├íc ─æß╗ïnh khi ghi '{config_name}.json'. Dß╗» liß╗çu CH╞»A ─É╞»ß╗óC L╞»U: {str(e)}\n{traceback.format_exc()}", 
                "VNU2F", 
                level=Qgis.Critical
            )
            return False

# -*- coding: utf-8 -*-
"""
Kho l╞░u trß╗» cß║Ñu h├¼nh (Repository Pattern) cho Plugin.
Xß╗¡ l├╜ tß║¡p trung c├íc thao t├íc ─æß╗ìc/ghi file JSON vß╗¢i c╞í chß║┐ Cache tr├¬n RAM (Defensive Programming).
"""

import os
import json
import traceback
from qgis.core import QgsMessageLog, Qgis

class ConfigRepository:
    _plugin_dir = None
    _cache = {}

    @classmethod
    def set_plugin_dir(cls, dir_path: str):
        """Khß╗ƒi tß║ío ─æ╞░ß╗¥ng dß║½n plugin v├á x├│a cache c┼⌐ ─æß╗â ph├▓ng r├▓ rß╗ë (Memory/Stale Cache Leak)."""
        cls._plugin_dir = dir_path
        cls.clear_cache()  # Lß╗¢p ph├▓ng thß╗º: lu├┤n reset khi dir thay ─æß╗òi

    @classmethod
    def clear_cache(cls):
        """X├│a to├án bß╗Ö cache tr├¬n RAM."""
        cls._cache.clear()

    @classmethod
    def get_config(cls, config_name: str, default=None):
        """
        ─Éß╗ìc v├á cache file cß║Ñu h├¼nh JSON tß╗½ th╞░ mß╗Ñc data.
        
        Parameters
        ----------
        config_name : str
            T├¬n file (kh├┤ng c├│ ─æu├┤i .json), v├¡ dß╗Ñ: 'land_use_codes'.
        default : any, optional
            Gi├í trß╗ï trß║ú vß╗ü nß║┐u lß╗ùi (VD: [] cho List, {} cho Dict).
        """
        if cls._plugin_dir is None:
            QgsMessageLog.logMessage(
                "ConfigRepository ch╞░a ─æ╞░ß╗úc khß╗ƒi tß║ío! Gß╗ìi get_config tr╞░ß╗¢c set_plugin_dir.", 
                "VNU2F", 
                level=Qgis.Critical
            )
            return default

        # 1. Trß║ú vß╗ü Cache nß║┐u c├│
        if config_name in cls._cache:
            return cls._cache[config_name]

        # 2. ─Éß╗ìc ß╗ò cß╗⌐ng
        json_path = os.path.join(cls._plugin_dir, "data", f"{config_name}.json")
        if not os.path.exists(json_path):
            return default

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                cls._cache[config_name] = data
                return data
        except json.JSONDecodeError as e:
            QgsMessageLog.logMessage(
                f"Lß╗ùi c├║ ph├íp JSON khi ─æß╗ìc '{config_name}.json': {str(e)}", 
                "VNU2F", 
                level=Qgis.Critical
            )
            return default
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Lß╗ùi kh├┤ng x├íc ─æß╗ïnh khi ─æß╗ìc '{config_name}.json': {str(e)}\n{traceback.format_exc()}", 
                "VNU2F", 
                level=Qgis.Warning
            )
            return default

    @classmethod
    def save_config(cls, config_name: str, data) -> bool:
        """
        Ghi file cß║Ñu h├¼nh JSON v├á cß║¡p nhß║¡t lß║íi cache.
        
        Parameters
        ----------
        config_name : str
            T├¬n file (kh├┤ng c├│ ─æu├┤i .json).
        data : list or dict
            Dß╗» liß╗çu cß║ºn l╞░u.
        """
        if cls._plugin_dir is None:
            QgsMessageLog.logMessage(
                "ConfigRepository ch╞░a ─æ╞░ß╗úc khß╗ƒi tß║ío! Gß╗ìi save_config tr╞░ß╗¢c set_plugin_dir.", 
                "VNU2F", 
                level=Qgis.Critical
            )
            return False

        json_path = os.path.join(cls._plugin_dir, "data", f"{config_name}.json")
        
        # ─Éß║úm bß║úo th╞░ mß╗Ñc data tß╗ôn tß║íi
        os.makedirs(os.path.dirname(json_path), exist_ok=True)

        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            # Ghi ─æ├¿ cache ngay sau khi l╞░u ─æ─⌐a th├ánh c├┤ng
            cls._cache[config_name] = data
            return True
        except PermissionError as e:
            QgsMessageLog.logMessage(
                f"Lß╗ùi quyß╗ün truy cß║¡p khi ghi '{config_name}.json'. Dß╗» liß╗çu CH╞»A ─É╞»ß╗óC L╞»U: {str(e)}", 
                "VNU2F", 
                level=Qgis.Critical
            )
            return False
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Lß╗ùi kh├┤ng x├íc ─æß╗ïnh khi ghi '{config_name}.json'. Dß╗» liß╗çu CH╞»A ─É╞»ß╗óC L╞»U: {str(e)}\n{traceback.format_exc()}", 
                "VNU2F", 
                level=Qgis.Critical
            )
            return False

