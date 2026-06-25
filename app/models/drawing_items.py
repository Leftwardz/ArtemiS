"""Modelo tipado de itens do editor visual (substitui tags §-delimitadas)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Optional


def new_object_id(prefix: str = '') -> str:
    uid = uuid.uuid4().hex[:12]
    return f'{prefix}{uid}' if prefix else uid


def _s(value: Any) -> str:
    if value is None:
        return ''
    return str(value).replace('.0', '') if isinstance(value, float) else str(value)


def _split_tag_fields(tag: str) -> list[str]:
    base = tag.replace(' IGNORE', '').strip()
    if '§' not in base:
        return [base]
    return base.split('§')


def _labels_join(labels: list[str]) -> str:
    return '.'.join(l.replace(' ', '_') for l in labels)


def _labels_split(text: str) -> list[str]:
    if not text:
        return []
    return [p.replace('_', ' ') for p in text.split('.')]


def _columns_split(text: str) -> list[str]:
    if not text:
        return []
    return text.split('.')


@dataclass
class SegmentLine:
    """Uma linha visual do segmento (pode ser continuação de quebra)."""
    preview_text: str
    x: str
    y: str
    is_wrap: bool = False


@dataclass
class DrawingObject:
    """Base para todos os itens do layout."""
    object_id: str
    item_type: str = ''
    scope: str = 'slot'

    def canvas_tags(self) -> tuple[str, ...]:
        return (f'obj:{self.object_id}',)

    def group_tag(self) -> Optional[str]:
        return None

    def legacy_tag(self) -> str:
        return ''

    def to_db_dict(self, **canvas_fields) -> dict:
        row = {
            'item_type': self.item_type,
            'scope': self.scope,
            'x1': None, 'x2': None, 'y1': None, 'y2': None,
            'font_name': None, 'font_size': None, 'font_style': None,
            'orientation': None, 'text': None, 'thickness': None, 'dashed': None,
            'barcode_height': None, 'barcode_width': None, 'line_distance': None,
            'segment_id': None, 'tag': self.legacy_tag(), 'proportion': None,
            'image': None, 'char_limit': None, 'file_columns': None,
        }
        row.update(canvas_fields)
        if not row.get('tag'):
            row['tag'] = self.legacy_tag()
        return row


@dataclass
class TextObject(DrawingObject):
    text: str = ''
    font_name: str = 'arial'
    font_size: str = '10'
    font_style: str = 'normal'
    orientation: str = '0'
    x: str = '0'
    y: str = '0'

    def __post_init__(self):
        self.item_type = 'text'

    def legacy_tag(self) -> str:
        return ''


@dataclass
class CounterObject(DrawingObject):
    text: str = '0000001'
    font_name: str = 'arial'
    font_size: str = '10'
    font_style: str = 'normal'
    orientation: str = '0'
    x: str = '0'
    y: str = '0'

    def __post_init__(self):
        self.item_type = 'counter'

    def legacy_tag(self) -> str:
        return f'counter{self.x}{self.y}§§§§'


@dataclass
class LineObject(DrawingObject):
    x1: str = '0'
    y1: str = '0'
    x2: str = '0'
    y2: str = '0'
    thickness: str = '1'
    dashed: str = ''

    def __post_init__(self):
        self.item_type = 'line'

    def legacy_tag(self) -> str:
        return ''


@dataclass
class RectangleObject(DrawingObject):
    x1: str = '0'
    y1: str = '0'
    x2: str = '0'
    y2: str = '0'
    thickness: str = '1'
    dashed: str = ''

    def __post_init__(self):
        self.item_type = 'rectangle'

    def legacy_tag(self) -> str:
        return ''


@dataclass
class BarcodeObject(DrawingObject):
    barcode_kind: str = 'barcode'  # barcode | barcode39 | barcodeQR | barcodeMatrix
    placeholder: str = ''
    file_column: str = ''
    barcode_width: str = '0.18'
    barcode_height: str = '1.5'
    proportion: str = '100'
    orientation: str = '0'
    x: str = '0'
    y: str = '0'
    companion_text_id: Optional[str] = None

    def __post_init__(self):
        self.item_type = self.barcode_kind

    @property
    def prefix(self) -> str:
        if self.barcode_kind == 'barcode':
            return 'barcode#'
        if self.barcode_kind == 'barcode39':
            return 'barcode39'
        if self.barcode_kind == 'barcodeQR':
            return 'barcodeQR'
        return 'barcodeMatrix'

    def legacy_tag(self) -> str:
        ph = self.placeholder.replace(' ', '_')
        if self.barcode_kind in ('barcodeQR', 'barcodeMatrix'):
            return f'{self.prefix}{self.x}{self.y}§§§{self.file_column}§{ph}'
        return f'{self.prefix}{self.x}{self.y}§{self.barcode_width}§{self.barcode_height}§{self.file_column}§{ph}'

    def legacy_text_tag(self) -> str:
        ph = self.placeholder.replace(' ', '_')
        return f'barcode_text{self.x}{self.y}§§§{self.file_column}§{ph}'


@dataclass
class BarcodeTextObject(DrawingObject):
    text: str = ''
    file_column: str = ''
    font_name: str = 'arial'
    font_size: str = '10'
    font_style: str = 'normal'
    orientation: str = '0'
    x: str = '0'
    y: str = '0'
    parent_barcode_id: Optional[str] = None

    def __post_init__(self):
        self.item_type = 'barcode_text'

    def legacy_tag(self) -> str:
        ph = self.text.replace(' ', '_')
        return f'barcode_text{self.x}{self.y}§§§{self.file_column}§{ph}'


@dataclass
class ImageObject(DrawingObject):
    proportion: str = '100'
    orientation: str = '0'
    x: str = '0'
    y: str = '0'
    image_blob: Optional[bytes] = None

    def __post_init__(self):
        self.item_type = 'image'

    def legacy_tag(self) -> str:
        return ''


@dataclass
class SegmentObject(DrawingObject):
    """Bloco de texto multi-linha ligado a colunas CSV — identidade estável via object_id."""
    columns: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    line_distance: str = '15'
    char_limit: str = '0'
    font_name: str = 'arial'
    font_size: str = '10'
    font_style: str = 'normal'
    orientation: str = '0'
    anchor_x: str = '0'
    anchor_y: str = '0'
    lines: list[SegmentLine] = field(default_factory=list)

    def __post_init__(self):
        self.item_type = 'segment'

    @property
    def segment_id(self) -> str:
        return self.object_id

    def group_tag(self) -> Optional[str]:
        return f'seg:{self.object_id}'

    def canvas_tags(self) -> tuple[str, ...]:
        tags = [f'obj:{self.object_id}', f'seg:{self.object_id}']
        return tuple(tags)

    def legacy_tag_for_line(self, line: SegmentLine) -> str:
        labels = _labels_join(self.labels)
        cols = '.'.join(self.columns)
        tag = f'{self.object_id}§{labels}§{self.line_distance}§{cols}§{self.char_limit}'
        if line.is_wrap:
            tag += ' IGNORE'
        return tag

    def legacy_tag(self) -> str:
        if self.lines:
            return self.legacy_tag_for_line(self.lines[0])
        return self.legacy_tag_for_line(SegmentLine('', self.anchor_x, self.anchor_y))

    def update_config(
        self,
        columns: list[str],
        labels: list[str],
        line_distance: str,
        char_limit: str,
        font_name: str,
        font_size: str,
        font_style: str,
        orientation: str,
    ) -> None:
        """Atualiza configuração mantendo o mesmo object_id/segment_id."""
        self.columns = list(columns)
        self.labels = list(labels)
        self.line_distance = _s(line_distance)
        self.char_limit = _s(char_limit)
        self.font_name = font_name
        self.font_size = _s(font_size)
        self.font_style = font_style
        self.orientation = _s(orientation)

    @classmethod
    def from_db_rows(cls, rows: list[dict]) -> SegmentObject:
        first = rows[0]
        tag = first.get('tag') or ''
        parts = _split_tag_fields(tag)
        segment_id = first.get('segment_id') or parts[0] or new_object_id('seg-')

        if len(parts) >= 5:
            labels = _labels_split(parts[1])
            line_distance = parts[2]
            columns = _columns_split(parts[3])
            char_limit = parts[4].replace(' IGNORE', '').strip()
        else:
            labels = _labels_split('')
            line_distance = first.get('line_distance') or '15'
            columns = _columns_split(first.get('file_columns') or '')
            char_limit = first.get('char_limit') or '0'

        obj = cls(
            object_id=segment_id,
            scope=first.get('scope') or 'slot',
            columns=columns,
            labels=labels or [f'Placeholder {i}' for i in range(len(columns))],
            line_distance=_s(line_distance),
            char_limit=_s(char_limit),
            font_name=first.get('font_name') or 'arial',
            font_size=_s(first.get('font_size') or '10'),
            font_style=first.get('font_style') or 'normal',
            orientation=_s(first.get('orientation') or '0'),
            anchor_x=_s(first.get('x1') or '0'),
            anchor_y=_s(first.get('y1') or '0'),
        )
        for row in rows:
            is_wrap = 'IGNORE' in (row.get('tag') or '')
            obj.lines.append(SegmentLine(
                preview_text=row.get('text') or '',
                x=_s(row.get('x1') or obj.anchor_x),
                y=_s(row.get('y1') or obj.anchor_y),
                is_wrap=is_wrap,
            ))
        return obj

    def to_db_rows(self) -> list[dict]:
        rows = []
        for line in self.lines:
            tag = self.legacy_tag_for_line(line)
            rows.append({
                'item_type': 'segment',
                'scope': self.scope,
                'x1': line.x,
                'y1': line.y,
                'x2': None,
                'y2': None,
                'font_name': self.font_name,
                'font_size': self.font_size,
                'font_style': self.font_style,
                'orientation': self.orientation,
                'text': line.preview_text,
                'thickness': None,
                'dashed': None,
                'barcode_height': None,
                'barcode_width': None,
                'line_distance': self.line_distance,
                'segment_id': self.segment_id,
                'tag': tag,
                'proportion': None,
                'image': None,
                'char_limit': self.char_limit,
                'file_columns': '.'.join(self.columns),
            })
        return rows


def object_from_db_row(row: dict) -> DrawingObject:
    """Instancia um objeto a partir de uma linha do banco (exceto segment — agrupar antes)."""
    item_type = row.get('item_type') or ''
    tag = row.get('tag') or ''
    oid = new_object_id()
    scope = row.get('scope') or 'slot'

    if item_type == 'text' and not tag.startswith(('segment', 'counter', 'barcode')):
        return TextObject(
            object_id=oid,
            scope=scope,
            text=row.get('text') or '',
            font_name=row.get('font_name') or 'arial',
            font_size=_s(row.get('font_size') or '10'),
            font_style=row.get('font_style') or 'normal',
            orientation=_s(row.get('orientation') or '0'),
            x=_s(row.get('x1') or '0'),
            y=_s(row.get('y1') or '0'),
        )
    if item_type == 'counter' or tag.startswith('counter'):
        return CounterObject(
            object_id=oid,
            scope=scope,
            text=row.get('text') or '0000001',
            font_name=row.get('font_name') or 'arial',
            font_size=_s(row.get('font_size') or '10'),
            font_style=row.get('font_style') or 'normal',
            orientation=_s(row.get('orientation') or '0'),
            x=_s(row.get('x1') or '0'),
            y=_s(row.get('y1') or '0'),
        )
    if item_type == 'barcode_text' or (tag.startswith('barcode') and item_type == 'barcode_text'):
        parts = _split_tag_fields(tag)
        col = parts[3] if len(parts) > 3 else row.get('file_columns') or ''
        return BarcodeTextObject(
            object_id=oid,
            scope=scope,
            text=row.get('text') or '',
            file_column=col,
            font_name=row.get('font_name') or 'arial',
            font_size=_s(row.get('font_size') or '10'),
            font_style=row.get('font_style') or 'normal',
            orientation=_s(row.get('orientation') or '0'),
            x=_s(row.get('x1') or '0'),
            y=_s(row.get('y1') or '0'),
        )
    if item_type in ('barcode', 'barcode39', 'barcodeQR', 'barcodeMatrix'):
        parts = _split_tag_fields(tag)
        return BarcodeObject(
            object_id=oid,
            scope=scope,
            barcode_kind=item_type,
            placeholder=row.get('text') or (parts[4].replace('_', ' ') if len(parts) > 4 else ''),
            file_column=parts[3] if len(parts) > 3 else row.get('file_columns') or '',
            barcode_width=parts[1] if len(parts) > 1 else row.get('barcode_width') or '0.18',
            barcode_height=parts[2] if len(parts) > 2 else row.get('barcode_height') or '1.5',
            proportion=_s(row.get('proportion') or '100'),
            orientation=_s(row.get('orientation') or '0'),
            x=_s(row.get('x1') or '0'),
            y=_s(row.get('y1') or '0'),
        )
    if item_type == 'line':
        return LineObject(
            object_id=oid,
            scope=scope,
            x1=_s(row.get('x1')), y1=_s(row.get('y1')),
            x2=_s(row.get('x2')), y2=_s(row.get('y2')),
            thickness=_s(row.get('thickness') or '1'),
            dashed=_s(row.get('dashed') or ''),
        )
    if item_type == 'rectangle':
        return RectangleObject(
            object_id=oid,
            scope=scope,
            x1=_s(row.get('x1')), y1=_s(row.get('y1')),
            x2=_s(row.get('x2')), y2=_s(row.get('y2')),
            thickness=_s(row.get('thickness') or '1'),
            dashed=_s(row.get('dashed') or ''),
        )
    if item_type == 'image':
        return ImageObject(
            object_id=oid,
            scope=scope,
            proportion=_s(row.get('proportion') or '100'),
            orientation=_s(row.get('orientation') or '0'),
            x=_s(row.get('x1') or '0'),
            y=_s(row.get('y1') or '0'),
            image_blob=row.get('image'),
        )
    return TextObject(object_id=oid, text=row.get('text') or '')


def load_objects_from_db(items: list[dict]) -> list[DrawingObject]:
    """Reconstrói objetos a partir das linhas do banco (agrupa segmentos)."""
    segment_rows: dict[str, list[dict]] = {}
    others: list[dict] = []
    for row in items:
        if row.get('item_type') == 'segment':
            sid = row.get('segment_id') or _split_tag_fields(row.get('tag') or '')[0]
            segment_rows.setdefault(sid, []).append(row)
        else:
            others.append(row)

    objects: list[DrawingObject] = []
    for rows in segment_rows.values():
        objects.append(SegmentObject.from_db_rows(rows))
    for row in others:
        objects.append(object_from_db_row(row))
    return objects
