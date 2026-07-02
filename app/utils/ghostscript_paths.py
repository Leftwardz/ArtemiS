"""Caminhos do Ghostscript empacotado (dev, PyInstaller e override em config.json)."""

import os
import sys

_GS_VENDOR = ('vendor', 'ghostscript')
_GS_EXE_NAME = 'gswin64c.exe'


def _candidate_roots():
    """Raízes onde vendor/ghostscript pode existir (ordem de preferência)."""
    if getattr(sys, 'frozen', False):
        # dist/ portável: recursos ficam ao lado de Main.exe (como config.json, azure.tcl).
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        roots = [exe_dir]
        meipass = getattr(sys, '_MEIPASS', None)
        if meipass:
            meipass = os.path.abspath(meipass)
            if meipass not in roots:
                roots.append(meipass)
        return roots

    return [os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))]


def _ghostscript_at(root):
    gs_root = os.path.join(root, *_GS_VENDOR)
    exe = os.path.join(gs_root, 'bin', _GS_EXE_NAME)
    lib = os.path.join(gs_root, 'lib')
    if os.path.isfile(exe) and os.path.isdir(lib):
        return gs_root
    return None


def bundled_ghostscript_root():
    for root in _candidate_roots():
        found = _ghostscript_at(root)
        if found:
            return found
    return os.path.join(_candidate_roots()[0], *_GS_VENDOR)


def bundled_ghostscript_exe():
    return os.path.join(bundled_ghostscript_root(), 'bin', _GS_EXE_NAME)


def bundled_ghostscript_lib():
    return os.path.join(bundled_ghostscript_root(), 'lib')


def ghostscript_is_available():
    for root in _candidate_roots():
        if _ghostscript_at(root):
            return True
    return False


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
