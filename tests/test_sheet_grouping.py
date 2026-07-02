"""Testes de agrupamento por cabeçalho de folha."""

from app.services.sheet_grouping import (
    build_sheet_pages,
    extract_sheet_header_group_columns,
    record_group_key,
    split_filelines_into_groups,
)


def _records():
    """Work; registro; informação; agência (índices 0..3)."""
    return [
        (0, ['Work 1', 'registro1', 'informação1', 'agencia1']),
        (1, ['Work 1', 'registro2', 'informação1', 'agencia1']),
        (2, ['Work 2', 'registro3', 'informação1', 'agencia1']),
        (3, ['Work 2', 'registro4', 'informação1', 'agencia2']),
    ]


def _sheet_segment(*columns: int):
    cols = '.'.join(f'Coluna_{c}' for c in columns)
    return {'item_type': 'segment', 'file_columns': cols}


def test_group_by_work_only_splits_two_groups():
    sheet_items = [_sheet_segment(1)]
    groups = split_filelines_into_groups(_records(), extract_sheet_header_group_columns(sheet_items))
    assert len(groups) == 2
    assert len(groups[0]) == 2
    assert len(groups[1]) == 2


def test_group_by_work_and_agency_splits_three_groups():
    sheet_items = [_sheet_segment(1, 4)]
    columns = extract_sheet_header_group_columns(sheet_items)
    groups = split_filelines_into_groups(_records(), columns)
    assert len(groups) == 3
    assert record_group_key(groups[0][0][1], columns) == ('Work 1', 'agencia1')
    assert record_group_key(groups[1][0][1], columns) == ('Work 2', 'agencia1')
    assert record_group_key(groups[2][0][1], columns) == ('Work 2', 'agencia2')


def test_build_sheet_pages_one_slot_per_page():
    sheet_items = [_sheet_segment(1)]
    pages = build_sheet_pages(_records(), sheet_items, slot_count=2)
    assert len(pages) == 2
    assert len(pages[0]['records']) == 2
    assert pages[0]['group_page'] == 1
    assert pages[0]['group_total'] == 1
    assert len(pages[1]['records']) == 2


def test_build_sheet_pages_overflow_within_same_group():
    """Mesma work, muitos registros → várias folhas com paginação 1/N."""
    records = [
        (0, ['Work 1', 'r1', 'i', 'a1']),
        (1, ['Work 1', 'r2', 'i', 'a1']),
        (2, ['Work 1', 'r3', 'i', 'a1']),
        (3, ['Work 1', 'r4', 'i', 'a1']),
        (4, ['Work 1', 'r5', 'i', 'a1']),
    ]
    sheet_items = [_sheet_segment(1)]
    pages = build_sheet_pages(records, sheet_items, slot_count=2)
    assert len(pages) == 3
    assert pages[0]['group_page'] == 1 and pages[0]['group_total'] == 3
    assert pages[1]['group_page'] == 2 and pages[1]['group_total'] == 3
    assert pages[2]['group_page'] == 3 and pages[2]['group_total'] == 3


def test_no_sheet_segments_keeps_linear_pagination():
    pages = build_sheet_pages(_records(), sheet_items=[], slot_count=2)
    assert len(pages) == 2
    assert pages[0]['group_total'] == 2
