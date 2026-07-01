# Build CoClick into a distributable zip (Windows / PowerShell).
#
#   1. installs runtime + build deps
#   2. runs PyInstaller (onedir, using build.spec)
#   3. zips dist\CoClick -> dist\CoClick.zip  (hand this to a friend)
#
# Run from the project root:  .\build.ps1

$ErrorActionPreference = "Stop"

Write-Host "==> Installing dependencies..." -ForegroundColor Cyan
py -m pip install -r requirements.txt
py -m pip install pyinstaller

Write-Host "==> Building with PyInstaller (onedir)..." -ForegroundColor Cyan
py -m PyInstaller build.spec --noconfirm

$distDir = Join-Path $PSScriptRoot "dist\CoClick"
if (-not (Test-Path $distDir)) {
    throw "Build failed: $distDir not found."
}

# Dedupe Tesseract DLLs: if a system Tesseract is on PATH, PyInstaller also copies
# its DLLs to _internal\ (root). We already ship the whole Tesseract under
# _internal\tesseract\ (and bot_engine.py points there), so the root copies are
# dead weight. Remove any root file that is byte-for-byte identical to one shipped
# under _internal\tesseract\.
$internal = Join-Path $distDir "_internal"
$tessDir  = Join-Path $internal "tesseract"
if ((Test-Path $tessDir) -and (Test-Path $internal)) {
    $freed = 0
    Get-ChildItem $tessDir -File | ForEach-Object {
        $rootCopy = Join-Path $internal $_.Name
        if (Test-Path $rootCopy) {
            $r = Get-Item $rootCopy
            if ($r.Length -eq $_.Length) {
                $freed += $r.Length
                Remove-Item $rootCopy -Force
            }
        }
    }
    Write-Host ("==> Deduped Tesseract DLLs, freed {0:N0} MB" -f ($freed/1MB)) -ForegroundColor Cyan
}

$zipPath = Join-Path $PSScriptRoot "dist\CoClick.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }

Write-Host "==> Zipping to $zipPath ..." -ForegroundColor Cyan
Compress-Archive -Path (Join-Path $distDir "*") -DestinationPath $zipPath

Write-Host ""
Write-Host "Done. Share dist\CoClick.zip" -ForegroundColor Green
if (-not (Test-Path (Join-Path $PSScriptRoot "vendor\tesseract\tesseract.exe"))) {
    Write-Host "WARNING: vendor\tesseract\tesseract.exe was not found, so Tesseract" -ForegroundColor Yellow
    Write-Host "         was NOT bundled. The exe will need a system Tesseract install." -ForegroundColor Yellow
    Write-Host "         See vendor\tesseract\README.txt to bundle it." -ForegroundColor Yellow
}
