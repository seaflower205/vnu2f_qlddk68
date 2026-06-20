# -*- coding: utf-8 -*-
from qgis.PyQt.QtCore import QObject, QTimer
from qgis.PyQt.QtWidgets import QApplication, QComboBox
from modules.common.ui_builder import (
    QEvent_FocusIn,
    QEvent_FocusOut,
    QEvent_MousePress,
    QEvent_MouseRelease,
    QEvent_Wheel,
)

class FocusSelectAllFilter(QObject):
    """Bộ lọc sự kiện tự động bôi đen toàn bộ chữ khi click vào ô nhập liệu để nhập đè ngay."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._just_focused = set()

    def eventFilter(self, obj, event):
        if event.type() == QEvent_FocusIn:
            if hasattr(obj, 'selectAll'):
                self._just_focused.add(obj)
                QTimer.singleShot(0, obj.selectAll)
        elif event.type() == QEvent_MouseRelease:
            if obj in self._just_focused:
                self._just_focused.remove(obj)
                if hasattr(obj, 'selectAll'):
                    QTimer.singleShot(0, obj.selectAll)
        elif event.type() == QEvent_FocusOut:
            if obj in self._just_focused:
                self._just_focused.discard(obj)
        return False


class WheelEventFilter(QObject):
    """Bộ lọc sự kiện chặn cuộn chuột (wheel) làm thay đổi giá trị của ô nhập."""
    def eventFilter(self, obj, event):
        if event.type() == QEvent_Wheel:
            # Chỉ cho phép cuộn đổi giá trị nếu widget đang được focus rõ ràng
            if not obj.hasFocus():
                event.ignore()
                # Gửi sự kiện cuộn chuột lên widget cha để tiếp tục cuộn trang scroll area
                parent = obj.parent()
                while parent:
                    if QApplication.sendEvent(parent, event):
                        break
                    parent = parent.parent()
                return True
        return False


class PlaceholderEventFilter(QObject):
    """Bộ lọc sự kiện tự động xóa văn bản gợi ý (placeholder) khi người dùng click vào và khôi phục khi rời đi."""
    def __init__(self, placeholder_text, parent=None):
        super().__init__(parent)
        self.placeholder = placeholder_text

    def eventFilter(self, obj, event):
        # FocusIn: Xóa placeholder khi người dùng chọn
        if event.type() == QEvent_FocusIn:
            if hasattr(obj, 'text') and obj.text() == self.placeholder:
                obj.clear()
            elif isinstance(obj, QComboBox) and obj.isEditable() and obj.currentText() == self.placeholder:
                obj.lineEdit().clear()
        # FocusOut: Khôi phục placeholder nếu không nhập gì
        elif event.type() == QEvent_FocusOut:
            if hasattr(obj, 'text') and not obj.text().strip():
                obj.setText(self.placeholder)
            elif isinstance(obj, QComboBox):
                if not obj.currentText().strip():
                    if obj.isEditable():
                        obj.lineEdit().setText(self.placeholder)
                    else:
                        idx = obj.findText(self.placeholder)
                        if idx >= 0:
                            obj.setCurrentIndex(idx)
        return False


class SearchableComboEventFilter(QObject):
    """Xóa text hiện tại và mở danh sách khi người dùng bắt đầu tìm trong combobox."""
    def __init__(self, combo, completer, popup, parent=None):
        super().__init__(parent)
        self.combo = combo
        self.completer = completer
        self.popup = popup

    def _resize_popup(self):
        width = self.combo.width()
        self.popup.setMinimumWidth(width)
        self.popup.setMaximumWidth(width)

    def _clear_and_open(self):
        if not self.combo.isVisible():
            return
        self._resize_popup()
        line_edit = self.combo.lineEdit()
        if line_edit:
            line_edit.clear()
            line_edit.setFocus()
        self.completer.setCompletionPrefix("")
        self.completer.complete()

    def eventFilter(self, obj, event):
        if event.type() == QEvent_FocusIn:
            if self.combo.property("_vnu2f_skip_clear_once"):
                self.combo.setProperty("_vnu2f_skip_clear_once", False)
                return False
            QTimer.singleShot(0, self._clear_and_open)
        elif event.type() == QEvent_MousePress:
            QTimer.singleShot(0, self._clear_and_open)
        return False

