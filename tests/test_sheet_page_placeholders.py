"""Testes de placeholders de página no cabeçalho."""

from app.services.pdf_service import _apply_sheet_page_placeholders


def test_placeholders_replaced():
    assert _apply_sheet_page_placeholders('Pág. {pag}/{total}', 2, 5) == 'Pág. 2/5'
    assert _apply_sheet_page_placeholders('{p} de {t}', 1, 3) == '1 de 3'


def test_placeholders_without_context_unchanged():
    assert _apply_sheet_page_placeholders('Sem flag', None, None) == 'Sem flag'
