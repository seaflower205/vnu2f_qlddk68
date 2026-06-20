# -*- coding: utf-8 -*-
import pytest

def test_tunnel_manager_contracts():
    from modules.webgis.tunnel_manager import TunnelManager
    
    assert hasattr(TunnelManager, 'run'), "TunnelManager must implement run()"
    assert hasattr(TunnelManager, 'start'), "TunnelManager must inherit from QThread"
    
    # Check signals
    from qgis.PyQt.QtCore import pyqtSignal
    assert hasattr(TunnelManager, 'tunnel_finished')
    assert hasattr(TunnelManager, 'deploy_finished')
    assert hasattr(TunnelManager, 'duckdns_finished')
