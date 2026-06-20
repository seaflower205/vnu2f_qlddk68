"""Pure-Python contracts for the safe Antigravity worker bridge."""

from pathlib import Path

from tools.run_agy_worker import (
    account_id, build_command, detect_active_email, is_quota_error,
    mask_email, public_registry, redact, register_active_account,
)


def test_command_is_sandboxed_and_never_uses_shell_text():
    command = build_command(Path("C:/agy/agy.exe"), "review this", "gemini-flash", 60)
    assert Path(command[0]) == Path("C:/agy/agy.exe")
    assert command[1] == "--sandbox"
    assert command[-2:] == ["--print", "review this"]
    assert "--dangerously-skip-permissions" not in command


def test_quota_detection_covers_common_provider_errors():
    assert is_quota_error("HTTP 429 Too Many Requests")
    assert is_quota_error("RESOURCE_EXHAUSTED: quota exceeded")
    assert not is_quota_error("completed normally")


def test_output_redacts_common_google_and_bearer_credentials():
    text = "Bearer abc.def.ghi AIza123456789012345678901234567890 eyJabcdefghijklmnopqrstuv"
    cleaned = redact(text)
    assert "abc.def.ghi" not in cleaned
    assert "AIza123" not in cleaned
    assert "eyJabc" not in cleaned


def test_account_identity_is_masked_and_stable():
    assert mask_email("person@example.com") == "pe***@example.com"
    assert account_id("Person@example.com") == account_id("person@example.com")


def test_registry_discovers_account_without_storing_raw_email(tmp_path, monkeypatch):
    log_dir = tmp_path / ".gemini" / "antigravity-cli" / "log"
    log_dir.mkdir(parents=True)
    (log_dir / "cli.log").write_text(
        "OAuth: authenticated successfully as person@example.com\n", encoding="utf-8"
    )
    monkeypatch.setattr(
        "tools.run_agy_worker.detect_active_email", lambda: detect_active_email(tmp_path)
    )
    registry_path = tmp_path / "accounts.json"
    registered = register_active_account(registry_path)
    public = public_registry(registry_path)
    assert registered["masked_email"] == "pe***@example.com"
    assert public["count"] == 1
    assert public["accounts"][0]["active"] is True
    assert "person@example.com" not in registry_path.read_text(encoding="utf-8")

