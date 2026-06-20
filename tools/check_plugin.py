# -*- coding: utf-8 -*-
"""Preflight checks for the VNU2F QLDDK68 QGIS plugin.

The checks are intentionally lightweight so they can run outside QGIS before a
UI/UX change is copied into an installed QGIS profile.
"""

from __future__ import annotations

import ast
import configparser
import json
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    from tools.analyze_code_graph import build_graph, load_rules, validate_graph, write_reports
except ModuleNotFoundError:  # Direct execution: python tools/check_plugin.py
    from analyze_code_graph import build_graph, load_rules, validate_graph, write_reports


ROOT = Path(__file__).resolve().parents[1]
NODE_EXE = Path(
    os.environ.get(
        "NODE_EXE",
        r"C:\Users\Sea Flower\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe",
    )
)

REQUIRED_FILES = [
    "__init__.py",
    "metadata.txt",
    "vnu2f_qlddk68.py",
    "config/land_types.json",
    "data/schema.sql",
    "data/schema_postgis.sql",
    "modules/webgis_launcher.py",
    "modules/common/qt_compat.py",
    "modules/common/common_utils.py",
    "modules/crs_converter/crs_dialog.py",
    "modules/crs_converter/crs_utils.py",
    "modules/crs_converter/font_utils.py",
    "modules/crs_converter/plot_utils.py",
    "modules/cadastral_importer/dialog.py",
    "modules/cadastral_importer/cad_reader.py",
    "modules/cadastral_importer/dossier.py",
    "modules/cadastral_importer/gtp_reader.py",
    "modules/cadastral_importer/pol_reader.py",
    "modules/cadastral_importer/sync_importer.py",
    "modules/cadastral_importer/layer_runtime.py",
    "webgis_demo/index.html",
    "webgis_demo/js/app.js",
    "webgis_demo/js/worker.js",
    "webgis_demo/css/layout.css",
    "webgis_demo/tools/convert_shp_to_geojson.py",
    "requirements-qgis.txt",
    "modules/crs_converter/tabs/health_tab.py",
]

REQUIRED_METADATA_KEYS = [
    "name",
    "qgisMinimumVersion",
    "description",
    "version",
    "author",
    "email",
]

REQUIRED_WEB_IDS = [
    "mapCanvas",
    "landChart",
    "groupChart",
    "searchInput",
    "resultList",
    "resultCount",
    "mapStatus",
    "coordStatus",
    "totalParcels",
    "totalArea",
    "landClassCount",
    "legend",
    "groupLegend",
    "landChartInfo",
    "groupChartInfo",
    "parcelTitle",
    "parcelType",
    "parcelDetails",
]


class CheckRun:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def ok(self, message: str) -> None:
        print(f"OK   {message}")

    def warn(self, message: str) -> None:
        self.warnings.append(message)
        print(f"WARN {message}")

    def fail(self, message: str) -> None:
        self.errors.append(message)
        print(f"FAIL {message}")


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def check_required_files(run: CheckRun) -> None:
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).exists()]
    if missing:
        for path in missing:
            run.fail(f"Missing required file: {path}")
        return
    run.ok("Required plugin files are present")


def check_no_generated_data(run: CheckRun) -> None:
    generated = ROOT / "webgis_demo" / "data" / "parcels.geojson"
    if generated.exists():
        run.warn("webgis_demo/data/parcels.geojson exists; do not include it in release ZIPs")
    else:
        run.ok("No generated WebGIS parcels.geojson in source tree")


def check_metadata(run: CheckRun) -> None:
    parser = configparser.ConfigParser()
    raw = (ROOT / "metadata.txt").read_text(encoding="utf-8")
    content = raw if raw.lstrip().startswith("[") else "[general]\n" + raw
    parser.read_string(content)
    missing = [key for key in REQUIRED_METADATA_KEYS if not parser["general"].get(key)]
    if missing:
        run.fail(f"metadata.txt missing keys: {', '.join(missing)}")
    else:
        run.ok("metadata.txt has required keys")


def check_json(run: CheckRun) -> None:
    path = ROOT / "config" / "land_types.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        run.fail(f"Invalid JSON {relative(path)}: {exc}")
        return

    bad_codes = []
    for code, item in data.items():
        if code.startswith("_"):
            continue
        color = item.get("color") if isinstance(item, dict) else None
        if not isinstance(color, list) or len(color) < 3:
            bad_codes.append(code)
            continue
        for channel in color[:3]:
            if not isinstance(channel, int) or channel < 0 or channel > 255:
                bad_codes.append(code)
                break

    if bad_codes:
        run.fail(f"Invalid land type colors: {', '.join(bad_codes[:10])}")
    else:
        # Subtract the number of metadata keys from data length
        valid_count = sum(1 for c in data if not c.startswith("_"))
        run.ok(f"land_types.json parsed with {valid_count} codes")


def check_python_syntax(run: CheckRun) -> None:
    excluded_parts = {"__pycache__", "dist", "scratch", ".git"}
    py_files = [
        path
        for path in ROOT.rglob("*.py")
        if not excluded_parts.intersection(path.parts)
    ]
    failed = False
    for path in py_files:
        try:
            ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        except UnicodeDecodeError as exc:
            failed = True
            run.fail(f"Python source is not UTF-8: {relative(path)}: {exc}")
        except SyntaxError as exc:
            failed = True
            run.fail(f"Python syntax error in {relative(path)}:{exc.lineno}: {exc.msg}")
    if not failed:
        run.ok(f"Python syntax OK for {len(py_files)} files")


