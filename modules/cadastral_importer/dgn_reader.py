# -*- coding: utf-8 -*-
"""Native DGN V8 parser and geometry/attribute extractor."""
from ..common.common_utils import log_warning


import os
import sys
import zlib
import struct
import json

from qgis.PyQt.QtCore import QVariant
from qgis.core import (
    QgsFeature,
    QgsField,
    QgsFields,
    QgsGeometry,
    QgsProject,
    QgsVectorLayer,
    QgsPointXY,
)
from ..crs_converter.font_utils import convert_tcvn3_to_unicode
from .layer_runtime import add_generated_layer, remove_previous_generated_layers

# Note: We import CadImportResult and CadImportIssue locally inside functions 
# to avoid circular dependency loops with cad_reader.py




from .dgn_native import import_dgn_v8_native

from .dgn_loader import _load_dgn_json_into_layers
