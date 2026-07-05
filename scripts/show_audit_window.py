"""Abre a tela de Auditoria/Logs para captura de tela (dev/Linux)."""

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
from app.ui.config_window import AuditWindow
from app.ui.ttk_theme import apply_azure_dark_theme


class _MockMaster(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.withdraw()
        apply_azure_dark_theme(self)


def main():
    with open('config.json', encoding='utf-8') as f:
        config = json.load(f)
    runtime.init(config, DataBase(config['database_location']))
    init_i18n(config)

    ctk.set_appearance_mode('dark')
    master = _MockMaster()
    win = AuditWindow(master)
    win.lift()
    win.focus_force()
    master.mainloop()


if __name__ == '__main__':
    main()
