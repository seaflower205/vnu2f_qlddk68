"""
Audit Trail — Persistent operation logging với chain hash.

Mỗi entry có:
- SHA-256 hash toàn phần layer (sort theo khóa nghiệp vụ)
- Chain hash (previous_entry_hash) chống tamper
- Recovery on restart (đọc dòng cuối JSONL)

Format: JSON Lines (JSONL).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Chain hash state — recovery on restart qua _init_chain_hash()
_last_entry_hash: str | None = None
_log_path_cache: Path | None = None


# ============================================================
# Layer Hash — Toàn phần, deterministic
# ============================================================



# ============================================================
# Log Path
# ============================================================

def _get_log_path() -> Path:
    """Xác định đường dẫn file audit log."""
    global _log_path_cache
    if _log_path_cache is not None:
        return _log_path_cache

    try:
        from qgis.core import QgsProject

        project_path = QgsProject.instance().fileName()
        if project_path:
            log_dir = Path(project_path).parent / "audit_logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            _log_path_cache = log_dir / "audit_trail.jsonl"
            return _log_path_cache
    except (ImportError, AttributeError):
        pass

    # Fallback
    import tempfile

    log_dir = Path(tempfile.gettempdir()) / "qgis_audit_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    _log_path_cache = log_dir / "audit_trail.jsonl"
    logger.warning(
        "Không xác định project path. "
        "Audit log tại: %s",
        _log_path_cache,
    )
    return _log_path_cache


def set_log_path(path: str | Path) -> None:
    """Override log path (dùng cho test)."""
    global _log_path_cache
    _log_path_cache = Path(path)
    _log_path_cache.parent.mkdir(parents=True, exist_ok=True)


# ============================================================
# Chain Hash — Recovery on restart
# ============================================================

def _init_chain_hash(log_path: Path) -> None:
    """Đọc dòng cuối JSONL để khôi phục chain khi restart plugin."""
    global _last_entry_hash

    if not log_path.exists():
        _last_entry_hash = None
        return

    last_line = None
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    last_line = stripped
    except OSError as e:
        logger.warning("Cannot read audit log for chain recovery: %s", e)
        _last_entry_hash = None
        return

    if last_line:
        try:
            entry = json.loads(last_line)
            _last_entry_hash = entry.get("entry_hash")
        except json.JSONDecodeError:
            logger.warning(
                "Last audit log entry is malformed. "
                "Chain hash reset."
            )
            _last_entry_hash = None


def _get_operator_name() -> str:
    """Lấy tên operator."""
    return os.environ.get("USER", os.environ.get("USERNAME", "unknown"))


def _get_software_version() -> str:
    """Lấy plugin version."""
    try:
        from qgis.core import Qgis

        return f"QGIS {Qgis.QGIS_VERSION} / VNU2F QLDDK68"
    except ImportError:
        return "VNU2F QLDDK68 (outside QGIS)"


# ============================================================
# Log Operation
# ============================================================

def log_operation(
    action: str,
    layer=None,
    result: str = "",
    **context,
) -> dict:
    """Ghi một entry vào audit trail.

    Chain hash: mỗi entry tham chiếu hash entry trước.
    Khi tamper 1 dòng → previous_entry_hash mismatch.

    Args:
        action: Tên hành động ("check_crs", "create_backup", ...)
        layer: QgsVectorLayer (optional, dùng để compute hash)
        result: Kết quả ("PASS", "WARNING", "BLOCK", ...)
        **context: Metadata bổ sung

    Returns:
        Entry dict đã ghi (bao gồm entry_hash)
    """
    global _last_entry_hash

    log_path = _get_log_path()

    # Recovery on restart
    if _last_entry_hash is None and log_path.exists():
        _init_chain_hash(log_path)

    # Build entry
    entry: dict = {
        "timestamp": datetime.now().isoformat(),
        "operator": _get_operator_name(),
        "action": action,
        "result": result,
        "software_version": _get_software_version(),
        "previous_entry_hash": _last_entry_hash,
    }

    # Layer hash (nếu có layer)
    if layer is not None:
        try:
            layer_hash, hash_stability = compute_layer_hash(layer)
            entry["input_hash"] = layer_hash
            entry["hash_stability"] = hash_stability
        except Exception as e:
            entry["input_hash"] = f"ERROR: {e}"
            entry["hash_stability"] = "error"

    # Context metadata
    if context:
        entry["context"] = context

    # Compute entry hash (chain)
    entry_json = json.dumps(
        entry, ensure_ascii=False, sort_keys=True,
    )
    entry["entry_hash"] = hashlib.sha256(
        entry_json.encode("utf-8"),
    ).hexdigest()

    _last_entry_hash = entry["entry_hash"]

    # Write to JSONL
    _write_entry(entry, log_path)

    return entry


def _write_entry(entry: dict, log_path: Path) -> None:
    """Ghi entry vào file JSONL."""
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(entry, ensure_ascii=False, sort_keys=True)
            )
            f.write("\n")
    except OSError as e:
        logger.error("Failed to write audit entry: %s", e)


# ============================================================
# Verify Integrity
# ============================================================

def verify_chain_integrity(
    log_path: str | Path | None = None,
) -> list[dict]:
    """Verify toàn bộ chain hash trong audit log.

    Returns:
        List các entry có chain bị broken (empty = OK).
    """
    path = Path(log_path) if log_path else _get_log_path()

    if not path.exists():
        return []

    broken: list[dict] = []
    previous_hash: str | None = None

    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            stripped = line.strip()
            if not stripped:
                continue

            try:
                entry = json.loads(stripped)
            except json.JSONDecodeError:
                broken.append({
                    "line": line_num,
                    "error": "Malformed JSON",
                })
                continue

            # Verify previous_entry_hash
            if entry.get("previous_entry_hash") != previous_hash:
                broken.append({
                    "line": line_num,
                    "error": "Chain hash mismatch",
                    "expected": previous_hash,
                    "got": entry.get("previous_entry_hash"),
                })

            # Verify entry_hash
            stored_hash = entry.pop("entry_hash", None)
            recomputed_json = json.dumps(
                entry, ensure_ascii=False, sort_keys=True,
            )
            recomputed_hash = hashlib.sha256(
                recomputed_json.encode("utf-8"),
            ).hexdigest()

            if stored_hash != recomputed_hash:
                broken.append({
                    "line": line_num,
                    "error": "Entry hash tampered",
                    "stored": stored_hash,
                    "recomputed": recomputed_hash,
                })

            entry["entry_hash"] = stored_hash
            previous_hash = stored_hash

    return broken

from .audit_hash import compute_layer_hash
