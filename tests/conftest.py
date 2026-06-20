import os
import sys
import pytest

# Ensure project root and its parent are in sys.path so fully-qualified package imports work
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_PARENT = os.path.dirname(PROJECT_ROOT)
if PROJECT_PARENT not in sys.path:
    sys.path.insert(0, PROJECT_PARENT)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Mock QGIS and PyQt modules if not present in the current environment
import sys
from unittest.mock import MagicMock

try:
    import qgis
except ImportError:
    # Create mock classes/modules
    mock_qgis = MagicMock()
    mock_qgis.core = MagicMock()
    mock_qgis.gui = MagicMock()
    mock_qgis.utils = MagicMock()
    
    class MockQgsCoordinateReferenceSystem:
        def __init__(self, *args, **kwargs): pass
        def authid(self): return "EPSG:4326"
        def isValid(self): return True
        @classmethod
        def fromProj(cls, *args): return cls()
        def toWkt(self): return "MOCK_WKT"
    mock_qgis.core.QgsCoordinateReferenceSystem = MockQgsCoordinateReferenceSystem
    class MockQgsFillSymbol:
        def __init__(self, *args, **kwargs): pass
        @staticmethod
        def createSimple(*args): return MagicMock()
        def symbolLayerCount(self): return 1
    class MockQgsCategorizedSymbolRenderer:
        def __init__(self, *args, **kwargs): pass
        def setSourceSymbol(self, *args): pass
    mock_qgis.core.QgsFillSymbol = MockQgsFillSymbol
    mock_qgis.core.QgsCategorizedSymbolRenderer = MockQgsCategorizedSymbolRenderer
    
    from qgis.PyQt.QtWidgets import QComboBox
    class MockMapLayerComboBox(QComboBox):
        def setFilters(self, filters): pass
        def setAllowEmptyLayer(self, allow): pass
        def setLayer(self, layer): pass
        def currentLayer(self): return MagicMock()
    
    class MockFieldComboBox(QComboBox):
        def setLayer(self, layer): pass
        
    from qgis.PyQt.QtWidgets import QLineEdit
    class MockFilterLineEdit(QLineEdit):
        def setShowSearchIcon(self, show): pass

    mock_qgis.gui.QgsMapLayerComboBox = MockMapLayerComboBox
    mock_qgis.gui.QgsFieldComboBox = MockFieldComboBox
    mock_qgis.gui.QgsFilterLineEdit = MockFilterLineEdit

    class MockQgsGeometry:
        def __init__(self, *args, **kwargs): 
            self.wkt = ""
        @classmethod
        def fromWkt(cls, wkt): 
            geom = cls()
            geom.wkt = wkt
            return geom
        def fromWkb(self, wkb): 
            self.wkt = wkb.decode() if wkb else ""
        def isNull(self): return not self.wkt
        def isEmpty(self): return not self.wkt
        def isGeosValid(self): 
            return "10 10, 10 0" not in self.wkt
        def area(self):
            if "3 3" in self.wkt: return 9.0
            if "4 4" in self.wkt: return 16.0
            if "8 8" in self.wkt: return 64.0
            if "10 10" in self.wkt: return 100.0
            if "30 10" in self.wkt: return 100.0
            return 0.0
        def asWkb(self): return self.wkt.encode() if self.wkt else b""
    mock_qgis.core.QgsGeometry = MockQgsGeometry
    
    class MockQgsProject:
        @classmethod
        def instance(cls):
            mock = MagicMock()
            mock_crs = MagicMock()
            mock_crs.authid.return_value = "EPSG:4326"
            mock_crs.description.return_value = "WGS 84"
            mock.crs.return_value = mock_crs
            mock.mapLayers = MagicMock(return_value={})
            return mock
    mock_qgis.core.QgsProject = MockQgsProject
    class MockQgsVectorLayer:
        def __init__(self, *args, **kwargs):
            self._renderer = None
        def isValid(self): return True
        def setRenderer(self, renderer): self._renderer = renderer
        def renderer(self): return self._renderer
        def triggerRepaint(self): pass
        def emitStyleChanged(self): pass
        def setCustomProperty(self, *args): pass
        def customProperty(self, *args): return ""
    mock_qgis.core.QgsVectorLayer = MockQgsVectorLayer
    
    mock_qgis.core.QgsApplication = MagicMock
    mock_qgis.core.QgsApplication.qgisUserDatabaseFilePath = MagicMock(return_value=os.path.join(PROJECT_ROOT, "scratch", "mock_qgis.db"))
    
    
    # Map qgis.PyQt to the real qgis.PyQt that is installed in the system

@pytest.fixture(scope="session")
def qgis_app(qapp):
    """Mock fixture for qgis_app since pytest-qgis is not installed."""
    return qapp

@pytest.fixture(scope="session")
def registered_vn2000_crs(qgis_app):
    """Fixture to ensure VN-2000 CRS databases are registered in the current session."""
    from modules.crs_converter.crs_utils import Vn2000DbHelper
    success, msg = Vn2000DbHelper.register_provinces()
    return success, msg

class MockLauncher:
    def __init__(self):
        self.webgis_dir = os.path.join(PROJECT_ROOT, "webgis_demo")
        self.passcode = "123456"
        self._server = None
        self._thread = None
        self._url = None
        self.errors = []

    def _push_error(self, msg):
        self.errors.append(msg)

@pytest.fixture(scope="session")
def webgis_test_server():
    """Fixture to manage internal WebGIS testing server lifetime."""
    from modules.webgis import start_server, stop_server
    launcher = MockLauncher()
    url = start_server(launcher)
    assert url is not None, f"Failed to start server: {launcher.errors}"
    yield launcher
    if launcher._server:
        stop_server(launcher._server)

@pytest.fixture
def mock_layer():
    """Layer chuẩn dùng lại được cho nhiều test"""
    from unittest.mock import MagicMock
    layer = MagicMock()
    layer.isValid.return_value = True
    layer.name.return_value = "test_layer"
    layer.featureCount.return_value = 100
    
    _props = {}
    layer.customProperty.side_effect = lambda k, d=None: _props.get(k, d)
    layer.setCustomProperty.side_effect = lambda k, v: _props.update({k: v})
    
    # Mock fields
    fields = MagicMock()
    fields.indexFromName.return_value = 1
    layer.fields.return_value = fields
    
    return layer

@pytest.fixture
def mock_iface(mock_layer):
    """Giả lập QGIS iface"""
    from unittest.mock import MagicMock
    iface = MagicMock()
    iface.activeLayer.return_value = mock_layer
    iface.mapCanvas.return_value = MagicMock()
    return iface
