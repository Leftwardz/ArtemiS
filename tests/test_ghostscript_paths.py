"""Testes de resolucao de caminhos do Ghostscript empacotado."""

import os
import sys
from unittest import mock

from app.utils import ghostscript_paths as gs


def test_dev_mode_finds_vendor_ghostscript():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    exe = os.path.join(root, 'vendor', 'ghostscript', 'bin', 'gswin64c.exe')
    if not os.path.isfile(exe):
        return  # repo sem binarios Windows (ex.: checkout parcial)

    with mock.patch.object(sys, 'frozen', False, create=True):
        assert gs.ghostscript_is_available()
        assert gs.bundled_ghostscript_exe() == exe


def test_frozen_prefers_exe_dir_over_meipass(tmp_path):
    exe_dir = tmp_path / 'dist'
    internal = exe_dir / '_internal'
    exe_dir.mkdir()
    internal.mkdir()

    def _plant_gs(root):
        gs_root = root / 'vendor' / 'ghostscript'
        (gs_root / 'bin').mkdir(parents=True)
        (gs_root / 'lib').mkdir()
        (gs_root / 'bin' / 'gswin64c.exe').write_bytes(b'gs')

    _plant_gs(exe_dir)
    # _internal sem GS — simula PyInstaller 6+ onde lib pode existir so na raiz dist/
    fake_exe = exe_dir / 'Main.exe'
    fake_exe.write_bytes(b'')

    with mock.patch.object(sys, 'frozen', True, create=True), \
            mock.patch.object(sys, 'executable', str(fake_exe), create=True), \
            mock.patch.object(sys, '_MEIPASS', str(internal), create=True):
        assert gs.ghostscript_is_available()
        assert gs.bundled_ghostscript_root() == str(exe_dir / 'vendor' / 'ghostscript')


def test_frozen_falls_back_to_meipass(tmp_path):
    exe_dir = tmp_path / 'dist'
    internal = exe_dir / '_internal'
    exe_dir.mkdir()
    internal.mkdir()

    gs_root = internal / 'vendor' / 'ghostscript'
    (gs_root / 'bin').mkdir(parents=True)
    (gs_root / 'lib').mkdir()
    (gs_root / 'bin' / 'gswin64c.exe').write_bytes(b'gs')

    fake_exe = exe_dir / 'Main.exe'
    fake_exe.write_bytes(b'')

    with mock.patch.object(sys, 'frozen', True, create=True), \
            mock.patch.object(sys, 'executable', str(fake_exe), create=True), \
            mock.patch.object(sys, '_MEIPASS', str(internal), create=True):
        assert gs.ghostscript_is_available()
        assert gs.bundled_ghostscript_root() == str(gs_root)
