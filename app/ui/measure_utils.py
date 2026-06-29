"""Conversão e formatação de medidas do editor (coords lógicas ↔ mm)."""

from __future__ import annotations

import math

from app.models.sheet_layout import CANVAS_SCALE, SheetLayout


def logical_to_mm(value: float) -> float:
    """Coordenada lógica do canvas → milímetros."""
    return SheetLayout.pt_to_mm(float(value) / CANVAS_SCALE)


def format_mm(value_logical: float, *, decimals: int = 1) -> str:
    return f'{logical_to_mm(value_logical):.{decimals}f} mm'


def format_delta_line(dx: float, dy: float, *, decimals: int = 1) -> str:
    """Texto compacto para régua ponto-a-ponto."""
    dist = math.hypot(dx, dy)
    return (
        f'ΔX {dx:.0f}  ΔY {dy:.0f}  |  '
        f'{dist:.0f} u  ({format_mm(dist, decimals=decimals)})'
    )


def edge_gap(a_min: float, a_max: float, b_min: float, b_max: float) -> float:
    """Espaço entre bordas de dois intervalos (0 se sobrepõem)."""
    if a_max <= b_min:
        return b_min - a_max
    if b_max <= a_min:
        return a_min - b_max
    return 0.0


def pair_spacing_lines(ax1: float, ay1: float, ax2: float, ay2: float,
                       bx1: float, by1: float, bx2: float, by2: float) -> list[str]:
    """Linhas de texto com espaçamento entre duas caixas (coords lógicas)."""
    h_gap = edge_gap(ax1, ax2, bx1, bx2)
    v_gap = edge_gap(ay1, ay2, by1, by2)
    acx, acy = (ax1 + ax2) / 2, (ay1 + ay2) / 2
    bcx, bcy = (bx1 + bx2) / 2, (by1 + by2) / 2
    center_dist = math.hypot(bcx - acx, bcy - acy)
    lines = [
        f'Horizontal (bordas): {format_mm(h_gap)}',
        f'Vertical (bordas): {format_mm(v_gap)}',
        f'Centro a centro: {format_mm(center_dist)}',
    ]
    if h_gap == 0 and v_gap == 0:
        lines.append('(caixas sobrepostas nas duas direções)')
    return lines


def bbox_size_lines(width_logical: float, height_logical: float) -> list[str]:
    return [
        f'Largura da seleção: {format_mm(width_logical)}',
        f'Altura da seleção: {format_mm(height_logical)}',
    ]
