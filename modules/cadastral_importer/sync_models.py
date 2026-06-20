# -*- coding: utf-8 -*-
"""Result models for synchronized cadastral imports."""
from dataclasses import dataclass, field


@dataclass
class ImportIssue:
    level: str
    message: str
    detail: str = ""


@dataclass
class SyncImportResult:
    output_layer_names: list[str] = field(default_factory=list)
    output_layers: list[object] = field(default_factory=list)
    feature_counts: dict[str, int] = field(default_factory=dict)
    matched_gtp: int = 0
    matched_pol: int = 0
    matched_shp: int = 0
    matched_xml: int = 0
    unmatched: int = 0
    issues: list[ImportIssue] = field(default_factory=list)

