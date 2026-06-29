"""Testes da ordem de preenchimento da grade de etiquetas."""

from app.models.sheet_layout import PACKING_COLUMN_DEPTH, PACKING_SEQUENTIAL, SheetLayout


def _offset_xy(layout: SheetLayout, index: int) -> tuple[float, float]:
    x_pt, y_pt = layout.slot_offsets_pt()[index]
    return layout.pt_to_mm(x_pt), layout.pt_to_mm(y_pt)


def test_sequential_fills_row_first():
    layout = SheetLayout(
        columns=3, rows=3, packing=PACKING_SEQUENTIAL,
        label_width_mm=10, label_height_mm=10, gap_x_mm=0, gap_y_mm=0,
        margin_left_mm=0, margin_top_mm=0,
    )
    x0, y0 = _offset_xy(layout, 0)
    x1, y1 = _offset_xy(layout, 1)
    x3, y3 = _offset_xy(layout, 3)
    assert y0 == y1
    assert x1 > x0
    assert y3 > y0


def test_column_depth_fills_column_first():
    layout = SheetLayout(
        columns=3, rows=3, packing=PACKING_COLUMN_DEPTH,
        label_width_mm=10, label_height_mm=10, gap_x_mm=0, gap_y_mm=0,
        margin_left_mm=0, margin_top_mm=0,
    )
    x0, y0 = _offset_xy(layout, 0)
    x1, y1 = _offset_xy(layout, 1)
    x3, y3 = _offset_xy(layout, 3)
    assert x0 == x1
    assert y1 > y0
    assert x3 > x0
    assert y3 == y0


def test_four_records_on_3x3_column_depth_positions():
    """Registros 1..4: coluna esquerda 1,2,3 e topo da segunda coluna = 4."""
    layout = SheetLayout(
        columns=3, rows=3, packing=PACKING_COLUMN_DEPTH,
        label_width_mm=10, label_height_mm=10, gap_x_mm=0, gap_y_mm=0,
        margin_left_mm=0, margin_top_mm=0,
    )
    slots = [_offset_xy(layout, i) for i in range(4)]
    assert slots[0][0] == slots[1][0] == slots[2][0]
    assert slots[0][1] < slots[1][1] < slots[2][1]
    assert slots[3][0] > slots[0][0]
    assert slots[3][1] == slots[0][1]
