"""Módulo de tradução (i18n) — arquivos JSON em app/i18n/locales/ e pasta locales/ do app."""

from app.i18n.loader import (
    PDF_MODE_SENTINEL,
    available_languages,
    get_i18n,
    get_language,
    init_i18n,
    is_pdf_mode_label,
    paper_color_label,
    pdf_mode_label,
    reload_locales,
    resolve_printer_selection,
    set_language,
    t,
)

__all__ = [
    'PDF_MODE_SENTINEL',
    'available_languages',
    'get_i18n',
    'get_language',
    'init_i18n',
    'is_pdf_mode_label',
    'paper_color_label',
    'pdf_mode_label',
    'reload_locales',
    'resolve_printer_selection',
    'set_language',
    't',
]
