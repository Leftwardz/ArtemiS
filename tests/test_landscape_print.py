"""Testes de orientação de impressão (paisagem no layout customizado)."""

import json

from app.models.sheet_layout import SheetLayout
from app.services.layout_service import (
    apply_page_preset,
    batch_print_orientation,
    infer_page_preset,
    is_landscape_layout,
    resolve_print_orientation,
    resolve_product_paper_size,
)
from app.services.production_service import validate_landscape_batch
from app.utils.printing.base import ORIENTATION_LANDSCAPE, ORIENTATION_PORTRAIT


def _layout_json(width_mm, height_mm):
    layout = SheetLayout(page_width_mm=width_mm, page_height_mm=height_mm)
    return layout.to_json()


def test_is_landscape_layout_inverted_a4():
    layout = SheetLayout(page_width_mm=297.0, page_height_mm=210.0, page_preset='A4')
    assert is_landscape_layout(layout)


def test_is_landscape_layout_portrait_a4():
    layout = SheetLayout(page_width_mm=210.0, page_height_mm=297.0, page_preset='A4')
    assert not is_landscape_layout(layout)


def test_resolve_print_orientation_custom_landscape():
    assert resolve_print_orientation('4', _layout_json(297, 210)) == ORIENTATION_LANDSCAPE


def test_resolve_print_orientation_custom_portrait():
    assert resolve_print_orientation('4', _layout_json(210, 297)) == ORIENTATION_PORTRAIT


def test_resolve_print_orientation_zebra_label_portrait():
    """Etiquetas largas (ex. 93×35 mm) não devem forçar paisagem na impressora."""
    layout = SheetLayout(
        page_width_mm=93.0,
        page_height_mm=35.0,
        label_width_mm=93.0,
        label_height_mm=35.0,
        columns=1,
        rows=1,
        margin_left_mm=0.0,
        margin_top_mm=0.0,
        page_preset='Personalizado',
    )
    assert resolve_print_orientation('4', layout.to_json()) == ORIENTATION_PORTRAIT


def test_resolve_print_orientation_standard_modes_are_portrait():
    for orientation in ('0', '1', '2', '3'):
        assert resolve_print_orientation(orientation, None) == ORIENTATION_PORTRAIT


def test_batch_print_orientation_uniform_landscape():
    configs = [_layout_json(297, 210), _layout_json(297, 210)]
    assert batch_print_orientation(['4', '4'], configs) == ORIENTATION_LANDSCAPE


def test_batch_print_orientation_mixed_returns_none():
    configs = [_layout_json(297, 210), _layout_json(210, 297)]
    assert batch_print_orientation(['4', '4'], configs) is None


def test_validate_landscape_batch_mixed():
    configs = [_layout_json(297, 210), _layout_json(210, 297)]
    assert validate_landscape_batch(['4', '4'], configs) == 'landscape.mixed_batch'


def test_validate_landscape_batch_ok():
    configs = [_layout_json(297, 210)]
    assert validate_landscape_batch(['4'], configs) is None


def test_validate_landscape_batch_pdftoprinter():
    configs = [_layout_json(297, 210)]
    assert validate_landscape_batch(['4'], configs, 'pdftoprinter') == 'landscape.pdftoprinter_unsupported'
    assert validate_landscape_batch(['4'], configs, 'ghostscript') is None


def test_apply_page_preset_a4_landscape():
    layout = apply_page_preset(SheetLayout(), 'A4_landscape')
    assert layout.page_width_mm == 297.0
    assert layout.page_height_mm == 210.0
    assert layout.page_preset == 'A4_landscape'
    assert is_landscape_layout(layout)


def test_infer_page_preset_from_manual_landscape_a4():
    layout = SheetLayout(page_width_mm=297.0, page_height_mm=210.0, page_preset='A4')
    assert infer_page_preset(layout) == 'A4_landscape'


def test_infer_page_preset_portrait_a4():
    layout = SheetLayout(page_width_mm=210.0, page_height_mm=297.0, page_preset='A4')
    assert infer_page_preset(layout) == 'A4'


def test_resolve_product_paper_size_landscape_preset():
    layout = SheetLayout(page_width_mm=297.0, page_height_mm=210.0, page_preset='A4_landscape')
    assert resolve_product_paper_size(4, layout.to_json()) == '9'
