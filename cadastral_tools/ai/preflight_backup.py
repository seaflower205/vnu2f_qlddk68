"""Backup and restore helpers used by the preflight safety gate."""
from __future__ import annotations

import hashlib
import logging
import re
import shutil
from datetime import datetime
from pathlib import Path

from .compat import require_qgis4

logger = logging.getLogger(__name__)


def _get_backup_dir(layer, backup_dir: Path | None = None) -> Path:
    if backup_dir is not None:
        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir
    try:
        from qgis.core import QgsProject
        project_path = QgsProject.instance().fileName()
        if project_path:
            target = Path(project_path).parent / "backups"
            target.mkdir(parents=True, exist_ok=True)
            return target
    except (ImportError, AttributeError):
        pass
    import tempfile
    target = Path(tempfile.gettempdir()) / "qgis_cadastral_backups"
    target.mkdir(parents=True, exist_ok=True)
    logger.warning("Không xác định được project path. Backup sẽ lưu tại: %s", target)
    return target


def _compute_file_hash(file_path: Path) -> str:
    digest = hashlib.sha256()
    with open(file_path, "rb") as stream:
        for chunk in iter(lambda: stream.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_backup(layer, backup_dir: Path | None = None, operator: str | None = None) -> dict:
    """Create an atomic GeoPackage backup of *layer*."""
    require_qgis4("step0_preflight")
    if layer.isEditable():
        raise RuntimeError(
            "Layer đang ở chế độ chỉnh sửa (edit mode). "
            "Hãy commit hoặc rollBack trước khi tạo backup."
        )
    from qgis.core import QgsCoordinateTransformContext, QgsVectorFileWriter

    target_dir = _get_backup_dir(layer, backup_dir)
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    current_operator = operator or "unknown"
    safe_name = re.sub(r"[^\w\-.]", "_", layer.name())
    filename = f"{safe_name}_{timestamp}_{current_operator}.gpkg"
    final_path = target_dir / filename
    temp_path = target_dir / f"{filename}.tmp"
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    error_code, error_msg = QgsVectorFileWriter.writeAsVectorFormatV3(
        layer, str(temp_path), QgsCoordinateTransformContext(), options
    )
    if error_code != QgsVectorFileWriter.WriterError.NoError:
        if temp_path.exists():
            temp_path.unlink()
        raise RuntimeError(f"Backup failed: {error_msg} (code: {error_code})")
    shutil.move(str(temp_path), str(final_path))
    backup_hash = _compute_file_hash(final_path)
    result = {
        "backup_path": str(final_path),
        "backup_hash": backup_hash,
        "timestamp": now.isoformat(),
        "operator": current_operator,
        "layer_name": layer.name(),
        "feature_count": layer.featureCount(),
    }
    logger.info("Backup created: %s (hash: %s)", final_path, backup_hash)
    return result


def restore_from_backup(
    backup_path: str | Path, target_layer, verify_hashes: bool = True
) -> dict:
    """Replace target features from a GeoPackage backup."""
    require_qgis4("step0_preflight")
    source = Path(backup_path)
    if not source.exists():
        raise FileNotFoundError(f"Backup file not found: {source}")
    from qgis.core import QgsVectorLayer

    backup_hash = _compute_file_hash(source)
    backup_layer = QgsVectorLayer(str(source), "backup_temp", "ogr")
    if not backup_layer.isValid():
        raise RuntimeError(f"Cannot load backup file: {source}")
    if target_layer.isEditable():
        raise RuntimeError(
            "Target layer đang ở edit mode. Commit hoặc rollBack trước khi restore."
        )
    target_layer.startEditing()
    try:
        target_layer.deleteFeatures([f.id() for f in target_layer.getFeatures()])
        for feature in backup_layer.getFeatures():
            target_layer.addFeature(feature)
        target_layer.commitChanges()
    except Exception:
        target_layer.rollBack()
        raise
    result = {
        "restored": True,
        "backup_path": str(source),
        "backup_hash": backup_hash,
        "feature_count_restored": target_layer.featureCount(),
    }
    logger.info(
        "Restored from backup: %s (%d features)",
        source,
        result["feature_count_restored"],
    )
    return result
