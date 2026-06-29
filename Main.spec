# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

import os

base_dir = os.path.abspath('.')

def _find_dll():
    for venv_name in ('.venv', 'venv'):
        candidate = os.path.join(base_dir, venv_name, 'Lib', 'site-packages',
                                 'pylibdmtx', 'libdmtx-64.dll')
        if os.path.isfile(candidate):
            return candidate
    raise FileNotFoundError('libdmtx-64.dll nao encontrado em .venv/venv')

dll_path = _find_dll()

# Ghostscript empacotado (rodar scripts/fetch_ghostscript.ps1 antes do build)
gs_bin = os.path.join(base_dir, 'vendor', 'ghostscript', 'bin')
gs_lib = os.path.join(base_dir, 'vendor', 'ghostscript', 'lib')
gs_datas = []
if os.path.isdir(gs_bin):
    gs_datas.append((gs_bin, os.path.join('vendor', 'ghostscript', 'bin')))
if os.path.isdir(gs_lib):
    gs_datas.append((gs_lib, os.path.join('vendor', 'ghostscript', 'lib')))

resource_datas = []
for _res in ('img', 'fontes', 'theme'):
    _res_path = os.path.join(base_dir, _res)
    if os.path.isdir(_res_path):
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='img/favicon3.ico',
)
