# -*- coding: utf-8 -*-
import http.client
import json
from urllib.parse import urlparse

def test_api_parcels(webgis_test_server):
    """Test retrieving GeoJSON parcels from /api/parcels."""
    launcher = webgis_test_server
    parsed_url = urlparse(launcher._url)
    host_port = parsed_url.netloc

    conn = http.client.HTTPConnection(host_port)
    conn.request("GET", "/api/parcels")
    resp = conn.getcall = conn.getresponse()
    body = resp.read().decode("utf-8")
    
    assert resp.status == 200
    data = json.loads(body)
    assert "type" in data
    assert data["type"] == "FeatureCollection"

def test_api_share_status(webgis_test_server):
    """Test retrieving share status via /api/share/status."""
    launcher = webgis_test_server
    parsed_url = urlparse(launcher._url)
    host_port = parsed_url.netloc

    conn = http.client.HTTPConnection(host_port)
    conn.request("GET", "/api/share/status")
    resp = conn.getresponse()
    body = resp.read().decode("utf-8")
    
    assert resp.status == 200
    data = json.loads(body)
    assert "active" in data
    assert "url" in data
    assert "passcode" in data

def test_passcode_auth_cookie_flow(webgis_test_server):
    """Test login via passcode and verify Set-Cookie header."""
    launcher = webgis_test_server
    parsed_url = urlparse(launcher._url)
    host_port = parsed_url.netloc

    # To trigger passcode check, we simulate a proxy request (adds X-Forwarded-For)
    headers = {"X-Forwarded-For": "8.8.8.8"}
    conn = http.client.HTTPConnection(host_port)
    
    # 1. Invalid passcode
    conn.request("GET", "/?key=wrongcode", headers=headers)
    resp = conn.getcall = conn.getresponse()
    body = resp.read().decode("utf-8")
    assert resp.status == 200
    assert "Khóa bảo mật không chính xác!" in body
    
    # 2. Valid passcode
    conn = http.client.HTTPConnection(host_port)
    conn.request("GET", f"/?key={launcher.passcode}", headers=headers)
    resp = conn.getresponse()
    body = resp.read().decode("utf-8")
    assert resp.status == 200
    
    # Check Set-Cookie header
    cookie_header = resp.getheader("Set-Cookie")
    assert cookie_header is not None
    assert "webgis_token=" in cookie_header
    assert launcher.passcode in cookie_header

def test_api_share_activation_flow(webgis_test_server):
    """Test activation and deactivation APIs."""
    launcher = webgis_test_server
    parsed_url = urlparse(launcher._url)
    host_port = parsed_url.netloc

    # 1. Deactivate first to ensure state
    conn = http.client.HTTPConnection(host_port)
    conn.request("GET", "/api/share/deactivate")
    resp = conn.getresponse()
    body = resp.read().decode("utf-8")
    assert resp.status == 200
    
    # 2. Check status (should be inactive)
    conn = http.client.HTTPConnection(host_port)
    conn.request("GET", "/api/share/status")
    resp = conn.getcall = conn.getresponse()
    data = json.loads(resp.read().decode("utf-8"))
    assert data["active"] is False

    # 3. Activate (should attempt tunnel, will mock/fail gracefully or run depending on setup)
    conn = http.client.HTTPConnection(host_port)
    conn.request("GET", "/api/share/activate")
    resp = conn.getresponse()
    data = json.loads(resp.read().decode("utf-8"))
    assert "active" in data
