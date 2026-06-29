"""Registro de objetos do editor — liga itens Tk Canvas a DrawingObject."""

from __future__ import annotations

from typing import Optional

from app.models.drawing_items import (
    BarcodeObject,
    BarcodeTextObject,
    CounterObject,
    DrawingObject,
    ImageObject,
    LineObject,
    RectangleObject,
    SegmentLine,
    SegmentObject,
    TextObject,
    load_objects_from_db,
    new_object_id,
)
from app.utils.barcode_generator import convert_image_to_blob


class DrawingStore:
    """Mantém objetos tipados e o vínculo canvas_id → object_id."""

    def __init__(self):
        self.objects: dict[str, DrawingObject] = {}
        self.canvas_to_object: dict[int, str] = {}
        self._segment_canvas_lines: dict[str, list[int]] = {}

    def clear(self):
        self.objects.clear()
        self.canvas_to_object.clear()
        self._segment_canvas_lines.clear()

    def register(self, obj: DrawingObject) -> None:
        if obj.object_id not in self.objects and self.objects:
            max_order = max(o.stack_order for o in self.objects.values())
            if obj.stack_order <= max_order:
                obj.stack_order = max_order + 1
        self.objects[obj.object_id] = obj

    def get(self, object_id: str) -> Optional[DrawingObject]:
        return self.objects.get(object_id)

    def get_by_canvas(self, canvas_id: int) -> Optional[DrawingObject]:
        oid = self.canvas_to_object.get(canvas_id)
        return self.objects.get(oid) if oid else None

    def bind_canvas(self, canvas_id: int, object_id: str) -> None:
        self.canvas_to_object[canvas_id] = object_id
        obj = self.objects.get(object_id)
        if isinstance(obj, SegmentObject):
            self._segment_canvas_lines.setdefault(object_id, [])
            if canvas_id not in self._segment_canvas_lines[object_id]:
                self._segment_canvas_lines[object_id].append(canvas_id)

    def unbind_canvas(self, canvas_id: int) -> None:
        oid = self.canvas_to_object.pop(canvas_id, None)
        if oid and oid in self._segment_canvas_lines:
            lines = self._segment_canvas_lines[oid]
            if canvas_id in lines:
                lines.remove(canvas_id)

    def segment_canvas_ids(self, segment_id: str) -> list[int]:
        return list(self._segment_canvas_lines.get(segment_id, []))

    def canvas_ids_for_object(self, object_id: str) -> list[int]:
        obj = self.objects.get(object_id)
        if isinstance(obj, SegmentObject):
            return self.segment_canvas_ids(object_id)
        return [cid for cid, oid in self.canvas_to_object.items() if oid == object_id]

    def group_canvas_ids(self, canvas_id: int) -> list[int]:
        """Retorna todos os canvas ids do mesmo grupo (segmento, etc.)."""
        obj = self.get_by_canvas(canvas_id)
        if isinstance(obj, SegmentObject):
            return self.segment_canvas_ids(obj.object_id)
        return [canvas_id]

    def load_from_db(self, items: list[dict]) -> None:
        self.clear()
        for obj in load_objects_from_db(items):
            self.register(obj)

    def sync_segment_lines_from_canvas(
        self, segment: SegmentObject, canvas, zoom: float = 1.0,
        preserve_preview_text: bool = False,
    ) -> None:
        """Atualiza coordenadas das linhas do segmento a partir do canvas (em coords lógicas)."""
        canvas_ids = self.segment_canvas_ids(segment.object_id)
        existing = list(segment.lines) if preserve_preview_text else []
        lines: list[SegmentLine] = []
        for i, cid in enumerate(canvas_ids):
            is_wrap = 'wrap' in canvas.gettags(cid)
            x, y = canvas.coords(cid)
            if preserve_preview_text and i < len(existing):
                text = existing[i].preview_text
            else:
                text = canvas.itemcget(cid, 'text')
            lines.append(SegmentLine(
                preview_text=text,
                x=str(int(round(x / zoom))),
                y=str(int(round(y / zoom))),
                is_wrap=is_wrap,
            ))
        lines.sort(key=lambda ln: (float(ln.y), float(ln.x)))
        segment.lines = lines
        if lines:
            segment.anchor_x = lines[0].x
            segment.anchor_y = lines[0].y

    def objects_for_scope(self, scope: str) -> list[DrawingObject]:
        items = [obj for obj in self.objects.values() if getattr(obj, 'scope', 'slot') == scope]
        return sorted(items, key=lambda o: o.stack_order)

    def sync_stack_order_from_canvas(self, canvas) -> None:
        """Atualiza stack_order dos objetos visíveis, por escopo (slot/sheet)."""
        seen: set[str] = set()
        scope_counters: dict[str, int] = {}
        for canvas_id in canvas.find_all():
            tags = canvas.gettags(canvas_id)
            if 'paper' in tags or 'slot_guide' in tags or 'slot_preview' in tags:
                continue
            obj = self.get_by_canvas(canvas_id)
            if obj is None or obj.object_id in seen:
                continue
            seen.add(obj.object_id)
            scope = getattr(obj, 'scope', 'slot') or 'slot'
            obj.stack_order = scope_counters.get(scope, 0)
            scope_counters[scope] = obj.stack_order + 1

    def serialize_all_to_db(
        self, canvas, canvas_dict_images: dict, zoom: float, active_scope: str,
        preserve_placeholder_text: bool = False,
    ) -> list[dict]:
        """Serializa todos os objetos; sincroniza coords do canvas e preserva stack_order."""
        self.sync_stack_order_from_canvas(canvas)
        synced_segments: set[str] = set()
        synced_ids: set[str] = set()

        for canvas_id in canvas.find_all():
            tags = canvas.gettags(canvas_id)
            if 'paper' in tags or 'slot_guide' in tags or 'slot_preview' in tags:
                continue
            obj = self.get_by_canvas(canvas_id)
            if obj is None:
                continue
            if isinstance(obj, SegmentObject):
                if obj.object_id in synced_segments:
                    continue
                synced_segments.add(obj.object_id)
                synced_ids.add(obj.object_id)
                self.sync_segment_lines_from_canvas(
                    obj, canvas, zoom, preserve_preview_text=preserve_placeholder_text,
                )
                self._sync_segment_font_from_canvas(obj, canvas, zoom)
                continue
            if obj.object_id in synced_ids:
                continue
            synced_ids.add(obj.object_id)
            self._serialize_canvas_item(
                canvas, canvas_id, canvas_dict_images, obj, zoom,
                preserve_placeholder_text=preserve_placeholder_text,
            )

        result: list[dict] = []
        for obj in sorted(
            self.objects.values(),
            key=lambda o: (0 if getattr(o, 'scope', 'slot') == 'slot' else 1, o.stack_order),
        ):
            if isinstance(obj, SegmentObject):
                result.extend(obj.to_db_rows())
            else:
                result.extend(self._object_to_db_rows(obj, canvas_dict_images))
        return result

    def _object_to_db_rows(self, obj: DrawingObject, canvas_dict_images: dict) -> list[dict]:
        if isinstance(obj, SegmentObject):
            return obj.to_db_rows()
        if isinstance(obj, LineObject):
            return [obj.to_db_dict(
                x1=obj.x1, y1=obj.y1, x2=obj.x2, y2=obj.y2,
                thickness=obj.thickness, dashed=obj.dashed,
            )]
        if isinstance(obj, RectangleObject):
            return [obj.to_db_dict(
                x1=obj.x1, y1=obj.y1, x2=obj.x2, y2=obj.y2,
                thickness=obj.thickness, dashed=obj.dashed,
            )]
        if isinstance(obj, (TextObject, CounterObject)):
            return [obj.to_db_dict(
                x1=obj.x, y1=obj.y, text=obj.text,
                font_name=obj.font_name, font_size=obj.font_size,
                font_style=obj.font_style, orientation=obj.orientation,
            )]
        if isinstance(obj, BarcodeTextObject):
            return [obj.to_db_dict(
                x1=obj.x, y1=obj.y, text=obj.text,
                font_name=obj.font_name, font_size=obj.font_size,
                font_style=obj.font_style, orientation=obj.orientation,
                file_columns=obj.file_column,
            )]
        if isinstance(obj, BarcodeObject):
            return [obj.to_db_dict(
                x1=obj.x, y1=obj.y, text=obj.placeholder.replace('_', ' '),
                barcode_width=obj.barcode_width, barcode_height=obj.barcode_height,
                file_columns=obj.file_column, proportion=obj.proportion,
                orientation=obj.orientation,
            )]
        if isinstance(obj, ImageObject):
            return [obj.to_db_dict(
                x1=obj.x, y1=obj.y, proportion=obj.proportion,
                orientation=obj.orientation, image=obj.image_blob,
            )]
        return []

    def serialize_to_db(self, canvas, canvas_dict_images: dict, zoom: float = 1.0) -> list[dict]:
        """Serializa canvas + objetos para o formato flat do banco (coords lógicas)."""
        seen_segments: set[str] = set()
        result: list[dict] = []

        for canvas_id in canvas.find_all():
            obj = self.get_by_canvas(canvas_id)
            if obj is None:
                continue
            if isinstance(obj, SegmentObject):
                if obj.object_id in seen_segments:
                    continue
                seen_segments.add(obj.object_id)
                self.sync_segment_lines_from_canvas(obj, canvas, zoom)
                self._sync_segment_font_from_canvas(obj, canvas, zoom)
                result.extend(obj.to_db_rows())
                continue

            row = self._serialize_canvas_item(canvas, canvas_id, canvas_dict_images, obj, zoom)
            if row:
                result.append(row)
        return result

    @staticmethod
    def _logical_font_size(font_size_screen: str, zoom: float) -> str:
        try:
            return str(max(1, int(round(int(float(font_size_screen)) / zoom))))
        except (TypeError, ValueError):
            return font_size_screen

    def _sync_segment_font_from_canvas(self, segment: SegmentObject, canvas, zoom: float = 1.0) -> None:
        ids = self.segment_canvas_ids(segment.object_id)
        if not ids:
            return
        cid = ids[0]
        font_full = canvas.itemcget(cid, 'font')
        if '{' in font_full:
            fontname = font_full.split('}')[0].replace('{', '')
            rest = font_full.split('}')[1].split()
            segment.font_name = fontname
            segment.font_size = self._logical_font_size(rest[0], zoom)
            segment.font_style = rest[1] if len(rest) > 1 else 'normal'
        else:
            parts = font_full.split()
            if len(parts) >= 3:
                segment.font_name = parts[0]
                segment.font_size = self._logical_font_size(parts[1], zoom)
                segment.font_style = parts[2]
        segment.orientation = canvas.itemcget(cid, 'angle').replace('.0', '')

    def _serialize_canvas_item(
        self, canvas, canvas_id, canvas_dict_images, obj, zoom: float = 1.0,
        preserve_placeholder_text: bool = False,
    ) -> Optional[dict]:
        ctype = canvas.type(canvas_id)
        tag = canvas.gettags(canvas_id)
        tag_str = tag[0] if tag else ''
        if 'IGNORE' in tag and tag_str:
            tag_str += ' IGNORE'

        if obj is None:
            return None

        if isinstance(obj, LineObject):
            x1, y1, x2, y2 = canvas.coords(canvas_id)
            obj.x1, obj.y1, obj.x2, obj.y2 = map(
                lambda v: str(int(round(v / zoom))), (x1, y1, x2, y2))
            obj.thickness = canvas.itemcget(canvas_id, 'width').replace('.0', '')
            dash = canvas.itemcget(canvas_id, 'dash')
            obj.dashed = dash.replace('.0', '') if dash else ''
            return obj.to_db_dict(
                x1=obj.x1, y1=obj.y1, x2=obj.x2, y2=obj.y2,
                thickness=obj.thickness, dashed=obj.dashed,
            )

        if isinstance(obj, RectangleObject):
            x1, y1, x2, y2 = canvas.coords(canvas_id)
            obj.x1, obj.y1, obj.x2, obj.y2 = map(
                lambda v: str(int(round(v / zoom))), (x1, y1, x2, y2))
            obj.thickness = canvas.itemcget(canvas_id, 'width').replace('.0', '')
            dash = canvas.itemcget(canvas_id, 'dash')
            obj.dashed = dash.replace('.0', '') if dash else ''
            return obj.to_db_dict(
                x1=obj.x1, y1=obj.y1, x2=obj.x2, y2=obj.y2,
                thickness=obj.thickness, dashed=obj.dashed,
            )

        if isinstance(obj, (TextObject, CounterObject, BarcodeTextObject)):
            x, y = canvas.coords(canvas_id)
            obj.x, obj.y = str(int(round(x / zoom))), str(int(round(y / zoom)))
            font_full = canvas.itemcget(canvas_id, 'font')
            if '{' in font_full:
                fontname = font_full.split('}')[0].replace('{', '')
                rest = font_full.split('}')[1].split()
                obj.font_name = fontname
                obj.font_size = self._logical_font_size(rest[0], zoom)
                obj.font_style = rest[1] if len(rest) > 1 else 'normal'
            else:
                parts = font_full.split()
                if len(parts) >= 3:
                    obj.font_name = parts[0]
                    obj.font_size = self._logical_font_size(parts[1], zoom)
                    obj.font_style = parts[2]
            obj.orientation = canvas.itemcget(canvas_id, 'angle').replace('.0', '')
            if not (preserve_placeholder_text and isinstance(obj, BarcodeTextObject)):
                obj.text = canvas.itemcget(canvas_id, 'text')
            fc = obj.file_column if isinstance(obj, BarcodeTextObject) else None
            return obj.to_db_dict(
                x1=obj.x, y1=obj.y, text=obj.text,
                font_name=obj.font_name, font_size=obj.font_size,
                font_style=obj.font_style, orientation=obj.orientation,
                file_columns=fc,
            )

        if isinstance(obj, BarcodeObject):
            x, y = canvas.coords(canvas_id)
            obj.x, obj.y = str(int(round(x / zoom))), str(int(round(y / zoom)))
            if canvas_id in canvas_dict_images:
                obj.proportion = str(canvas_dict_images[canvas_id][3])
                obj.orientation = str(canvas_dict_images[canvas_id][4])
            return obj.to_db_dict(
                x1=obj.x, y1=obj.y, text=obj.placeholder.replace('_', ' '),
                barcode_width=obj.barcode_width, barcode_height=obj.barcode_height,
                file_columns=obj.file_column, proportion=obj.proportion,
                orientation=obj.orientation,
            )

        if isinstance(obj, ImageObject):
            x, y = canvas.coords(canvas_id)
            obj.x, obj.y = str(int(round(x / zoom))), str(int(round(y / zoom)))
            if canvas_id in canvas_dict_images:
                obj.proportion = str(canvas_dict_images[canvas_id][3])
                obj.orientation = str(canvas_dict_images[canvas_id][4])
                obj.image_blob = convert_image_to_blob(canvas_dict_images[canvas_id][2])
            return obj.to_db_dict(
                x1=obj.x, y1=obj.y, proportion=obj.proportion,
                orientation=obj.orientation, image=obj.image_blob,
            )

        return None


