# -*- coding: utf-8 -*-
"""CLI tool for managing PyQt i18n workflow.

Commands:
    extract  – Scan .py sources, generate .ts files via pylupdate6/5.
    compile  – Compile .ts → .qm via lrelease.
    sync     – Run extract then compile.
    status   – Show translated / untranslated counts per .ts file.

Usage:
    python tools/i18n_manager.py extract
    python tools/i18n_manager.py compile
    python tools/i18n_manager.py sync
    python tools/i18n_manager.py status --languages vi en
"""

from __future__ import annotations

import argparse
import glob
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PLUGIN_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir)
)
I18N_DIR = os.path.join(PLUGIN_ROOT, "i18n")
SOURCE_DIRS = ["modules", "cadastral_tools"]
DEFAULT_LANGUAGES = ["vi", "en"]

# Candidate directories where QGIS / OSGeo4W may install Qt tools.
_QGIS_BIN_CANDIDATES: list[str] = []
if sys.platform == "win32":
    _program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    # Enumerate QGIS installs (e.g. QGIS 3.*, QGIS 4.*)
    for _entry in sorted(glob.glob(os.path.join(_program_files, "QGIS*")), reverse=True):
        _bin = os.path.join(_entry, "bin")
        if os.path.isdir(_bin):
            _QGIS_BIN_CANDIDATES.append(_bin)
        
        # Check Python Scripts directories (e.g. apps/Python312/Scripts)
        _apps = os.path.join(_entry, "apps")
        if os.path.isdir(_apps):
            for _py_dir in glob.glob(os.path.join(_apps, "Python*")):
                _scripts = os.path.join(_py_dir, "Scripts")
                if os.path.isdir(_scripts):
                    _QGIS_BIN_CANDIDATES.append(_scripts)
            
            # Check Qt apps bin (e.g. apps/qt6/bin)
            for _qt in ("qt6", "qt5"):
                _qt_bin = os.path.join(_apps, _qt, "bin")
                if os.path.isdir(_qt_bin):
                    _QGIS_BIN_CANDIDATES.append(_qt_bin)

    _osgeo = r"C:\OSGeo4W\bin"
    if os.path.isdir(_osgeo):
        _QGIS_BIN_CANDIDATES.append(_osgeo)


# ---------------------------------------------------------------------------
# Tool discovery helpers
# ---------------------------------------------------------------------------

def _find_tool(names: list[str]) -> str | None:
    """Return the first executable found on PATH or in QGIS bin dirs.

    *names* is tried in order (e.g. ``['pylupdate6', 'pylupdate5']``).
    """
    for name in names:
        # 1. Check PATH via shutil.which
        found = shutil.which(name)
        if found:
            return found
        # 2. Check QGIS / OSGeo4W candidate directories
        for candidate_dir in _QGIS_BIN_CANDIDATES:
            candidate = os.path.join(candidate_dir, name)
            if os.path.isfile(candidate):
                return candidate
            # Windows: try with .exe / .bat
            for ext in (".exe", ".bat"):
                candidate_ext = candidate + ext
                if os.path.isfile(candidate_ext):
                    return candidate_ext
    return None


def _find_pylupdate() -> str:
    tool = _find_tool(["pylupdate6", "pylupdate5"])
    if tool is None:
        _abort("pylupdate6 / pylupdate5 not found. "
               "Install PyQt6-tools or ensure QGIS bin is on PATH.")
    return tool


def _find_lrelease() -> str:
    tool = _find_tool(["lrelease", "lrelease-qt6", "lrelease-qt5"])
    if tool is None:
        _abort("lrelease not found. "
               "Install Qt linguist tools or ensure QGIS bin is on PATH.")
    # This return is never reached after _abort, but keeps mypy happy.
    return tool  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _abort(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)
    sys.exit(1)


def _info(msg: str) -> None:
    print(f"[i18n] {msg}")


def _collect_py_sources() -> list[str]:
    """Return relative paths (from *PLUGIN_ROOT*) of all ``*.py`` files
    under the configured source directories."""
    sources: list[str] = []
    for src_dir_name in SOURCE_DIRS:
        src_dir = os.path.join(PLUGIN_ROOT, src_dir_name)
        if not os.path.isdir(src_dir):
            continue
        for root, _dirs, files in os.walk(src_dir):
            for fname in sorted(files):
                if fname.endswith(".py"):
                    rel = os.path.relpath(os.path.join(root, fname), PLUGIN_ROOT)
                    sources.append(rel.replace("\\", "/"))
    return sources


