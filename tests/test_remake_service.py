"""Remake job preparation."""

from app.i18n import PDF_MODE_SENTINEL
from app.services.remake_service import prepare_remake_job


class _FakeFile:
    def __init__(self, rows):
        self._rows = rows

    def search_by_rangelist(self, position_list):
        return [self._rows[i - 1] for i in position_list]


class _Product:
    orientation = '0'
    layout_config = None


class _FakeDb:
    def __init__(self, product=None, drawings=None):
        self._product = product
        self._drawings = drawings or []

    def search_product(self, client, product):
        return self._product

    def consult_drawings_from_product(self, client, product):
        return self._drawings


def test_prepare_remake_job_ok_pdf_mode():
    file_utils = _FakeFile([(0, ['line'])])
    db = _FakeDb(product=_Product(), drawings=[{'item_type': 'text'}])
    result = prepare_remake_job(
        db, 'Cliente', 'Produto', file_utils, r'C:\AR\work.csv', [1], PDF_MODE_SENTINEL,
    )
    assert result.ok is True
    assert result.lines == [[(0, ['line']), r'C:\AR\work.csv']]
    assert result.items == [[{'item_type': 'text'}]]
    assert result.orientations == ['0']


def test_prepare_remake_job_empty_selection():
    file_utils = _FakeFile([(0, ['line'])])
    db = _FakeDb(product=_Product())
    result = prepare_remake_job(
        db, 'Cliente', 'Produto', file_utils, r'C:\AR\work.csv', [], PDF_MODE_SENTINEL,
    )
    assert result.ok is False


def test_prepare_remake_job_missing_product():
    file_utils = _FakeFile([(0, ['line'])])
    db = _FakeDb(product=None)
    result = prepare_remake_job(
        db, 'Cliente', 'Produto', file_utils, r'C:\AR\work.csv', [1], PDF_MODE_SENTINEL,
    )
    assert result.ok is False
