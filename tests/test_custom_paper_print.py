"""Custom label paper dimensions for print jobs."""

import json

from app.models.sheet_layout import SheetLayout
from app.services.layout_service import (
    batch_print_job_dimensions_mm,
    batch_print_job_paper_size,
    resolve_job_paper_dimensions_mm,
)
from app.utils.printing.backends.ghostscript import uses_devmode_gdi_for_job
from app.utils.printing.base import ORIENTATION_PORTRAIT, PrintJob


def _zebra_layout_json(width=95.0, height=30.0):
    layout = SheetLayout(
        page_width_mm=width,
        page_height_mm=height,
        label_width_mm=width,
        label_height_mm=height,
        columns=1,
        rows=1,
        margin_left_mm=0.0,
        margin_top_mm=0.0,
        page_preset='Personalizado',
    )
    return layout.to_json()


def test_resolve_job_paper_dimensions_custom_label():
    dims = resolve_job_paper_dimensions_mm('4', _zebra_layout_json())
    assert dims == (95.0, 30.0)


def test_resolve_job_paper_dimensions_a4_preset():
    layout = SheetLayout(page_preset='A4')
    dims = resolve_job_paper_dimensions_mm('4', layout.to_json())
    assert dims is None


def test_batch_print_job_dimensions_uniform():
    configs = [_zebra_layout_json(), _zebra_layout_json(95, 30)]
    assert batch_print_job_dimensions_mm(['4', '4'], configs) == (95.0, 30.0)


def test_batch_print_job_dimensions_mixed_returns_none():
    a4 = SheetLayout(page_preset='A4').to_json()
    zebra = _zebra_layout_json()
    assert batch_print_job_dimensions_mm(['4', '4'], [a4, zebra]) is None


def test_batch_print_job_paper_size_custom_is_zero():
    configs = [_zebra_layout_json()]
    assert batch_print_job_paper_size(['4'], configs) == '0'


def test_custom_label_routes_ghostscript_to_devmode_gdi():
    job = PrintJob(
        pdf_path=r'C:\temp\label.pdf',
        printer='Zebra',
        paper_size='0',
        paper_width_mm=95.0,
        paper_height_mm=30.0,
        orientation=ORIENTATION_PORTRAIT,
    )
    assert uses_devmode_gdi_for_job(job)


def test_portrait_a4_stays_on_mswinpr2():
    job = PrintJob(
        pdf_path=r'C:\temp\ar.pdf',
        printer='HP',
        paper_size='9',
        orientation=ORIENTATION_PORTRAIT,
    )
    assert not uses_devmode_gdi_for_job(job)
