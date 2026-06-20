# -*- coding: utf-8 -*-
"""
Lớp tương thích Qt5 ↔ Qt6 tập trung.

Cung cấp các hằng số enum đã resolve sẵn để toàn bộ plugin không cần
viết ``if hasattr(...)`` rải rác trong từng file.

Cách dùng::

    from ..common.qt_compat import (
        QEvent_FocusIn, QEvent_FocusOut, QEvent_MousePress,
        MatchContains, ScrollBarAlwaysOn, ScrollBarAlwaysOff,
        FrameNoFrame, FocusNoFocus,
    )
"""

from qgis.PyQt.QtCore import Qt, QEvent
from qgis.PyQt.QtGui import QPalette
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QCompleter,
    QFrame,
    QMessageBox,
    QSizePolicy,
    QHeaderView,
)


# ═══════════════════════════════════════════════════════════════════════
# QEvent types
# ═══════════════════════════════════════════════════════════════════════
if hasattr(QEvent, 'Type'):
    QEvent_FocusIn = QEvent.Type.FocusIn
    QEvent_FocusOut = QEvent.Type.FocusOut
    QEvent_MousePress = QEvent.Type.MouseButtonPress
    QEvent_MouseRelease = QEvent.Type.MouseButtonRelease
    QEvent_Wheel = QEvent.Type.Wheel
else:
    QEvent_FocusIn = QEvent.FocusIn
    QEvent_FocusOut = QEvent.FocusOut
    QEvent_MousePress = QEvent.MouseButtonPress
    QEvent_MouseRelease = QEvent.MouseButtonRelease
    QEvent_Wheel = QEvent.Wheel


# ═══════════════════════════════════════════════════════════════════════
# Qt core flags
# ═══════════════════════════════════════════════════════════════════════
if hasattr(Qt, 'MatchFlag'):
    MatchContains = Qt.MatchFlag.MatchContains
else:
    MatchContains = Qt.MatchContains

if hasattr(Qt, 'ScrollBarPolicy'):
    ScrollBarAlwaysOn = Qt.ScrollBarPolicy.ScrollBarAlwaysOn
    ScrollBarAlwaysOff = Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    ScrollBarAsNeeded = Qt.ScrollBarPolicy.ScrollBarAsNeeded
else:
    ScrollBarAlwaysOn = Qt.ScrollBarAlwaysOn
    ScrollBarAlwaysOff = Qt.ScrollBarAlwaysOff
    ScrollBarAsNeeded = Qt.ScrollBarAsNeeded

if hasattr(Qt, 'FocusPolicy'):
    FocusNoFocus = Qt.FocusPolicy.NoFocus
else:
    FocusNoFocus = Qt.NoFocus

if hasattr(Qt, 'AlignmentFlag'):
    AlignRight = Qt.AlignmentFlag.AlignRight
    AlignVCenter = Qt.AlignmentFlag.AlignVCenter
    AlignRightVCenter = AlignRight | AlignVCenter
else:
    AlignRight = Qt.AlignRight
    AlignVCenter = Qt.AlignVCenter
    AlignRightVCenter = AlignRight | AlignVCenter

if hasattr(Qt, 'TextInteractionFlag'):
    TextSelectableByMouse = Qt.TextInteractionFlag.TextSelectableByMouse
else:
    TextSelectableByMouse = Qt.TextSelectableByMouse

if hasattr(Qt, 'ContextMenuPolicy'):
    CustomContextMenu = Qt.ContextMenuPolicy.CustomContextMenu
else:
    CustomContextMenu = Qt.CustomContextMenu

if hasattr(Qt, 'ItemFlag'):
    ItemIsEnabled = Qt.ItemFlag.ItemIsEnabled
    ItemIsSelectable = Qt.ItemFlag.ItemIsSelectable
    ItemIsEditable = Qt.ItemFlag.ItemIsEditable
else:
    ItemIsEnabled = Qt.ItemIsEnabled
    ItemIsSelectable = Qt.ItemIsSelectable
    ItemIsEditable = Qt.ItemIsEditable


# ═══════════════════════════════════════════════════════════════════════
# QPalette
# ═══════════════════════════════════════════════════════════════════════
if hasattr(QPalette, 'ColorRole'):
    PaletteWindow = QPalette.ColorRole.Window
else:
    PaletteWindow = QPalette.Window


# ═══════════════════════════════════════════════════════════════════════
# QFrame
# ═══════════════════════════════════════════════════════════════════════
if hasattr(QFrame, 'Shape') and hasattr(QFrame.Shape, 'NoFrame'):
    FrameNoFrame = QFrame.Shape.NoFrame
else:
    FrameNoFrame = QFrame.NoFrame

if hasattr(QFrame, 'Shape') and hasattr(QFrame.Shape, 'StyledPanel'):
    FrameStyledPanel = QFrame.Shape.StyledPanel
