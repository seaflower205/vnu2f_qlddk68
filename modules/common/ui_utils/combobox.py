# -*- coding: utf-8 -*-
from qgis.PyQt.QtCore import QTimer
from qgis.PyQt.QtWidgets import QComboBox, QListView, QStyledItemDelegate, QLineEdit, QSpinBox, QDoubleSpinBox
from modules.common.ui_builder import (
    MatchContains, ScrollBarAlwaysOn, InsertPolicyNoInsert, CompletionModePopup
)
from .filters import SearchableComboEventFilter, PlaceholderEventFilter, FocusSelectAllFilter, WheelEventFilter
from .styles import get_dialog_stylesheet

def make_combo_box_searchable(combo):
    """Làm cho QComboBox có thể tìm kiếm/lọc nội dung khi gõ chữ."""
    combo.setEditable(True)
    combo.setInsertPolicy(InsertPolicyNoInsert)
    
    completer = combo.completer()
    if completer:
        completer.setFilterMode(MatchContains)
        
        # Thiết lập completion mode là PopupCompletion để hiện danh sách gợi ý dạng dropdown
        completer.setCompletionMode(CompletionModePopup)
            
        # Thiết lập QListView và delegate cho completer popup để hiển thị thanh cuộn và style chuẩn
        popup = QListView(combo)
        popup.setMaximumHeight(360) # Tăng từ 240 lên 360 để to và rõ ràng hơn
        popup_width = combo.width()
        popup.setMinimumWidth(popup_width)
        popup.setMaximumWidth(popup_width)
        completer.setPopup(popup)
        popup.setStyleSheet(get_dialog_stylesheet())
            
        delegate = QStyledItemDelegate(popup)
        popup.setItemDelegate(delegate)
        # Luôn hiển thị thanh cuộn dọc để người dùng dễ dàng định vị và sử dụng khi tìm kiếm
        popup.setVerticalScrollBarPolicy(ScrollBarAlwaysOn)
        
        # Ghi đè phương thức showPopup để mở trực tiếp completer
        # Xoá completion prefix trước khi hiện để hiển thị toàn bộ danh sách thay vị chỉ lọc theo phần tử đang chọn
        def _custom_show_popup():
            popup_width = combo.width()
            popup.setMinimumWidth(popup_width)
            popup.setMaximumWidth(popup_width)
            if combo.lineEdit():
                combo.lineEdit().clear()
                combo.lineEdit().setFocus()
            completer.setCompletionPrefix("")
            completer.complete()
        combo.showPopup = _custom_show_popup

        if combo.lineEdit() and not combo.property("_vnu2f_search_filter_installed"):
            search_filter = SearchableComboEventFilter(combo, completer, popup, combo)
            combo.lineEdit().installEventFilter(search_filter)
            combo._vnu2f_search_filter = search_filter
            combo.activated.connect(lambda *args, c=combo: c.setProperty("_vnu2f_skip_clear_once", True))
            combo.setProperty("_vnu2f_search_filter_installed", True)


def install_symmetric_combo_popup(combo):
    """Ép popup QComboBox thường trùng chiều rộng ô gốc trước mỗi lần mở."""
    if combo.property("_vnu2f_symmetric_popup_installed"):
        return

    original_show_popup = combo.showPopup

    def _show_popup():
        try:
            view = combo.view()
            width = combo.width()
            view.setMinimumWidth(width)
            view.setMaximumWidth(width)
        except Exception:  # noqa: BLE001 — intentional suppress
            pass
        original_show_popup()

    combo.showPopup = _show_popup
    combo.setProperty("_vnu2f_symmetric_popup_installed", True)


