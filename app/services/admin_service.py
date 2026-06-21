"""Acesso a dados de administração — UI não chama DataBase diretamente."""

from app import audit, runtime
from app.utils import windows_auth
from app.utils.printer_handler import enumerate_installed_printers, printer_is_available


def get_db():
    return runtime.context.db


def list_client_names(name=''):
    return runtime.context.db.search_clients_names(name)


def list_products(client):
    return runtime.context.db.search_products(client)


def list_config_access():
    return runtime.context.db.list_config_access()


def add_config_access(principal_name, principal_type):
    result = runtime.context.db.insert_config_access(principal_name, principal_type)
    if result:
        audit.log_cadastro('access_add', detail=f'{principal_type}: {principal_name}')
    return result


def delete_config_access(principal_name):
    result = runtime.context.db.delete_config_access(principal_name)
    if result:
        audit.log_cadastro('access_delete', detail=principal_name)
    return result


def can_access_config():
    allowed = list_config_access()
    return windows_auth.can_access_config(allowed)


def get_current_windows_user():
    return windows_auth.get_current_principal()


def is_windows_admin():
    return windows_auth.is_windows_admin()


def search_windows_principals(query, principal_type='both'):
    return windows_auth.search_principals(query, principal_type)


def resolve_windows_principal(text):
    return windows_auth.resolve_manual_principal(text)


def list_registered_printers(enabled_only=False):
    return runtime.context.db.list_registered_printers(enabled_only=enabled_only)


def add_registered_printer(name, display_name, enabled=True, notes=''):
    result = runtime.context.db.insert_registered_printer(name, display_name, enabled, notes)
    if result:
        audit.log_cadastro('printer_add', detail=f'{display_name} ({name})', printer=name)
    return result


def update_registered_printer(printer_id, name, display_name, enabled, notes):
    current = next(
        (p for p in list_registered_printers() if p.get('id') == printer_id),
        None,
    )
    result = runtime.context.db.update_registered_printer(
        printer_id, name, display_name, enabled, notes,
    )
    changed = bool(result) and (
        current is None
        or current.get('name') != name
        or current.get('display_name') != (display_name or name)
        or bool(current.get('enabled')) != bool(enabled)
        or (current.get('notes') or '') != (notes or '')
    )
    if changed:
        audit.log_cadastro(
            'printer_update',
            detail=f'#{printer_id} {display_name} ({name}) enabled={enabled}',
            printer=name,
        )
    return result


def delete_registered_printer(printer_id):
    result = runtime.context.db.delete_registered_printer(printer_id)
    if result:
        audit.log_cadastro('printer_delete', detail=f'#{printer_id}')
    return result


def discover_installed_printers():
    return enumerate_installed_printers()


def verify_printer_available(name):
    return printer_is_available(name)


def get_printer_combo_options():
    """
    Retorna (labels para combo, mapa label → nome Windows).
    Labels usam display_name; nomes duplicados recebem sufixo.
    """
    entries = list_registered_printers(enabled_only=True)
    name_by_label = {}
    labels = []
    label_count = {}

    for entry in entries:
        base = (entry['display_name'] or entry['name']).strip()
        count = label_count.get(base, 0) + 1
        label_count[base] = count
        label = base if count == 1 else f'{base} ({count})'
        name_by_label[label] = entry['name']
        labels.append(label)

    return labels, name_by_label


def resolve_printer_name(combo_label):
    if combo_label == 'Criar PDF':
        return combo_label
    _labels, name_by_label = get_printer_combo_options()
    return name_by_label.get(combo_label, combo_label)


def list_print_groups():
    return runtime.context.db.search_print_group()


def insert_print_group(name):
    result = runtime.context.db.insert_print_group(name)
    audit.log_cadastro('print_group_add', detail=name)
    return result


def delete_print_group(name):
    result = runtime.context.db.delete_print_group(name)
    audit.log_cadastro('print_group_delete', detail=name)
    return result


def delete_client(client):
    result = runtime.context.db.delete_client(client)
    if result:
        audit.log_cadastro('client_delete', detail=client)
    return result


def insert_client(name):
    result = runtime.context.db.insert_client(name)
    audit.log_cadastro('client_add', detail=name)
    return result


def search_product(client, product_name):
    return runtime.context.db.search_product(client, product_name)


def client_exists(client_name):
    return bool(runtime.context.db.search_clients_names(client_name))


def product_exists(client_name, product_name):
    return product_name in runtime.context.db.search_products(client_name)
