# Valida Ghostscript na pasta dist copiada (PC de producao)
# Uso: cd D:\ArtemiS   (pasta com Main.exe)
#      .\scripts\test_ghostscript_dist.ps1
# Ou copie este script junto com dist/ e execute na raiz da instalacao.

param(
    [string]$DistDir = (Get-Location).Path
)

$ErrorActionPreference = 'Stop'
$DistDir = (Resolve-Path $DistDir).Path

Write-Host "Pasta de instalacao: $DistDir"
Write-Host ''

$Required = @(
    'Main.exe',
    'vendor\ghostscript\bin\gswin64c.exe',
    'vendor\ghostscript\bin\gsdll64.dll',
    'vendor\ghostscript\lib\Fontmap.ATB'
)

$missing = @()
foreach ($rel in $Required) {
    $full = Join-Path $DistDir $rel
    if (-not (Test-Path $full)) {
        $missing += $rel
    } else {
        $item = Get-Item $full
        Write-Host "  OK  $rel ($($item.Length) bytes)"
    }
}

if ($missing.Count -gt 0) {
    Write-Host ''
    Write-Error "Faltando: $($missing -join ', ')`nCopie a pasta dist/ inteira (nao apenas Main.exe)."
}

$GsExe = Join-Path $DistDir 'vendor\ghostscript\bin\gswin64c.exe'
Write-Host ''
Write-Host 'Smoke test: gswin64c --version'
$version = & $GsExe --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "gswin64c falhou (exit $LASTEXITCODE).`nPossiveis causas: antivirus, pasta de rede UNC, permissao.`nSaida: $version"
}

Write-Host "Ghostscript OK: $version"
Write-Host ''
Write-Host 'Caminhos que o ArtemiS usa (frozen):'
Write-Host "  exe_dir     = $DistDir"
Write-Host "  gs_root     = $(Join-Path $DistDir 'vendor\ghostscript')"
Write-Host "  gswin64c    = $GsExe"
Write-Host "  GS_LIB      = $(Join-Path $DistDir 'vendor\ghostscript\lib')"
Write-Host ''
Write-Host 'Se o teste passou mas o app diz motor indisponivel, veja logs/print.log no startup.'
