"""Caminhos do Ghostscript empacotado (dev, PyInstaller e override em config.json)."""

import os
import subprocess
import sys
from typing import Optional

_GS_VENDOR = ('vendor', 'ghostscript')
_GS_EXE_NAME = 'gswin64c.exe'
_GS_DLL_NAME = 'gsdll64.dll'
_GS_LIB_MARKER = 'Fontmap.ATB'
_smoke_test_cache: Optional[bool] = None


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
    lib_marker = os.path.join(lib, _GS_LIB_MARKER)
    if (
        os.path.isfile(exe)
        and os.path.isfile(dll)
        and os.path.isdir(lib)
        and os.path.isfile(lib_marker)
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


def ghostscript_files_present():
    for root in _candidate_roots():
        if _ghostscript_at(root):
            return True
    return False


def ghostscript_smoke_test(*, config=None) -> bool:
    """Executa gswin64c --version (cache em memoria). Usado no exe empacotado."""
    global _smoke_test_cache
    if _smoke_test_cache is not None:
        return _smoke_test_cache

    if not ghostscript_files_present():
        _smoke_test_cache = False
        return False

    gs_exe = resolve_ghostscript_exe(config)
    if not os.path.isfile(gs_exe):
        _smoke_test_cache = False
        return False

    bin_dir = ghostscript_bin_dir() or os.path.dirname(gs_exe)
    try:
        result = subprocess.run(
            [gs_exe, '--version'],
            env=ghostscript_env(config),
            capture_output=True,
            text=True,
            cwd=bin_dir,
            timeout=15,
        )
        _smoke_test_cache = result.returncode == 0
    except Exception:
        _smoke_test_cache = False
    return _smoke_test_cache


def ghostscript_is_available():
    if not ghostscript_files_present():
        return False
    if getattr(sys, 'frozen', False):
        return ghostscript_smoke_test()
    return True


def describe_ghostscript_paths() -> dict:
    """Resumo dos caminhos resolvidos (para logs/diagnóstico)."""
    roots = _candidate_roots()
    files_ok = ghostscript_files_present()
    smoke_ok = ghostscript_smoke_test() if files_ok and getattr(sys, 'frozen', False) else None
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
        'files_present': files_ok,
        'smoke_test_passed': smoke_ok,
    }


def log_ghostscript_startup():
    """Registra diagnostico de GS no log de impressao (exe empacotado)."""
    if not getattr(sys, 'frozen', False):
        return
    try:
        from app.utils.printing.logger import get_print_logger
        info = describe_ghostscript_paths()
        get_print_logger().info('Ghostscript startup: %s', info)
    except Exception:
        pass


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
