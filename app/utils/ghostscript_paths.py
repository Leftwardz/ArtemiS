"""Caminhos do Ghostscript empacotado (dev, PyInstaller e override em config.json)."""

import os
import sys

_GS_VENDOR = ('vendor', 'ghostscript')
_GS_EXE_NAME = 'gswin64c.exe'


def _project_root():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def bundled_ghostscript_root():
    return os.path.join(_project_root(), *_GS_VENDOR)


def bundled_ghostscript_exe():
    return os.path.join(bundled_ghostscript_root(), 'bin', _GS_EXE_NAME)


def bundled_ghostscript_lib():
    return os.path.join(bundled_ghostscript_root(), 'lib')


def ghostscript_is_available():
    return os.path.isfile(bundled_ghostscript_exe()) and os.path.isdir(bundled_ghostscript_lib())


def resolve_ghostscript_exe(config=None):
    """
    Ordem: config['ghostscript_path'] -> vendor empacotado -> gswin64c no PATH.
    """
    if config and (config.get('ghostscript_path') or '').strip():
        return config['ghostscript_path'].strip()

    bundled = bundled_ghostscript_exe()
    if os.path.isfile(bundled):
        return bundled

    # fallback: instalacao global no PATH
    return _GS_EXE_NAME


def ghostscript_env(config=None):
    """Variáveis de ambiente para o subprocess encontrar lib/ (obrigatório)."""
    env = os.environ.copy()
    lib = bundled_ghostscript_lib()
    if os.path.isdir(lib):
        env['GS_LIB'] = lib
    override = (config or {}).get('ghostscript_lib')
    if override and os.path.isdir(override):
        env['GS_LIB'] = override
    return env
