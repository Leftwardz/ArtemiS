"""Abre dialogs de cliente/produto para captura de tela (dev/Linux)."""

import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'dev_stubs'))
os.chdir(HERE)

import tkinter as tkmod

tkmod.Wm.wm_iconbitmap = lambda self, *args, **kwargs: None
tkmod.Wm.iconbitmap = lambda self, *args, **kwargs: None

import customtkinter as ctk

ctk.CTk.iconbitmap = lambda self, *args, **kwargs: None
ctk.CTkToplevel.iconbitmap = lambda self, *args, **kwargs: None

from app import runtime
from app.i18n import init_i18n, t
from app.models.database_manager import DataBase
from app.services import admin_service
from app.ui.config_window import AddClientWindow, DuplicateProductWindow, ExportProductWindow
from app.ui.ttk_theme import apply_azure_dark_theme


class _MockMaster(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.withdraw()
        apply_azure_dark_theme(self)
        self.client_list = type('CL', (), {'radio_var': tkmod.StringVar(value='DEMO'), 'focus': lambda: None})()
        self.product_list = type('PL', (), {'radio_var': tkmod.StringVar(), 'focus': lambda: None})()

    def refresh(self):
        pass

    def update_client_list(self):
        pass


def _seed_demo_data():
    if 'DEMO' not in admin_service.list_client_names():
        admin_service.insert_client('DEMO')
    products = admin_service.list_products('DEMO')
    if 'ProdutoAR' not in products:
        admin_service.get_db().insert_product('ProdutoAR', 'DEMO', 'Branco', 0, 'A4')


def main():
    with open('config.json', encoding='utf-8') as f:
        config = json.load(f)
    runtime.init(config, DataBase(config['database_location']))
    runtime.context.db.create_tables()
    init_i18n(config)
    _seed_demo_data()

    ctk.set_appearance_mode('dark')
    master = _MockMaster()

    AddClientWindow(master, t('config.client_name_prompt'), lambda: None)

    DuplicateProductWindow(
        master, t('config.duplicate_product_title'), 'DEMO', 'ProdutoAR',
    )

    ExportProductWindow(master)

    master.mainloop()


if __name__ == '__main__':
    main()
