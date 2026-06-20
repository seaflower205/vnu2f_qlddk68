import pytest
from qgis.PyQt.QtCore import QThread
from modules.webgis.tunnel_manager import TunnelManager

def test_tunnel_manager_is_qthread():
    """Verify TunnelManager correctly inherits from QThread to avoid freezing QGIS."""
    print(f"TunnelManager type: {type(TunnelManager)}, val: {TunnelManager}")
    print(f"QThread type: {type(QThread)}, val: {QThread}")
    assert issubclass(TunnelManager, QThread)
    assert hasattr(TunnelManager, "run")
    assert callable(TunnelManager.run)

def test_tunnel_manager_signals():
    """Verify TunnelManager has the required signals."""
    manager = TunnelManager("tunnel")
    assert hasattr(manager, "tunnel_finished")
    assert hasattr(manager, "deploy_finished")
    assert hasattr(manager, "duckdns_finished")
