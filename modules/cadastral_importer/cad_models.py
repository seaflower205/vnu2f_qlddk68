# -*- coding: utf-8 -*-
"""CAD result models and source selection helpers."""
from dataclasses import dataclass, field

CAD_EXTENSIONS = (".dxf", ".dgn", ".dwg")

@dataclass
class CadImportIssue:
    level: str
    message: str
    detail: str = ""


@dataclass
class CadSourceLayerSummary:
    name: str
    uri: str
    valid: bool
    feature_count: int = 0
    geometry_type: str = ""
    error: str = ""
    layer: object | None = field(default=None, repr=False, compare=False)


@dataclass
class CadImportResult:
    cad_path: str
    cad_format: str
    crs_authid: str
    source_layers: list[CadSourceLayerSummary] = field(default_factory=list)
    output_layer_names: list[str] = field(default_factory=list)
    output_layers: list[object] = field(default_factory=list)
    feature_counts: dict[str, int] = field(default_factory=dict)
    skipped_features: int = 0
    issues: list[CadImportIssue] = field(default_factory=list)


def find_cad_path(group) -> str | None:
    """Return the first CAD source path from a SourceGroup-like object."""
    for extension in CAD_EXTENSIONS:
        path = group.get(extension) if group else None
        if path:
            return path
    return None


def is_dgn_v8(filepath: str) -> bool:
    """Return whether a DGN source uses the V8 compound-file signature."""
    try:
        with open(filepath, "rb") as stream:
            return stream.read(8) == b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"
    except OSError:
        return False


