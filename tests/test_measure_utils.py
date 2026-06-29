"""Testes de conversão e espaçamento do editor."""

import math

from app.ui.measure_utils import (
    bbox_size_lines,
    edge_gap,
    format_delta_line,
    logical_to_mm,
    pair_spacing_lines,
)
from app.models.sheet_layout import CANVAS_SCALE, SheetLayout


def test_logical_to_mm_roundtrip_with_layout():
    mm = 100.0
    logical = SheetLayout.mm_to_pt(mm) * CANVAS_SCALE
    assert abs(logical_to_mm(logical) - mm) < 0.01


def test_format_delta_line():
    text = format_delta_line(30, 40)
    assert 'ΔX 30' in text
    assert 'ΔY 40' in text
    assert '50 u' in text
    assert 'mm' in text


def test_edge_gap():
    assert edge_gap(0, 10, 20, 30) == 10
    assert edge_gap(0, 20, 10, 30) == 0


def test_pair_spacing_lines():
    lines = pair_spacing_lines(0, 0, 10, 10, 20, 0, 30, 10)
    assert any('Horizontal' in ln for ln in lines)
    assert any('Vertical' in ln for ln in lines)
    assert any('Centro a centro' in ln for ln in lines)


def test_bbox_size_lines():
    lines = bbox_size_lines(100, 50)
    assert len(lines) == 2
    assert 'Largura' in lines[0]
