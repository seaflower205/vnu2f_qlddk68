# -*- coding: utf-8 -*-
from qgis.PyQt.QtCore import QSettings

def load_setting(feature: str, key: str, default=None):
    try:
        return QSettings().value(f"{feature}/{key}", default)
    except TypeError:
        return default

def save_setting(feature: str, key: str, value):
    QSettings().setValue(f"{feature}/{key}", value)