def check_js_syntax(run: CheckRun) -> None:
    js_files = [
        ROOT / "webgis_demo" / "js" / "app.js",
        ROOT / "webgis_demo" / "js" / "worker.js",
    ]
    if not NODE_EXE.exists():
        run.warn(f"Node.js not found at {NODE_EXE}; skipped JS syntax check")
        return
    
    for app in js_files:
        result = subprocess.run(
            [str(NODE_EXE), "--check", str(app)],
            cwd=str(ROOT),
            text=True,
            capture_output=True,
        )
        if result.returncode:
            run.fail(f"JavaScript syntax error in {relative(app)}: {result.stderr.strip()}")
        else:
            run.ok(f"JavaScript syntax OK for {relative(app)}")


def check_web_contract(run: CheckRun) -> None:
    index = (ROOT / "webgis_demo" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "webgis_demo" / "js" / "app.js").read_text(encoding="utf-8")

    missing_ids = [element_id for element_id in REQUIRED_WEB_IDS if f'id="{element_id}"' not in index]
    if missing_ids:
        run.fail(f"index.html missing required IDs: {', '.join(missing_ids)}")
    else:
        run.ok("WebGIS required DOM IDs are present")

    queried_ids = sorted(set(re.findall(r'querySelector\("#([^"]+)"\)', app)))
    missing_queries = [element_id for element_id in queried_ids if f'id="{element_id}"' not in index]
    if missing_queries:
        run.fail(f"app.js queries IDs not present in index.html: {', '.join(missing_queries)}")
    else:
        run.ok("app.js DOM queries match index.html IDs")

    if "?v=" not in index:
        run.warn("index.html asset URLs have no cache-busting ?v= query")
    else:
        run.ok("WebGIS assets use cache-busting query strings")


def check_js_imports(run: CheckRun) -> None:
    js_dir = ROOT / "webgis_demo" / "js"
    js_files = list(js_dir.rglob("*.js"))
    import_pat = re.compile(r'import\s+.*?\s+from\s+["\'](.*?)["\']')
    
    has_error = False
    for path in js_files:
        try:
            content = path.read_text(encoding="utf-8")
        except Exception as exc:
            run.fail(f"Could not read {relative(path)}: {exc}")
            continue
            
        for match in import_pat.finditer(content):
            import_path = match.group(1)
            if "?v=" in import_path:
                run.fail(f"Internal import in {relative(path)} contains version query: '{import_path}'. Internal imports should be clean relative paths without version queries to prevent duplicate module state.")
                has_error = True
                
        worker_pat = re.compile(r'new\s+Worker\s*\(\s*["\'](.*?)["\']\s*\)')
        for match in worker_pat.finditer(content):
            worker_path = match.group(1)
            if "?v=" in worker_path:
                run.fail(f"Internal Worker in {relative(path)} contains version query: '{worker_path}'. Internal workers should be clean paths without version queries.")
                has_error = True
                
    if not has_error:
        run.ok("Internal JavaScript imports are clean (no duplicate state risk)")


def check_sql(run: CheckRun) -> None:
    for path in [ROOT / "data" / "schema.sql", ROOT / "data" / "schema_postgis.sql"]:
        text = path.read_text(encoding="utf-8")
        if "CREATE TABLE" not in text.upper():
            run.fail(f"{relative(path)} does not contain CREATE TABLE")
        else:
            run.ok(f"{relative(path)} contains table definitions")


def check_packaging(run: CheckRun) -> None:
    script = ROOT / "tools" / "package_plugin.py"
    text = script.read_text(encoding="utf-8")
    if "parcels.geojson" not in text:
        run.warn("package_plugin.py should explicitly exclude generated parcels.geojson")
    elif "EXCLUDED_FILE_NAMES" not in text:
        run.warn("package_plugin.py mentions parcels.geojson; ensure generated data is excluded")
    if "dist" not in text or "zip" not in text.lower():
        run.warn("package_plugin.py does not appear to create a ZIP package")
    else:
        run.ok("Packaging script is present")


def check_code_graph(run: CheckRun) -> None:
    """Regenerate diagnostics and enforce the committed architecture policy."""
    try:
        rules = load_rules()
        graph = build_graph(ROOT, rules)
        write_reports(graph)
        violations = validate_graph(graph, rules)
    except (OSError, ValueError, SyntaxError, json.JSONDecodeError) as exc:
        run.fail(f"Could not build code graph: {exc}")
        return
    if violations:
        for violation in violations:
            run.fail(f"Code graph: {violation}")
    else:
        run.ok(
            f"Code graph architecture OK ({len(graph['nodes'])} modules, "
            f"{len(graph['edges'])} edges)"
        )


def main() -> int:
    os.chdir(ROOT)
    run = CheckRun()
    print(f"Checking plugin at {ROOT}")
    check_required_files(run)
    check_no_generated_data(run)
    check_metadata(run)
    check_json(run)
    check_python_syntax(run)
    check_js_syntax(run)
    check_web_contract(run)
    check_js_imports(run)
    check_sql(run)
    check_packaging(run)
    check_code_graph(run)

    print()
    if run.warnings:
        print(f"Warnings: {len(run.warnings)}")
    if run.errors:
        print(f"FAILED: {len(run.errors)} error(s)")
        return 1
    print("PASSED: all blocking checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
