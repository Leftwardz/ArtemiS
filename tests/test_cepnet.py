"""CEPNet (Correios) encoding and batch validation."""

import pytest

from app.i18n import init_i18n
from app.utils.cepnet import (
    CepNetValidationError,
    cepnet_check_digit,
    cepnet_payload_digits,
    create_cepnet_bytes,
    normalize_cep_digits,
    validate_cepnet_batch,
)


init_i18n({'language': 'pt', 'locales_folder': ''})


def test_check_digit():
    assert cepnet_check_digit('12345678') == '4'
    assert cepnet_check_digit('01310100') == '8'


def test_normalize_accepts_hyphenated_cep():
    assert normalize_cep_digits('01310-100') == '01310100'


def test_normalize_rejects_letters():
    with pytest.raises(CepNetValidationError):
        normalize_cep_digits('01310A100')


def test_normalize_rejects_wrong_length():
    with pytest.raises(CepNetValidationError):
        normalize_cep_digits('1234567')


def test_payload_nine_digits():
    assert cepnet_payload_digits('01310100') == '013101004'


def test_create_cepnet_bytes_png():
    buf = create_cepnet_bytes('01310100')
    assert buf.read(8) == b'\x89PNG\r\n\x1a\n'


def test_validate_cepnet_batch_rejects_invalid_line():
    items = [[{
        'item_type': 'barcodeCepnet',
        'file_columns': 'Coluna_3',
    }]]
    files_lines = [[
        (0, ['a', 'b', 'INVALID', 'd']),
        '/tmp/work.csv',
    ]]
    with pytest.raises(CepNetValidationError) as exc:
        validate_cepnet_batch(items, files_lines)
    assert 'INVALID' in exc.value.user_message or 'INVALID' in str(exc.value)


def test_validate_cepnet_batch_accepts_valid_rows():
    items = [[{
        'item_type': 'barcodeCepnet',
        'file_columns': 'Coluna_2',
    }]]
    files_lines = [[
        (0, ['x', '01310100']),
        (1, ['y', '01310-100']),
        '/tmp/work.csv',
    ]]
    validate_cepnet_batch(items, files_lines)


def test_validate_cepnet_batch_rejects_entire_batch_on_first_error():
    items = [[{
        'item_type': 'barcodeCepnet',
        'file_columns': 'Coluna_1',
    }]]
    files_lines = [[
        (0, ['01310100']),
        (1, ['ABCDEFGH']),
        '/tmp/work.csv',
    ]]
    with pytest.raises(CepNetValidationError):
        validate_cepnet_batch(items, files_lines)
