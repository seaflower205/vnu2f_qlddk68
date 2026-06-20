# -*- coding: utf-8 -*-
"""Internet tunneling and remote deployment handlers for WebGIS."""

import os
import time
import subprocess
import shutil
import json
import urllib.request
import urllib.parse
import urllib.error
import base64
from qgis.PyQt.QtCore import QThread, pyqtSignal

def _shorten_url(long_url):
    safe_url = urllib.parse.quote(long_url)
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

class TunnelManager(QThread):
    tunnel_finished = pyqtSignal(bool, str, str, object)
    deploy_finished = pyqtSignal(bool, str, str)
    duckdns_finished = pyqtSignal(bool, str)

    def __init__(self, mode, launcher=None, **kwargs):
        super().__init__()
        self.mode = mode
        self.launcher = launcher
        self.kwargs = kwargs

    def run(self):
        if self.mode == "tunnel":
            self._run_tunnel()
        elif self.mode == "duckdns":
            self._run_duckdns()
        elif self.mode == "github":
            self._run_github()

    def _run_tunnel(self):
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
        if self.launcher and self.launcher._url:
            from urllib.parse import urlparse
            try:
                parsed_url = urlparse(self.launcher._url)
                if parsed_url.port:
                    port = str(parsed_url.port)
            except Exception:  # noqa: BLE001 — intentional suppress
                pass

        creationflags = 0
        if os.name == "nt":
            creationflags = subprocess.CREATE_NO_WINDOW

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
                self.tunnel_finished.emit(True, url, short_url or "", proc)
                return
            else:
                try:
                    proc.terminate()
                except Exception:  # noqa: BLE001 — intentional suppress
                    pass
        except Exception:  # noqa: BLE001 — intentional suppress
            pass

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
                self.tunnel_finished.emit(True, url, short_url or "", proc)
                return
            else:
                try:
                    proc.terminate()
                except Exception:  # noqa: BLE001 — intentional suppress
                    pass
                self.tunnel_finished.emit(False, "Cả Serveo và Localhost.run đều không phản hồi. Hãy kiểm tra kết nối mạng hoặc SSH client.", "", None)
        except Exception as e:  # noqa: BLE001 — intentional suppress
            self.tunnel_finished.emit(False, f"Lỗi kết nối tunnel: {e}", "", None)

    def _run_duckdns(self):
        domain = self.kwargs.get('domain')
        token = self.kwargs.get('token')
        url = f"https://www.duckdns.org/update?domains={urllib.parse.quote(domain)}&token={urllib.parse.quote(token)}"
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                body = response.read().decode("utf-8").strip()
                if body == "OK":
                    self.duckdns_finished.emit(True, "OK")
                else:
                    self.duckdns_finished.emit(False, f"DuckDNS API returned: {body}")
        except Exception as e:  # noqa: BLE001 — intentional suppress
            self.duckdns_finished.emit(False, str(e))

    def _run_github(self):
        username = self.kwargs.get('username')
        token = self.kwargs.get('token')
        
        repo_name = "vnu2f_webgis"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "VNU2F-Plugin"
        }
        
        create_url = "https://api.github.com/user/repos"
        data = json.dumps({
            "name": repo_name,
            "description": "WebGIS quản lý thửa đất từ plugin VNU2F QLDDK68",
            "private": False,
            "has_pages": True,
            "auto_init": True
        }).encode('utf-8')
        
        req = urllib.request.Request(create_url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req):
                pass
        except urllib.error.HTTPError as e:
            if e.code != 422: # 422: repo already exists
                try:
                    err_msg = e.read().decode('utf-8')
                    err_data = json.loads(err_msg)
                    self.deploy_finished.emit(False, f"Lỗi tạo repository: {err_data.get('message', err_msg)}", "")
                except Exception:  # noqa: BLE001 — intentional suppress
                    self.deploy_finished.emit(False, f"Lỗi tạo repository (Mã: {e.code})", "")
                return
        except Exception as e:  # noqa: BLE001 — intentional suppress
            self.deploy_finished.emit(False, f"Lỗi kết nối GitHub: {e}", "")
            return
            
        time.sleep(2)
        
        files_to_upload = [
            ("index.html", "index.html"),
            ("css/layout.css", "css/layout.css"),
            ("js/app.js", "js/app.js"),
            ("js/worker.js", "js/worker.js"),
            ("data/parcels.geojson", "data/parcels.geojson")
        ]
        
        for local_rel, repo_path in files_to_upload:
            local_path = os.path.join(self.launcher.webgis_dir, local_rel) if self.launcher else ""
            if not local_path or not os.path.exists(local_path):
                continue
                
            with open(local_path, "rb") as f:
                content = f.read()
            
            content_b64 = base64.b64encode(content).decode('utf-8')
            
            file_url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{repo_path}"
            req_get = urllib.request.Request(file_url, headers=headers, method="GET")
            sha = None
            try:
                with urllib.request.urlopen(req_get) as resp_get:
                    file_info = json.loads(resp_get.read().decode('utf-8'))
                    sha = file_info.get("sha")
            except Exception:  # noqa: BLE001 — intentional suppress
                pass
            
            put_data = {
                "message": f"Deploy {repo_path} via VNU2F QLDDK68",
                "content": content_b64,
            }
            if sha:
                put_data["sha"] = sha
                
            put_data_bytes = json.dumps(put_data).encode('utf-8')
            req_put = urllib.request.Request(file_url, data=put_data_bytes, headers=headers, method="PUT")
            try:
                with urllib.request.urlopen(req_put):
                    pass
            except urllib.error.HTTPError as e:
                try:
                    err_msg = e.read().decode('utf-8')
                    err_data = json.loads(err_msg)
                    self.deploy_finished.emit(False, f"Lỗi lưu file {repo_path}: {err_data.get('message', err_msg)}", "")
                except Exception:  # noqa: BLE001 — intentional suppress
                    self.deploy_finished.emit(False, f"Lỗi lưu file {repo_path} (Mã: {e.code})", "")
                return
            except Exception as e:  # noqa: BLE001 — intentional suppress
                self.deploy_finished.emit(False, f"Lỗi upload file {repo_path}: {e}", "")
                return
        
        pages_url = f"https://api.github.com/repos/{username}/{repo_name}/pages"
        req_pages_get = urllib.request.Request(pages_url, headers=headers, method="GET")
        pages_exists = False
        try:
            with urllib.request.urlopen(req_pages_get):
                pages_exists = True
        except Exception:  # noqa: BLE001 — intentional suppress
            pass
            
        if not pages_exists:
            pages_data = json.dumps({
                "source": {
                    "branch": "main",
                    "path": "/"
                }
            }).encode('utf-8')
            req_pages_post = urllib.request.Request(pages_url, data=pages_data, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req_pages_post):
                    pass
            except Exception:  # noqa: BLE001 — intentional suppress
                pass
        
        live_url = f"https://{username}.github.io/{repo_name}/"
        self.deploy_finished.emit(True, live_url, "")
