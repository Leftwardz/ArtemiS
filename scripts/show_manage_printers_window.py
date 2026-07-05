"""Abre Gerenciar Impressoras para captura de tela (dev/Linux)."""

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
from app.i18n import init_i18n
from app.models.database_manager import DataBase
from app.services import admin_service
from app.ui.config_window import EditRegisteredPrinterWindow, ManagePrintersWindow
from app.ui.ttk_theme import apply_azure_dark_theme


class _MockMaster(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.withdraw()
        apply_azure_dark_theme(self)


def _seed_demo_printers():
    demos = [
        ('\\\\srv\\HP-LaserJet', 'HP Produção', True, 'Setor expedição'),
        ('Microsoft Print to PDF', 'PDF Demo', False, ''),
    ]
    existing = {p['name'].lower() for p in admin_service.list_registered_printers()}
    for name, display, enabled, notes in demos:
        if name.lower() not in existing:
            admin_service.add_registered_printer(name, display, enabled, notes)


def main():
    with open('config.json', encoding='utf-8') as f:
        config = json.load(f)
    runtime.init(config, DataBase(config['database_location']))
    runtime.context.db.create_tables()
    init_i18n(config)
    _seed_demo_printers()

    ctk.set_appearance_mode('dark')
    master = _MockMaster()
    win = ManagePrintersWindow(master)
    win.lift()
    win.focus_force()

    edit = EditRegisteredPrinterWindow(
        master,
        on_save=lambda: None,
        printer={
            'name': '\\\\srv\\HP-LaserJet',
            'display_name': 'HP Produção',
            'enabled': True,
            'notes': 'Setor expedição',
            'id': 1,
        },
    )
    edit.lift()

    master.mainloop()


if __name__ == '__main__':
    main()
