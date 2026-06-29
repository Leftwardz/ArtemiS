"""Testes do módulo de tradução."""

from app.i18n import available_languages, init_i18n, set_language, t


def test_default_portuguese():
    init_i18n({'language': 'pt', 'locales_folder': ''})
    assert t('main.select_printer') == 'Selecione a impressora:'


def test_english():
    init_i18n({'language': 'en', 'locales_folder': ''})
    assert t('main.select_printer') == 'Select printer:'


def test_french():
    init_i18n({'language': 'fr', 'locales_folder': ''})
    assert 'imprimante' in t('main.select_printer').lower()


def test_available_languages():
    init_i18n({'language': 'pt', 'locales_folder': ''})
    codes = {code for code, _ in available_languages()}
    assert {'pt', 'en', 'fr'}.issubset(codes)


def test_missing_key_returns_key():
    init_i18n({'language': 'pt', 'locales_folder': ''})
    assert t('nonexistent.key') == 'nonexistent.key'
