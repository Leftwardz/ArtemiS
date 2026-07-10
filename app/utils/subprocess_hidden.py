"""Subprocess helpers that avoid flashing a console window on Windows."""

import subprocess
import sys

_CREATE_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
_SW_HIDE = 0


def _apply_hidden_flags(kwargs: dict) -> dict:
    if sys.platform == 'win32':
        if _CREATE_NO_WINDOW:
            flags = kwargs.pop('creationflags', 0)
            kwargs['creationflags'] = flags | _CREATE_NO_WINDOW
        startupinfo = kwargs.get('startupinfo')
        if startupinfo is None:
            startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = _SW_HIDE
        kwargs['startupinfo'] = startupinfo
    return kwargs


def run_hidden(*popenargs, **kwargs):
    return subprocess.run(*popenargs, **_apply_hidden_flags(kwargs))


def call_hidden(*popenargs, **kwargs):
    return subprocess.call(*popenargs, **_apply_hidden_flags(kwargs))
