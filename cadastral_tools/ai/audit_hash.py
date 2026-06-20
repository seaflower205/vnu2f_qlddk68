"""Mechanically extracted functions from audit_trail.py."""
from __future__ import annotations

import hashlib
import json

def compute_layer_hash(
    layer,
    stable_key_fields: tuple[str, ...] | None = (
        "ma_dvhc", "so_to", "so_thua",
    ),
) -> tuple[str, str]:
    """SHA-256 hash TOÀN PHẦN, deterministic.

    Sort order:
    1. Ưu tiên khóa nghiệp vụ: MaDVHC + SoTo + SoThua
    2. Fallback: feature.id() (ghi hash_stability="provider_fid")

    Feature ID có thể không ổn định sau export/import,
    nên KHÔNG coi là khóa pháp lý.

    Returns:
        (hex_digest, hash_stability)
        hash_stability = "business_key" | "provider_fid"
    """
    from .lookup_tables.field_mapping import resolve_field

    h = hashlib.sha256()
    hash_stability = "business_key"

    # 1. CRS
    h.update(layer.crs().toWkt().encode("utf-8"))

    # 2. Schema
    fields_schema = sorted(
        (f.name(), f.typeName()) for f in layer.fields()
    )
    h.update(
        json.dumps(fields_schema, sort_keys=True).encode("utf-8")
    )

    # 3. Resolve sort key fields
    resolved_keys: list[str] = []
    if stable_key_fields:
        field_names = [f.name() for f in layer.fields()]
        for canonical in stable_key_fields:
            actual = resolve_field(field_names, canonical)
            if actual:
                resolved_keys.append(actual)

    if not resolved_keys:
        hash_stability = "provider_fid"

    # 4. Sort + hash features
    def sort_key(feature):
        if resolved_keys:
            return tuple(
                str(feature[k]) if feature[k] is not None else ""
                for k in resolved_keys
            )
        return (feature.id(),)

    features = sorted(layer.getFeatures(), key=sort_key)

    for feature in features:
        geom = feature.geometry()
        if not geom.isNull():
            h.update(geom.asWkb())

        attrs = {}
        for i in range(len(layer.fields())):
            field_name = layer.fields()[i].name()
            value = feature[i]
            attrs[field_name] = (
                str(value) if value is not None else ""
            )
        h.update(
            json.dumps(
                attrs, sort_keys=True, ensure_ascii=False,
            ).encode("utf-8")
        )

    return h.hexdigest(), hash_stability
