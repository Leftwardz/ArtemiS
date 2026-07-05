"""Translatable labels for the product editor."""

from __future__ import annotations

from app.i18n import paper_color_label, t
from app.models.sheet_layout import PACKING_COLUMN_DEPTH, PACKING_SEQUENTIAL
from app.ui.constants import PAPER_COLOR_LIST

ORIENTATION_COUNT = 5
PAGE_PRESET_KEYS = ('A4', 'A3', 'Carta', 'Personalizado')
DASH_CANVAS_KEYS = ('0', '4', '40')
DASH_I18N_KEYS = ('normal', 'small', 'large')
TOOL_INTERNAL_KEYS = (
    'Selecionar', 'Mover', 'Linha', 'Quadrado', 'Texto Fixo',
    'Segmento', 'Código Barras', 'Imagem', 'Medir',
)


def orientation_labels() -> list[str]:
    return [t(f'designer.orientations.{i}') for i in range(ORIENTATION_COUNT)]


def orientation_index_from_label(label: str) -> int:
    return orientation_labels().index(label)


def packing_label_for_value(value: str) -> str:
    return t(f'designer.packing.{value}')


def packing_labels() -> list[str]:
    return [packing_label_for_value(PACKING_SEQUENTIAL), packing_label_for_value(PACKING_COLUMN_DEPTH)]


def packing_value_from_label(label: str) -> str:
    for value in (PACKING_SEQUENTIAL, PACKING_COLUMN_DEPTH):
        if packing_label_for_value(value) == label:
            return value
    return PACKING_SEQUENTIAL


def page_preset_label(key: str) -> str:
    return t(f'designer.page_preset.{key}')


def page_preset_labels() -> list[str]:
    return [page_preset_label(key) for key in PAGE_PRESET_KEYS]


def scope_label(scope: str) -> str:
    return t(f'designer.scope.{scope}')


def scope_labels() -> list[str]:
    from app.models.sheet_layout import SCOPE_SHEET, SCOPE_SLOT
    return [scope_label(SCOPE_SLOT), scope_label(SCOPE_SHEET)]


def scope_from_label(label: str) -> str:
    from app.models.sheet_layout import SCOPE_SHEET, SCOPE_SLOT
    for scope in (SCOPE_SLOT, SCOPE_SHEET):
        if scope_label(scope) == label:
            return scope
    return SCOPE_SLOT


def tool_short_label(tool_key: str) -> str:
    return t(f'designer.tool.{tool_key}')


def paper_color_labels() -> list[str]:
    return [paper_color_label(key) for key in PAPER_COLOR_LIST]


def paper_color_key_from_label(label: str) -> str:
    for key in PAPER_COLOR_LIST:
        if paper_color_label(key) == label:
            return key
    return label


def dash_labels() -> list[str]:
    return [t(f'designer.dash.{key}') for key in DASH_I18N_KEYS]


def dash_label_for_canvas(dash_key: str) -> str:
    mapping = dict(zip(DASH_CANVAS_KEYS, DASH_I18N_KEYS))
    return t(f'designer.dash.{mapping.get(dash_key, "normal")}')


def dash_canvas_from_label(label: str) -> str:
    for canvas_key, i18n_key in zip(DASH_CANVAS_KEYS, DASH_I18N_KEYS):
        if t(f'designer.dash.{i18n_key}') == label:
            return '' if canvas_key == '0' else canvas_key
    return ''


def layout_error_message(code: str) -> str:
    return t(f'designer.layout_error.{code}')


def page_preset_key_from_label(label: str) -> str:
    for key in PAGE_PRESET_KEYS:
        if page_preset_label(key) == label:
            return key
    return 'A4'


def column_label(index: int) -> str:
    return t('designer.column', n=index)


def barcode_model_labels() -> list[str]:
    return [t('designer.barcode_128'), t('designer.barcode_39'), t('designer.qrcode'), t('designer.matrix')]


def barcode_kind_from_model_label(label: str) -> str:
    mapping = {
        t('designer.barcode_128'): 'barcode',
        t('designer.barcode_39'): 'barcode39',
        t('designer.qrcode'): 'barcodeQR',
        t('designer.matrix'): 'barcodeMatrix',
    }
    return mapping.get(label, 'barcode')


def font_style_label(db_value: str) -> str:
    return t('designer.font_bold') if str(db_value).lower() == 'bold' else t('designer.font_normal')


def font_style_db_from_label(label: str) -> str:
    return 'bold' if label == t('designer.font_bold') else 'normal'


def is_linear_barcode_model(label: str) -> bool:
    return label in (t('designer.barcode_128'), t('designer.barcode_39'))
