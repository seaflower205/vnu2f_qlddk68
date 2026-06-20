# -*- coding: utf-8 -*-
"""
/***************************************************************************
 VNU2F QLDDK68
 Plugin hỗ trợ trắc địa - địa chính Việt Nam
                             -------------------
        begin                : 2026-06-04
        copyright            : (C) 2026 by VNU2F
        email                : vnu2f@example.com
 ***************************************************************************/
"""

import os
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsMessageLog, Qgis

# Import dialog và các module phụ thuộc
try:
    from .modules.common import dep_installer
    from .modules.plugin_actions import PluginActionsMixin
except ImportError:
    from modules.common import dep_installer
    from modules.plugin_actions import PluginActionsMixin



class VNU2FQLDDK68Plugin(PluginActionsMixin):
    """Lớp plugin chính cho VNU2F QLDDK68.
    Cung cấp bộ công cụ chuyển đổi hệ tọa độ VN-2000 chuẩn 7 tham số.
    """

    PLUGIN_NAME = 'VNU2F QLDDK68'

    def __init__(self, iface):
        # Lưu tham chiếu đến giao diện QGIS
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.toolbar = None
        self.menu_name = self.PLUGIN_NAME
        self._crs_dialog = None
        self._cadastral_import_dialog = None
        self._webgis_launcher = None

    def _get_icon_path(self, icon_filename='icon_crs.svg'):
        # Thử lấy icon_crs.svg, nếu không có thì dùng icon.png mặc định
        path = os.path.join(self.plugin_dir, icon_filename)
        if os.path.exists(path):
            return path
        return os.path.join(self.plugin_dir, 'icon.png')

    def initGui(self):
        """Khởi tạo thanh công cụ và menu của plugin."""
        # Kiểm tra trạng thái thư viện khi khởi động sẽ được thực hiện thủ công trong tab Health Check.

        # Tự động đăng ký các hệ tọa độ VN-2000 khi khởi động plugin

        try:
            try:
                from .modules.crs_converter.crs_utils import Vn2000DbHelper
            except ImportError:
                from modules.crs_converter.crs_utils import Vn2000DbHelper
            success, msg = Vn2000DbHelper.register_provinces()
            QgsMessageLog.logMessage(f"Tự động nạp CRS VN-2000: {msg}", self.PLUGIN_NAME, Qgis.Info)
        except Exception as e:
            QgsMessageLog.logMessage(f"Lỗi khi tự động nạp CRS VN-2000: {e}", self.PLUGIN_NAME, Qgis.Warning)

        # Di trú/Kiểm tra phiên bản cơ sở dữ liệu khi khởi động
        try:
            import sqlite3
            try:
                from .modules.common.db_migration import get_db_version, migrate
                from .modules.crs_converter.crs_utils import Vn2000DbHelper
            except ImportError:
                from modules.common.db_migration import get_db_version, migrate
                from modules.crs_converter.crs_utils import Vn2000DbHelper
            db_path = Vn2000DbHelper.get_qgis_db_path()
            if db_path:
                with sqlite3.connect(db_path) as conn:
                    v = get_db_version(conn)
                    migrate(conn, v)
                QgsMessageLog.logMessage("Đã di trú cơ sở dữ liệu thành công.", self.PLUGIN_NAME, Qgis.Info)
        except Exception as e:
            QgsMessageLog.logMessage(f"Lỗi di trú CSDL khi load plugin: {e}", self.PLUGIN_NAME, Qgis.Warning)

        self.toolbar = self.iface.addToolBar(self.PLUGIN_NAME)
        self.toolbar.setObjectName(self.PLUGIN_NAME)

        # Đăng ký Action chính: Chuyển đổi Hệ Tọa Độ VN-2000
        icon_path = self._get_icon_path('icon_crs.svg')
        icon = QIcon(icon_path)
        
        self.action = QAction(icon, 'Chuyển đổi Hệ Tọa Độ VN-2000', self.iface.mainWindow())
        self.action.triggered.connect(self._open_crs_converter)
        self.action.setStatusTip('Mở công cụ đăng ký và chuyển đổi hệ tọa độ VN-2000')
        
        self.toolbar.addAction(self.action)
        self.iface.addPluginToMenu(self.menu_name, self.action)
        
        self.actions.append(self.action)

        # Đăng ký Action nhập CAD địa chính và đồng bộ thuộc tính
        cad_icon_path = self._get_icon_path('icon_cad.svg')
        cad_icon = QIcon(cad_icon_path)

        self.action_cadastral_import = QAction(
            cad_icon,
            'Nhập CAD địa chính',
            self.iface.mainWindow()
        )
        self.action_cadastral_import.triggered.connect(self._open_cadastral_importer)
        self.action_cadastral_import.setStatusTip(
            'Nhập DWG/DGN/DXF và đồng bộ thuộc tính từ GTP/POL/SHP'
        )

        self.toolbar.addAction(self.action_cadastral_import)
        self.iface.addPluginToMenu(self.menu_name, self.action_cadastral_import)
        self.actions.append(self.action_cadastral_import)

        # Đăng ký Action mở WebGIS quản lý thửa đất demo
        webgis_icon_path = self._get_icon_path('icon_basemap.svg')
        webgis_icon = QIcon(webgis_icon_path)

        self.action_webgis = QAction(
            webgis_icon,
            'Mở WebGIS quản lý thửa đất',
            self.iface.mainWindow()
        )
        self.action_webgis.triggered.connect(self._open_webgis)
        self.action_webgis.setStatusTip(
            'Mở WebGIS demo tra cứu và quản lý thửa đất từ dữ liệu địa chính'
        )

        self.toolbar.addAction(self.action_webgis)
        self.iface.addPluginToMenu(self.menu_name, self.action_webgis)
        self.actions.append(self.action_webgis)

        # Đăng ký Action Chia sẻ WebGIS
        share_icon_path = self._get_icon_path('icon_share.svg')
        share_icon = QIcon(share_icon_path)

        self.action_share_webgis = QAction(
            share_icon,
            'Chia sẻ bản đồ WebGIS',
            self.iface.mainWindow()
        )
        self.action_share_webgis.triggered.connect(self._share_webgis)
        self.action_share_webgis.setStatusTip(
            'Chia sẻ bản đồ WebGIS hiện tại lên Internet (LAN, Serveo, hoặc GitHub Pages)'
        )

        self.toolbar.addAction(self.action_share_webgis)
        self.iface.addPluginToMenu(self.menu_name, self.action_share_webgis)
        self.actions.append(self.action_share_webgis)

    def unload(self):
        """Giải phóng menu, thanh công cụ và các marker khi unload plugin."""
        # 1. Đóng và dọn dẹp dialog trước
        if self._crs_dialog:
            try:
                self._crs_dialog.close()
            except Exception:
                pass
            self._crs_dialog = None

        if self._cadastral_import_dialog:
            try:
                self._cadastral_import_dialog.close()
            except Exception:
                pass
            self._cadastral_import_dialog = None

        if self._webgis_launcher:
            try:
                self._webgis_launcher.stop()
            except Exception:
                pass
            self._webgis_launcher = None

        # 2. Xóa các action khỏi giao diện QGIS
        for action in self.actions:
            try:
                self.iface.removePluginMenu(self.menu_name, action)
            except Exception:
                pass
            try:
                self.iface.removeToolBarIcon(action)
            except Exception:
                pass

        # 3. Xóa thanh công cụ
        if hasattr(self, 'toolbar') and self.toolbar:
            try:
                self.toolbar.setParent(None)
                del self.toolbar
            except Exception:
                pass

        self.actions.clear()

# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Fallback factory when QGIS imports this file as a top-level module.

    Normal plugin loading uses ``__init__.py``. Some development installs put
    the plugin directory itself on ``PYTHONPATH``, which makes Python import
    this ``vnu2f_qlddk68.py`` module instead of the package. Keeping the same
    factory here makes both layouts work.
    """
    return VNU2FQLDDK68Plugin(iface)
