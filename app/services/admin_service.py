"""Acesso a dados de administração — UI não chama DataBase diretamente."""

from app import runtime


def get_db():
    return runtime.db


def list_client_names(name=''):
    return runtime.db.search_clients_names(name)


def list_products(client):
    return runtime.db.search_products(client)


def list_users():
    return runtime.db.users_list()


def delete_user(username):
    return runtime.db.delete_user(username)


def register_user(username, password, privileges='admin'):
    return runtime.db.register_user(username, password, privileges)


def verify_user(username, password):
    return runtime.db.verify_user(username, password)


def has_login():
    return runtime.db.has_login()


def list_printers():
    return runtime.db.search_printers()


def save_printers(printers_list):
    return runtime.db.save_printers(printers_list)


def list_print_groups():
    return runtime.db.search_print_group()


def insert_print_group(name):
    return runtime.db.insert_print_group(name)


def delete_print_group(name):
    return runtime.db.delete_print_group(name)


def delete_client(client):
    return runtime.db.delete_client(client)


def insert_client(name):
    return runtime.db.insert_client(name)


def search_product(client, product_name):
    return runtime.db.search_product(client, product_name)


def client_exists(client_name):
    return bool(runtime.db.search_clients_names(client_name))


def product_exists(client_name, product_name):
    return product_name in runtime.db.search_products(client_name)


# Aliases compatíveis com API legada de DataBase
search_clients_names = list_client_names
search_products = list_products
users_list = list_users
search_printers = list_printers
search_print_group = list_print_groups
