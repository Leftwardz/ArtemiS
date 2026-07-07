"""CEPNet (Correios) — codificação POSTNET brasileira para CEP de 8 dígitos + verificador."""

from __future__ import annotations

import io
import re
from typing import Optional

from PIL import Image, ImageDraw

from app.i18n import t

# Posições 7-4-2-1-0: 1 = barra longa, 0 = barra curta (guia Correios, tabela 3).
CEPNET_DIGIT_PATTERNS = {
    '0': '11000',
    '1': '00011',
    '2': '00101',
    '3': '00110',
    '4': '01001',
    '5': '01010',
    '6': '01100',
    '7': '10001',
    '8': '10010',
    '9': '10100',
}

# Dimensões nominais (mm) — guia técnico CEPNet / POSTNET.
_BAR_W_MM = 0.5
_SPACE_W_MM = 0.55
_TALL_H_MM = 3.175
_SHORT_H_MM = 1.27
_RENDER_DPI = 300


class CepNetValidationError(Exception):
    """CEP inválido para geração CEPNet."""

    def __init__(self, reason_key: str, *, user_message: str = '', **params):
        self.reason_key = reason_key
        self.params = params
        self.user_message = user_message or t(reason_key, **params)
        super().__init__(self.user_message)


def cepnet_check_digit(eight_digits: str) -> str:
    total = sum(int(d) for d in eight_digits)
    return str((10 - (total % 10)) % 10)


def normalize_cep_digits(raw: str) -> str:
    """Normaliza CEP para 8 dígitos ou levanta CepNetValidationError."""
    if raw is None or not str(raw).strip():
        raise CepNetValidationError('cepnet.reason_empty')

    text = str(raw).strip()
    if re.search(r'[A-Za-z]', text):
        raise CepNetValidationError('cepnet.reason_letters')

    cleaned = re.sub(r'\D', '', text)
    if not cleaned:
        raise CepNetValidationError('cepnet.reason_empty')
    if len(cleaned) != 8:
        raise CepNetValidationError('cepnet.reason_length', count=len(cleaned))
    return cleaned


def cepnet_payload_digits(raw: str) -> str:
    """8 dígitos + dígito verificador (9 dígitos codificados)."""
    cep = normalize_cep_digits(raw)
    return cep + cepnet_check_digit(cep)


def _bar_sequence(payload_nine_digits: str) -> list[str]:
    """47 barras: frame + 9×5 + frame ('T' alta, 'S' curta)."""
    bars: list[str] = ['T']
    for digit in payload_nine_digits:
        for bit in CEPNET_DIGIT_PATTERNS[digit]:
            bars.append('T' if bit == '1' else 'S')
    bars.append('T')
    return bars


def render_cepnet_image(raw_cep: str, *, dpi: int = _RENDER_DPI) -> Image.Image:
    payload = cepnet_payload_digits(raw_cep)
    bars = _bar_sequence(payload)

    px_per_mm = dpi / 25.4
    bar_w = max(1, int(round(_BAR_W_MM * px_per_mm)))
    space_w = max(1, int(round(_SPACE_W_MM * px_per_mm)))
    tall_h = max(1, int(round(_TALL_H_MM * px_per_mm)))
    short_h = max(1, int(round(_SHORT_H_MM * px_per_mm)))
    quiet_h = max(2, int(round(1.016 * px_per_mm)))
    quiet_w = bar_w * 10

    inner_w = len(bars) * bar_w + max(0, len(bars) - 1) * space_w
    width = inner_w + 2 * quiet_w
    height = tall_h + 2 * quiet_h

    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)
    x = quiet_w
    baseline = quiet_h + tall_h

    for bar in bars:
        h = tall_h if bar == 'T' else short_h
        y0 = baseline - h
        draw.rectangle([x, y0, x + bar_w - 1, baseline - 1], fill='black')
        x += bar_w + space_w

    return img


def create_cepnet_bytes(raw_cep: str) -> io.BytesIO:
    """PNG em memória para embed no PDF."""
    buffer = io.BytesIO()
    render_cepnet_image(raw_cep).save(buffer, format='PNG')
    buffer.seek(0)
    return buffer


def create_cepnet(raw_cep: str, path: str = 'temp/cepnet.png') -> None:
    render_cepnet_image(raw_cep).save(path, format='PNG')


def _cepnet_items(items) -> list:
    return [it for it in (items or []) if it.get('item_type') == 'barcodeCepnet']


def validate_cepnet_placeholders(items) -> None:
    """Valida placeholders de teste no template."""
    for item in _cepnet_items(items):
        sample = (item.get('text') or '').strip()
        if not sample:
            raise CepNetValidationError(
                'cepnet.invalid_placeholder',
                user_message=t('cepnet.invalid_placeholder', reason=t('cepnet.reason_empty')),
                reason=t('cepnet.reason_empty'),
            )
        try:
            normalize_cep_digits(sample)
        except CepNetValidationError as exc:
            raise CepNetValidationError(
                'cepnet.invalid_placeholder',
                user_message=t('cepnet.invalid_placeholder', reason=exc.user_message),
                reason=exc.user_message,
            ) from exc


def validate_cepnet_batch(items, files_lines) -> None:
    """Valida todos os CEPs do lote; rejeita o lote inteiro na primeira falha."""
    from app.services.sheet_grouping import parse_column_indices
    import os

    for product_idx, raw_lines in enumerate(files_lines):
        if not raw_lines:
            continue
        file_lines = raw_lines[:-1]
        filepath = raw_lines[-1]
        filename = os.path.basename(str(filepath)) if filepath else f'#{product_idx + 1}'
        product_items = items[product_idx] if product_idx < len(items) else []
        cepnet_fields = _cepnet_items(product_items)
        if not cepnet_fields:
            continue

        for line_no, (_counter, row) in enumerate(file_lines, start=1):
            for field in cepnet_fields:
                cols = parse_column_indices(field.get('file_columns') or '')
                if not cols:
                    continue
                col_idx = cols[0]
                col_label = field.get('file_columns') or str(col_idx + 1)
                raw_value = row[col_idx] if col_idx < len(row) else ''
                try:
                    normalize_cep_digits(raw_value)
                except CepNetValidationError as exc:
                    raise CepNetValidationError(
                        'cepnet.invalid_batch',
                        user_message=t(
                            'cepnet.invalid_batch',
                            file=filename,
                            line=line_no,
                            column=col_label,
                            value=str(raw_value).strip(),
                            reason=exc.user_message,
                        ),
                        file=filename,
                        line=line_no,
                        column=col_label,
                        value=str(raw_value).strip(),
                        reason=exc.user_message,
                    ) from exc
