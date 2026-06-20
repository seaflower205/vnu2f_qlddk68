"""Mechanically extracted functions from tunnel.py."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import time

def _shorten_url(long_url):
    import urllib.request
    import urllib.parse
    
    safe_url = urllib.parse.quote(long_url)
    
    # 1. Try with statistics logging enabled
    try:
        api_url = f"https://is.gd/create.php?format=json&logstats=1&url={safe_url}"
        req = urllib.request.Request(
            api_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            resp_bytes = response.read()
            data = json.loads(resp_bytes.decode("utf-8"))
            if "shorturl" in data:
                return data.get("shorturl")
    except Exception:  # noqa: BLE001 — intentional suppress
        pass

    # 2. Fallback: try without statistics logging (standard shortening)
    try:
        api_url = f"https://is.gd/create.php?format=json&url={safe_url}"
        req = urllib.request.Request(
            api_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data.get("shorturl")
    except Exception:  # noqa: BLE001 — intentional suppress
        return None

def start_internet_tunnel(launcher):
    """Start SSH tunnel connecting Serveo or localhost.run in a background thread."""
    def run():
        ssh_bin = shutil.which("ssh")
        if not ssh_bin:
            default_paths = [
                r"C:\Windows\System32\OpenSSH\ssh.exe",
                r"C:\Windows\Sysnative\OpenSSH\ssh.exe",
                r"C:\Program Files\Git\usr\bin\ssh.exe",
            ]
            for p in default_paths:
                if os.path.exists(p):
                    ssh_bin = p
                    break
        if not ssh_bin:
            ssh_bin = "ssh"

        port = "8765"
        if launcher._url:
            from urllib.parse import urlparse
            try:
                parsed_url = urlparse(launcher._url)
                if parsed_url.port:
                    port = str(parsed_url.port)
            except Exception:  # noqa: BLE001 — intentional suppress
                pass

        creationflags = 0
        if os.name == "nt":
            creationflags = subprocess.CREATE_NO_WINDOW

        # 1. Try with Serveo
        try:
            cmd = [ssh_bin, "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5", "-R", f"80:127.0.0.1:{port}", "serveo.net"]
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=creationflags
            )
            url = None
            start_time = time.time()
            while time.time() - start_time < 10:
                line = proc.stdout.readline()
                if not line:
                    break
                if "serveousercontent.com" in line or "https://" in line:
                    import re
                    match = re.search(r"https://[a-zA-Z0-9\-\.]+", line)
                    if match:
                        url = match.group(0)
                        break
            if url:
                short_url = _shorten_url(url)
                launcher._tunnel_url = short_url if short_url else url
                launcher._tunnel_process = proc
                launcher.signals.tunnel_finished.emit(True, url, short_url or "", proc)
                return
            else:
                try:
                    proc.terminate()
                except Exception:  # noqa: BLE001 — intentional suppress
                    pass
        except Exception:  # noqa: BLE001 — intentional suppress
            pass

        # 2. Fallback to localhost.run
        try:
            cmd = [ssh_bin, "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5", "-R", f"80:127.0.0.1:{port}", "nokey@localhost.run"]
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=creationflags
            )
            url = None
            start_time = time.time()
            while time.time() - start_time < 10:
                line = proc.stdout.readline()
                if not line:
                    break
                if "lhr.life" in line or "https://" in line:
                    import re
                    match = re.search(r"https://[a-zA-Z0-9\-\.]+", line)
                    if match:
                        url = match.group(0)
                        break
            if url:
                short_url = _shorten_url(url)
                launcher._tunnel_url = short_url if short_url else url
                launcher._tunnel_process = proc
                launcher.signals.tunnel_finished.emit(True, url, short_url or "", proc)
                return
            else:
                try:
                    proc.terminate()
                except Exception:  # noqa: BLE001 — intentional suppress
                    pass
                launcher._tunnel_url = None
                launcher._tunnel_process = None
                launcher.signals.tunnel_finished.emit(False, "Cả Serveo và Localhost.run đều không phản hồi. Hãy kiểm tra kết nối mạng hoặc SSH client.", "", None)
        except Exception as e:  # noqa: BLE001 — intentional suppress
            launcher._tunnel_url = None
            launcher._tunnel_process = None
            launcher.signals.tunnel_finished.emit(False, f"Lỗi kết nối tunnel: {e}", "", None)

    threading.Thread(target=run, daemon=True).start()
