"""Testes de resolução de pastas de tradução (dev e dist PyInstaller)."""

import sys
import tempfile
from pathlib import Path
from unittest import mock

from app.i18n.loader import _candidate_builtin_locale_dirs


def test_dev_mode_uses_package_locales():
    with mock.patch.object(sys, 'frozen', False, create=True):
        dirs = _candidate_builtin_locale_dirs()
    assert len(dirs) == 1
    assert dirs[0].name == 'locales'
    assert (dirs[0] / 'pt.json').is_file()


def test_frozen_prefers_exe_dir_locales():
    with tempfile.TemporaryDirectory() as tmp:
        exe_dir = Path(tmp) / 'dist'
        internal = exe_dir / '_internal'
        builtin = exe_dir / 'app' / 'i18n' / 'locales'
        user_locales = exe_dir / 'locales'
        builtin.mkdir(parents=True)
        user_locales.mkdir(parents=True)
        (builtin / 'pt.json').write_text('{}', encoding='utf-8')

        with mock.patch.object(sys, 'frozen', True, create=True), \
                mock.patch.object(sys, 'executable', str(exe_dir / 'Main.exe')), \
                mock.patch.object(sys, '_MEIPASS', str(internal), create=True):
            dirs = _candidate_builtin_locale_dirs()

        assert dirs[0] == builtin
        assert user_locales in dirs
        assert internal / 'app' / 'i18n' / 'locales' in dirs
