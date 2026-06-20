# -*- coding: utf-8 -*-
"""Package and deploy the plugin to the QGIS profile plugins directory.
"""

import os
import shutil
import zipfile
from pathlib import Path
import sys

# Ensure tools directory is in path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from package_plugin import build_package

PLUGIN_NAME = "vnu2f_qlddk68"

def deploy():
    root = Path(__file__).resolve().parents[1]
    zip_path = build_package(root)
    print(f"Zip created at: {zip_path}")

    appdata = os.environ.get("APPDATA")
    if not appdata:
        print("Error: APPDATA environment variable not found.")
        return False

    target_dir = Path(appdata) / "QGIS" / "QGIS4" / "profiles" / "default" / "python" / "plugins" / PLUGIN_NAME
    
    # Try QGIS4, fallback to QGIS3 if needed
    if not target_dir.parent.exists():
        target_dir = Path(appdata) / "QGIS" / "QGIS3" / "profiles" / "default" / "python" / "plugins" / PLUGIN_NAME
        
    if not target_dir.parent.exists():
        print(f"Error: QGIS plugin directory parent does not exist: {target_dir.parent}")
        return False

    print(f"Deploying to: {target_dir}")
    if target_dir.exists():
        try:
            shutil.rmtree(target_dir)
        except Exception as e:
            print(f"Warning: Could not remove old directory: {e}. Trying to overwrite files.")
        
    # Unzip to target's parent directory
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(target_dir.parent)
        
    print("Deployment successful!")
    return True

if __name__ == "__main__":
    deploy()