def customize_combo_boxes(parent_dialog):
    """Tự động kiểm tra và nâng cấp toàn bộ QComboBox và các ô nhập liệu trong hộp thoại."""
    if not hasattr(parent_dialog, '_focus_filter'):
        parent_dialog._focus_filter = FocusSelectAllFilter(parent_dialog)
    if not hasattr(parent_dialog, '_wheel_filter'):
        parent_dialog._wheel_filter = WheelEventFilter(parent_dialog)
        
    focus_filter = parent_dialog._focus_filter
    wheel_filter = parent_dialog._wheel_filter
        
    
    # Gán bộ lọc focus bôi đen chữ cho các ô nhập
    for widget in parent_dialog.findChildren((QLineEdit, QSpinBox, QDoubleSpinBox)):
        widget.installEventFilter(focus_filter)
        if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            widget.installEventFilter(wheel_filter)

    for combo in parent_dialog.findChildren(QComboBox):
        combo.installEventFilter(wheel_filter)
        # Ép QComboBox sử dụng QListView làm view để tránh popup dạng QMenu native bị cụt và có scrollbar mũi tên trên Windows
        try:
            if not isinstance(combo.view(), QListView):
                view = QListView(combo)
                combo.setView(view)
                delegate = QStyledItemDelegate(view)
                view.setItemDelegate(delegate)
        except Exception:  # noqa: BLE001 — intentional suppress
            pass

        # Đảm bảo QComboBox thường xổ đúng theo chiều rộng ô để không bị lệch popup.
        # Các combobox dữ liệu dài vẫn bám theo chiều rộng ô khi mở popup tìm kiếm.
        combo.setMaxVisibleItems(15)
        try:
            combo.view().setMinimumWidth(0)
            combo.view().setMaximumWidth(16777215)
        except Exception:  # noqa: BLE001 — intentional suppress
            pass
        install_symmetric_combo_popup(combo)

        def upgrade_combo(c=combo):
            if c.count() > 8 and not c.isEditable():
                make_combo_box_searchable(c)
                # Áp dụng bộ lọc sự kiện placeholder cho các giá trị mặc định khi editable
                current_text = c.currentText()
                if current_text.startswith("---") and current_text.endswith("---"):
                    filter_obj = PlaceholderEventFilter(current_text, c)
                    c.lineEdit().installEventFilter(filter_obj)
                c.lineEdit().installEventFilter(focus_filter)

        # Chạy thử nâng cấp ban đầu
        upgrade_combo()

        # Áp dụng bộ lọc sự kiện placeholder cho các giá trị mặc định nếu chưa editable
        if not combo.isEditable():
            current_text = combo.currentText()
            if current_text.startswith("---") and current_text.endswith("---"):
                filter_obj = PlaceholderEventFilter(current_text, combo)
                combo.installEventFilter(filter_obj)

        # Lắng nghe sự kiện thay đổi dữ liệu trong model để nâng cấp khi số lượng items tăng
        model = combo.model()
        if model:
            model.rowsInserted.connect(lambda *args, c=combo: upgrade_combo(c))
            model.modelReset.connect(lambda c=combo: upgrade_combo(c))


def populate_layers_to_combo(combo, polygon_only=False, active_layer_id=None, plugin_state=None):
    """
    Populates vector layers from QgsProject into the given QComboBox.
    
    :param combo: QComboBox instance. Must be a valid parented widget.
    :param polygon_only: If True, filters to QgsMapLayerType.VectorLayer and QgsWkbTypes.PolygonGeometry.
    :param active_layer_id: Optional string ID of the active layer to set as current index.
    """
    from qgis.core import QgsProject, QgsMapLayerType, QgsWkbTypes, QgsVectorLayer
    
    if combo is None:
        return
        
    combo.blockSignals(True)
    combo.clear()
    
    active_idx = -1
    if plugin_state and hasattr(plugin_state, "get_project_layers"):
        layers = plugin_state.get_project_layers().values()
    else:
        layers = QgsProject.instance().mapLayers().values()
    
    for layer in layers:
        if not isinstance(layer, QgsVectorLayer):
            continue
            
        if polygon_only:
            if (layer.type() == QgsMapLayerType.VectorLayer and 
                layer.geometryType() == QgsWkbTypes.PolygonGeometry):
                combo.addItem(layer.name(), layer.id())
                if active_layer_id and layer.id() == active_layer_id:
                    active_idx = combo.count() - 1
        else:
            combo.addItem(layer.name(), layer.id())
            if active_layer_id and layer.id() == active_layer_id:
                active_idx = combo.count() - 1
                
    combo.blockSignals(False)
    
    if combo.count() > 0:
        if active_idx != -1:
            combo.setCurrentIndex(active_idx)
        else:
            combo.setCurrentIndex(0)
