"""Testes de duplex por item (partição, validação de lote, páginas PDF)."""

import io

from reportlab.pdfgen import canvas

from app.services.pdf_service import (
    configure_full_A4_ar,
    partition_drawings_by_duplex,
    product_requires_duplex,
)
from app.services.production_service import validate_duplex_batch


def test_partition_drawings_by_duplex():
    items = [
        {'item_type': 'text', 'duplex': '0', 'text': 'front'},
        {'item_type': 'text', 'duplex': '1', 'text': 'back'},
        {'item_type': 'text', 'text': 'default_front'},
    ]
    front, back = partition_drawings_by_duplex(items)
    assert len(front) == 2
    assert len(back) == 1
    assert back[0]['text'] == 'back'


def test_product_requires_duplex_false_by_default():
    items = [{'item_type': 'text', 'text': 'a'}]
    assert not product_requires_duplex(items)


def test_validate_duplex_batch_mixed():
    items_list = [
        [{'item_type': 'text', 'duplex': '1'}],
        [{'item_type': 'text', 'duplex': '0'}],
    ]
    assert validate_duplex_batch(items_list, 'ghostscript') == 'duplex.mixed_batch'


def test_validate_duplex_batch_pdftoprinter():
    items_list = [[{'item_type': 'text', 'duplex': '1'}]]
    assert validate_duplex_batch(items_list, 'pdftoprinter') == 'duplex.pdftoprinter_unsupported'


def test_validate_duplex_batch_ok():
    items_list = [
        [{'item_type': 'text', 'duplex': '1'}],
        [{'item_type': 'text', 'duplex': '1'}],
    ]
    assert validate_duplex_batch(items_list, 'ghostscript') is None


def test_configure_full_A4_ar_duplex_doubles_pages():
    base = {
        'item_type': 'text', 'x1': '100', 'y1': '100', 'x2': None, 'y2': None,
        'font_name': 'arial', 'font_size': '10', 'font_style': 'normal', 'orientation': '0',
        'file_columns': None, 'segment_id': None, 'tag': '', 'proportion': None,
        'thickness': None, 'dashed': None, 'barcode_height': None, 'barcode_width': None,
        'line_distance': None, 'char_limit': None, 'image': None,
    }
    items = [[
        {**base, 'duplex': '0', 'text': 'f'},
        {**base, 'duplex': '1', 'text': 'b'},
    ]]
    filelines = [['0', ['col'], '/tmp/x.csv']]
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    configure_full_A4_ar(pdf, filelines, items, 0, 1, None, 'test')
    pdf.save()
    buffer.seek(0)
    from PyPDF2 import PdfReader
    reader = PdfReader(buffer)
    assert len(reader.pages) == 2
