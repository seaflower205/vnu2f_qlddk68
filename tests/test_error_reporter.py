import json

def test_redact_hides_sensitive_keys():
    from modules.common.error_reporter import _redact
    
    # Simple redact
    result1 = _redact({"token": "abc123", "layer": "ranh_thua"})
    assert result1["token"] == "***REDACTED***"
    assert result1["layer"] == "ranh_thua"
    
    # Case insensitivity and other sensitive keys
    result2 = _redact({"PASSCODE": "secret123", "normal": 42})
    assert result2["PASSCODE"] == "***REDACTED***"
    assert result2["normal"] == 42
    
    # Non-dict inputs
    assert _redact("not a dict") == "not a dict"

def test_log_error_writes_breadcrumb(tmp_path, monkeypatch):
    from modules.common import error_reporter
    
    # Mock log path to point to pytest tmp_path
    log_file = tmp_path / "test_log.jsonl"
    monkeypatch.setattr(error_reporter, "get_log_path", lambda: log_file)
    
    # Clear breadcrumb for clean state
    error_reporter._BREADCRUMB.clear()
    
    # Call actions
    error_reporter.log_action("click_button1", btn_id="btn_apply")
    error_reporter.log_action("click_button2", btn_id="btn_export")
    
    # Trigger an error
    try:
        1 / 0
    except ZeroDivisionError as e:
        entry = error_reporter.log_error("Test division by zero", exc=e, source_tag="TestModule", user="admin")
        
    # Check returned entry
    assert entry["message"] == "Test division by zero"
    assert entry["source_tag"] == "TestModule"
    assert "ZeroDivisionError" in entry["traceback"]
    assert len(entry["breadcrumb"]) == 2
    assert entry["breadcrumb"][0]["action"] == "click_button1"
    
    # Check file writing
    assert log_file.exists()
    lines = log_file.read_text(encoding="utf-8").strip().split('\n')
    assert len(lines) == 1
    
    written_data = json.loads(lines[0])
    assert written_data["message"] == "Test division by zero"
    assert written_data["source_tag"] == "TestModule"
    assert "ZeroDivisionError" in written_data["traceback"]
    assert len(written_data["breadcrumb"]) == 2
    assert written_data["breadcrumb"][1]["action"] == "click_button2"

def test_track_action_decorator():
    from modules.common.error_reporter import track_action, _BREADCRUMB
    
    _BREADCRUMB.clear()
    
    @track_action("mocked_ui_action", source_tag="UI")
    def do_something(x):
        if x < 0:
            raise ValueError("Negative value not allowed")
        return x * 2
        
    # Test success
    res = do_something(5)
    assert res == 10
    assert len(_BREADCRUMB) == 1
    assert _BREADCRUMB[-1]["action"] == "mocked_ui_action"
    
    # Test exception
    try:
        do_something(-1)
        assert False, "Should have raised"
    except ValueError:
        pass
        
    assert len(_BREADCRUMB) == 2
    assert _BREADCRUMB[-1]["action"] == "mocked_ui_action"
