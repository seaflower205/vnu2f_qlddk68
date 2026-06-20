# -*- coding: utf-8 -*-
"""Internet tunneling and remote deployment handlers for WebGIS."""

import os
import time
import subprocess
import threading
import shutil
import json



def stop_tunnel(launcher):
    """Stop the active SSH tunnel process if running."""
    if hasattr(launcher, "_tunnel_process") and launcher._tunnel_process:
        try:
            launcher._tunnel_process.terminate()
        except Exception:  # noqa: BLE001 — intentional suppress
            pass
        launcher._tunnel_process = None
    launcher._tunnel_url = None

def update_duckdns(launcher, domain, token):
    """Update public IP to DuckDNS subdomain."""
    def run():
        import urllib.request
        import urllib.parse
        url = f"https://www.duckdns.org/update?domains={urllib.parse.quote(domain)}&token={urllib.parse.quote(token)}"
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                body = response.read().decode("utf-8").strip()
                if body == "OK":
                    launcher.signals.duckdns_finished.emit(True, "OK")
                else:
                    launcher.signals.duckdns_finished.emit(False, f"DuckDNS API returned: {body}")
        except Exception as e:  # noqa: BLE001 — intentional suppress
            launcher.signals.duckdns_finished.emit(False, str(e))

    threading.Thread(target=run, daemon=True).start()


from .tunnel_quick import _shorten_url, start_internet_tunnel

from .tunnel_github import deploy_to_github
