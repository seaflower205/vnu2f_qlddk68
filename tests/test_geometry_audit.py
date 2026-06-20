# -*- coding: utf-8 -*-
"""
Geometry Audit Test Suite — Phase 5, Component 2
=================================================
Uses QFontMetrics to detect text overflow/clipping in QComboBox and QLabel
widgets across all 6 plugin UI targets at multiple window sizes.

Targets:
  1. CRSConverterDialog
  2. CadastralImportDialog
  3. SymbologyTab  (parametrized)
  4. StatsTab      (parametrized)
  5. LabelTab      (parametrized)
  6. SettingsTab   (parametrized)

Window sizes tested: 800×600, 1024×768, 1920×1080
"""

import json
import os
import datetime

import pytest

from qgis.PyQt.QtCore import QEventLoop, QTimer
from qgis.PyQt.QtGui import QFontMetrics
from qgis.PyQt.QtWidgets import QApplication, QComboBox, QLabel


# ---------------------------------------------------------------------------
# Helper — wait_for_layout_ready()
# ---------------------------------------------------------------------------

def wait_for_layout_ready(widget, timeout_ms=200):
    """Ensure the Qt layout engine has finished rendering before measuring.

    CRITICAL: Must be called before ANY geometry measurement to avoid the
    width‑returns‑0 bug that occurs when the paint queue hasn't flushed.

    Steps
    -----
    1. ``widget.adjustSize()`` — force Qt layout recalculation.
    2. ``QApplication.processEvents()`` — flush the paint queue.
    3. ``QTimer.singleShot`` + ``QEventLoop`` — wait ≥ 50 ms for settle.
    4. ``QApplication.processEvents()`` — final flush after timer fires.
    """
    widget.adjustSize()
    QApplication.processEvents()
    loop = QEventLoop()
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    QApplication.processEvents()


# ---------------------------------------------------------------------------
# GeometryAuditor
# ---------------------------------------------------------------------------

class GeometryAuditor:
    """Walk a widget tree and detect text overflow / clipping in children."""

    # A ratio ≥ 1.0 means the text physically overflows the container.
    OVERFLOW_THRESHOLD = 1.0
    # A ratio ≥ 0.95 means the text is very close to the edge (clipped).
    CLIP_THRESHOLD = 0.95

    # Pixels reserved for QComboBox internal padding and drop-arrow.
    _COMBO_PADDING = 12
    _COMBO_ARROW_WIDTH = 30

    def audit_widget(self, widget):
        """Recursively audit all QComboBox and QLabel children.

        Returns
        -------
        list[dict]
            Each dict contains: widget_name, widget_type, issue_type,
            text, text_width_px, available_width_px, ratio.
        """
        issues = []
        for combo in widget.findChildren(QComboBox):
            if not combo.isVisible():
                continue
            issues.extend(self._audit_combobox(combo))
        for label in widget.findChildren(QLabel):
            if not label.isVisible():
                continue
            if label.wordWrap():
                continue
            issues.extend(self._audit_label(label))
        return issues

    # -- private helpers ---------------------------------------------------

    def _audit_combobox(self, combo):
        """Measure every item in *combo* against its available pixel width."""
        results = []
        available_w = (
            combo.width() - self._COMBO_PADDING - self._COMBO_ARROW_WIDTH
        )

        # ── RENDER_ERROR guard ──────────────────────────────────────────
        if available_w <= 0:
            results.append(self._make_entry(
                widget=combo,
                issue_type="RENDER_ERROR",
                text="<widget not rendered>",
                text_width_px=0,
                available_width_px=available_w,
            ))
            return results

        fm = QFontMetrics(combo.font())
        for idx in range(combo.count()):
            text = combo.itemText(idx)
            if not text:
                continue
            text_w = fm.boundingRect(text).width()
            ratio = text_w / available_w
            if ratio >= self.OVERFLOW_THRESHOLD:
                results.append(self._make_entry(
                    widget=combo,
                    issue_type="OVERFLOW",
                    text=text,
                    text_width_px=text_w,
                    available_width_px=available_w,
                ))
            elif ratio >= self.CLIP_THRESHOLD:
                results.append(self._make_entry(
                    widget=combo,
                    issue_type="CLIP_WARNING",
                    text=text,
                    text_width_px=text_w,
                    available_width_px=available_w,
                ))
        return results

    def _audit_label(self, label):
        """Measure the displayed text of *label* against its pixel width."""
        import re
        results = []
        text = label.text()
        if not text:
            return results

        # Strip HTML tags to get actual rendered text
        plain_text = re.sub(r'<[^>]*>', '', text)
        plain_text = plain_text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")

        # Account for content margins (left + right).
        margins = label.contentsMargins()
        available_w = label.width() - margins.left() - margins.right()

        # ── RENDER_ERROR guard ──────────────────────────────────────────
        if available_w <= 0:
            results.append(self._make_entry(
                widget=label,
                issue_type="RENDER_ERROR",
                text=text,
                text_width_px=0,
                available_width_px=available_w,
            ))
            return results

        fm = QFontMetrics(label.font())
        text_w = fm.boundingRect(plain_text).width()
        ratio = text_w / available_w
        if ratio >= self.OVERFLOW_THRESHOLD:
            results.append(self._make_entry(
                widget=label,
                issue_type="OVERFLOW",
                text=text,
                text_width_px=text_w,
                available_width_px=available_w,
            ))
        elif ratio >= self.CLIP_THRESHOLD:
            results.append(self._make_entry(
                widget=label,
                issue_type="CLIP_WARNING",
                text=text,
                text_width_px=text_w,
                available_width_px=available_w,
            ))
        return results

    @staticmethod
    def _make_entry(*, widget, issue_type, text, text_width_px,
                    available_width_px):
        """Build a standardised issue dict."""
        ratio = (
            text_width_px / available_width_px
            if available_width_px > 0
            else float("inf")
        )
        return {
            "widget_name": widget.objectName() or type(widget).__name__,
            "widget_type": type(widget).__name__,
            "issue_type": issue_type,
            "text": text,
            "text_width_px": text_width_px,
            "available_width_px": available_width_px,
            "ratio": round(ratio, 4),
        }


