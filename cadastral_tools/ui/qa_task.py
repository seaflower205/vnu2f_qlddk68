"""
Worker Task chạy tiến trình QA dưới nền (QgsTask) để không treo GUI.
"""
from __future__ import annotations

import logging

from qgis.core import QgsTask
from qgis.PyQt.QtCore import pyqtSignal

from ..ai.qa_runner import QARunConfig, QAResult, QARunner

logger = logging.getLogger(__name__)


class CadastralQATask(QgsTask):
    """
    QgsTask worker thực thi chuỗi kiểm định QA.
    KHÔNG truy cập GUI, KHÔNG gọi QgsVectorLayer. Active trên bộ nhớ (Snapshot).
    """

    finished_qa = pyqtSignal(object)  # QAResult

    def __init__(self, description: str, config: QARunConfig):
        super().__init__(description, QgsTask.CanCancel)
        self.config = config
        self.result = None
        self.exception = None

        self.config.progress_callback = self._on_runner_progress
        self.config.is_cancelled = self.isCanceled

    def run(self) -> bool:
        try:
            logger.info("Bắt đầu QA Task trên Snapshot Data...")
            
            runner = QARunner(self.config)
            self.result = runner.run()

            return True
        except Exception as e:
            logger.exception("Task bị sụp do lỗi không lường trước: %s", e)
            self.exception = e
            return False

    def _on_runner_progress(self, percent: float, msg: str) -> None:
        if percent >= 0:
            self.setProgress(percent)

    def finished(self, result: bool) -> None:
        if self.isCanceled():
            if self.result:
                self.result.cancelled = True
            else:
                self.result = QAResult(cancelled=True)
                
        elif not result:
            if not self.result:
                self.result = QAResult()
            self.result.errors.append(f"Task sụp đổ (Crash): {self.exception}")

        self.finished_qa.emit(self.result)
