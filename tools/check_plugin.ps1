$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$python = "C:\Python314\python.exe"

if (-not (Test-Path $python)) {
    $python = "python"
}

Set-Location $root
& $python tools\check_plugin.py
