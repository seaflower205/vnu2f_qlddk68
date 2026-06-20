"""
Logger trung tâm — ghi log dạng JSON Lines (.jsonl) để dễ parse,
kèm breadcrumb (vết hành động) và redact dữ liệu nhạy cảm.
"""
import json
import traceback
import functools
from collections import deque
from datetime import datetime
from pathlib import Path

REDACT_KEYS = {"passcode", "token", "password", "api_key", "secret"}
_BREADCRUMB = deque(maxlen=50)   # 50 hành động gần nhất, lưu RAM

def _redact(data: dict) -> dict:
    if not isinstance(data, dict):
        return data
    return {
        k: ("***REDACTED***" if isinstance(k, str) and k.lower() in REDACT_KEYS else v)
        for k, v in data.items()
    }

def get_log_path() -> Path:
    # Chọn thư mục plugin/logs
    log_dir = Path(__file__).parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    return log_dir / f"plugin_{datetime.now():%Y%m%d}.jsonl"

def log_action(action: str, **context):
    """Ghi vết hành động — KHÔNG phải lỗi, chỉ để truy ngược khi có lỗi xảy ra."""
    entry = {
        "ts": datetime.now().isoformat(),
        "type": "action",
        "action": action,
        "context": _redact(context),
    }
    _BREADCRUMB.append(entry)

def log_error(message, exc: Exception = None, source_tag: str = None, tb_str: str = None, **context):
    """Ghi lỗi đầy đủ traceback + breadcrumb dẫn tới lỗi đó."""
    if isinstance(message, Exception):
        if exc is None:
            exc = message
        message = str(message)

    if not tb_str and exc:
        try:
            tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        except Exception:
            pass

    if not tb_str:
        tb_str = traceback.format_exc()
        if tb_str == "NoneType: None\n" or not tb_str.strip():
            tb_str = None

    entry = {
        "ts": datetime.now().isoformat(),
        "type": "error",
        "message": str(message),
        "source_tag": source_tag,
        "context": _redact(context),
        "traceback": tb_str,
        "breadcrumb": list(_BREADCRUMB),
    }
    try:
        with open(get_log_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001
        pass
        
    try:
        from qgis.core import QgsMessageLog, Qgis
        msg = f"{message}\n\nTraceback:\n{tb_str}" if tb_str else str(message)
        QgsMessageLog.logMessage(msg, "VNU2F", Qgis.Critical)
    except Exception:
        pass
        
    return entry

def track_action(action_name: str, source_tag: str = None):
    """Decorator gắn vào hàm xử lý sự kiện UI quan trọng (nút bấm, v.v.)"""
    def decorator(func):
        import inspect
        sig = inspect.signature(func)
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            log_action(action_name)
            try:
                # Lọc args để tránh lỗi PyQt truyền dư biến `checked` từ signal
                valid_args = args[:len(sig.parameters)]
                return func(*valid_args, **kwargs)
            except Exception as e:
                log_error(f"Lỗi khi thực hiện: {action_name}", exc=e, source_tag=source_tag)
                raise
        return wrapper
    return decorator
