"""Agrupamento de registros por colunas do cabeçalho de folha (layout customizado)."""

from __future__ import annotations

import math
from typing import Any


def parse_column_indices(file_columns: str | None) -> list[int]:
    """Converte 'Coluna_1.Coluna_3' em índices 0-based [0, 2]."""
    if not file_columns:
        return []
    indices: list[int] = []
    for part in file_columns.split('.'):
        part = part.strip()
        if part.startswith('Coluna_'):
            indices.append(int(part.replace('Coluna_', '')) - 1)
    return indices


def extract_sheet_header_group_columns(sheet_items: list[dict]) -> list[int]:
    """Colunas usadas em segmentos do cabeçalho — definem a chave de agrupamento."""
    seen: set[int] = set()
    ordered: list[int] = []
    for item in sheet_items or []:
        if item.get('item_type') != 'segment':
            continue
        for col in parse_column_indices(item.get('file_columns')):
            if col not in seen:
                seen.add(col)
                ordered.append(col)
    return ordered


def record_group_key(columns: list[str], column_indices: list[int]) -> tuple[str, ...]:
    """Tupla de valores normalizados para comparar registros na mesma folha."""
    if not column_indices:
        return ()
    values: list[str] = []
    for idx in column_indices:
        try:
            values.append((columns[idx] or '').strip())
        except IndexError:
            values.append('')
    return tuple(values)


def split_filelines_into_groups(filelines: list, column_indices: list[int]) -> list[list]:
    """Quebra a lista quando algum valor de agrupamento muda."""
    if not column_indices:
        return [list(filelines)]

    groups: list[list] = []
    current_key: tuple[str, ...] | None = None
    current_group: list = []

    for record in filelines:
        key = record_group_key(record[1], column_indices)
        if current_key is None:
            current_key = key
            current_group = [record]
        elif key == current_key:
            current_group.append(record)
        else:
            groups.append(current_group)
            current_key = key
            current_group = [record]

    if current_group:
        groups.append(current_group)
    return groups


def build_sheet_pages(
    filelines: list,
    sheet_items: list[dict],
    slot_count: int,
) -> list[dict[str, Any]]:
    """Monta páginas respeitando grupos do cabeçalho e capacidade de slots.

    Cada entrada: ``records``, ``group_page`` (1-based), ``group_total``.
    """
    slot_count = max(1, slot_count)
    group_columns = extract_sheet_header_group_columns(sheet_items)
    groups = split_filelines_into_groups(filelines, group_columns)

    pages: list[dict[str, Any]] = []
    for group in groups:
        group_total = max(1, math.ceil(len(group) / slot_count))
        for page_idx in range(group_total):
            start = page_idx * slot_count
            pages.append({
                'records': group[start:start + slot_count],
                'group_page': page_idx + 1,
                'group_total': group_total,
            })
    return pages
