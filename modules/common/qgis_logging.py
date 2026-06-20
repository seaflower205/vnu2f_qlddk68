# -*- coding: utf-8 -*-
"""Small logging bridge for code that may also be imported outside QGIS."""

from __future__ import annotations

import logging

try:
    from qgis.core import Qgis, QgsMessageLog
except Exception:  # pragma: no cover - used only outside QGIS
    Qgis = None
    QgsMessageLog = None


PLUGIN_LOG_NAME = "VNU2F QLDDK68"


def log_warning(message, tag=PLUGIN_LOG_NAME):
    if QgsMessageLog and Qgis:
        QgsMessageLog.logMessage(str(message), tag, Qgis.Warning)
        return
    logging.getLogger(tag).warning("%s", message)


def log_critical(message, tag=PLUGIN_LOG_NAME):
    if QgsMessageLog and Qgis:
        QgsMessageLog.logMessage(str(message), tag, Qgis.Critical)
        return
    logging.getLogger(tag).error("%s", message)