else:
    FrameStyledPanel = QFrame.StyledPanel


# ═══════════════════════════════════════════════════════════════════════
# QComboBox
# ═══════════════════════════════════════════════════════════════════════
if hasattr(QComboBox, 'InsertPolicy'):
    InsertPolicyNoInsert = QComboBox.InsertPolicy.NoInsert
else:
    InsertPolicyNoInsert = QComboBox.NoInsert


# ═══════════════════════════════════════════════════════════════════════
# QCompleter
# ═══════════════════════════════════════════════════════════════════════
if hasattr(QCompleter, 'CompletionMode'):
    CompletionModePopup = QCompleter.CompletionMode.PopupCompletion
else:
    CompletionModePopup = QCompleter.PopupCompletion


# ═══════════════════════════════════════════════════════════════════════
# QAbstractItemView / QTableWidget
# ═══════════════════════════════════════════════════════════════════════
if hasattr(QAbstractItemView, 'SelectionBehavior'):
    SelectRows = QAbstractItemView.SelectionBehavior.SelectRows
    NoEditTriggers = QAbstractItemView.EditTrigger.NoEditTriggers
else:
    SelectRows = QAbstractItemView.SelectRows
    NoEditTriggers = QAbstractItemView.NoEditTriggers

if hasattr(QAbstractItemView, 'SelectionMode'):
    SingleSelection = QAbstractItemView.SelectionMode.SingleSelection
    ExtendedSelection = QAbstractItemView.SelectionMode.ExtendedSelection
else:
    SingleSelection = QAbstractItemView.SingleSelection
    ExtendedSelection = QAbstractItemView.ExtendedSelection


# ═══════════════════════════════════════════════════════════════════════
# QSizePolicy
# ═══════════════════════════════════════════════════════════════════════
if hasattr(QSizePolicy, 'Policy'):
    SizePolicyExpanding = QSizePolicy.Policy.Expanding
    SizePolicyFixed = QSizePolicy.Policy.Fixed
else:
    SizePolicyExpanding = QSizePolicy.Expanding
    SizePolicyFixed = QSizePolicy.Fixed


# ═══════════════════════════════════════════════════════════════════════
# QMessageBox
# ═══════════════════════════════════════════════════════════════════════
if hasattr(QMessageBox, 'StandardButton'):
    MessageBoxYes = QMessageBox.StandardButton.Yes
    MessageBoxNo = QMessageBox.StandardButton.No
else:
    MessageBoxYes = QMessageBox.Yes
    MessageBoxNo = QMessageBox.No


# ═══════════════════════════════════════════════════════════════════════
# QHeaderView
# ═══════════════════════════════════════════════════════════════════════
if hasattr(QHeaderView, 'ResizeMode'):
    HeaderStretch = QHeaderView.ResizeMode.Stretch
    HeaderResizeToContents = QHeaderView.ResizeMode.ResizeToContents
    HeaderInteractive = QHeaderView.ResizeMode.Interactive
else:
    HeaderStretch = QHeaderView.Stretch
    HeaderResizeToContents = QHeaderView.ResizeToContents
    HeaderInteractive = QHeaderView.Interactive

# ═══════════════════════════════════════════════════════════════════════
# BrushStyle for Symbology Fills
# ═══════════════════════════════════════════════════════════════════════
if hasattr(Qt, 'BrushStyle'):
    BrushStyleSolid = Qt.BrushStyle.SolidPattern
    BrushStyleNo = Qt.BrushStyle.NoBrush
    BrushStyleDense1 = Qt.BrushStyle.Dense1Pattern
    BrushStyleDense2 = Qt.BrushStyle.Dense2Pattern
    BrushStyleDense3 = Qt.BrushStyle.Dense3Pattern
    BrushStyleDense4 = Qt.BrushStyle.Dense4Pattern
    BrushStyleDense5 = Qt.BrushStyle.Dense5Pattern
    BrushStyleDense6 = Qt.BrushStyle.Dense6Pattern
    BrushStyleDense7 = Qt.BrushStyle.Dense7Pattern
    BrushStyleDiagCross = Qt.BrushStyle.DiagCrossPattern
else:
    BrushStyleSolid = Qt.SolidPattern
    BrushStyleNo = Qt.NoBrush
    BrushStyleDense1 = Qt.Dense1Pattern
    BrushStyleDense2 = Qt.Dense2Pattern
    BrushStyleDense3 = Qt.Dense3Pattern
    BrushStyleDense4 = Qt.Dense4Pattern
    BrushStyleDense5 = Qt.Dense5Pattern
    BrushStyleDense6 = Qt.Dense6Pattern
    BrushStyleDense7 = Qt.Dense7Pattern
    BrushStyleDiagCross = Qt.DiagCrossPattern

