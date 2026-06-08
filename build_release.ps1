$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host '[1/5] Build run_app.exe (卡丘像素画)...'
pyinstaller -w --icon=app.ico --clean --onefile --name "卡丘像素画" run_app.py

Write-Host '[2/5] Build backend.exe...'
pyinstaller --clean --onefile --name backend backend/main.py

Write-Host '[3/5] Build Tauri frontend...'
Push-Location frontend
try {
    npm run tauri build
}
finally {
    Pop-Location
}

Write-Host '[4/5] Ensure dist directory exists...'
$distDir = Join-Path $scriptDir 'dist'
if (-not (Test-Path $distDir)) {
    New-Item -ItemType Directory -Path $distDir | Out-Null
}

Write-Host '[5/5] Copy frontend.exe to dist...'
$frontendExe = Join-Path $scriptDir 'frontend/src-tauri/target/release/frontend.exe'
if (-not (Test-Path $frontendExe)) {
    throw "frontend.exe not found: $frontendExe"
}

Copy-Item -Path $frontendExe -Destination (Join-Path $distDir 'frontend.exe') -Force

Write-Host '[6/6] Copy block library and assets...'
$libraryFile = Join-Path $scriptDir 'block_library.json'
if (Test-Path $libraryFile) {
    Copy-Item -Path $libraryFile -Destination (Join-Path $distDir 'block_library.json') -Force
}

$assetsDir = Join-Path $scriptDir 'frontend/src/assets'
$distAssetsDir = Join-Path $distDir 'assets'
if (Test-Path $assetsDir) {
    if (-not (Test-Path $distAssetsDir)) {
        New-Item -ItemType Directory -Path $distAssetsDir | Out-Null
    }
    Copy-Item -Path (Join-Path $assetsDir '*') -Destination $distAssetsDir -Recurse -Force
}

Write-Host 'Build finished successfully.' -ForegroundColor Green