def make_text_object(x, y, text, font_name, font_size, font_style, orientation, is_counter=False) -> DrawingObject:
    if is_counter:
        return CounterObject(
            object_id=new_object_id('cnt-'),
            text=text, font_name=font_name, font_size=str(font_size),
            font_style=font_style, orientation=str(orientation),
            x=str(x), y=str(y),
        )
    return TextObject(
        object_id=new_object_id('txt-'),
        text=text, font_name=font_name, font_size=str(font_size),
        font_style=font_style, orientation=str(orientation),
        x=str(x), y=str(y),
    )


def make_line_object(x1, y1, x2, y2, thickness='1', dashed='') -> LineObject:
    return LineObject(
        object_id=new_object_id('ln-'),
        x1=str(x1), y1=str(y1), x2=str(x2), y2=str(y2),
        thickness=str(thickness), dashed=dashed or '',
    )


def make_rectangle_object(x1, y1, x2, y2, thickness='1', dashed='') -> RectangleObject:
    return RectangleObject(
        object_id=new_object_id('rect-'),
        x1=str(x1), y1=str(y1), x2=str(x2), y2=str(y2),
        thickness=str(thickness), dashed=dashed or '',
    )


def make_segment_object(
    x, y, columns, labels, line_distance, char_limit,
    font_name, font_size, font_style, preview_lines,
) -> SegmentObject:
    seg_id = new_object_id('seg-')
    lines = [
        SegmentLine(text, str(x), str(y), is_wrap=wrap)
        for text, wrap in preview_lines
    ]
    return SegmentObject(
        object_id=seg_id,
        columns=columns,
        labels=labels,
        line_distance=str(line_distance),
        char_limit=str(char_limit),
        font_name=font_name,
        font_size=str(font_size),
        font_style=font_style,
        anchor_x=str(x),
        anchor_y=str(y),
        lines=lines,
    )


def make_barcode_object(kind, x, y, file_column, placeholder, width, height) -> BarcodeObject:
    return BarcodeObject(
        object_id=new_object_id('bc-'),
        barcode_kind=kind,
        x=str(x), y=str(y),
        file_column=file_column,
        placeholder=placeholder,
        barcode_width=str(width),
        barcode_height=str(height),
    )


def make_barcode_text_object(x, y, text, file_column, parent_id=None) -> BarcodeTextObject:
    return BarcodeTextObject(
        object_id=new_object_id('bct-'),
        x=str(x), y=str(y),
        text=text,
        file_column=file_column,
        parent_barcode_id=parent_id,
    )


def make_image_object(x, y, proportion=100, orientation=0) -> ImageObject:
    return ImageObject(
        object_id=new_object_id('img-'),
        x=str(x), y=str(y),
        proportion=str(proportion),
        orientation=str(orientation),
    )
