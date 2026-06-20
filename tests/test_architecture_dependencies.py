"""Architecture contract backed by the source-derived runtime code graph."""

from pathlib import Path

from tools.analyze_code_graph import build_graph, load_rules, validate_graph
from tools.package_plugin import check_package


def test_runtime_dependency_graph_obeys_architecture_rules():
    rules = load_rules()
    graph = build_graph(rules=rules)
    errors = validate_graph(graph, rules)
    assert not errors, "Architecture violations:\n- " + "\n- ".join(errors)


def test_code_graph_records_expected_reference_metadata():
    graph = build_graph(rules=load_rules())
    assert graph["schema_version"] == 1
    assert all(edge["kind"] and edge["confidence"] for edge in graph["edges"])
    assert all(node["path"].endswith(".py") for node in graph["nodes"])


def test_validator_rejects_new_cycle_core_ui_orphan_and_missing_api():
    graph = {
        "nodes": [
            {"id": "pkg.core.service", "path": "pkg/core/service.py", "symbols": []},
            {"id": "pkg.ui.view", "path": "pkg/ui/view.py", "symbols": []},
            {"id": "pkg.orphan", "path": "pkg/orphan.py", "symbols": []},
        ],
        "edges": [
            {"source": "pkg.core.service", "target": "pkg.ui.view", "kind": "static_import"},
            {"source": "pkg.ui.view", "target": "pkg.core.service", "kind": "lazy_import"},
        ],
        "references": [],
    }
    rules = {
        "cycle_allowlist": [], "orphan_allowlist": [], "entry_modules": [],
        "required_public_api": {"pkg.core.service": ["PublicFacade"]},
        "forbidden_import_roots": [], "allowed_tools_modules": [],
    }
    errors = validate_graph(graph, rules)
    assert any("New dependency cycle" in error for error in errors)
    assert any("core -> ui" in error for error in errors)
    assert any("Orphan runtime module: pkg.orphan" in error for error in errors)
    assert any("PublicFacade" in error for error in errors)


def test_package_check_is_read_only_for_dist_outputs():
    root = Path(__file__).resolve().parents[1]
    dist_dir = root / "dist"
    before_exists = dist_dir.exists()
    before = {
        path.relative_to(dist_dir).as_posix(): path.stat().st_mtime_ns
        for path in dist_dir.rglob("*")
        if path.is_file()
    } if before_exists else {}

    check_package(root)

    assert dist_dir.exists() == before_exists
    after = {
        path.relative_to(dist_dir).as_posix(): path.stat().st_mtime_ns
        for path in dist_dir.rglob("*")
        if path.is_file()
    } if dist_dir.exists() else {}
    assert after == before
