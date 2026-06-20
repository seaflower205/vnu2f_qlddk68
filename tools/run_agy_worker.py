#!/usr/bin/env python3
"""Safe, credential-blind bridge to the official Antigravity CLI.

This wrapper deliberately does not read, copy, import, or rotate OAuth state.
The active ``agy`` account is selected by the user outside this process.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_AGY = Path.home() / "AppData" / "Local" / "agy" / "bin" / "agy.exe"
SECRET_NAME = re.compile(r"(?i)(secret|token|api[_-]?key|password|credential|auth)")
QUOTA_ERROR = re.compile(
    r"(?i)(quota.{0,40}(exhausted|exceeded|limit)|rate.?limit|resource.?exhausted|\b429\b)"
)
REDACTIONS = (
    (re.compile(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]+"), "Bearer ***"),
    (re.compile(r"AIza[0-9A-Za-z_-]{20,}"), "AIza***"),
    (re.compile(r"eyJ[A-Za-z0-9._-]{20,}"), "***"),
)
AUTH_SUCCESS = re.compile(r"OAuth: authenticated successfully as ([^\s,]+)", re.IGNORECASE)
DEFAULT_REGISTRY = Path("scratch") / "agy_worker" / "accounts.json"


def find_agy() -> Path:
    override = os.environ.get("AGY_BIN")
    candidate = Path(override).expanduser() if override else None
    if candidate and candidate.is_file():
        return candidate.resolve()
    discovered = shutil.which("agy") or shutil.which("agy.exe")
    if discovered:
        return Path(discovered).resolve()
    if DEFAULT_AGY.is_file():
        return DEFAULT_AGY.resolve()
    raise FileNotFoundError("Không tìm thấy agy.exe; đặt AGY_BIN hoặc chạy `agy install`.")


def clean_environment() -> dict[str, str]:
    """Keep normal process settings but never forward provider secrets."""
    return {key: value for key, value in os.environ.items() if not SECRET_NAME.search(key)}


def redact(text: str) -> str:
    result = text
    for pattern, replacement in REDACTIONS:
        result = pattern.sub(replacement, result)
    return result


def is_quota_error(*parts: str) -> bool:
    return bool(QUOTA_ERROR.search("\n".join(parts)))


def build_command(agy: Path, prompt: str, model: str | None, timeout: int) -> list[str]:
    command = [str(agy), "--sandbox", "--print-timeout", f"{timeout}s"]
    if model:
        command.extend(["--model", model])
    command.extend(["--print", prompt])
    return command


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    prompt_group = parser.add_mutually_exclusive_group()
    prompt_group.add_argument("--prompt")
    prompt_group.add_argument("--prompt-file", type=Path)
    parser.add_argument("--model")
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--register-current", action="store_true")
    parser.add_argument("--list-accounts", action="store_true")
    return parser.parse_args(argv)


def mask_email(email: str) -> str:
    local, separator, domain = email.strip().partition("@")
    if not separator:
        return "***"
    return f"{local[:2]}***@{domain}"


def account_id(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()[:12]


def detect_active_email(home: Path | None = None) -> str | None:
    """Read only successful-auth log metadata; never open OAuth credentials."""
    root = (home or Path.home()) / ".gemini" / "antigravity-cli" / "log"
    if not root.is_dir():
        return None
    logs = sorted(root.rglob("*.log"), key=lambda path: path.stat().st_mtime, reverse=True)
    for path in logs[:10]:
        try:
            matches = AUTH_SUCCESS.findall(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        if matches:
            return matches[-1]
    return None


def load_registry(path: Path) -> dict:
    if not path.is_file():
        return {"schema_version": 1, "active_account_id": None, "accounts": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not isinstance(data.get("accounts"), dict):
        raise ValueError(f"Registry không hợp lệ: {path}")
    return data


def save_registry(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def register_active_account(path: Path, status: str = "ready") -> dict | None:
    email = detect_active_email()
    if not email:
        return None
    identifier = account_id(email)
    registry = load_registry(path)
    entry = registry["accounts"].setdefault(identifier, {})
    entry.update({
        "masked_email": mask_email(email),
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "status": status,
    })
    registry["active_account_id"] = identifier
    save_registry(path, registry)
    return {"account_id": identifier, **entry}


def public_registry(path: Path) -> dict:
    registry = load_registry(path)
    accounts = [{
        "account_id": identifier,
        "masked_email": entry.get("masked_email", "***"),
        "status": entry.get("status", "unknown"),
        "last_seen": entry.get("last_seen"),
        "active": identifier == registry.get("active_account_id"),
    } for identifier, entry in sorted(registry["accounts"].items())]
    return {"count": len(accounts), "accounts": accounts}



def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        agy = find_agy()
        cwd = args.cwd.expanduser().resolve(strict=True)
        registry_path = args.registry.expanduser().resolve()
        if args.list_accounts:
            print(json.dumps(public_registry(registry_path), ensure_ascii=False))
            return 0
        if args.register_current:
            account = register_active_account(registry_path)
            if account is None:
                raise ValueError("Không tìm thấy OAuth thành công trong log agy.")
            print(json.dumps({"ok": True, "status": "registered", "account": account}, ensure_ascii=False))
            return 0
        if not cwd.is_dir():
            raise NotADirectoryError(cwd)
        if args.prompt_file:
            prompt = args.prompt_file.read_text(encoding="utf-8")
        else:
            prompt = args.prompt or ""
        if not prompt and not args.dry_run:
            raise ValueError("Cần --prompt hoặc --prompt-file.")
        if args.dry_run:
            print(json.dumps({
                "ok": True, "status": "dry_run", "agy": str(agy),
                "cwd": str(cwd), "model": args.model, "prompt_chars": len(prompt),
                "sandbox": True,
            }, ensure_ascii=False))
            return 0

        command = build_command(agy, prompt, args.model, args.timeout)
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=clean_environment(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=args.timeout + 15,
            shell=False,
            check=False,
        )
        stdout, stderr = redact(completed.stdout), redact(completed.stderr)
        quota = is_quota_error(stdout, stderr)
        account = register_active_account(
            registry_path, status="quota_exhausted" if quota else "ready"
        )
        payload = {
            "ok": completed.returncode == 0 and not quota,
            "status": "quota_exhausted" if quota else "completed" if completed.returncode == 0 else "failed",
            "exit_code": completed.returncode,
            "quota_exhausted": quota,
            "stdout": stdout,
            "stderr": stderr,
            "account": account,
        }
        print(json.dumps(payload, ensure_ascii=False))
        return 75 if quota else completed.returncode

    except subprocess.TimeoutExpired as exc:
        stdout = redact(exc.stdout) if exc.stdout else ""
        stderr = redact(exc.stderr) if exc.stderr else ""
        print(json.dumps({
            "ok": False,
            "status": "timeout",
            "error": redact(str(exc)),
            "stdout": stdout,
            "stderr": stderr
        }, ensure_ascii=False))
        return 124
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "status": "configuration_error", "error": redact(str(exc))}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
