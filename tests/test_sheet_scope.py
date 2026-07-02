"""Testes do escopo sheet/slot (layout customizado)."""

from app.models.drawing_items import TextObject, new_object_id
from app.models.sheet_layout import SCOPE_SHEET, SCOPE_SLOT
from app.services.pdf_service import partition_drawings_by_scope
from app.ui.drawing_store import DrawingStore


def test_partition_drawings_by_scope():
    items = [
        {'item_type': 'text', 'scope': 'slot', 'text': 'a'},
        {'item_type': 'text', 'scope': 'sheet', 'text': 'b'},
        {'item_type': 'text', 'text': 'c'},
    ]
    slot_items, sheet_items = partition_drawings_by_scope(items)
    assert len(slot_items) == 2
    assert len(sheet_items) == 1
    assert sheet_items[0]['text'] == 'b'


def test_serialize_all_to_db_keeps_inactive_scope():
    store = DrawingStore()
    slot_obj = TextObject(object_id=new_object_id('txt-'), scope=SCOPE_SLOT, text='slot', x='10', y='20')
    sheet_obj = TextObject(object_id=new_object_id('txt-'), scope=SCOPE_SHEET, text='sheet', x='30', y='40')
    store.register(slot_obj)
    store.register(sheet_obj)

    class FakeCanvas:
        def find_all(self):
            return []

    rows = store.serialize_all_to_db(FakeCanvas(), {}, zoom=1.0, active_scope=SCOPE_SLOT)
    scopes = {r.get('scope') for r in rows}
    texts = {r.get('text') for r in rows}
    assert SCOPE_SLOT in scopes
    assert SCOPE_SHEET in scopes
    assert 'slot' in texts
    assert 'sheet' in texts
