# -*- coding: utf-8 -*-
"""
topology_tools - Standalone library for geometry cleaning, polygonization, and topology validation.
"""

from .line_cleaner import clean_lines
from .geometry_validator import validate_and_repair, check_topology_errors
from .polygonizer import create_polygons, assign_labels

__version__ = "1.0.0"

__all__ = [
    "clean_lines",
    "validate_and_repair",
    "check_topology_errors",
    "create_polygons",
    "assign_labels",
]
