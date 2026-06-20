# -*- coding: utf-8 -*-
"""Detect related cadastral source files in a folder."""

from __future__ import annotations

import os
from dataclasses import dataclass, field



KNOWN_EXTENSIONS = {
    ".dgn",
    ".dwg",
    ".dxf",
    ".gtp",
    ".pol",
    ".gcn",
    ".txt",
    ".shp",
    ".shx",
    ".dbf",
    ".prj",
    ".cpg",
    ".xml",
}


@dataclass
class SourceGroup:
    stem: str
    folder: str
    files: dict[str, str] = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        return os.path.basename(self.stem)

    def get(self, extension: str) -> str | None:
        return self.files.get(extension.lower())


def scan_sources(path: str) -> list[SourceGroup]:
    """Scan a folder or a selected file and group cadastral sidecars by stem."""
    if os.path.isfile(path):
        root_folder = os.path.dirname(path)
    else:
        root_folder = path

    groups: dict[str, SourceGroup] = {}
    for current_folder, _, file_names in os.walk(root_folder):
        for file_name in file_names:
            ext = os.path.splitext(file_name)[1].lower()
            if ext not in KNOWN_EXTENSIONS:
                continue
            full_path = os.path.join(current_folder, file_name)
            stem = os.path.splitext(full_path)[0]
            group = groups.setdefault(
                stem,
                SourceGroup(stem=stem, folder=current_folder),
            )
            group.files[ext] = full_path

    if os.path.isfile(path):
        selected_stem = os.path.splitext(path)[0]
        if selected_stem in groups:
            return [groups[selected_stem]]

    return sorted(groups.values(), key=lambda item: item.stem.lower())


def find_primary_group(groups: list[SourceGroup]) -> SourceGroup | None:
    """Prefer CAD groups, with GTP/POL/SHP sidecars treated as sync data."""
    for ext in (".dwg", ".dgn", ".dxf"):
        for group in groups:
            if group.get(ext):
                return group
    return groups[0] if groups else None
