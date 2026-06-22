"""Adaptador Tk Canvas → dict de desenhos (camada UI, não serviço)."""

from app.utils.barcode_generator import convert_image_to_blob


def serialize_canvas_to_dict(canvas, canvas_dict_images: dict, drawing_store=None, zoom: float = 1.0) -> list:
    if drawing_store is not None:
        return drawing_store.serialize_to_db(canvas, canvas_dict_images, zoom=zoom)
    return _serialize_legacy(canvas, canvas_dict_images)


def _serialize_legacy(canvas, canvas_dict_images: dict) -> list:
    result = []
    for item in canvas.find_all():
        row = _legacy_row_from_canvas(canvas, item, canvas_dict_images)
        if row:
            result.append(row)
    return result


def _legacy_row_from_canvas(canvas, item, canvas_dict_images: dict) -> dict:
    tag = canvas.gettags(item)

    if 'IGNORE' in tag:
        tag = tag[0] if tag else ''
        tag += ' IGNORE'
    else:
        tag = tag[0] if tag else ''

    item_dict = {
        'x1': None, 'x2': None, 'y1': None, 'y2': None, 'font_name': None,
        'font_size': None, 'font_style': None, 'orientation': None, 'text': None,
        'thickness': None, 'dashed': None, 'barcode_height': None, 'barcode_width': None,
        'line_distance': None, 'segment_id': None, 'tag': tag, 'proportion': None,
        'image': None, 'char_limit': None, 'file_columns': None,
    }

    if canvas.type(item) == 'text':
        if tag.startswith('segment'):
            item_dict['item_type'] = 'segment'
        elif tag.startswith('barcode'):
            item_dict['item_type'] = 'barcode_text'
        elif tag.startswith('counter'):
            item_dict['item_type'] = 'counter'
        else:
            item_dict['item_type'] = 'text'
    elif canvas.type(item) == 'image':
        if tag.startswith('barcodeQR'):
            item_dict['item_type'] = 'barcodeQR'
        elif tag.startswith('barcodeMatrix'):
            item_dict['item_type'] = 'barcodeMatrix'
        elif tag.startswith('barcode#'):
            item_dict['item_type'] = 'barcode'
        elif tag.startswith('barcode39'):
            item_dict['item_type'] = 'barcode39'
        else:
            item_dict['item_type'] = 'image'
    else:
        item_dict['item_type'] = canvas.type(item)

    if item_dict['item_type'] in ['line', 'rectangle']:
        x1, y1, x2, y2 = canvas.coords(item)
        item_dict['x1'] = str(x1).replace('.0', '')
        item_dict['y1'] = str(y1).replace('.0', '')
        item_dict['x2'] = str(x2).replace('.0', '')
        item_dict['y2'] = str(y2).replace('.0', '')
    else:
        x1, y1 = canvas.coords(item)
        item_dict['x1'] = str(x1).replace('.0', '')
        item_dict['y1'] = str(y1).replace('.0', '')

    if item_dict['item_type'] in ['segment', 'barcode_text', 'counter', 'text']:
        font_full = canvas.itemconfig(item, 'font')[4]
        if '{' in font_full:
            fontname = font_full.split('}')[0].replace('{', '')
            fontsize = font_full.split('}')[1].split()[0]
            font_style = font_full.split('}')[1].split()[1]
            font_full = [fontname, fontsize, font_style]
        else:
            font_full = canvas.itemconfig(item, 'font')[4].split()

        item_dict['font_name'] = font_full[0]
        item_dict['font_size'] = font_full[1]
        item_dict['font_style'] = font_full[2]
        item_dict['orientation'] = canvas.itemconfig(item, 'angle')[4].replace('.0', '')
        item_dict['text'] = canvas.itemconfig(item, 'text')[4]

    elif item_dict['item_type'] in ['line', 'rectangle']:
        item_dict['thickness'] = canvas.itemconfig(item, 'width')[4].replace('.0', '')
        item_dict['dashed'] = canvas.itemconfig(item, 'dash')[4].replace('.0', '')

    if item_dict['item_type'] in ['barcode', 'barcode39']:
        item_dict['barcode_height'] = tag.split('§')[2]
        item_dict['barcode_width'] = tag.split('§')[1]

    if item_dict['item_type'] in ['barcodeQR', 'barcodeMatrix', 'barcode', 'barcode39']:
        item_dict['proportion'] = str(canvas_dict_images[item][3])
        item_dict['orientation'] = str(canvas_dict_images[item][4])
        item_dict['text'] = tag.split('§')[4]

    if item_dict['item_type'] == 'segment':
        item_dict['segment_id'] = tag.split('§')[0]
        item_dict['line_distance'] = tag.split('§')[2]
        item_dict['char_limit'] = tag.split('§')[4]

    if item_dict['item_type'] == 'image':
        item_dict['proportion'] = str(canvas_dict_images[item][3])
        item_dict['orientation'] = str(canvas_dict_images[item][4])
        item_dict['image'] = convert_image_to_blob(canvas_dict_images[item][2])

    item_dict['file_columns'] = tag.split('§')[3] if '§' in tag else None
    return item_dict
