"""Mechanically extracted functions from tunnel.py."""
from __future__ import annotations

import json
import os
import threading
import time

def deploy_to_github(launcher, username, token):
    """Automatically deploy local WebGIS assets to GitHub Pages."""
    def run():
        import urllib.request
        import urllib.error
        import base64
        
        repo_name = "vnu2f_webgis"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "VNU2F-Plugin"
        }
        
        # 1. Create repository if missing
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
            with urllib.request.urlopen(req) as resp:  # noqa: F841  # noqa: F841
                pass
        except urllib.error.HTTPError as e:
            if e.code != 422: # 422: repo already exists
                try:
                    err_msg = e.read().decode('utf-8')
                    err_data = json.loads(err_msg)
                    launcher.signals.deploy_finished.emit(False, f"Lỗi tạo repository: {err_data.get('message', err_msg)}")
                except Exception:  # noqa: BLE001 — intentional suppress
                    launcher.signals.deploy_finished.emit(False, f"Lỗi tạo repository (Mã: {e.code})")
                return
        except Exception as e:  # noqa: BLE001 — intentional suppress
            launcher.signals.deploy_finished.emit(False, f"Lỗi kết nối GitHub: {e}")
            return
            
        time.sleep(2)
        
        # 2. Upload static assets
        files_to_upload = [
            ("index.html", "index.html"),
            ("css/layout.css", "css/layout.css"),
            ("js/app.js", "js/app.js"),
            ("js/worker.js", "js/worker.js"),
            ("data/parcels.geojson", "data/parcels.geojson")
        ]
        
        for local_rel, repo_path in files_to_upload:
            local_path = os.path.join(launcher.webgis_dir, local_rel)
            if not os.path.exists(local_path):
                continue
                
            with open(local_path, "rb") as f:
                content = f.read()
            
            content_b64 = base64.b64encode(content).decode('utf-8')
            
            # Check SHA of the file if it exists (for updates)
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
                with urllib.request.urlopen(req_put) as resp_put:  # noqa: F841  # noqa: F841
                    pass
            except urllib.error.HTTPError as e:
                try:
                    err_msg = e.read().decode('utf-8')
                    err_data = json.loads(err_msg)
                    launcher.signals.deploy_finished.emit(False, f"Lỗi lưu file {repo_path}: {err_data.get('message', err_msg)}")
                except Exception:  # noqa: BLE001 — intentional suppress
                    launcher.signals.deploy_finished.emit(False, f"Lỗi lưu file {repo_path} (Mã: {e.code})")
                return
            except Exception as e:  # noqa: BLE001 — intentional suppress
                launcher.signals.deploy_finished.emit(False, f"Lỗi upload file {repo_path}: {e}")
                return
        
        # 3. Activate GitHub Pages if needed
        pages_url = f"https://api.github.com/repos/{username}/{repo_name}/pages"
        req_pages_get = urllib.request.Request(pages_url, headers=headers, method="GET")
        pages_exists = False
        try:
            with urllib.request.urlopen(req_pages_get) as resp_pages:  # noqa: F841  # noqa: F841
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
                with urllib.request.urlopen(req_pages_post) as resp_pages_post:  # noqa: F841  # noqa: F841
                    pass
            except Exception:  # noqa: BLE001 — intentional suppress
                pass
        
        live_url = f"https://{username}.github.io/{repo_name}/"
        launcher.signals.deploy_finished.emit(True, live_url)

    threading.Thread(target=run, daemon=True).start()
