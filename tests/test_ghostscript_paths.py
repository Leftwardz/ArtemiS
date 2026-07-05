"""Testes de resolucao de caminhos do Ghostscript empacotado."""

import os
import sys
from unittest import mock

from app.utils import ghostscript_paths as gs


def _reset_smoke_cache():
    gs._smoke_test_cache = None


def _plant_gs(root):
    gs_root = os.path.join(root, 'vendor', 'ghostscript')
    bin_dir = os.path.join(gs_root, 'bin')
    lib_dir = os.path.join(gs_root, 'lib')
    os.makedirs(bin_dir, exist_ok=True)
    os.makedirs(lib_dir, exist_ok=True)
    open(os.path.join(bin_dir, 'gswin64c.exe'), 'wb').close()
    open(os.path.join(bin_dir, 'gsdll64.dll'), 'wb').close()
    open(os.path.join(lib_dir, 'Fontmap.ATB'), 'w', encoding='utf-8').write('%!')


def test_dev_mode_finds_vendor_ghostscript():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    exe = os.path.join(root, 'vendor', 'ghostscript', 'bin', 'gswin64c.exe')
    if not os.path.isfile(exe):
        return  # repo sem binarios Windows (ex.: checkout parcial)

    _reset_smoke_cache()
    with mock.patch.object(sys, 'frozen', False, create=True):
        assert gs.ghostscript_files_present()
        assert gs.ghostscript_is_available()
        assert gs.bundled_ghostscript_exe() == exe


def test_frozen_prefers_exe_dir_over_meipass(tmp_path):
    _reset_smoke_cache()
    exe_dir = tmp_path / 'dist'
    internal = exe_dir / '_internal'
    exe_dir.mkdir()
    internal.mkdir()

    _plant_gs(str(exe_dir))
    fake_exe = exe_dir / 'Main.exe'
    fake_exe.write_bytes(b'')

    with mock.patch.object(sys, 'frozen', True, create=True), \
            mock.patch.object(sys, 'executable', str(fake_exe), create=True), \
            mock.patch.object(sys, '_MEIPASS', str(internal), create=True), \
            mock.patch.object(gs, 'ghostscript_smoke_test', return_value=True):
        assert gs.ghostscript_is_available()
        assert gs.bundled_ghostscript_root() == str(exe_dir / 'vendor' / 'ghostscript')
        assert gs.resolve_ghostscript_exe() == str(exe_dir / 'vendor' / 'ghostscript' / 'bin' / 'gswin64c.exe')


def test_frozen_falls_back_to_meipass(tmp_path):
    _reset_smoke_cache()
    exe_dir = tmp_path / 'dist'
    internal = exe_dir / '_internal'
    exe_dir.mkdir()
    internal.mkdir()

    _plant_gs(str(internal))
    fake_exe = exe_dir / 'Main.exe'
    fake_exe.write_bytes(b'')

    with mock.patch.object(sys, 'frozen', True, create=True), \
            mock.patch.object(sys, 'executable', str(fake_exe), create=True), \
            mock.patch.object(sys, '_MEIPASS', str(internal), create=True), \
            mock.patch.object(gs, 'ghostscript_smoke_test', return_value=True):
        assert gs.ghostscript_is_available()
        assert gs.bundled_ghostscript_root() == str(internal / 'vendor' / 'ghostscript')


def test_frozen_does_not_use_path_fallback(tmp_path):
    exe_dir = tmp_path / 'dist'
    exe_dir.mkdir()
    fake_exe = exe_dir / 'Main.exe'
    fake_exe.write_bytes(b'')

    with mock.patch.object(sys, 'frozen', True, create=True), \
            mock.patch.object(sys, 'executable', str(fake_exe), create=True), \
            mock.patch.object(sys, '_MEIPASS', str(exe_dir / '_internal'), create=True):
        resolved = gs.resolve_ghostscript_exe()
        assert resolved.endswith('gswin64c.exe')
        assert os.path.isabs(resolved)
        assert resolved != 'gswin64c.exe'


def test_frozen_smoke_test_required(tmp_path):
    _reset_smoke_cache()
    exe_dir = tmp_path / 'dist'
    exe_dir.mkdir()
    _plant_gs(str(exe_dir))
    fake_exe = exe_dir / 'Main.exe'
    fake_exe.write_bytes(b'')

    with mock.patch.object(sys, 'frozen', True, create=True), \
            mock.patch.object(sys, 'executable', str(fake_exe), create=True), \
            mock.patch.object(sys, '_MEIPASS', str(exe_dir / '_internal'), create=True), \
            mock.patch.object(gs, 'ghostscript_smoke_test', return_value=False):
        assert gs.ghostscript_files_present()
        assert not gs.ghostscript_is_available()


def test_ghostscript_env_prepends_bin_to_path(tmp_path):
    _reset_smoke_cache()
    exe_dir = tmp_path / 'dist'
    exe_dir.mkdir()
    _plant_gs(str(exe_dir))
    fake_exe = exe_dir / 'Main.exe'
    fake_exe.write_bytes(b'')

    with mock.patch.object(sys, 'frozen', True, create=True), \
            mock.patch.object(sys, 'executable', str(fake_exe), create=True), \
            mock.patch.object(sys, '_MEIPASS', str(exe_dir / '_internal'), create=True):
        env = gs.ghostscript_env()
        bin_dir = str(exe_dir / 'vendor' / 'ghostscript' / 'bin')
        assert env['GS_LIB'] == str(exe_dir / 'vendor' / 'ghostscript' / 'lib')
        assert env['PATH'].startswith(bin_dir)
