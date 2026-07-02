"""Caminhos do Ghostscript empacotado (dev, PyInstaller e override em config.json)."""

import os
import sys

_GS_VENDOR = ('vendor', 'ghostscript')
_GS_EXE_NAME = 'gswin64c.exe'
_GS_DLL_NAME = 'gsdll64.dll'


def _candidate_roots():
    """Raízes onde vendor/ghostscript pode existir (ordem de preferência)."""
    if getattr(sys, 'frozen', False):
        # dist/ portável: recursos ficam ao lado de Main.exe (como config.json).
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        roots: list[str] = []
        for candidate in (
            exe_dir,
            os.path.join(exe_dir, '_internal'),
            getattr(sys, '_MEIPASS', None),
        ):
            if not candidate:
                continue
            candidate = os.path.abspath(candidate)
            if candidate not in roots:
                roots.append(candidate)
        return roots

    return [os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))]


def _ghostscript_at(root):
    gs_root = os.path.join(root, *_GS_VENDOR)
    exe = os.path.join(gs_root, 'bin', _GS_EXE_NAME)
    dll = os.path.join(gs_root, 'bin', _GS_DLL_NAME)
    lib = os.path.join(gs_root, 'lib')
    init_ps = os.path.join(lib, 'gs_init.ps')
    if (
        os.path.isfile(exe)
        and os.path.isfile(dll)
        and os.path.isdir(lib)
        and os.path.isfile(init_ps)
    ):
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


def ghostscript_bin_dir():
    bin_dir = os.path.join(bundled_ghostscript_root(), 'bin')
    return os.path.abspath(bin_dir) if os.path.isdir(bin_dir) else None


def ghostscript_is_available():
    for root in _candidate_roots():
        if _ghostscript_at(root):
            return True
    return False


def describe_ghostscript_paths() -> dict:
    """Resumo dos caminhos resolvidos (para logs/diagnóstico)."""
    roots = _candidate_roots()
    return {
        'frozen': bool(getattr(sys, 'frozen', False)),
        'executable': getattr(sys, 'executable', ''),
        'candidate_roots': roots,
        'resolved_root': bundled_ghostscript_root(),
        'exe': bundled_ghostscript_exe(),
        'exe_exists': os.path.isfile(bundled_ghostscript_exe()),
        'dll_exists': os.path.isfile(
            os.path.join(bundled_ghostscript_root(), 'bin', _GS_DLL_NAME),
        ),
        'lib': bundled_ghostscript_lib(),
        'lib_exists': os.path.isdir(bundled_ghostscript_lib()),
    }


def resolve_ghostscript_exe(config=None):
    """
    Ordem: config['ghostscript_path'] -> vendor empacotado -> gswin64c no PATH.

    No executável empacotado (PyInstaller) não usa PATH: só o vendor ao lado de
    Main.exe (evita falso positivo quando o Python de dev tem GS global).
    """
    if config and (config.get('ghostscript_path') or '').strip():
        return os.path.abspath(config['ghostscript_path'].strip())

    bundled = bundled_ghostscript_exe()
    if os.path.isfile(bundled):
        return os.path.abspath(bundled)

    if getattr(sys, 'frozen', False):
        return os.path.abspath(bundled)

    return _GS_EXE_NAME


def ghostscript_env(config=None):
    """Variáveis de ambiente para o subprocess encontrar lib/ e gsdll64.dll."""
    env = os.environ.copy()
    gs_root = bundled_ghostscript_root()
    lib = os.path.join(gs_root, 'lib')
    bin_dir = os.path.join(gs_root, 'bin')
    if os.path.isdir(lib):
        env['GS_LIB'] = os.path.abspath(lib)
    if os.path.isdir(bin_dir):
        bin_abs = os.path.abspath(bin_dir)
        path = env.get('PATH', '')
        if bin_abs.casefold() not in {p.casefold() for p in path.split(os.pathsep) if p}:
            env['PATH'] = bin_abs + os.pathsep + path
    override = (config or {}).get('ghostscript_lib')
    if override and os.path.isdir(override):
        env['GS_LIB'] = os.path.abspath(override)
    return env
