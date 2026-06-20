# -*- coding: utf-8 -*-
"""Build a clean QGIS plugin zip — Smart Packaging (Strict Whitelist).

The archive contains only runtime files needed by QGIS. Development notes,
screenshots, crash probes, caches, old test databases and generated artifacts
are intentionally excluded so QGIS/Antigravity does not pick up stale code.

Usage:
    python tools/package_plugin.py              # Build ZIP
    python tools/package_plugin.py --dry-run    # List files only, don't create ZIP
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import zipfile
from pathlib import Path

try:
    from tools.analyze_code_graph import build_graph, load_rules, validate_graph
except ModuleNotFoundError:  # Direct execution: python tools/package_plugin.py
    from analyze_code_graph import build_graph, load_rules, validate_graph

# Ensure UTF-8 output on Windows (box-drawing characters in reports)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass  # Python < 3.7


PLUGIN_NAME = "vnu2f_qlddk68"

# Baseline size from v0.3.0 build (bytes)
BASELINE_BYTES = 2_346_410

# ═══════════════════════════════════════════════════════════════════════
# STRICT WHITELIST — Chỉ file khớp pattern dưới đây mới vào ZIP
# ═══════════════════════════════════════════════════════════════════════

WHITELIST_ROOT_FILES = {
    "__init__.py",
    "vnu2f_qlddk68.py",
    "metadata.txt",
    "requirements-qgis.txt",
    "icon.png",
    "icon_basemap.svg",
    "icon_cad.svg",
    "icon_crs.svg",
    "icon_db.svg",
    "icon_font.svg",
    "icon_share.svg",
    "icon_copy.svg",
    "icon_history.svg",
}

WHITELIST_DIRS = {
    "config",
    "data",
    "modules",
    "webgis_demo",
    "templates",
    "vendor",
    "cadastral_tools",
    "i18n",
}

# ═══════════════════════════════════════════════════════════════════════
# HARD BLACKLIST — Bất kỳ path chứa pattern này → loại bỏ tuyệt đối
# ═══════════════════════════════════════════════════════════════════════

BLACKLIST_DIRS = {
    "__pycache__",
    ".git",
    ".ruff_cache",
    ".mypy_cache",
    ".pytest_cache",
    "tests",
    "test",
    "scratch",
    "cache",
    "screenshots",
    "ui_preview",
    "dist",
    ".agents",
    ".github",
    "node_modules",
    ".qgis-settings",
}

BLACKLIST_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".log",
    ".tmp",
    ".bak",
    ".md",
    ".ts",
}

BLACKLIST_FILES = {
    "parcels.geojson",
    "cad_reader.exe",
    "cad_reader",
    ".coverage",
    ".gitignore",
    "docker-compose.langfuse.yml",
    "clidsi.log",
    "generate_templates.py",
}

# ═══════════════════════════════════════════════════════════════════════
# TOOLS ALLOWLIST — Cho phép các runtime files xác định trong tools/
# ═══════════════════════════════════════════════════════════════════════

ALLOWED_TOOLS_PREFIXES = (
    "tools/libraries/topology-tools/src/topology_tools/",
    "tools/libraries/vn_mapfont_converter/vn_mapfont_converter/",
)

ALLOWED_TOOLS_FILES = {
    "tools/libraries/topology-tools/bin/cad_reader_windows.exe",
}



def _is_runtime_file(path: Path, root: Path) -> bool:
    """Determine if a file should be included in the plugin ZIP.

    Three-stage filter:
    1. HARD BLACKLIST: reject any path containing blacklisted dir/ext/name
    2. VENDOR & TOOLS special rules: allow specific runtime parts
    3. WHITELIST: only allow files under whitelisted dirs or root file set
    """
    rel = path.relative_to(root)
    parts = rel.parts

    # ── Stage 1: Hard blacklist ──
    if any(part in BLACKLIST_DIRS for part in parts[:-1]):
        return False
    if path.name in BLACKLIST_FILES:
        return False
    if path.suffix.lower() in BLACKLIST_EXTENSIONS:
        return False
    # Exclude webgis_demo/tools/ sub-directory
    if len(parts) > 1 and parts[0] == "webgis_demo" and parts[1] == "tools":
        return False

    # ── Stage 2: Vendor & Tools special rules ──
    if not parts:
        return False

    if parts[0] == "vendor":
        if len(parts) >= 2 and parts[1] == "olefile":
            # Only pack python files, license, and contributors txt to minimize size
            if path.suffix.lower() == ".py" or path.name in {"LICENSE.txt", "CONTRIBUTORS.txt"}:
                return True
            return False
        if len(parts) == 3 and parts[1] == "wheels" and path.suffix.lower() == ".whl":
            return True
        if len(parts) == 2 and path.name in {"vendor.json"}:
            return True
        return False

    if parts[0] == "tools":
        rel_posix = rel.as_posix()
        return (
            rel_posix in ALLOWED_TOOLS_FILES
            or any(
                rel_posix.startswith(prefix) and rel_posix.endswith(".py")
                for prefix in ALLOWED_TOOLS_PREFIXES
            )
        )

    # ── Stage 3: Whitelist ──
    if len(parts) == 1:
        return parts[0] in WHITELIST_ROOT_FILES
    return parts[0] in WHITELIST_DIRS


def build_package(root: Path, *, dry_run: bool = False) -> Path | None:
    """Build the plugin ZIP archive.

    Args:
        root: Plugin project root directory.
        dry_run: If True, list files only without creating ZIP.

    Returns:
        Path to the created ZIP, or None if dry_run.
    """
    try:
        rules = load_rules()
        graph = build_graph(root, rules)
    except (OSError, ValueError, SyntaxError) as exc:
        raise RuntimeError(f"Code graph could not be built: {exc}") from exc
    violations = validate_graph(graph, rules)
    if violations:
        details = "\n  - ".join(violations)
        raise RuntimeError(f"Code graph check failed; package refused:\n  - {details}")
    print(f"  Code graph check passed ({len(graph['nodes'])} modules)")

    dist_dir = root / "dist"
    stage_root = dist_dir / PLUGIN_NAME
    zip_path = dist_dir / f"{PLUGIN_NAME}.zip"
    manifest_path = dist_dir / "package_manifest.txt"

    # Collect files
    manifest_entries: list[str] = []
    file_count = 0

    for path in sorted(root.rglob("*")):
        if not path.is_file() or not _is_runtime_file(path, root):
            continue
        rel = path.relative_to(root)
        manifest_entries.append(rel.as_posix())
        file_count += 1

    # ── Dry-run mode ──
    if dry_run:
        print(f"╔══════════════════════════════════════════════════╗")
        print(f"║  📦 SMART PACKAGING — DRY RUN                    ║")
        print(f"╠══════════════════════════════════════════════════╣")
        print(f"║  Files to include: {file_count:<29}║")
        print(f"╚══════════════════════════════════════════════════╝")
        print()
        for entry in manifest_entries:
            print(f"  ✓ {entry}")
        print(f"\n  Total: {file_count} files")

        # Write manifest even in dry-run
        dist_dir.mkdir(parents=True, exist_ok=True)
        with open(manifest_path, "w", encoding="utf-8") as f:
            for entry in manifest_entries:
                f.write(f"{entry}\n")
        print(f"  Manifest: {manifest_path}")
        return None

    # ── Build ZIP ──
    if stage_root.exists():
        shutil.rmtree(stage_root)
    if zip_path.exists():
        zip_path.unlink()

    stage_root.mkdir(parents=True, exist_ok=True)

    for path in root.rglob("*"):
        if not path.is_file() or not _is_runtime_file(path, root):
            continue
        rel = path.relative_to(root)
        target = stage_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(stage_root.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(dist_dir).as_posix())

    shutil.rmtree(stage_root)

    # ── Clean up other zip files in dist/ to avoid confusion ──
    for item in dist_dir.glob("*.zip"):
        if item.name != zip_path.name:
            try:
                item.unlink()
                print(f"  Removed stale/unoptimized archive: {item.name}")
            except Exception:
                pass

    # ── Write manifest ──
    with open(manifest_path, "w", encoding="utf-8") as f:
        for entry in manifest_entries:
            f.write(f"{entry}\n")

    # ═══ Size comparison report ═══
    zip_size = zip_path.stat().st_size
    baseline_mb = BASELINE_BYTES / (1024 * 1024)
    current_mb = zip_size / (1024 * 1024)
    saved_mb = baseline_mb - current_mb
    saved_pct = (saved_mb / baseline_mb) * 100 if baseline_mb > 0 else 0

    print(f"╔══════════════════════════════════════════════════╗")
    print(f"║  📦 SMART PACKAGING REPORT                       ║")
    print(f"╠══════════════════════════════════════════════════╣")
    print(f"║  Baseline (v0.3.0):  {baseline_mb:>7.2f} MB                ║")
    print(f"║  Current build:      {current_mb:>7.2f} MB                ║")
    print(f"║  Saved:              {saved_mb:>7.2f} MB ({saved_pct:>5.1f}%)       ║")
    print(f"║  Files in package:   {file_count:>7}                    ║")
    print(f"║  Manifest:           dist/package_manifest.txt   ║")
    print(f"╚══════════════════════════════════════════════════╝")

    return zip_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a clean QGIS plugin zip (Strict Whitelist)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files to include without creating the ZIP archive.",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    try:
        result = build_package(root, dry_run=args.dry_run)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if result is not None:
        print(f"\n  Output: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
