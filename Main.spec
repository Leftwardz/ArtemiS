# -*- mode: python ; coding: utf-8 -*-


block_cipher = None

import os

base_dir = os.path.abspath('.')  # diretório atual, geralmente onde o .spec está
dll_path = os.path.join(base_dir, 'venv', 'Lib', 'site-packages', 'pylibdmtx', 'libdmtx-64.dll')


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[(dll_path, '.')],
    datas=[],
    hiddenimports=['reportlab.graphics.barcode.usps4s', 'reportlab.graphics.barcode.code128', 'reportlab.graphics.barcode.code93', 'reportlab.graphics.barcode.code39', 'reportlab.graphics.barcode.usps'],
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
    icon='img/favicon3.ico'
)
