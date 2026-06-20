# -*- coding: utf-8 -*-
"""
Hộp thoại chuyển đổi Hệ tọa độ VN-2000 (CRS Converter Dialog).
"""

import importlib
import traceback

from qgis.PyQt.QtCore import Qt, QTimer
from qgis.PyQt.QtWidgets import (
    QDialog, QHBoxLayout, QVBoxLayout, QLabel, QListWidget, QWidget, QStackedWidget
)
from qgis.core import Qgis, QgsMessageLog, QgsProject

from modules.common.ui_utils import get_dialog_stylesheet, customize_combo_boxes, is_dark_mode, set_dialog_icon, create_themed_button
from ..common.i18n import tr
from ..common.qt_compat import TextSelectableByMouse, ScrollBarAlwaysOff
from ..common.scroll_utils import wrap_widget_in_scroll
from .crs_tab_registry_mixin import CrsTabRegistryMixin

class CRSConverterDialog(CrsTabRegistryMixin, QDialog):
    """Hộp thoại chính của phân hệ Chuyển đổi Hệ tọa độ VN-2000."""

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Lấy Map Canvas từ dự án QGIS hiện tại
        try:
            from qgis.utils import iface
            self.iface = iface
            self.canvas = iface.mapCanvas()
        except (ImportError, AttributeError):
            self.iface = None
            self.canvas = None

        self.setWindowTitle(tr("crs.window_title"))
        self.resize(1180, 760)
        self.setMinimumSize(960, 640)
        self._tabs = {}
        self._target_index = -1
        self._is_first_load = True
        self._load_timer = QTimer(self)
        self._load_timer.setSingleShot(True)
        self._load_timer.timeout.connect(self._on_load_timeout)
        
        # Khởi tạo Plugin State dùng chung cho địa chính
        top_package = __name__.split(".")[0]
        try:
            plugin_state_module = importlib.import_module(f"{top_package}.cadastral_tools.core.plugin_state")
        except ImportError:
            try:
                plugin_state_module = importlib.import_module("cadastral_tools.core.plugin_state")
            except ImportError:
                plugin_state_module = importlib.import_module("vnu2f_qlddk68.cadastral_tools.core.plugin_state")
        PluginState = getattr(plugin_state_module, "PluginState")
        self._plugin_state = PluginState()

        set_dialog_icon(self, 'icon.png')
        
        self._setup_ui()
        self._update_project_crs_status()
        
        # Kích hoạt tìm kiếm thông minh và bôi đen khi focus
        customize_combo_boxes(self)
        
        # Áp dụng stylesheet chuẩn (Light/Dark Mode) sau khi đã tạo xong các widget
        self.setStyleSheet(get_dialog_stylesheet())

    def _setup_ui(self):
        # Main layout of the dialog (Horizontal, 0 margins)
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar (QListWidget) on the left
        self.sidebar = QListWidget(self)
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(210)
        self.sidebar.setHorizontalScrollBarPolicy(ScrollBarAlwaysOff)
        
        if hasattr(Qt, 'FocusPolicy') and hasattr(Qt.FocusPolicy, 'NoFocus'):
            self.sidebar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        elif hasattr(Qt, 'NoFocus'):
            self.sidebar.setFocusPolicy(Qt.NoFocus)
            
        tab_specs = self._tab_specs()
        for spec in tab_specs:
            self.sidebar.addItem(spec["title"])
        main_layout.addWidget(self.sidebar)

        # Content Panel on the right (contains top label, pages, and bottom buttons)
        content_widget = QWidget(self)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(12)
        main_layout.addWidget(content_widget)

        # 1. Trạng thái CRS dự án hiện tại
        self.lbl_project_crs = QLabel(content_widget)
        if is_dark_mode():
            self.lbl_project_crs.setStyleSheet(
                "padding: 12px 16px; border: 1px solid #27272a; "
                "border-radius: 6px; font-weight: 600; background-color: #18181b; color: #fafafa;"
            )
        else:
            self.lbl_project_crs.setStyleSheet(
                "padding: 12px 16px; border: 1px solid #e4e4e7; "
                "border-radius: 6px; font-weight: 600; background-color: #ffffff; color: #09090b;"
            )
        self.lbl_project_crs.setWordWrap(True)
        content_layout.addWidget(self.lbl_project_crs)

        # 2. StackedWidget chứa các trang bên phải
        self.pages = QStackedWidget(content_widget)
        content_layout.addWidget(self.pages)

        # Tạo các widget placeholder trống để giữ đúng index khớp với sidebar
        for _ in tab_specs:
            self.pages.addWidget(QWidget(self.pages))

        # Kết nối sự kiện chuyển trang bằng hàm lazy load của chúng ta
        self.sidebar.currentRowChanged.connect(self._on_sidebar_changed)
        
        # Mặc định kích hoạt trang đầu tiên (nạp ngay)
        self.sidebar.setCurrentRow(0)

        # 3. Thanh nút điều khiển dưới cùng inside the content panel
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 8, 0, 0)
        btn_reset = create_themed_button(tr("common.reset"), parent=content_widget)
        btn_reset.clicked.connect(self._on_reset)
        btn_reset.setMinimumHeight(38)
        bottom_layout.addWidget(btn_reset)
        bottom_layout.addStretch()
        
        btn_close = create_themed_button(tr("common.close"), parent=content_widget)
        btn_close.clicked.connect(self.close)
        btn_close.setMinimumHeight(38)
        bottom_layout.addWidget(btn_close)
        content_layout.addLayout(bottom_layout)


    def _on_sidebar_changed(self, index):
        """Lazy load tab con khi người dùng nhấp chọn trên sidebar."""
        self._load_timer.stop()  # Luôn dừng timer đang chờ của tab trước để tránh việc load ngầm đè lên tab hiện tại
        tab_specs = self._tab_specs()
        if index < 0 or index >= len(tab_specs):
            return
            
        # Hiển thị trang (có thể là trang thật hoặc placeholder cũ) ngay lập tức để UI mượt mà
        self.pages.setCurrentIndex(index)
        
        spec = tab_specs[index]
        attr = spec["attr"]
        
        # Nếu tab đã được nạp (hoặc nạp lỗi trước đó và đánh dấu False), không làm gì thêm
        if self._tabs.get(attr) is not None:
            return
            
        if self._is_first_load:
            self._is_first_load = False
            self._target_index = index
            self._on_load_timeout()
        else:
            self._target_index = index
            self._load_timer.stop()
            self._load_timer.start(150) # Chờ 150ms trước khi nạp thực tế để tránh click loạn xạ gây văng

    def _on_load_timeout(self):
        """Hàm callback được gọi khi timer debounce phát hỏa."""
        index = self._target_index
        tab_specs = self._tab_specs()
        if index < 0 or index >= len(tab_specs):
            return
            
        spec = tab_specs[index]
        attr = spec["attr"]
        
        # Kiểm tra lại xem tab đã được nạp hay chưa trước khi nạp
        if self._tabs.get(attr) is None:
            real_tab = self._create_tab_page(spec)
            placeholder = self.pages.widget(index)
            self.pages.insertWidget(index, real_tab)
            self.pages.removeWidget(placeholder)
            placeholder.deleteLater()
            
            # Đảm bảo hiển thị đúng trang sau khi nạp xong
            self.pages.setCurrentIndex(index)

    def _create_tab_page(self, spec):
        try:
            mod_path = spec["module"]
            if mod_path.startswith("."):
                package = __package__ or __name__.rpartition(".")[0]
                module = importlib.import_module(mod_path, package=package)
            else:
                module = importlib.import_module(mod_path)
            tab_class = getattr(module, spec["class"])
            args = spec.get("args", lambda: ())()
            kwargs = spec.get("kwargs", lambda: {})()
            tab = tab_class(*args, **kwargs)
            self._tabs[spec["attr"]] = tab
            setattr(self, spec["attr"], tab)
            return self._wrap_in_scroll(tab) if spec.get("scroll") else tab
        except Exception as exc:
            # Lưu False thay vì None để tránh cố gắng nạp lại liên tục mỗi khi chuyển tab
            self._tabs[spec["attr"]] = False
            setattr(self, spec["attr"], None)
            detail = traceback.format_exc()
            QgsMessageLog.logMessage(
                f"Không khởi tạo được tab '{spec['title']}': {exc}\n{detail}",
                "VNU2F QLDDK68",
                Qgis.Critical,
            )
            return self._error_page(spec["title"], exc)

    def _error_page(self, title, exc):
        label = QLabel(
            f"Không mở được: {title}\n\n"
            f"Chi tiết: {exc}\n\n"
            "Các tab khác vẫn dùng được. Vui lòng mở QGIS Log Panel (hoặc xem file qgis_crash.log) để xem traceback đầy đủ.",
            self
        )
        label.setWordWrap(True)
        label.setMargin(24)
        label.setTextInteractionFlags(TextSelectableByMouse)
        label.setStyleSheet("font-size: 13px; color: #ef4444; font-weight: 500;")
        return label

    def _wrap_in_scroll(self, widget):
        """Bọc một widget vào QScrollArea để chống co vỡ giao diện."""
        return wrap_widget_in_scroll(widget, self, "QScrollArea { background-color: transparent; border: none; } QScrollArea > QWidget > QWidget { background-color: transparent; }")

    def _update_project_crs_status(self):
        """Cập nhật nhãn trạng thái hệ tọa độ của Dự án QGIS hiện tại."""
        if not self.iface:
            self.lbl_project_crs.setText(tr("crs.status.unavailable"))
            return
        
        crs = QgsProject.instance().crs()
        if crs.isValid():
            desc = crs.description()
            auth = crs.authid()
            self.lbl_project_crs.setText(tr("crs.status.current", desc=desc, auth=auth))
        else:
            self.lbl_project_crs.setText(tr("crs.status.invalid"))

    def _on_reset(self):
        """Đặt lại trạng thái của tất cả các tab."""
        for tab in self._tabs.values():
            if tab and hasattr(tab, "reset"):
                tab.reset()

    def closeEvent(self, event):
        """Dọn dẹp tài nguyên của toàn bộ các tab con khi đóng hộp thoại."""
        if hasattr(self, "_load_timer"):
            self._load_timer.stop()
        for attr, tab in list(self._tabs.items()):
            if tab and hasattr(tab, "cleanup"):
                try:
                    tab.cleanup()
                except Exception as e:
                    QgsMessageLog.logMessage(
                        f"Lỗi dọn dẹp tab '{attr}' khi đóng dialog: {e}",
                        "VNU2F QLDDK68",
                        Qgis.Warning
                    )
        super().closeEvent(event)

    def reject(self):
        """Đảm bảo dừng timer nạp ngầm khi người dùng từ chối/hủy dialog."""
        if hasattr(self, "_load_timer"):
            self._load_timer.stop()
        super().reject()
