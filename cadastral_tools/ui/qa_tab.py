"""
Controller cho QA Tab. Chạy logic khởi tạo và nhận kết quả từ background task.
"""
from __future__ import annotations

import logging
from datetime import date

from qgis.PyQt.QtWidgets import QWidget, QMessageBox
from qgis.PyQt.QtCore import Qt, QModelIndex
from qgis.core import (
    QgsProject, QgsMapLayerType, QgsVectorLayer, QgsApplication
)

from .qa_tab_ui import QATabUi, QAResultTableModel
from .qa_task import CadastralQATask
from ..ai.qa_runner import QARunConfig, FeatureSnapshot, LayerSnapshot
from ..ai.legal_resolver import LegalContext
from ..ai.step0_preflight import check_crs, create_backup

logger = logging.getLogger(__name__)


class QATab(QWidget):
    def __init__(self, plugin_state=None, parent=None):
        super().__init__(parent)
        self.plugin_state = plugin_state
        self.ui = QATabUi()
        self.ui.setup_ui(self)
        
        self.table_model = QAResultTableModel()
        self.ui.table_view.setModel(self.table_model)

        self.ui.btn_run.clicked.connect(self.on_run_clicked)
        self.ui.btn_cancel.clicked.connect(self.on_cancel_clicked)
        self.ui.boundary_combo.currentIndexChanged.connect(self.on_boundary_changed)
        self.ui.table_view.doubleClicked.connect(self.on_issue_double_clicked)
        
        QgsProject.instance().layersAdded.connect(self.refresh_layers)
        QgsProject.instance().layersRemoved.connect(self.refresh_layers)
        self.refresh_layers()
        
        self.current_task = None

    def refresh_layers(self, _=None):
        self.ui.layer_combo.clear()
        self.ui.boundary_combo.clear()
        self.ui.boundary_combo.addItem("-- Không sử dụng ranh giới --", None)
        
        layers = QgsProject.instance().mapLayers().values()
        for layer in layers:
            if layer.type() == QgsMapLayerType.VectorLayer and layer.geometryType() == 2: # Polygon
                self.ui.layer_combo.addItem(layer.name(), layer.id())
                self.ui.boundary_combo.addItem(layer.name(), layer.id())
                
        self.on_boundary_changed()

    def on_boundary_changed(self):
        has_boundary = self.ui.boundary_combo.currentData() is not None
        self.ui.chk_gaps.setEnabled(has_boundary)
        if not has_boundary:
            self.ui.chk_gaps.setChecked(False)

    def _create_snapshot(self, layer: QgsVectorLayer, preflight_hash: str = "") -> LayerSnapshot:
        """Tạo bản sao an toàn (WKB) của layer trên main thread."""
        features = []
        for feat in layer.getFeatures():
            geom = feat.geometry()
            wkb = geom.asWkb() if not geom.isNull() else b""
            bbox = geom.boundingBox() if not geom.isNull() else None
            bbox_tuple = (bbox.xMinimum(), bbox.yMinimum(), bbox.xMaximum(), bbox.yMaximum()) if bbox else None
            
            attrs = {f.name(): feat.attribute(f.name()) for f in layer.fields()}
                
            features.append(FeatureSnapshot(
                fid=feat.id(),
                wkb=wkb,
                bbox=bbox_tuple,
                attrs=attrs
            ))
            
        field_names = [f.name() for f in layer.fields()]
            
        return LayerSnapshot(
            layer_id=layer.id(),
            layer_name=layer.name(),
            crs_wkt=layer.crs().toWkt(),
            fields=field_names,
            features=features,
            preflight_hash=preflight_hash
        )

    def on_run_clicked(self):
        layer_id = self.ui.layer_combo.currentData()
        if not layer_id:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn lớp thửa đất cần kiểm tra.")
            return
            
        main_layer = QgsProject.instance().mapLayer(layer_id)
        if not main_layer:
            return
            
        boundary_id = self.ui.boundary_combo.currentData()
        boundary_layer = QgsProject.instance().mapLayer(boundary_id) if boundary_id else None

        self.ui.lbl_status.setText("Đang kiểm tra an toàn (Preflight)...")
        QApplication = QgsApplication.instance()
        QApplication.processEvents()
        
        # Lấy Ngày áp dụng pháp lý từ UI
        as_of = self.ui.date_edit.date().toPyDate()
        legal_ctx = LegalContext(as_of_date=as_of)
        
        crs_result = check_crs(main_layer, legal_ctx)
        if not crs_result.can_continue:
            QMessageBox.critical(self, "Lỗi CRS", crs_result.reason or "Hệ tọa độ không hợp lệ.")
            self.ui.lbl_status.setText("Bị chặn bởi Preflight (CRS).")
            return
            
        preflight_hash = ""
        try:
            # Nên tạo option backup trên UI, tạm thời vẫn chạy create_backup
            backup_info = create_backup(main_layer)
            preflight_hash = backup_info.get("backup_hash", "")
        except RuntimeError as e:
            QMessageBox.warning(self, "Lỗi Backup", str(e))
            self.ui.lbl_status.setText("Bị chặn do không thể sao lưu.")
            return
            
        self.ui.lbl_status.setText("Đang nạp dữ liệu (Snapshot) lên RAM...")
        QApplication.processEvents()
        
        main_snapshot = self._create_snapshot(main_layer, preflight_hash)
        boundary_snapshot = self._create_snapshot(boundary_layer, "") if boundary_layer else None

        # Parse operation_type
        op_text = self.ui.cbo_operation.currentText()
        if "tach_thua" in op_text:
            op_type = "tach_thua"
        elif "hop_thua" in op_text:
            op_type = "hop_thua"
        elif "nghiem_thu" in op_text:
            op_type = "nghiem_thu"
        elif "migration_warning" in op_text:
            op_type = "migration_warning"
        else:
            op_type = "kiem_tra_hien_trang"

        # Lấy default admin codes
        def_com = self.ui.txt_default_commune.text().strip()
        def_prov = self.ui.txt_default_province.text().strip()

        config = QARunConfig(
            legal_context=legal_ctx,
            run_topology=self.ui.chk_topology.isChecked(),
            run_attributes=True,
            run_legal_audit=self.ui.chk_legal.isChecked(),
            operation_type=op_type,
            run_gaps=self.ui.chk_gaps.isChecked() and boundary_snapshot is not None,
            default_commune_code=def_com if def_com else None,
            default_province_code=def_prov if def_prov else None,
            boundary_layer_snapshot=boundary_snapshot,
            main_layer_snapshot=main_snapshot,
        )

        self.current_task = CadastralQATask("Cadastral QA Check", config)
        self.current_task.finished_qa.connect(self.on_task_finished)
        self.current_task.progressChanged.connect(self.on_task_progress)

        self.ui.btn_run.setEnabled(False)
        self.ui.btn_cancel.setEnabled(True)
        self.ui.progress_bar.setValue(0)
        self.ui.progress_bar.show()
        self.ui.lbl_status.setText("Đang chạy kiểm định...")
        
        QgsApplication.taskManager().addTask(self.current_task)

    def on_cancel_clicked(self):
        if self.current_task:
            self.current_task.cancel()
            self.ui.lbl_status.setText("Đang hủy task...")

    def on_task_progress(self, percent):
        self.ui.progress_bar.setValue(int(percent))

    def on_task_finished(self, result):
        self.ui.btn_run.setEnabled(True)
        self.ui.btn_cancel.setEnabled(False)
        self.ui.progress_bar.hide()
        self.current_task = None
        
        if result.cancelled:
            self.ui.lbl_status.setText("Đã hủy quá trình kiểm định.")
            return
            
        if result.errors:
            QMessageBox.critical(self, "Lỗi Nghiêm Trọng", "\n".join(result.errors))
            self.ui.lbl_status.setText("Kết thúc với lỗi.")
        else:
            issue_count = len(result.issues)
            self.ui.lbl_status.setText(f"Hoàn thành trong {result.elapsed_ms}ms. Phát hiện {issue_count} lỗi/cảnh báo.")
            
        self.table_model.update_data(result.issues)

    def on_issue_double_clicked(self, index: QModelIndex):
        issue = self.table_model.get_issue_at(index.row())
        if not issue:
            return
            
        layer = QgsProject.instance().mapLayer(issue.layer_id)
        from qgis.utils import iface
        if not iface:
            return

        if not layer:
            QMessageBox.warning(self, "Layer Unavailable", "Lớp bản đồ chứa lỗi này đã bị xóa hoặc không còn tồn tại trong Project.")
            # Zoom to bbox if possible
            if issue.bbox:
                from qgis.core import QgsRectangle
                rect = QgsRectangle(issue.bbox[0], issue.bbox[1], issue.bbox[2], issue.bbox[3])
                iface.mapCanvas().setExtent(rect)
                iface.mapCanvas().refresh()
            return
            
        if issue.feature_id is not None and issue.feature_id >= 0:
            layer.selectByIds([issue.feature_id])
            iface.mapCanvas().zoomToSelected(layer)
        elif issue.bbox:
            from qgis.core import QgsRectangle
            rect = QgsRectangle(issue.bbox[0], issue.bbox[1], issue.bbox[2], issue.bbox[3])
            iface.mapCanvas().setExtent(rect)
            iface.mapCanvas().refresh()
