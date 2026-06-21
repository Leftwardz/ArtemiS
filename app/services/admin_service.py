"""Acesso a dados de administração — UI não chama DataBase diretamente."""

from app import runtime


def get_db():
    return runtime.context.db


def list_client_names(name=''):
    return runtime.context.db.search_clients_names(name)


def list_products(client):
    return runtime.context.db.search_products(client)


def list_users():
    return runtime.context.db.users_list()


def delete_user(username):
    return runtime.context.db.delete_user(username)


def register_user(username, password, privileges='admin'):
    return runtime.context.db.register_user(username, password, privileges)


def verify_user(username, password):
    return runtime.context.db.verify_user(username, password)


def has_login():
    return runtime.context.db.has_login()


def list_printers():
    return runtime.context.db.search_printers()


def save_printers(printers_list):
    return runtime.context.db.save_printers(printers_list)


def list_print_groups():
    return runtime.context.db.search_print_group()


def insert_print_group(name):
    return runtime.context.db.insert_print_group(name)


def delete_print_group(name):
    return runtime.context.db.delete_print_group(name)


def delete_client(client):
    return runtime.context.db.delete_client(client)


def insert_client(name):
    return runtime.context.db.insert_client(name)


def search_product(client, product_name):
    return runtime.context.db.search_product(client, product_name)


def client_exists(client_name):
    return bool(runtime.context.db.search_clients_names(client_name))


def product_exists(client_name, product_name):
    return product_name in runtime.context.db.search_products(client_name)
