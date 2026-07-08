"""Font catalog and ReportLab name resolution."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app.i18n import init_i18n
from app.services import font_service


init_i18n({'language': 'pt', 'locales_folder': ''})


@pytest.fixture
def font_env(tmp_path, monkeypatch):
    builtin_dir = tmp_path / 'fontes'
    builtin_dir.mkdir()
    custom_dir = tmp_path / 'custom_fonts'
    custom_dir.mkdir()

    regular = builtin_dir / 'sample.ttf'
    bold = builtin_dir / 'sample_bold.ttf'
    regular.write_bytes(b'mock-regular')
    bold.write_bytes(b'mock-bold')

    catalog = {
        'families': [{
            'id': 'sample',
            'display_name': 'Sample Font',
            'regular': 'sample.ttf',
            'bold': 'sample_bold.ttf',
            'aliases': ['sample font', 'arial'],
        }],
    }
    with open(builtin_dir / 'fonts.json', 'w', encoding='utf-8') as handle:
        json.dump(catalog, handle)

    config = {
        'database_location': str(tmp_path / 'database.db'),
        'fonts_folder': str(custom_dir),
    }

    monkeypatch.setattr(font_service, 'app_dir', lambda: tmp_path)
    font_service.init_fonts(config)
    yield {
        'tmp_path': tmp_path,
        'builtin_dir': builtin_dir,
        'custom_dir': custom_dir,
        'config': config,
    }
    font_service._catalog_cache = None
    font_service._lookup.clear()
    font_service._registered_names.clear()


def test_load_catalog_builtin(font_env):
    families = font_service.load_catalog(force=True)
    assert len(families) == 1
    assert families[0].display_name == 'Sample Font'
    assert families[0].regular_path.is_file()


def test_resolve_reportlab_font_aliases(font_env):
    assert font_service.resolve_reportlab_font('arial', 'normal') == 'Sample Font'
    assert font_service.resolve_reportlab_font('Arial', 'bold') == 'Sample Font-Bold'


def test_list_font_families(font_env):
    assert font_service.list_font_families() == ['Sample Font']


def test_import_custom_font(font_env, monkeypatch):
    registered = []

    def fake_register(name, path):
        registered.append((name, path))

    monkeypatch.setattr(font_service.pdfmetrics, 'registerFont', fake_register)
    monkeypatch.setattr(
        font_service,
        '_copy_ttf',
        lambda source, dest_dir, prefix: dest_dir / f'{prefix}_{Path(source).name}',
    )

    source = font_env['tmp_path'] / 'new.ttf'
    source.write_bytes(b'new-font')
    result = font_service.import_font(str(source), 'Brand New')
    assert result.ok
    assert (font_env['custom_dir'] / 'fonts.custom.json').is_file()
    assert font_service.lookup_font('Brand New') is not None


def test_custom_fonts_dir_unc_default(tmp_path, monkeypatch):
    monkeypatch.setattr(font_service, 'app_dir', lambda: tmp_path)
    font_service.init_fonts({
        'database_location': r'\\server\share\database.db',
        'fonts_folder': '',
    })
    assert font_service.custom_fonts_dir() == Path(r'\\server\share\fontes')


def test_register_all_fonts_idempotent(font_env, monkeypatch):
    calls = []

    def fake_register(font):
        calls.append(font.fontName)

    monkeypatch.setattr(font_service.pdfmetrics, 'registerFont', fake_register)
    font_service._registered_names.clear()
    font_service.register_all_fonts()
    first_count = len(calls)
    font_service.register_all_fonts()
    assert len(calls) == first_count
