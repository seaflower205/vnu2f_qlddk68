# -*- coding: utf-8 -*-
"""Consolidated utility module for logging and asynchronous task management in QGIS."""

from __future__ import annotations

import logging
import traceback
import inspect

try:
    from qgis.core import Qgis, QgsMessageLog, QgsTask, QgsApplication
    HAS_QGIS = True
except Exception:  # noqa: BLE001 — intentional suppress
    Qgis = None
    QgsMessageLog = None
    QgsTask = object  # Fallback for subclassing when QGIS is absent
    QgsApplication = None
    HAS_QGIS = False

PLUGIN_LOG_NAME = "VNU2F QLDDK68"

# ==============================================================================
# LOGGING UTILITIES
# ==============================================================================

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

# ==============================================================================
# ASYNCHRONOUS TASK MANAGER
# ==============================================================================

class BackgroundTask(QgsTask):
    """A general-purpose QgsTask wrapper to run Python functions in the background."""

    def __init__(self, description: str, func, *args, on_finished=None, on_error=None, **kwargs):
        if HAS_QGIS:
            super().__init__(description, QgsTask.CanCancel)
        else:
            # Simple dummy init for tests running outside QGIS
            self._desc = description
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.on_finished = on_finished
        self.on_error = on_error
        self.exception = None
        self.result = None

    def description(self):
        if HAS_QGIS:
            return super().description()
        return getattr(self, '_desc', "Task")

    def run(self):
        if HAS_QGIS:
            QgsMessageLog.logMessage(f"Bắt đầu tác vụ nền: {self.description()}", "VNU2F_Task", Qgis.Info)
        try:
            kwargs = dict(self.kwargs)
            try:
                sig = inspect.signature(self.func)
                has_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
                has_is_canceled_cb = 'is_canceled_cb' in sig.parameters
                if has_is_canceled_cb or has_kwargs:
                    # Under QGIS we use the built-in isCanceled check. Outside, we pass a dummy lambda.
                    kwargs['is_canceled_cb'] = self.isCanceled if HAS_QGIS else (lambda: False)
            except Exception:  # noqa: BLE001 — intentional suppress
                pass
            
            # Execute the heavy function
            self.result = self.func(*self.args, **kwargs)
            return True
        except Exception as e:
            self.exception = e
            if HAS_QGIS:
                QgsMessageLog.logMessage(
                    f"Lỗi trong tác vụ nền {self.description()}: {str(e)}\n{traceback.format_exc()}",
                    "VNU2F_Task",
                    Qgis.Critical
                )
            return False

    def finished(self, result):
        """Called automatically on the QGIS UI (main) thread when run() completes."""
        if HAS_QGIS:
            if result:
                QgsMessageLog.logMessage(f"Hoàn thành tác vụ nền: {self.description()}", "VNU2F_Task", Qgis.Success)
                if self.on_finished:
                    try:
                        self.on_finished(self.result)
                    except Exception as e:
                        QgsMessageLog.logMessage(
                            f"Lỗi callback finished của {self.description()}: {str(e)}",
                            "VNU2F_Task",
                            Qgis.Critical
                        )
            else:
                QgsMessageLog.logMessage(f"Tác vụ thất bại hoặc bị hủy: {self.description()}", "VNU2F_Task", Qgis.Warning)
                if self.on_error:
                    self.on_error(self.exception or Exception("Tác vụ bị hủy hoặc thất bại không rõ nguyên nhân."))

def run_in_background(description: str, func, *args, on_finished=None, on_error=None, **kwargs) -> BackgroundTask:
    """Convenience helper to run a function in a QgsTask."""
    task = BackgroundTask(description, func, *args, on_finished=on_finished, on_error=on_error, **kwargs)
    if HAS_QGIS and QgsApplication:
        QgsApplication.taskManager().addTask(task)
    return task
