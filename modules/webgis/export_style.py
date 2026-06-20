# -*- coding: utf-8 -*-
"""Renderer and color helpers for WebGIS exports."""

def _build_renderer_color_lookup(layer) -> dict:
    """Build a mapping {str(value) -> hex_color} from the layer's renderer.

    Reads the renderer's category/symbol definitions directly via Python
    properties.  This avoids calling ``symbolForFeature`` which requires
    ``startRender``/``stopRender`` and can cause C++ access-violation
    crashes (segfaults) that Python ``try/except`` cannot catch.
    """
    lookup = {}
    try:
        renderer = layer.renderer()
        if renderer is None:
            return lookup

        class_name = renderer.__class__.__name__

        if class_name == "QgsCategorizedSymbolRenderer":
            for cat in renderer.categories():
                sym = cat.symbol()
                if sym:
                    lookup[str(cat.value())] = sym.color().name()

        elif class_name == "QgsGraduatedSymbolRenderer":
            for rng in renderer.ranges():
                sym = rng.symbol()
                if sym:
                    # Use range label as key since graduated doesn't have discrete values
                    lookup[rng.label()] = sym.color().name()

        elif class_name == "QgsSingleSymbolRenderer":
            sym = renderer.symbol()
            if sym:
                lookup["__default__"] = sym.color().name()

        elif class_name == "QgsRuleBasedRenderer":
            # Walk the rule tree and extract colors from leaf rules
            root = renderer.rootRule()
            if root:
                for rule in root.descendants():
                    sym = rule.symbol()
                    if sym:
                        label = rule.label() or rule.filterExpression() or "__rule__"
                        lookup[str(label)] = sym.color().name()
    except Exception:  # noqa: BLE001 — intentional suppress
        pass
    return lookup


def _lookup_feature_color(color_lookup: dict, feature, classify_field: str | None) -> str | None:
    """Try to find a feature's color from a pre-built color lookup table."""
    if not color_lookup:
        return None

    # 1. Single symbol renderer — one color for all features
    if "__default__" in color_lookup and len(color_lookup) == 1:
        return color_lookup["__default__"]

    # 2. Categorized renderer — match feature attribute value
    if classify_field:
        try:
            val = str(feature[classify_field])
            if val in color_lookup:
                return color_lookup[val]
        except Exception:  # noqa: BLE001 — intentional suppress
            pass

    # 3. Try matching any property value against the lookup
    try:
        for val in color_lookup:
            if val.startswith("__"):
                continue
            try:
                fval = str(feature[val]) if feature.fields().indexOf(val) >= 0 else None
            except Exception:  # noqa: BLE001 — intentional suppress
                fval = None
            if fval and fval in color_lookup:
                return color_lookup[fval]
    except Exception:  # noqa: BLE001 — intentional suppress
        pass

    return None


def _get_classify_field(layer) -> str | None:
    """Return the classification attribute field name from the renderer, if any."""
    try:
        renderer = layer.renderer()
        if renderer and hasattr(renderer, "classAttribute"):
            return renderer.classAttribute()
    except Exception:  # noqa: BLE001 — intentional suppress
        pass
    return None


def _context_color(launcher, feature, kind, color_lookup=None, classify_field=None) -> str:
    color = _lookup_feature_color(color_lookup or {}, feature, classify_field)
    if color:
        return color
    colors = {
        "cafe": "#a16207",
        "school": "#2563eb",
        "food": "#dc2626",
        "road": "#f97316",
        "water": "#0284c7",
        "place": "#059669",
        "point": "#7c3aed",
        "line": "#f97316",
        "area": "#22c55e",
    }
    return colors.get(kind, "#64748b")

def _feature_color(launcher, feature, land_code, color_lookup=None, classify_field=None) -> str:
    color = _lookup_feature_color(color_lookup or {}, feature, classify_field)
    if color:
        return color
    return _land_color(launcher, land_code)

def _land_color(launcher, code) -> str:
    return launcher.land_type_colors.get(str(code).upper(), "#8ab4f8")

def _clamp_color(value) -> int:
    try:
        return max(0, min(255, int(value)))
    except (TypeError, ValueError):
        return 0

