# -*- coding: utf-8 -*-
"""Internal HTTP Server and Dynamic Parcels API for WebGIS."""

import functools
import json
import time
import threading
import secrets
import string
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from .server_api_mixin import WebGisApiMixin

LOGIN_HTML = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>WebGIS - Bảo mật</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #0f172a;
            color: #f8fafc;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            margin: 0;
        }
        .card {
            background-color: #1e293b;
            padding: 2.5rem;
            border-radius: 12px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
            width: 100%;
            max-width: 380px;
            text-align: center;
        }
        h2 {
            margin-top: 0;
            color: #38bdf8;
            font-weight: 600;
        }
        p {
            font-size: 0.9rem;
            color: #94a3b8;
            margin-bottom: 1.5rem;
        }
        input[type="password"] {
            width: 100%;
            padding: 0.75rem;
            border: 1px solid #475569;
            background-color: #0f172a;
            color: #f8fafc;
            border-radius: 6px;
            margin-bottom: 1rem;
            box-sizing: border-box;
            font-size: 1.1rem;
            text-align: center;
            letter-spacing: 0.25em;
        }
        input[type="password"]:focus {
            outline: none;
            border-color: #38bdf8;
        }
        button {
            width: 100%;
            padding: 0.75rem;
            background-color: #0284c7;
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 1rem;
            font-weight: 500;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        button:hover {
            background-color: #0369a1;
        }
        .error {
            color: #ef4444;
            font-size: 0.85rem;
            margin-top: 0.75rem;
        }
    </style>
</head>
<body>
    <div class="card">
        <h2>WebGIS Authentication</h2>
        <p>Vui lòng nhập khóa bảo mật (passcode) được cấp từ QGIS Plugin để truy cập bản đồ.</p>
        <form method="GET" action="/">
            <input type="password" name="key" placeholder="••••••" autofocus required>
            <button type="submit">Đăng nhập</button>
        </form>
        {error_placeholder}
    </div>
</body>
</html>
"""

def generate_passcode() -> str:
    # 6-character secure random passcode
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(6))

class _QuietHandler(WebGisApiMixin, SimpleHTTPRequestHandler):
    launcher = None
    LOGIN_HTML = LOGIN_HTML

    def log_message(self, format, *args):
        return

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()


    def do_HEAD(self):
        if not self._check_auth():
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            return
        super().do_HEAD()






import atexit  # noqa: E402

_active_servers = []

def _cleanup_servers():
    for server in list(_active_servers):
        try:
            t = threading.Thread(target=server.shutdown)
            t.daemon = True
            t.start()
            t.join(timeout=1.0)
            server.server_close()
        except Exception:  # noqa: BLE001 — intentional suppress
            pass
    _active_servers.clear()

atexit.register(_cleanup_servers)

def stop_server(server):
    if server in _active_servers:
        try:
            t = threading.Thread(target=server.shutdown)
            t.daemon = True
            t.start()
            t.join(timeout=1.0)
            server.server_close()
        except Exception:  # noqa: BLE001 — intentional suppress
            pass
        try:
            _active_servers.remove(server)
        except ValueError:
            pass

def start_server(launcher) -> str | None:
    """Ensure the local HTTP server is running and returns the local URL."""
    _QuietHandler.launcher = launcher
    
    if not getattr(launcher, "passcode", None):
        launcher.passcode = generate_passcode()
        
    if launcher._server and launcher._thread and launcher._thread.is_alive() and launcher._url:
        return launcher._url

    handler = functools.partial(_QuietHandler, directory=launcher.webgis_dir)
    last_error = None
    for port in range(8765, 8796):
        try:
            server = ThreadingHTTPServer(("0.0.0.0", port), handler)
            server.daemon_threads = True
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            _active_servers.append(server)
            launcher._server = server
            launcher._thread = thread
            launcher._url = f"http://127.0.0.1:{port}/?key={launcher.passcode}"
            return launcher._url
        except OSError as exc:
            last_error = exc

    launcher._push_error(f"Không khởi động được WebGIS server nội bộ: {last_error}")
    return None
