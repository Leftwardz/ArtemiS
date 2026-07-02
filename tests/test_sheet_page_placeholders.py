"""Testes de placeholders de página no cabeçalho."""

from app.services.sheet_page_placeholders import (
    apply_sheet_page_placeholders,
    has_sheet_page_placeholders,
)


def test_has_sheet_page_placeholders():
    assert has_sheet_page_placeholders('Pág. {p}/{t}')
    assert has_sheet_page_placeholders('{pag} de {total}')
    assert not has_sheet_page_placeholders('Texto fixo')


def test_placeholders_replaced():
    assert apply_sheet_page_placeholders('Pág. {pag}/{total}', 2, 5) == 'Pág. 2/5'
    assert apply_sheet_page_placeholders('{p} de {t}', 1, 3) == '1 de 3'


def test_placeholders_without_context_unchanged():
    assert apply_sheet_page_placeholders('Sem flag', None, None) == 'Sem flag'
