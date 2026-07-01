# -*- mode: python ; coding: utf-8 -*-
# Build: pyinstaller Main.spec
# Saida: dist/ pronta para copiar nos PCs (Main.exe + fontes/ + theme/ + ...)

block_cipher = None

import os
import shutil

base_dir = os.path.abspath('.')


def _find_dll():
    for venv_name in ('.venv', 'venv'):
        candidate = os.path.join(base_dir, venv_name, 'Lib', 'site-packages',
                                 'pylibdmtx', 'libdmtx-64.dll')
        if os.path.isfile(candidate):
            return candidate
    raise FileNotFoundError('libdmtx-64.dll nao encontrado em .venv/venv')


dll_path = _find_dll()

# Ghostscript empacotado (versionado em vendor/ghostscript/ — vem no git clone)
gs_bin = os.path.join(base_dir, 'vendor', 'ghostscript', 'bin')
gs_lib = os.path.join(base_dir, 'vendor', 'ghostscript', 'lib')
gs_exe = os.path.join(gs_bin, 'gswin64c.exe')
if not os.path.isfile(gs_exe) or not os.path.isdir(gs_lib):
    raise SystemExit(
        'Ghostscript nao encontrado em vendor/ghostscript/.\n'
        'Faca git clone completo (bin/ e lib/ estao versionados) ou rode scripts/fetch_ghostscript.ps1.'
    )
gs_datas = [
    (gs_bin, os.path.join('vendor', 'ghostscript', 'bin')),
    (gs_lib, os.path.join('vendor', 'ghostscript', 'lib')),
]

resource_datas = []
for _res in ('img', 'fontes', 'theme'):
    _res_path = os.path.join(base_dir, _res)
    if not os.path.isdir(_res_path):
        raise SystemExit(f'Pasta obrigatoria ausente: {_res}/')
    resource_datas.append((_res_path, _res))

_i18n_locales = os.path.join(base_dir, 'app', 'i18n', 'locales')
if os.path.isdir(_i18n_locales):
    resource_datas.append((_i18n_locales, os.path.join('app', 'i18n', 'locales')))

_azure_tcl = os.path.join(base_dir, 'azure.tcl')
if os.path.isfile(_azure_tcl):
    resource_datas.append((_azure_tcl, '.'))

all_datas = gs_datas + resource_datas

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[(dll_path, '.')],
    datas=all_datas,
    hiddenimports=[
        'reportlab.graphics.barcode.usps4s',
        'reportlab.graphics.barcode.code128',
        'reportlab.graphics.barcode.code93',
        'reportlab.graphics.barcode.code39',
        'reportlab.graphics.barcode.usps',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='img/favicon3.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Main',
)

# --- Monta dist/ plana: copia extras e achata dist/Main/ -> dist/ ---
_bundle_dir = os.path.join(base_dir, 'dist', 'Main')
_dist_dir = os.path.join(base_dir, 'dist')

_external_files = [
    'config.json',
    'PDFtoPrinter.exe',
    'PDFtoPrinter_2.exe',
    'PDFtoPrinter_3.exe',
    'PDFtoPrinter_4.exe',
    'PDFtoPrinter_5.exe',
]
for _name in _external_files:
    _src = os.path.join(base_dir, _name)
    if not os.path.isfile(_src):
        raise SystemExit(f'Arquivo obrigatorio para dist/ nao encontrado: {_name}')
    shutil.copy2(_src, os.path.join(_bundle_dir, _name))

for _subdir in ('temp', 'logs'):
    os.makedirs(os.path.join(_bundle_dir, _subdir), exist_ok=True)

if not os.path.isfile(os.path.join(_bundle_dir, 'Main.exe')):
    raise SystemExit('Build PyInstaller nao gerou dist/Main/Main.exe')

# Achata dist/Main/* para dist/ (pasta pronta para deploy)
for _name in os.listdir(_bundle_dir):
    _src = os.path.join(_bundle_dir, _name)
    _dst = os.path.join(_dist_dir, _name)
    if os.path.isdir(_dst):
        shutil.rmtree(_dst)
    elif os.path.isfile(_dst):
        os.remove(_dst)
    shutil.move(_src, _dst)
try:
    os.rmdir(_bundle_dir)
except OSError:
    pass

_required_in_dist = [
    'Main.exe',
    'config.json',
    'fontes',
    'theme',
    'img',
    'azure.tcl',
    'vendor/ghostscript/bin/gswin64c.exe',
    'libdmtx-64.dll',
    'PDFtoPrinter.exe',
]
for _rel in _required_in_dist:
    if not os.path.exists(os.path.join(_dist_dir, _rel.replace('/', os.sep))):
        raise SystemExit(f'dist/ incompleto apos build: faltando {_rel}')

print('dist/ pronta para deploy nos PCs:')
print('  Main.exe, fontes/, theme/, img/, vendor/ghostscript/, azure.tcl')
print('  config.json, PDFtoPrinter*.exe, libdmtx-64.dll, temp/, logs/')
