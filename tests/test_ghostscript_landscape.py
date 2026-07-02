"""Testes do comando Ghostscript para impressão em paisagem."""

from app.utils.printing.backends.ghostscript import build_ghostscript_command
from app.utils.printing.base import ORIENTATION_LANDSCAPE, ORIENTATION_PORTRAIT, PrintJob


def _job(**kwargs):
    defaults = {
        'pdf_path': r'C:\temp\ar.pdf',
        'printer': 'HP LaserJet',
        'paper_size': '9',
        'orientation': ORIENTATION_PORTRAIT,
    }
    defaults.update(kwargs)
    return PrintJob(**defaults)


def test_portrait_a4_uses_named_papersize():
    cmd = build_ghostscript_command('gswin64c.exe', _job())
    assert '-sPAPERSIZE=a4' in cmd
    assert '-c' not in cmd
    assert cmd[-1] == r'C:\temp\ar.pdf'


def test_landscape_a4_uses_explicit_dimensions():
    cmd = build_ghostscript_command('gswin64c.exe', _job(orientation=ORIENTATION_LANDSCAPE))
    assert '-sPAPERSIZE=842x595' in cmd
    assert '-c' not in cmd
    assert cmd[-1] == r'C:\temp\ar.pdf'


def test_landscape_unknown_paper_uses_setpagedevice_with_f():
    cmd = build_ghostscript_command(
        'gswin64c.exe',
        _job(orientation=ORIENTATION_LANDSCAPE, paper_size='17'),
    )
    assert '-c' in cmd
    assert '<</Orientation 1>> setpagedevice' in cmd
    f_index = cmd.index('-f')
    assert cmd[f_index + 1] == r'C:\temp\ar.pdf'


def test_landscape_any_paper_uses_setpagedevice_with_f():
    cmd = build_ghostscript_command(
        'gswin64c.exe',
        _job(orientation=ORIENTATION_LANDSCAPE, paper_size='0'),
    )
    assert '<</Orientation 1>> setpagedevice' in cmd
    assert cmd.index('-f') == len(cmd) - 2
