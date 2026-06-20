# -*- coding: utf-8 -*-
"""
Nhà máy giao diện (UI Builder/Widget Factory) thuần Python.
Thay thế hoàn toàn cách tạo UI cũ, loại bỏ các lỗi sai Enum của PyQt.
Đóng gói toàn bộ chuẩn PyQt6 (QGIS 4.0+) vào một mối duy nhất.
"""

from qgis.PyQt.QtCore import Qt, QEvent
from qgis.PyQt.QtWidgets import (
    QTableWidgetItem, QAbstractItemView, QHeaderView, QSizePolicy, QFrame, QComboBox
)
from qgis.PyQt.QtGui import QPalette

# ---------------------------------------------------------
# Hằng số chuẩn PyQt6 (QGIS 4+)
# ---------------------------------------------------------
# CheckState
CheckStateChecked = Qt.CheckState.Checked
CheckStateUnchecked = Qt.CheckState.Unchecked
CheckStatePartiallyChecked = Qt.CheckState.PartiallyChecked

# ItemFlags
ItemIsEnabled = Qt.ItemFlag.ItemIsEnabled
ItemIsSelectable = Qt.ItemFlag.ItemIsSelectable
ItemIsEditable = Qt.ItemFlag.ItemIsEditable
ItemIsUserCheckable = Qt.ItemFlag.ItemIsUserCheckable
    
# Selection & Header
SelectRows = QAbstractItemView.SelectionBehavior.SelectRows
SingleSelection = QAbstractItemView.SelectionMode.SingleSelection
ExtendedSelection = QAbstractItemView.SelectionMode.ExtendedSelection
NoEditTriggers = QAbstractItemView.EditTrigger.NoEditTriggers
HeaderStretch = QHeaderView.ResizeMode.Stretch
HeaderResizeToContents = QHeaderView.ResizeMode.ResizeToContents
HeaderInteractive = QHeaderView.ResizeMode.Interactive
CustomContextMenu = Qt.ContextMenuPolicy.CustomContextMenu

# Brush styles
BrushStyleNo = Qt.BrushStyle.NoBrush
BrushStyleSolid = Qt.BrushStyle.SolidPattern
BrushStyleDense1 = Qt.BrushStyle.Dense1Pattern
BrushStyleDense2 = Qt.BrushStyle.Dense2Pattern
BrushStyleDense3 = Qt.BrushStyle.Dense3Pattern
BrushStyleDense4 = Qt.BrushStyle.Dense4Pattern
BrushStyleDense5 = Qt.BrushStyle.Dense5Pattern
BrushStyleDense6 = Qt.BrushStyle.Dense6Pattern
BrushStyleDense7 = Qt.BrushStyle.Dense7Pattern
BrushStyleDiagCross = Qt.BrushStyle.DiagCrossPattern

# MatchFlags
MatchContains = Qt.MatchFlag.MatchContains
MatchExactly = Qt.MatchFlag.MatchExactly

# ScrollBar & Frame
ScrollBarAlwaysOff = Qt.ScrollBarPolicy.ScrollBarAlwaysOff
ScrollBarAlwaysOn = Qt.ScrollBarPolicy.ScrollBarAlwaysOn
FrameNoFrame = QFrame.Shape.NoFrame
FrameStyledPanel = QFrame.Shape.StyledPanel
FrameSunken = QFrame.Shadow.Sunken
FrameRaised = QFrame.Shadow.Raised
FramePlain = QFrame.Shadow.Plain

# Focus
FocusNoFocus = Qt.FocusPolicy.NoFocus

# Events
QEvent_FocusIn = QEvent.Type.FocusIn
QEvent_FocusOut = QEvent.Type.FocusOut
QEvent_MousePress = QEvent.Type.MouseButtonPress
QEvent_MouseRelease = QEvent.Type.MouseButtonRelease
QEvent_Wheel = QEvent.Type.Wheel

# MessageBox
from qgis.PyQt.QtWidgets import QMessageBox
MessageBoxYes = QMessageBox.StandardButton.Yes
MessageBoxNo = QMessageBox.StandardButton.No

# SizePolicy
SizePolicyExpanding = QSizePolicy.Policy.Expanding
SizePolicyFixed = QSizePolicy.Policy.Fixed

# Completion
try:
    from qgis.PyQt.QtWidgets import QCompleter
    CompletionModePopup = QCompleter.CompletionMode.PopupCompletion
except Exception:
    CompletionModePopup = 0
    
try:
    InsertPolicyNoInsert = QComboBox.InsertPolicy.NoInsert
except Exception:
    InsertPolicyNoInsert = 0

# Palette
PaletteWindow = QPalette.ColorRole.Window

# Text interaction
TextSelectableByMouse = Qt.TextInteractionFlag.TextSelectableByMouse
    
    # ---------------------------------------------------------
    # Factory Methods (Tạo Widget chuẩn)
    # ---------------------------------------------------------

class UiBuilder:
    @staticmethod
    def create_table_checkbox(checked: bool = False, enabled: bool = True) -> QTableWidgetItem:
        """Tạo một ô Checkbox chuẩn cho QTableWidget."""
        item = QTableWidgetItem()
        item.setCheckState(CheckStateChecked if checked else CheckStateUnchecked)
        
        flags = ItemIsUserCheckable
        if enabled:
            flags |= ItemIsEnabled
        item.setFlags(flags)
        
        return item
    
    @staticmethod
    def create_table_text(text: str, bold: bool = False, editable: bool = False) -> QTableWidgetItem:
        """Tạo một ô Text chuẩn cho QTableWidget."""
        item = QTableWidgetItem(str(text))
        
        flags = ItemIsEnabled | ItemIsSelectable
        if editable:
            flags |= ItemIsEditable
        item.setFlags(flags)
        
        if bold:
            font = item.font()
            font.setBold(True)
            item.setFont(font)
            
        return item
