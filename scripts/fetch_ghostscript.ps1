# Baixa e instala Ghostscript AGPL (Windows x64) em vendor/ghostscript/
# Uso: .\scripts\fetch_ghostscript.ps1

$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VendorDir = Join-Path $ProjectRoot 'vendor\ghostscript'
$VersionFile = Join-Path $VendorDir 'VERSION'

if (-not (Test-Path $VersionFile)) {
    throw "Arquivo não encontrado: $VersionFile"
}

$Version = (Get-Content $VersionFile -Raw).Trim()
$Tag = 'gs' + ($Version -replace '\.', '')
$InstallerName = "${Tag}w64.exe"
$Url = "https://github.com/ArtifexSoftware/ghostpdl-downloads/releases/download/$Tag/$InstallerName"

$TempDir = Join-Path $env:TEMP "artemis-gs-$Tag"
$InstallerPath = Join-Path $TempDir $InstallerName
$InstallDir = Join-Path $TempDir 'install'

Write-Host "Ghostscript $Version (tag $Tag) -> $VendorDir"

New-Item -ItemType Directory -Force -Path $TempDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $VendorDir 'bin') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $VendorDir 'lib') | Out-Null

if (-not (Test-Path $InstallerPath)) {
    Write-Host "Baixando $Url ..."
    Invoke-WebRequest -Uri $Url -OutFile $InstallerPath -UseBasicParsing
}

if (Test-Path $InstallDir) {
    Remove-Item $InstallDir -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

Write-Host "Instalando em pasta temporaria (silencioso) ..."
# /D= deve ser o ultimo argumento e sem aspas no caminho para alguns instaladores Inno Setup
$proc = Start-Process -FilePath $InstallerPath -ArgumentList @('/S', "/D=$InstallDir") -Wait -PassThru
if ($proc.ExitCode -ne 0) {
    throw "Instalador retornou codigo $($proc.ExitCode)"
}

$BinSrc = Join-Path $InstallDir 'bin'
$LibSrc = Join-Path $InstallDir 'lib'
if (-not (Test-Path (Join-Path $BinSrc 'gswin64c.exe'))) {
    throw "gswin64c.exe nao encontrado apos instalar em $InstallDir"
}

Write-Host "Copiando bin e lib ..."
Get-ChildItem (Join-Path $VendorDir 'bin') -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
Get-ChildItem (Join-Path $VendorDir 'lib') -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
Copy-Item -Path (Join-Path $BinSrc '*') -Destination (Join-Path $VendorDir 'bin') -Recurse -Force
Copy-Item -Path (Join-Path $LibSrc '*') -Destination (Join-Path $VendorDir 'lib') -Recurse -Force

$LicenseCandidates = @(
    (Join-Path $InstallDir 'LICENSE'),
    (Join-Path $InstallDir 'LICENSE.txt'),
    (Join-Path (Join-Path $InstallDir 'doc') 'COPYING')
)
foreach ($candidate in $LicenseCandidates) {
    if (Test-Path $candidate) {
        Copy-Item $candidate (Join-Path $VendorDir 'LICENSE.txt') -Force
        break
    }
}

$ExePath = Join-Path $VendorDir 'bin\gswin64c.exe'
if (-not (Test-Path $ExePath)) {
    throw 'Falha ao instalar gswin64c.exe'
}

Write-Host "Concluido: $ExePath"
