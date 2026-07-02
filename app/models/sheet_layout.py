"""Modelo reutilizável de layout de folha / grade de etiquetas."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

MM_PER_PT = 25.4 / 72.0
PT_PER_MM = 72.0 / 25.4
CANVAS_SCALE = 2.0  # canvas px = PDF pt * CANVAS_SCALE (legado do editor)

CUSTOM_ORIENTATION_INDEX = 4
PACKING_SEQUENTIAL = 'sequential'
PACKING_COLUMN_DEPTH = 'column_depth'

PACKING_UI_LABELS: dict[str, str] = {
    'Linha a linha': PACKING_SEQUENTIAL,
    'Coluna a coluna': PACKING_COLUMN_DEPTH,
}
PACKING_VALUE_TO_LABEL = {v: k for k, v in PACKING_UI_LABELS.items()}

SCOPE_SLOT = 'slot'
SCOPE_SHEET = 'sheet'


@dataclass
class SheetLayout:
    """Descritor de folha com grade de etiquetas (abordagem B: assistente de grade)."""

    version: int = 1
    page_width_mm: float = 210.0
    page_height_mm: float = 297.0
    label_width_mm: float = 100.0
    label_height_mm: float = 50.0
    margin_left_mm: float = 5.0
    margin_top_mm: float = 5.0
    margin_right_mm: float = 0.0
    margin_bottom_mm: float = 0.0
    columns: int = 2
    rows: int = 2
    gap_x_mm: float = 2.0
    gap_y_mm: float = 2.0
    packing: str = PACKING_SEQUENTIAL
    show_cut_guides: bool = False
    page_preset: str = 'A4'

    @property
    def slot_count(self) -> int:
        return max(0, self.columns) * max(0, self.rows)

    @staticmethod
    def mm_to_pt(value_mm: float) -> float:
        return float(value_mm) * PT_PER_MM

    @staticmethod
    def pt_to_mm(value_pt: float) -> float:
        return float(value_pt) * MM_PER_PT

    def label_canvas_size(self) -> tuple[int, int]:
        width = max(1, int(round(self.mm_to_pt(self.label_width_mm) * CANVAS_SCALE)))
        height = max(1, int(round(self.mm_to_pt(self.label_height_mm) * CANVAS_SCALE)))
        return width, height

    def page_size_pt(self) -> tuple[float, float]:
        return self.mm_to_pt(self.page_width_mm), self.mm_to_pt(self.page_height_mm)

    def slot_top_left_mm(self, row: int, col: int) -> tuple[float, float]:
        x = self.margin_left_mm + col * (self.label_width_mm + self.gap_x_mm)
        y = self.margin_top_mm + row * (self.label_height_mm + self.gap_y_mm)
        return x, y

    def iter_slots_row_col(self):
        """Percorre (row, col) na ordem de preenchimento dos registros."""
        if self.packing == PACKING_COLUMN_DEPTH:
            for col in range(self.columns):
                for row in range(self.rows):
                    yield row, col
        else:
            for row in range(self.rows):
                for col in range(self.columns):
                    yield row, col

    def compute_slot_origins_mm(self) -> list[tuple[float, float]]:
        """Origem inferior-esquerda de cada slot (mm), na ordem de preenchimento."""
        origins: list[tuple[float, float]] = []
        for row, col in self.iter_slots_row_col():
            x, y_top = self.slot_top_left_mm(row, col)
            y = self.page_height_mm - y_top - self.label_height_mm
            origins.append((x, y))
        return origins

    def slot_offsets_pt(self) -> list[tuple[float, float]]:
        """Offset superior-esquerdo de cada slot (pt), na ordem de preenchimento."""
        offsets: list[tuple[float, float]] = []
        for row, col in self.iter_slots_row_col():
            x, y = self.slot_top_left_mm(row, col)
            offsets.append((self.mm_to_pt(x), self.mm_to_pt(y)))
        return offsets

    def page_canvas_size(self) -> tuple[int, int]:
        width = max(1, int(round(self.mm_to_pt(self.page_width_mm) * CANVAS_SCALE)))
        height = max(1, int(round(self.mm_to_pt(self.page_height_mm) * CANVAS_SCALE)))
        return width, height

    def slot_guide_rects_logical(self) -> list[tuple[int, int, int, int]]:
        """Retângulos guia dos slots em coords lógicas (ordem de preenchimento)."""
        rects: list[tuple[int, int, int, int]] = []
        lw = int(round(self.mm_to_pt(self.label_width_mm) * CANVAS_SCALE))
        lh = int(round(self.mm_to_pt(self.label_height_mm) * CANVAS_SCALE))
        for row, col in self.iter_slots_row_col():
            x_mm, y_top_mm = self.slot_top_left_mm(row, col)
            x = int(round(self.mm_to_pt(x_mm) * CANVAS_SCALE))
            y = int(round(self.mm_to_pt(y_top_mm) * CANVAS_SCALE))
            rects.append((x, y, x + lw, y + lh))
        return rects

    def validate(self) -> Optional[str]:
        if self.label_width_mm <= 0 or self.label_height_mm <= 0:
            return 'Largura e altura da etiqueta devem ser maiores que zero.'
        if self.page_width_mm <= 0 or self.page_height_mm <= 0:
            return 'Largura e altura da folha devem ser maiores que zero.'
        if self.columns < 1 or self.rows < 1:
            return 'Colunas e linhas devem ser pelo menos 1.'
        if self.columns * self.rows < 1:
            return 'A grade deve ter pelo menos uma etiqueta.'

        grid_w = (
            self.margin_left_mm
            + self.columns * self.label_width_mm
            + max(0, self.columns - 1) * self.gap_x_mm
        )
        grid_h = (
            self.margin_top_mm
            + self.rows * self.label_height_mm
            + max(0, self.rows - 1) * self.gap_y_mm
        )
        if grid_w > self.page_width_mm + 0.01:
            return 'A grade ultrapassa a largura da folha.'
        if grid_h > self.page_height_mm + 0.01:
            return 'A grade ultrapassa a altura da folha.'
        return None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Optional[dict[str, Any]]) -> SheetLayout:
        if not data:
            return cls()
        fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in fields}
        return cls(**filtered)

    @classmethod
    def from_json(cls, data: Optional[str | dict[str, Any]]) -> SheetLayout:
        if not data:
            return cls()
        if isinstance(data, str):
            try:
                parsed = json.loads(data)
            except json.JSONDecodeError:
                return cls()
            return cls.from_dict(parsed)
        return cls.from_dict(data)

    @classmethod
    def default(cls) -> SheetLayout:
        return cls()
