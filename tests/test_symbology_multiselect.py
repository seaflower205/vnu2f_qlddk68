# -*- coding: utf-8 -*-
import os
import sys

# Ensure parent directory of the project is in sys.path so that
# vnu2f_qlddk68 is imported as a proper package, resolving relative imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
parent_dir = os.path.dirname(project_root)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QTableWidgetSelectionRange
from cadastral_tools.core.plugin_state import PluginState
from cadastral_tools.ui.symbology_tab import SymbologyTab

def test_symbology_multi_selection_sync(qgis_app):
    """Verify that changing a symbology attribute in one selected row updates all other selected rows,
    while leaving non-selected rows unchanged.
    """
    # 1. Initialize SymbologyTab
    state = PluginState()
    tab = SymbologyTab(state)
    
    # 2. Populate table with test configs
    configs = [
        {"code": "ONT", "name_vi": "Đất ở nông thôn", "fill_color": "#ff0000", "border_color": "#000000", "border_width_mm": 0.2, "pattern": "solid", "opacity": 1.0},
        {"code": "ODT", "name_vi": "Đất ở đô thị", "fill_color": "#00ff00", "border_color": "#000000", "border_width_mm": 0.3, "pattern": "solid", "opacity": 1.0},
        {"code": "BHK", "name_vi": "Đất trồng cây hàng năm khác", "fill_color": "#0000ff", "border_color": "#000000", "border_width_mm": 0.4, "pattern": "solid", "opacity": 1.0},
        {"code": "LUC", "name_vi": "Đất chuyên trồng lúa", "fill_color": "#ffff00", "border_color": "#000000", "border_width_mm": 0.5, "pattern": "solid", "opacity": 1.0},
    ]
    tab.load_code_configs_to_table(configs)
    
    assert tab.table.rowCount() == 4
    
    # 3. Select rows 0, 1, 2 programmatically (Extended Selection)
    range_select = QTableWidgetSelectionRange(0, 0, 2, 7)
    tab.table.setRangeSelected(range_select, True)
    
    # Verify selection
    selected_ranges = tab.table.selectedRanges()
    assert len(selected_ranges) == 1
    assert selected_ranges[0].topRow() == 0
    assert selected_ranges[0].bottomRow() == 2

    # --- Test 1: Background Color Sync ---
    # Change color on row 1 (which is selected) by updating its UserRole data
    item_bg_row1 = tab.table.item(1, 3)
    item_bg_row1.setData(Qt.ItemDataRole.UserRole, "#ff00ff")
    
    # Assert selected rows (0, 1, 2) are updated
    assert tab.table.item(0, 3).data(Qt.ItemDataRole.UserRole) == "#ff00ff"
    assert tab.table.item(1, 3).data(Qt.ItemDataRole.UserRole) == "#ff00ff"
    assert tab.table.item(2, 3).data(Qt.ItemDataRole.UserRole) == "#ff00ff"
    # Assert non-selected row (3) remains unchanged
    assert tab.table.item(3, 3).data(Qt.ItemDataRole.UserRole) == "#ffff00"

    # --- Test 2: Border Color Sync ---
    item_border_row0 = tab.table.item(0, 4)
    item_border_row0.setData(Qt.ItemDataRole.UserRole, "#123456")
    
    assert tab.table.item(0, 4).data(Qt.ItemDataRole.UserRole) == "#123456"
    assert tab.table.item(1, 4).data(Qt.ItemDataRole.UserRole) == "#123456"
    assert tab.table.item(2, 4).data(Qt.ItemDataRole.UserRole) == "#123456"
    assert tab.table.item(3, 4).data(Qt.ItemDataRole.UserRole) == "#000000"

    # --- Test 3: Border Width Sync ---
    item_width_row2 = tab.table.item(2, 5)
    item_width_row2.setText("1.25")
    
    assert tab.table.item(0, 5).text() == "1.25"
    assert tab.table.item(1, 5).text() == "1.25"
    assert tab.table.item(2, 5).text() == "1.25"
    assert tab.table.item(3, 5).text() == "0.50"

    # --- Test 4: Pattern Sync ---
    item_pattern_row1 = tab.table.item(1, 6)
    item_pattern_row1.setText("Horizontal Hatch")
    
    assert tab.table.item(0, 6).text() == "Horizontal Hatch"
    assert tab.table.item(1, 6).text() == "Horizontal Hatch"
    assert tab.table.item(2, 6).text() == "Horizontal Hatch"
    assert tab.table.item(3, 6).text() == "Solid"

    # --- Test 5: Opacity Sync ---
    item_opacity_row0 = tab.table.item(0, 7)
    item_opacity_row0.setText("75%")
    
    assert tab.table.item(0, 7).text() == "75%"
    assert tab.table.item(1, 7).text() == "75%"
    assert tab.table.item(2, 7).text() == "75%"
    assert tab.table.item(3, 7).text() == "100%"
