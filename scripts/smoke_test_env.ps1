# Smoke test do ambiente Python (Windows — dev ou antes do build).
# Uso: .\scripts\smoke_test_env.ps1
#      .\scripts\smoke_test_env.ps1 -Python py -PythonVersion 3.14
# Valida: venv, pip install, py_compile, pytest, imports críticos.

param(
    [string]$Python = 'py',
    [string]$PythonVersion = '3.14',
    [switch]$SkipPytest,
    [switch]$RunBuild
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$VenvDir = Join-Path $ProjectRoot '.venv-smoke'
if (Test-Path $VenvDir) { Remove-Item -Recurse -Force $VenvDir }

Write-Host '== ArtemiS smoke test (Windows) ==' -ForegroundColor Cyan
Write-Host "Python launcher: $Python -$PythonVersion"
Write-Host ''

& $Python "-$PythonVersion" -m venv $VenvDir
$Py = Join-Path $VenvDir 'Scripts\python.exe'
$Pip = Join-Path $VenvDir 'Scripts\pip.exe'

& $Py --version
& $Pip install -q -U pip setuptools wheel
& $Pip install -q -r (Join-Path $ProjectRoot 'requirements.txt') pytest

Write-Host '[1/5] py_compile' -ForegroundColor Yellow
& $Py -m py_compile (Join-Path $ProjectRoot 'Main.py') (Join-Path $ProjectRoot 'app\bootstrap.py')

if (-not $SkipPytest) {
    Write-Host '[2/5] pytest' -ForegroundColor Yellow
    $env:PYTHONPATH = $ProjectRoot
    & $Py -m pytest (Join-Path $ProjectRoot 'tests') -q
    if ($LASTEXITCODE -ne 0) { throw 'pytest falhou' }
} else {
    Write-Host '[2/5] pytest (pulado)' -ForegroundColor DarkYellow
}

Write-Host '[3/5] barcode imports' -ForegroundColor Yellow
& $Py -c @"
from app.utils.barcode_generator import create_barcode_bytes, create_datamatrix_bytes, create_qrcode_bytes
create_barcode_bytes('1234567890', 0.3, 8)
create_datamatrix_bytes('12345')
create_qrcode_bytes('test')
print('barcodes OK')
"@
if ($LASTEXITCODE -ne 0) { throw 'imports de barcode falharam' }

Write-Host '[4/5] pywin32' -ForegroundColor Yellow
& $Py -c "import win32print; print('win32print OK:', len(win32print.EnumPrinters(2)))"
if ($LASTEXITCODE -ne 0) { throw 'pywin32 falhou' }

if ($RunBuild) {
    Write-Host '[5/5] build + verify_dist' -ForegroundColor Yellow
  # Usa o venv de smoke só para validar que o build script encontra pyinstaller no venv principal
    $MainVenvPy = @(
        (Join-Path $ProjectRoot '.venv\Scripts\python.exe'),
        (Join-Path $ProjectRoot 'venv\Scripts\python.exe')
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $MainVenvPy) {
        Write-Warning 'Venv principal (.venv) nao encontrado; copie .venv-smoke para .venv ou crie manualmente antes do build.'
    } else {
        & (Join-Path $ProjectRoot 'scripts\build.ps1')
    }
} else {
    Write-Host '[5/5] build (pulado; use -RunBuild para incluir)' -ForegroundColor DarkYellow
}

Write-Host ''
Write-Host 'OK: ambiente validado.' -ForegroundColor Green
Write-Host 'Proximo passo manual: abrir Main.exe ou rodar Main.py e testar PDF de teste + impressao.'
