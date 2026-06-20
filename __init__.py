"""
/***************************************************************************
 VNU2F QLDDK68
 Plugin hỗ trợ trắc địa - địa chính Việt Nam
 (vnu2f: Đơn vị phát triển; qlddk68: Chuyên ngành Quản lý đất đai khóa K68)
 Thay thế AutoCAD, MicroStation, FAMIS, GCADAS bằng QGIS.
                             -------------------
        begin                : 2026-06-04
        copyright            : (C) 2026 by VNU2F
        email                : vnu2f@example.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   Chương trình này là phần mềm tự do; bạn có thể phân phối lại và/hoặc *
 *   sửa đổi nó theo các điều khoản của Giấy phép Công cộng GNU phiên     *
 *   bản 2 (GPLv2) do Tổ chức Phần mềm Tự do công bố.                     *
 *                                                                         *
 ***************************************************************************/
"""
import sys
import os

plugin_dir = os.path.dirname(__file__)

def _add_internal_libraries_to_path():
    internal_paths = [
        os.path.join(plugin_dir, "tools", "libraries", "topology-tools", "src"),
        os.path.join(plugin_dir, "tools", "libraries", "vn_mapfont_converter"),
    ]
    for lib_path in internal_paths:
        if os.path.isdir(lib_path) and lib_path not in sys.path:
            sys.path.insert(0, lib_path)

_add_internal_libraries_to_path()

if plugin_dir not in sys.path:
    sys.path.insert(0, plugin_dir)

# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Tải lớp plugin VNU2FQLDDK68Plugin từ module chính.

    :param iface: Đối tượng giao diện QGIS (QgisInterface).
    :type iface: QgsInterface
    :returns: Thể hiện của lớp plugin chính.
    :rtype: VNU2FQLDDK68Plugin
    """
    from .vnu2f_qlddk68 import VNU2FQLDDK68Plugin
    return VNU2FQLDDK68Plugin(iface)