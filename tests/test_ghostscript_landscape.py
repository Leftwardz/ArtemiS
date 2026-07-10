"""Testes do backend Ghostscript (comando mswinpr2 e roteamento paisagem)."""

from app.utils.printing.backends.ghostscript import (
    build_ghostscript_command,
    uses_devmode_gdi_for_job,
)
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


def test_landscape_job_routes_to_devmode_gdi():
    assert uses_devmode_gdi_for_job(_job(orientation=ORIENTATION_LANDSCAPE))
    assert not uses_devmode_gdi_for_job(_job(orientation=ORIENTATION_PORTRAIT))


def test_custom_label_job_routes_to_devmode_gdi():
    assert uses_devmode_gdi_for_job(_job(
        paper_size='0',
        paper_width_mm=95.0,
        paper_height_mm=30.0,
    ))