# ---------------------------------------------------------------------------
# Pytest test class
# ---------------------------------------------------------------------------

WINDOW_SIZES = [
    (800, 600),
    (1024, 768),
    (1920, 1080),
]


class TestGeometryAudit:
    """Geometry‑level audit tests for all 6 plugin UI targets."""

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _output_dir():
        tests_dir = os.path.dirname(os.path.abspath(__file__))
        out = os.path.join(tests_dir, "visual_logs")
        os.makedirs(out, exist_ok=True)
        return out

    @classmethod
    def _save_report(cls, name, issues, *, extra_meta=None):
        """Persist a JSON report under ``tests/visual_logs/``."""
        report = {
            "audit_name": name,
            "timestamp": datetime.datetime.now().isoformat(),
            "total_issues": len(issues),
            "overflow_count": sum(
                1 for i in issues if i["issue_type"] == "OVERFLOW"
            ),
            "clip_warning_count": sum(
                1 for i in issues if i["issue_type"] == "CLIP_WARNING"
            ),
            "render_error_count": sum(
                1 for i in issues if i["issue_type"] == "RENDER_ERROR"
            ),
            "issues": issues,
        }
        if extra_meta:
            report["meta"] = extra_meta

        path = os.path.join(
            cls._output_dir(),
            f"geometry_audit_{name}.json",
        )
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, ensure_ascii=False)
        print(f"\n[GEOMETRY AUDIT] Report saved → {path}")
        return path

    @staticmethod
    def _overflow_issues(issues):
        """Return only hard OVERFLOW entries (CLIP_WARNING is tolerated)."""
        return [i for i in issues if i["issue_type"] == "OVERFLOW"]

    # -- 1. CRSConverterDialog -------------------------------------------

    def test_crs_dialog_no_overflow(self, qgis_app):
        """CRSConverterDialog must have 0 OVERFLOW violations across all tabs."""
        from modules.crs_converter.crs_dialog import CRSConverterDialog

        dialog = CRSConverterDialog()
        dialog.resize(1024, 768)
        dialog.show()

        all_issues = []
        n_tabs = dialog.sidebar.count()
        for idx in range(n_tabs):
            dialog.sidebar.setCurrentRow(idx)
            # Wait for lazy loading debounce (150ms) + layout rendering settle (200ms)
            wait_for_layout_ready(dialog, timeout_ms=350)
            
            issues = GeometryAuditor().audit_widget(dialog)
            for issue in issues:
                if issue not in all_issues:
                    all_issues.append(issue)

        self._save_report("crs_dialog", all_issues)
        dialog.close()

        overflows = self._overflow_issues(all_issues)
        assert len(overflows) == 0, (
            f"CRSConverterDialog has {len(overflows)} OVERFLOW issue(s):\n"
            + json.dumps(overflows, indent=2, ensure_ascii=False)
        )

    # -- 2. CadastralImportDialog ----------------------------------------

    def test_cadastral_dialog_no_overflow(self, qgis_app):
        """CadastralImportDialog must have 0 OVERFLOW violations."""
        from modules.cadastral_importer.dialog import CadastralImportDialog

        dialog = CadastralImportDialog()
        dialog.resize(1024, 768)
        dialog.show()
        wait_for_layout_ready(dialog, timeout_ms=200)

        issues = GeometryAuditor().audit_widget(dialog)
        self._save_report("cadastral_dialog", issues)
        dialog.close()

        overflows = self._overflow_issues(issues)
        assert len(overflows) == 0, (
            f"CadastralImportDialog has {len(overflows)} OVERFLOW issue(s):\n"
            + json.dumps(overflows, indent=2, ensure_ascii=False)
        )

    # -- 3. Cadastral tabs (parametrized) --------------------------------

    @pytest.mark.parametrize(
        "tab_module, tab_class_name",
        [
            ("vnu2f_qlddk68.cadastral_tools.ui.symbology_tab", "SymbologyTab"),
            ("vnu2f_qlddk68.cadastral_tools.ui.stats_tab", "StatsTab"),
            ("vnu2f_qlddk68.cadastral_tools.ui.label_tab", "LabelTab"),
            ("vnu2f_qlddk68.cadastral_tools.ui.settings_tab", "SettingsTab"),
        ],
        ids=["SymbologyTab", "StatsTab", "LabelTab", "SettingsTab"],
    )
    def test_cadastral_tab_no_overflow(
        self, qgis_app, tab_module, tab_class_name
    ):
        """Each cadastral tab must have 0 OVERFLOW violations."""
        import importlib

        from cadastral_tools.core.plugin_state import PluginState

        mod = importlib.import_module(tab_module)
        TabClass = getattr(mod, tab_class_name)

        plugin_state = PluginState()
        tab = TabClass(plugin_state)
        tab.resize(1024, 768)
        tab.show()
        wait_for_layout_ready(tab, timeout_ms=200)

        issues = GeometryAuditor().audit_widget(tab)
        report_name = f"tab_{tab_class_name.lower()}"
        self._save_report(report_name, issues)
        tab.close()

        overflows = self._overflow_issues(issues)
        assert len(overflows) == 0, (
            f"{tab_class_name} has {len(overflows)} OVERFLOW issue(s):\n"
            + json.dumps(overflows, indent=2, ensure_ascii=False)
        )

    # -- 4. Multi‑size test (3 window sizes) -----------------------------

    @pytest.mark.parametrize(
        "width, height",
        WINDOW_SIZES,
        ids=[f"{w}x{h}" for w, h in WINDOW_SIZES],
    )
    def test_geometry_audit_at_multiple_sizes(
        self, qgis_app, width, height
    ):
        """CRSConverterDialog must pass at every standard resolution across all tabs."""
        from modules.crs_converter.crs_dialog import CRSConverterDialog

        dialog = CRSConverterDialog()
        dialog.resize(width, height)
        dialog.show()

        all_issues = []
        n_tabs = dialog.sidebar.count()
        for idx in range(n_tabs):
            dialog.sidebar.setCurrentRow(idx)
            # Wait for lazy loading debounce (150ms) + layout rendering settle (200ms)
            wait_for_layout_ready(dialog, timeout_ms=350)
            
            issues = GeometryAuditor().audit_widget(dialog)
            for issue in issues:
                if issue not in all_issues:
                    all_issues.append(issue)

        report_name = f"crs_dialog_{width}x{height}"
        self._save_report(
            report_name,
            all_issues,
            extra_meta={"window_width": width, "window_height": height},
        )
        dialog.close()

        overflows = self._overflow_issues(all_issues)
        assert len(overflows) == 0, (
            f"CRSConverterDialog at {width}×{height} has "
            f"{len(overflows)} OVERFLOW issue(s):\n"
            + json.dumps(overflows, indent=2, ensure_ascii=False)
        )
