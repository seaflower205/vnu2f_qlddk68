"""Mechanically extracted responsibilities from server.py."""

import functools
import json
import time
import threading
import secrets
import string
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
import atexit  # noqa: E402


class WebGisApiMixin:
    def _check_auth(self) -> bool:
        # Check if the host is local (localhost or 127.0.0.1) and not proxying
        host = self.headers.get("Host", "")
        host_name = host.split(":")[0] if ":" in host else host
        
        has_proxy_headers = any(h in self.headers for h in (
            "X-Forwarded-For", "X-Forwarded-Host", "X-Forwarded-Proto",
            "X-Real-IP", "Forwarded", "Via"
        ))
        
        if host_name in ("127.0.0.1", "localhost") and not has_proxy_headers:
            return True

        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        url_key = query.get("key", [None])[0]
        
        cookie_header = self.headers.get("Cookie", "")
        cookie_match = re.search(r"webgis_token=([a-zA-Z0-9]+)", cookie_header)
        cookie_key = cookie_match.group(1) if cookie_match else None
        
        expected_passcode = getattr(type(self).launcher, "passcode", None)
        
        is_authenticated = False
        if not expected_passcode:
            is_authenticated = True
        else:
            is_authenticated = (url_key == expected_passcode) or (cookie_key == expected_passcode)
            
        if not is_authenticated:
            time.sleep(1.0)  # Throttling to prevent brute force
            
        return is_authenticated
    def do_GET(self):
        parsed = urlparse(self.path)
        if not self._check_auth():
            if parsed.path in ["", "/", "/index.html"]:
                query = parse_qs(parsed.query)
                url_key = query.get("key", [None])[0]
                error_msg = ""
                if url_key is not None:
                    error_msg = '<div class="error">Khóa bảo mật không chính xác!</div>'
                
                response_html = self.LOGIN_HTML.replace("{error_placeholder}", error_msg)
                response_bytes = response_html.encode("utf-8")
                
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(response_bytes)))
                self.end_headers()
                self.wfile.write(response_bytes)
                return
            else:
                self.send_response(401)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Unauthorized"}).encode("utf-8"))
                return
                
        query = parse_qs(parsed.query)
        url_key = query.get("key", [None])[0]
        expected_passcode = getattr(type(self).launcher, "passcode", None)
        if url_key == expected_passcode and expected_passcode:
            original_end_headers = self.end_headers
            def custom_end_headers():
                self.send_header("Set-Cookie", f"webgis_token={expected_passcode}; Path=/; Max-Age=3600; SameSite=Lax")
                original_end_headers()
            self.end_headers = custom_end_headers
            
        if parsed.path == "/api/parcels":
            self.handle_api_parcels(parsed)
        elif parsed.path == "/api/share/status":
            self.handle_api_share_status()
        elif parsed.path == "/api/share/activate":
            self.handle_api_share_activate()
        elif parsed.path == "/api/share/deactivate":
            self.handle_api_share_deactivate()
        else:
            super().do_GET()
    def handle_api_parcels(self, parsed):
        import os
        launcher = type(self).launcher
        response_bytes = b""
        
        if launcher:
            out_path = os.path.join(launcher.webgis_dir, "data", "parcels.geojson")
            if os.path.exists(out_path):
                try:
                    with open(out_path, "rb") as f:
                        response_bytes = f.read()
                except Exception:  # noqa: BLE001 — intentional suppress
                    pass

        if not response_bytes:
            response_bytes = json.dumps({"type": "FeatureCollection", "features": []}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()
        
        self.wfile.write(response_bytes)
    def handle_api_share_status(self):
        launcher = type(self).launcher
        is_active = (getattr(launcher, "_tunnel_process", None) is not None) and (launcher._tunnel_process.poll() is None)
        if not is_active:
            launcher._tunnel_url = None
            launcher._tunnel_process = None
            
        tunnel_url = getattr(launcher, "_tunnel_url", "") if is_active else ""
        passcode = getattr(launcher, "passcode", "")
        
        response_bytes = json.dumps({
            "active": is_active,
            "url": tunnel_url,
            "passcode": passcode
        }).encode("utf-8")
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(response_bytes)
    def handle_api_share_activate(self):
        launcher = type(self).launcher
        from .tunnel import start_internet_tunnel
        
        is_active = (getattr(launcher, "_tunnel_process", None) is not None) and (launcher._tunnel_process.poll() is None)
        if not is_active:
            launcher._tunnel_url = None
            launcher._tunnel_process = None
            start_internet_tunnel(launcher)
            
        # Wait up to 12 seconds for URL
        start_time = time.time()
        while time.time() - start_time < 12:
            if getattr(launcher, "_tunnel_url", None):
                break
            time.sleep(0.5)
            
        is_active = (getattr(launcher, "_tunnel_process", None) is not None) and (launcher._tunnel_process.poll() is None)
        tunnel_url = getattr(launcher, "_tunnel_url", "") if is_active else ""
        passcode = getattr(launcher, "passcode", "")
        
        response_bytes = json.dumps({
            "active": is_active,
            "url": tunnel_url,
            "passcode": passcode,
            "error": None if is_active else "Không khởi tạo được SSH tunnel. Vui lòng thử lại sau."
        }).encode("utf-8")
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(response_bytes)
    def handle_api_share_deactivate(self):
        launcher = type(self).launcher
        from .tunnel import stop_tunnel
        stop_tunnel(launcher)
        
        response_bytes = json.dumps({
            "active": False,
            "status": "stopped"
        }).encode("utf-8")
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(response_bytes)
