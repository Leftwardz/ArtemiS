# Verifica se dist/ esta pronta para copiar nos PCs (apos pyinstaller Main.spec)
# Uso: .\scripts\verify_dist.ps1

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DistDir = Join-Path $ProjectRoot 'dist'

$RequiredFiles = @(
    'Main.exe',
    'config.json',
    'azure.tcl',
    'libdmtx-64.dll',
    'PDFtoPrinter.exe',
    'PDFtoPrinter_2.exe',
    'PDFtoPrinter_3.exe',
    'PDFtoPrinter_4.exe',
    'PDFtoPrinter_5.exe',
    'vendor\ghostscript\bin\gswin64c.exe',
    'vendor\ghostscript\bin\gsdll64.dll'
)

$RequiredDirs = @(
    'fontes',
    'theme',
    'img',
    'vendor\ghostscript\lib',
    'app\i18n\locales',
    'temp',
    'logs'
)

$missing = @()
foreach ($name in $RequiredFiles) {
    if (-not (Test-Path (Join-Path $DistDir $name))) {
        $missing += $name
    }
}
foreach ($name in $RequiredDirs) {
    if (-not (Test-Path (Join-Path $DistDir $name))) {
        $missing += "$name/"
    }
}

if ($missing.Count -gt 0) {
    Write-Error "dist/ incompleta. Faltando: $($missing -join ', ')`nRode: pyinstaller Main.spec"
}

$exe = Join-Path $DistDir 'Main.exe'
$fontCount = (Get-ChildItem (Join-Path $DistDir 'fontes') -File).Count
$sizeMb = [math]::Round((Get-Item $exe).Length / 1MB, 1)
Write-Host "OK: dist/ pronta para deploy ($sizeMb MB em Main.exe, $fontCount fontes)"
Write-Host "  Copie a pasta dist/ inteira para os PCs de producao."
