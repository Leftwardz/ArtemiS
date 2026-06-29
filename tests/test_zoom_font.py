"""Zoom não deve alterar font_size lógico dos objetos."""

from app.models.drawing_items import SegmentObject, TextObject, new_object_id
from app.ui.drawing_store import DrawingStore


def _zfont(logical: int, zoom: float) -> int:
    return max(1, int(round(logical * zoom)))


class FakeCanvas:
    def __init__(self, items):
        self._items = items

    def find_all(self):
        return list(self._items.keys())

    def gettags(self, cid):
        return self._items[cid].get('tags', ())

    def type(self, cid):
        return self._items[cid]['type']

    def coords(self, cid):
        return self._items[cid]['coords']

    def itemcget(self, cid, key):
        return self._items[cid].get(key, '')


def test_zoom_cycles_preserve_text_font_size():
    store = DrawingStore()
    obj = TextObject(
        object_id=new_object_id('txt-'),
        text='hello',
        font_name='arial',
        font_size='12',
        font_style='normal',
        orientation='0',
        x='100',
        y='200',
    )
    store.register(obj)

    zooms = [1.0, 1.25, 1.5, 1.75, 2.0, 1.5, 1.25, 1.0, 0.75, 1.0, 1.25, 0.5, 1.0]
    for zoom in zooms:
        screen_font = _zfont(12, zoom)
        canvas = FakeCanvas({
            1: {
                'type': 'text',
                'coords': (100 * zoom, 200 * zoom),
                'font': f'arial {screen_font} normal',
                'angle': '0',
                'text': 'hello',
            },
        })
        store.bind_canvas(1, obj.object_id)
        store.sync_geometry_from_canvas(canvas, {}, zoom)
        store.canvas_to_object.clear()

    assert obj.font_size == '12'


def test_zoom_cycles_preserve_segment_font_size():
    store = DrawingStore()
    seg = SegmentObject(
        object_id=new_object_id('seg-'),
        columns=['Coluna_1'],
        labels=['Label'],
        line_distance='15',
        char_limit='40',
        font_name='arial',
        font_size='10',
        font_style='normal',
        orientation='0',
        anchor_x='50',
        anchor_y='60',
    )
    seg.lines = []
    store.register(seg)

    zooms = [1.0, 1.25, 1.5, 2.0, 0.75, 1.0, 1.33, 1.66, 1.0]
    for zoom in zooms:
        screen_font = _zfont(10, zoom)
        canvas = FakeCanvas({
            1: {
                'type': 'text',
                'coords': (50 * zoom, 60 * zoom),
                'font': f'arial {screen_font} normal',
                'angle': '0',
                'text': 'Label',
            },
        })
        store.bind_canvas(1, seg.object_id)
        store.sync_geometry_from_canvas(canvas, {}, zoom)
        store.canvas_to_object.clear()

    assert seg.font_size == '10'


def test_serialize_all_to_db_keeps_store_font_not_canvas():
    store = DrawingStore()
    obj = TextObject(
        object_id=new_object_id('txt-'),
        text='x',
        font_name='arial',
        font_size='14',
        font_style='normal',
        orientation='0',
        x='10',
        y='20',
    )
    store.register(obj)
    zoom = 1.5
    screen_font = _zfont(14, zoom)
    canvas = FakeCanvas({
        1: {
            'type': 'text',
            'coords': (15, 30),
            'font': f'arial {screen_font} normal',
            'angle': '0',
            'text': 'x',
        },
    })
    store.bind_canvas(1, obj.object_id)
    rows = store.serialize_all_to_db(canvas, {}, zoom=zoom, active_scope='slot')
    text_rows = [r for r in rows if r.get('item_type') == 'text']
    assert len(text_rows) == 1
    assert text_rows[0]['font_size'] == '14'
