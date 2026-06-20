"""Thread-safe snapshots and issue contracts shared by QA stages."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeatureSnapshot:
    fid: int
    wkb: bytes
    bbox: tuple[float, float, float, float]
    attrs: dict[str, object]


@dataclass(frozen=True)
class LayerSnapshot:
    layer_id: str
    layer_name: str
    crs_wkt: str
    fields: list[str]
    features: list[FeatureSnapshot]
    preflight_hash: str


@dataclass
class QAIssue:
    rule_id: str
    severity: str
    feature_id: int | None
    layer_id: str
    geometry_ref: str | None
    bbox: tuple[float, float, float, float] | None
    description: str
    confidence: str = "deterministic"
