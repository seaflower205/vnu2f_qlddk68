# -*- coding: utf-8 -*-
"""Pure normalization helpers shared by cadastral synchronization."""
try:
    from ..crs_converter.font_utils import convert_tcvn3_to_unicode
except Exception:
    def convert_tcvn3_to_unicode(text):
        return text

def _sheet_parcel(sheet, parcel):
    sheet_int = _safe_int(sheet)
    parcel_int = _safe_int(parcel)
    if sheet_int is None or parcel_int is None:
        return None
    return sheet_int, parcel_int


def _first_int(attrs, names):
    return _safe_int(_first_text(attrs, names))


def _first_float(attrs, names):
    return _safe_float(_first_text(attrs, names))


def _first_text(attrs, names):
    normalized = {_normalize_key(key): value for key, value in attrs.items()}
    for name in names:
        value = normalized.get(_normalize_key(name))
        if value not in (None, ""):
            return str(value)
    return ""


def _convert_attrs_tcvn3(attrs):
    return {
        key: convert_tcvn3_to_unicode(value) if isinstance(value, str) else value
        for key, value in attrs.items()
    }


def _normalize_key(value):
    return "".join(ch for ch in str(value).lower() if ch.isalnum())


def _safe_int(value):
    if value in (None, ""):
        return None
    try:
        text = str(value).strip()
        if not text or "*" in text:
            return None
        return int(float(text))
    except (TypeError, ValueError):
        return None


def _safe_float(value):
    if value in (None, ""):
        return None
    try:
        text = str(value).strip().replace(",", ".")
        if not text or "*" in text:
            return None
        return float(text)
    except (TypeError, ValueError):
        return None


def _text(value):
    return "" if value is None else str(value).strip()


def _append_unique(values, value):
    value = _text(value)
    if value and value not in values:
        values.append(value)


def _first_present(*values):
    for value in values:
        if value not in (None, ""):
            return value
    return None
