"""Serviço de layout de folha — presets, validação e resolução para produção/PDF."""

from __future__ import annotations

from typing import Optional

from app.models.sheet_layout import (
    CUSTOM_ORIENTATION_INDEX,
    PACKING_SEQUENTIAL,
    PACKING_UI_LABELS,
    SheetLayout,
)
from app.utils.printing.base import ORIENTATION_LANDSCAPE, ORIENTATION_PORTRAIT

PAGE_PRESETS: dict[str, tuple[float, float]] = {
    'A4': (210.0, 297.0),
    'A3': (297.0, 420.0),
    'Carta': (215.9, 279.4),
    'Personalizado': (210.0, 297.0),
}

PAGE_PRESET_LABELS = list(PAGE_PRESETS.keys())


def apply_page_preset(layout: SheetLayout, preset: str) -> SheetLayout:
    if preset in PAGE_PRESETS and preset != 'Personalizado':
        w, h = PAGE_PRESETS[preset]
        layout.page_width_mm = w
        layout.page_height_mm = h
    layout.page_preset = preset
    return layout


def build_grid_layout(
    *,
    page_preset: str,
    page_width_mm: float,
    page_height_mm: float,
    label_width_mm: float,
    label_height_mm: float,
    columns: int,
    rows: int,
    margin_left_mm: float,
    margin_top_mm: float,
    gap_x_mm: float,
    gap_y_mm: float,
    packing: str = PACKING_SEQUENTIAL,
    show_cut_guides: bool = False,
) -> SheetLayout:
    layout = SheetLayout(
        page_width_mm=page_width_mm,
        page_height_mm=page_height_mm,
        label_width_mm=label_width_mm,
        label_height_mm=label_height_mm,
        margin_left_mm=margin_left_mm,
        margin_top_mm=margin_top_mm,
        margin_right_mm=0.0,
        margin_bottom_mm=0.0,
        columns=int(columns),
        rows=int(rows),
        gap_x_mm=gap_x_mm,
        gap_y_mm=gap_y_mm,
        packing=packing if packing in PACKING_UI_LABELS.values() else PACKING_SEQUENTIAL,
        show_cut_guides=show_cut_guides,
        page_preset=page_preset,
    )
    return apply_page_preset(layout, page_preset)


def layout_from_product(product) -> Optional[SheetLayout]:
    if product is None:
        return None
    orientation = str(getattr(product, 'orientation', '0'))
    if orientation != str(CUSTOM_ORIENTATION_INDEX):
        return None
    return SheetLayout.from_json(getattr(product, 'layout_config', None))


def is_custom_orientation(orientation) -> bool:
    return str(orientation) == str(CUSTOM_ORIENTATION_INDEX)


def resolve_layout_for_orientation(orientation, layout_config_json: Optional[str]) -> Optional[SheetLayout]:
    if not is_custom_orientation(orientation):
        return None
    return SheetLayout.from_json(layout_config_json)


def is_landscape_layout(layout: SheetLayout) -> bool:
    """Folha em paisagem quando a largura (mm) excede a altura (mm)."""
    return float(layout.page_width_mm) > float(layout.page_height_mm)


def resolve_print_orientation(orientation, layout_config_json: Optional[str] = None) -> str:
    """Orientação física da impressora para o job (portrait/landscape).

    Apenas o modo customizado (índice 4) pode exigir paisagem, quando a folha
    foi definida com largura maior que altura (ex.: A4 invertido 297×210 mm).
    """
    if not is_custom_orientation(orientation):
        return ORIENTATION_PORTRAIT
    layout = resolve_layout_for_orientation(orientation, layout_config_json)
    if layout and is_landscape_layout(layout):
        return ORIENTATION_LANDSCAPE
    return ORIENTATION_PORTRAIT


def batch_print_orientation(
    orientation_list,
    layout_config_list: Optional[list] = None,
) -> Optional[str]:
    """Orientação única do lote, ou None se retrato e paisagem estiverem misturados."""
    configs = layout_config_list or []
    resolved = []
    for i, product_orientation in enumerate(orientation_list):
        layout_json = configs[i] if i < len(configs) else None
        resolved.append(resolve_print_orientation(product_orientation, layout_json))
    if all(o == ORIENTATION_LANDSCAPE for o in resolved):
        return ORIENTATION_LANDSCAPE
    if all(o == ORIENTATION_PORTRAIT for o in resolved):
        return ORIENTATION_PORTRAIT
    return None
