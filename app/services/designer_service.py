import base64
import json
from typing import List, Optional

from app.utils.barcode_generator import convert_image_to_blob


ORIENTATION_LABELS = [
    '3 por Folha - Vertical',
    '2 por Folha - Horizontal',
    '1 por folha - A4',
    '2 por folha - Vertical',
]


def validate_product_name(current_name: str, new_name: str, existing_products: List[str]) -> Optional[str]:
    if new_name in existing_products and new_name != current_name:
        return 'ERROR - Nome de Produto já existente para esse cliente'
    if new_name == 'Novo Produto':
        return 'ERROR - Por favor, dar um novo nome ao produto'
    if new_name.strip() == '':
        return 'ERROR - Nome do Produto não pode ser vazio'
    if '-' in new_name.strip():
        return 'ERROR - Nome do Produto não pode conter traço " - "'
    return None


def orientation_index_from_label(label: str) -> int:
    return ORIENTATION_LABELS.index(label)


def load_product_drawings(client: str, product_name: str, db):
    return db.consult_drawings_from_product(client, product_name)


def save_product_with_drawings(
    client: str,
    current_name: str,
    new_name: str,
    color: str,
    orientation_type: int,
    paper_size: str,
    drawings: list,
    db,
):
    db.change_or_add_product_name(client, current_name, new_name, color, orientation_type, paper_size)
    db.del_all_drawing_from_product(client, new_name)
    db.save_drawings(client, new_name, drawings)


def delete_product(client: str, product_name: str, db) -> bool:
    return db.delete_product(client, product_name)


def duplicate_product(
    source_client: str,
    source_product: str,
    target_client: str,
    target_product: str,
    db,
) -> Optional[str]:
    if target_product in db.search_products(target_client):
        return 'Nome de produto já existe'

    product_obj = db.search_product(source_client, source_product)
    db.insert_product(
        target_product,
        target_client,
        product_obj.paper_color,
        product_obj.orientation,
        product_obj.paper_size,
    )
    items = db.consult_drawings_from_product(source_client, source_product)
    db.save_drawings(target_client, target_product, items)
    return None


def build_export_payload(client: str, product: str, db) -> dict:
    product_db = db.search_product(client, product)
    items = db.consult_drawings_from_product(client, product)

    for item in items:
        if item['image']:
            item['image'] = base64.b64encode(item['image']).decode('utf-8')

    return {
        'cliente': client,
        'produto': product,
        'paper_size': product_db.paper_size,
        'color': db.search_color(client, product),
        'orientation': product_db.orientation,
        'items': items,
    }


def parse_import_file(file_path: str) -> dict:
    with open(file_path) as file:
        product_file = json.load(file)

    for item in product_file['items']:
        if item['image']:
            item['image'] = base64.b64decode(item['image'].encode('utf-8'))

    return product_file


def replace_imported_drawings(client_name: str, product_name: str, items: list, db):
    db.del_all_drawing_from_product(client_name, product_name)
    db.save_drawings(client_name, product_name, items)


def import_product_for_existing_client(
    client_name: str,
    product_name: str,
    color: str,
    orientation: str,
    paper_size: str,
    items: list,
    db,
):
    db.insert_product(product_name, client_name, color, orientation, paper_size)
    db.save_drawings(client_name, product_name, items)


def import_product_with_new_client(
    client_name: str,
    product_name: str,
    color: str,
    orientation: str,
    paper_size: str,
    items: list,
    db,
):
    db.insert_client(client_name)
    db.insert_product(product_name, client_name, color, orientation, paper_size)
    db.save_drawings(client_name, product_name, items)


def has_unsaved_changes(
    client: str,
    product_name: str,
    new_name: str,
    color: str,
    orientation_index: int,
    paper_size: str,
    current_drawings: list,
    saved_drawings: list,
    db,
) -> bool:
    product = db.search_product(client, product_name)
    if not product:
        return True

    if new_name != product_name or current_drawings != saved_drawings:
        return True
    if color != product.paper_color:
        return True
    if orientation_index != int(product.orientation):
        return True
    if paper_size != product.paper_size:
        return True
    return False


def serialize_canvas_to_dict(canvas, canvas_dict_images: dict) -> list:
    result = []

    for item in canvas.find_all():
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
            'image': None, 'char_limit': None,
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
        result.append(item_dict)

    return result
