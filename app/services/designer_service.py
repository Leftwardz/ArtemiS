import base64
import json
from typing import List, Optional

from app import audit
from app.models.sheet_layout import CUSTOM_ORIENTATION_INDEX
from app.services.layout_service import get_product_paper_size


ORIENTATION_LABELS = [
    '3 por Folha - Vertical',
    '2 por Folha - Horizontal',
    '1 por folha - A4',
    '2 por folha - Vertical',
    'Customizado',
]


def validate_product_name(current_name: str, new_name: str, existing_products: List[str]) -> Optional[str]:
    from app.i18n import t
    default_name = t('designer.new_product')
    if new_name in existing_products and new_name != current_name:
        return 'name_exists'
    if new_name in (default_name, 'Novo Produto'):
        return 'rename_default'
    if new_name.strip() == '':
        return 'name_empty'
    if '-' in new_name.strip():
        return 'name_dash'
    return None


def orientation_index_from_label(label: str) -> int:
    from app.i18n.designer_labels import orientation_index_from_label as _index_from_label
    return _index_from_label(label)


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
    layout_config: Optional[str] = None,
):
    db.change_or_add_product_name(
        client, current_name, new_name, color, orientation_type, paper_size, layout_config,
    )
    db.del_all_drawing_from_product(client, new_name)
    db.save_drawings(client, new_name, drawings)
    renamed = '' if current_name == new_name else f' (renomeado de "{current_name}")'
    audit.log_cadastro('product_save', detail=f'{client} / {new_name}{renamed}')


def delete_product(client: str, product_name: str, db) -> bool:
    result = db.delete_product(client, product_name)
    if result:
        audit.log_cadastro('product_delete', detail=f'{client} / {product_name}')
    return result


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
    paper_size = get_product_paper_size(product_obj)
    db.insert_product(
        target_product,
        target_client,
        product_obj.paper_color,
        product_obj.orientation,
        paper_size,
        getattr(product_obj, 'layout_config', None),
    )
    items = db.consult_drawings_from_product(source_client, source_product)
    db.save_drawings(target_client, target_product, items)
    audit.log_cadastro(
        'product_duplicate',
        detail=f'{source_client}/{source_product} -> {target_client}/{target_product}',
    )
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
        'paper_size': get_product_paper_size(product_db),
        'color': db.search_color(client, product),
        'orientation': product_db.orientation,
        'layout_config': getattr(product_db, 'layout_config', None),
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
    audit.log_cadastro('product_import_replace', detail=f'{client_name} / {product_name}')


def import_product_for_existing_client(
    client_name: str,
    product_name: str,
    color: str,
    orientation: str,
    paper_size: str,
    items: list,
    db,
    layout_config: Optional[str] = None,
):
    db.insert_product(product_name, client_name, color, orientation, paper_size, layout_config)
    db.save_drawings(client_name, product_name, items)
    audit.log_cadastro('product_import', detail=f'{client_name} / {product_name}')


def import_product_with_new_client(
    client_name: str,
    product_name: str,
    color: str,
    orientation: str,
    paper_size: str,
    items: list,
    db,
    layout_config: Optional[str] = None,
):
    db.insert_client(client_name)
    db.insert_product(product_name, client_name, color, orientation, paper_size, layout_config)
    db.save_drawings(client_name, product_name, items)
    audit.log_cadastro(
        'product_import_new_client',
        detail=f'cliente novo "{client_name}" / produto "{product_name}"',
    )


def _normalize_drawing_row(row: dict) -> dict:
    """Normaliza linha do banco/serialização para comparação estável (None → '')."""
    string_fields = (
        'item_type', 'scope', 'duplex', 'x1', 'x2', 'y1', 'y2',
        'font_name', 'font_size', 'font_style', 'orientation', 'thickness', 'dashed',
        'text', 'file_columns', 'barcode_height', 'barcode_width',
        'line_distance', 'segment_id', 'tag', 'proportion', 'char_limit',
    )
    out = {}
    for key in string_fields:
        value = row.get(key)
        out[key] = '' if value is None else str(value)
    out['stack_order'] = int(row.get('stack_order') or 0)
    out['image'] = row.get('image')
    return out


def _drawings_equal(current: list, saved: list) -> bool:
    sort_key = lambda r: (
        r['stack_order'], r['item_type'], r['segment_id'], r['x1'], r['y1'], r['tag'],
    )
    a = sorted((_normalize_drawing_row(r) for r in current), key=sort_key)
    b = sorted((_normalize_drawing_row(r) for r in saved), key=sort_key)
    return a == b


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
    layout_config: Optional[str] = None,
) -> bool:
    product = db.search_product(client, product_name)
    if not product:
        return True

    if new_name != product_name or not _drawings_equal(current_drawings, saved_drawings):
        return True
    if color != product.paper_color:
        return True
    if orientation_index != int(product.orientation):
        return True
    saved_paper = get_product_paper_size(product)
    if paper_size != saved_paper:
        return True
    if orientation_index == CUSTOM_ORIENTATION_INDEX:
        saved_layout = getattr(product, 'layout_config', None) or ''
        current_layout = layout_config or ''
        if current_layout != saved_layout:
            return True
    return False