def _ensure_i18n_dir() -> None:
    os.makedirs(I18N_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# .pro file generation
# ---------------------------------------------------------------------------

def _generate_pro(sources: list[str], languages: list[str]) -> str:
    """Write a temporary ``.pro`` file and return its path.

    The ``.pro`` file is placed inside *PLUGIN_ROOT* so that relative paths
    inside it resolve correctly when pylupdate processes it.
    """
    lines: list[str] = ["# Auto-generated by i18n_manager.py – DO NOT EDIT", ""]
    lines.append("SOURCES = \\")
    for i, src in enumerate(sources):
        suffix = " \\" if i < len(sources) - 1 else ""
        lines.append(f"    {src}{suffix}")
    lines.append("")
    ts_files = [f"i18n/{lang}.ts" for lang in languages]
    lines.append("TRANSLATIONS = \\")
    for i, ts in enumerate(ts_files):
        suffix = " \\" if i < len(ts_files) - 1 else ""
        lines.append(f"    {ts}{suffix}")
    lines.append("")

    # Write into plugin root so relative paths work
    fd, pro_path = tempfile.mkstemp(suffix=".pro", prefix="i18n_", dir=PLUGIN_ROOT)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return pro_path


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_extract(languages: list[str]) -> None:
    """Scan Python sources and generate / update ``.ts`` translation files."""
    _ensure_i18n_dir()
    sources = _collect_py_sources()
    if not sources:
        _abort("No .py source files found under: " + ", ".join(SOURCE_DIRS))

    pylupdate = _find_pylupdate()
    _info(f"Using: {pylupdate}")
    _info(f"Found {len(sources)} source file(s)")

    is_pyqt6 = "pylupdate6" in os.path.basename(pylupdate).lower()
    if is_pyqt6:
        # pylupdate6 (PyQt6) syntax: pylupdate6 --no-obsolete --ts <file> <sources...>
        for lang in languages:
            ts_path = os.path.join(I18N_DIR, f"{lang}.ts")
            cmd = [pylupdate, "--no-obsolete", "--ts", ts_path] + sources
            _info(f"Running: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                cwd=PLUGIN_ROOT,
                capture_output=True,
                text=True,
            )
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            if result.returncode != 0:
                _abort(f"pylupdate6 exited with code {result.returncode} for {lang}")
    else:
        # pylupdate5 (PyQt5) syntax uses .pro file
        pro_path = _generate_pro(sources, languages)
        try:
            cmd = [pylupdate, "-noobsolete", pro_path]
            _info(f"Running: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                cwd=PLUGIN_ROOT,
                capture_output=True,
                text=True,
            )
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            if result.returncode != 0:
                _abort(f"pylupdate exited with code {result.returncode}")
        finally:
            # Clean up temporary .pro file
            try:
                os.remove(pro_path)
            except OSError:
                pass

    # Summary
    print()
    _info("=== Extract Summary ===")
    for lang in languages:
        ts_path = os.path.join(I18N_DIR, f"{lang}.ts")
        exists = os.path.isfile(ts_path)
        _info(f"  {lang}.ts : {'OK' if exists else 'MISSING'}")
    _info("Done.")


def cmd_compile(languages: list[str]) -> None:
    """Compile all ``.ts`` files into ``.qm`` binary files."""
    _ensure_i18n_dir()
    lrelease = _find_lrelease()
    _info(f"Using: {lrelease}")

    ts_files = []
    for lang in languages:
        ts_path = os.path.join(I18N_DIR, f"{lang}.ts")
        if os.path.isfile(ts_path):
            ts_files.append(ts_path)
        else:
            _info(f"  [SKIP] {lang}.ts not found – run 'extract' first.")

    if not ts_files:
        _abort("No .ts files found to compile.")

    for ts_path in ts_files:
        qm_path = ts_path.rsplit(".", 1)[0] + ".qm"
        cmd = [lrelease, ts_path, "-qm", qm_path]
        _info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            cwd=PLUGIN_ROOT,
            capture_output=True,
            text=True,
        )
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        if result.returncode != 0:
            _info(f"  [WARN] lrelease exited with code {result.returncode} for {ts_path}")

    # Summary
    print()
    _info("=== Compile Summary ===")
    for lang in languages:
        qm_path = os.path.join(I18N_DIR, f"{lang}.qm")
        exists = os.path.isfile(qm_path)
        _info(f"  {lang}.qm : {'OK' if exists else 'MISSING'}")
    _info("Done.")


def cmd_sync(languages: list[str]) -> None:
    """Run extract followed by compile."""
    cmd_extract(languages)
    print()
    cmd_compile(languages)


def cmd_status(languages: list[str]) -> None:
    """Parse ``.ts`` XML files and print translated / untranslated counts."""
    _ensure_i18n_dir()
    print()
    _info("=== Translation Status ===")

    for lang in languages:
        ts_path = os.path.join(I18N_DIR, f"{lang}.ts")
        if not os.path.isfile(ts_path):
            _info(f"  {lang}.ts : NOT FOUND")
            continue

        try:
            tree = ET.parse(ts_path)  # noqa: S314
        except ET.ParseError as exc:
            _info(f"  {lang}.ts : PARSE ERROR – {exc}")
            continue

        root = tree.getroot()
        total = 0
        translated = 0
        untranslated = 0
        obsolete = 0
        unfinished = 0

        for message in root.iter("message"):
            total += 1
            translation_el = message.find("translation")
            if translation_el is None:
                untranslated += 1
                continue
            msg_type = translation_el.get("type", "")
            if msg_type == "obsolete":
                obsolete += 1
            elif msg_type == "unfinished":
                unfinished += 1
            elif translation_el.text:
                translated += 1
            else:
                untranslated += 1

        _info(f"  {lang}.ts : {total} total | "
              f"{translated} translated | "
              f"{unfinished} unfinished | "
              f"{untranslated} untranslated | "
              f"{obsolete} obsolete")

    _info("Done.")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="i18n_manager",
        description="Manage PyQt i18n workflow for VNU2F_QLDDK68 plugin.",
    )
    parser.add_argument(
        "command",
        choices=["extract", "compile", "sync", "status"],
        help="Action to perform.",
    )
    parser.add_argument(
        "--languages",
        nargs="+",
        default=DEFAULT_LANGUAGES,
        metavar="LANG",
        help="Language codes to process (default: %(default)s).",
    )
    args = parser.parse_args()

    dispatch = {
        "extract": cmd_extract,
        "compile": cmd_compile,
        "sync": cmd_sync,
        "status": cmd_status,
    }
    dispatch[args.command](args.languages)


if __name__ == "__main__":
    main()
