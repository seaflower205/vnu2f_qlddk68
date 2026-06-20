# -*- coding: utf-8 -*-
import http.client
from urllib.parse import urlparse

def test_webgis_server_running(webgis_test_server):
    """Verify that the WebGIS local server is running and passcode is generated."""
    launcher = webgis_test_server
    assert launcher._server is not None
    assert launcher.passcode is not None
    assert launcher._url is not None

def test_webgis_homepage_without_passcode(webgis_test_server):
    """Verify requesting the homepage without passcode gets the auth page (200 OK)."""
    launcher = webgis_test_server
    parsed_url = urlparse(launcher._url)
    host_port = parsed_url.netloc

    conn = http.client.HTTPConnection(host_port)
    headers = {"X-Forwarded-For": "8.8.8.8"}
    conn.request("GET", "/", headers=headers)
    resp = conn.getresponse()
    body = resp.read().decode("utf-8")
    
    assert resp.status == 200
    assert "WebGIS Authentication" in body

def test_webgis_block_assets_without_auth(webgis_test_server):
    """Verify that requesting a sensitive asset without passcode blocks access with 401."""
    launcher = webgis_test_server
    parsed_url = urlparse(launcher._url)
    host_port = parsed_url.netloc

    conn = http.client.HTTPConnection(host_port)
    headers = {"X-Forwarded-For": "8.8.8.8"}
    conn.request("GET", "/js/app.js", headers=headers)
    resp = conn.getresponse()
    resp.read()
    
    assert resp.status == 401
