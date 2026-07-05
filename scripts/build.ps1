# Build portavel do ArtemiS (PyInstaller + Ghostscript + verificacao)
# Uso: .\scripts\build.ps1
# Saida: pasta dist/ pronta para copiar nos PCs de producao

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$GsExe = Join-Path $ProjectRoot 'vendor\ghostscript\bin\gswin64c.exe'
if (-not (Test-Path $GsExe)) {
    Write-Host 'Ghostscript ausente em vendor/ghostscript/ — executando fetch...'
    & (Join-Path $ProjectRoot 'scripts\fetch_ghostscript.ps1')
}

$PyInstaller = @(
    (Join-Path $ProjectRoot '.venv\Scripts\pyinstaller.exe'),
    (Join-Path $ProjectRoot 'venv\Scripts\pyinstaller.exe'),
    'pyinstaller'
) | Where-Object { $_ -eq 'pyinstaller' -or (Test-Path $_) } | Select-Object -First 1

if (-not $PyInstaller) {
    throw 'PyInstaller nao encontrado. Ative o venv e instale: pip install pyinstaller'
}

Write-Host "Build: $PyInstaller Main.spec"
& $PyInstaller (Join-Path $ProjectRoot 'Main.spec')
if ($LASTEXITCODE -ne 0) { throw "PyInstaller falhou (exit $LASTEXITCODE)" }

& (Join-Path $ProjectRoot 'scripts\verify_dist.ps1')

$DistGs = Join-Path $ProjectRoot 'dist\vendor\ghostscript\bin\gswin64c.exe'
Write-Host "Smoke test Ghostscript: $DistGs"
$version = & $DistGs --version 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "gswin64c --version falhou (exit $LASTEXITCODE): $version"
}
Write-Host "Ghostscript OK: $version"
Write-Host ''
Write-Host 'Build concluido. Copie a pasta dist/ inteira para os PCs de producao.'
