"""Abre a tela de Remake para captura de tela (dev/Linux)."""

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
from app.i18n import init_i18n, pdf_mode_label
from app.models.database_manager import DataBase
from app.ui.theme import init_theme_from_config
from app.ui.ttk_theme import apply_azure_dark_theme


class _MockMaster(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.withdraw()
        apply_azure_dark_theme(self)

    @staticmethod
    def _printer_combo_values():
        return [pdf_mode_label(), 'Impressora Demo']

    def create_pdf(self, *args, **kwargs):
        pass

    def clean_worklist(self):
        pass

    def refresh(self):
        pass

    def focus_set(self):
        pass

    def deiconify(self):
        pass


def main():
    with open('config.json', encoding='utf-8') as f:
        config = json.load(f)
    init_theme_from_config(config)
    runtime.init(config, DataBase(config['database_location']))
    runtime.context.db.create_tables()
    init_i18n(config)

    from app.ui.remake_window import RemakeWindow

    sample = os.path.join(HERE, 'demo_remake.csv')
    with open(sample, 'w', encoding='utf-8') as f:
        f.write('DEMO-ProdutoAR;AR10000001BR;MARIA SILVA SANTOS;WO98765;1\n')
        f.write('1;AR10000001BR;MARIA SILVA SANTOS;extra;1\n')
        f.write('2;AR10000002BR;JOAO SOUZA OLIVEIRA;extra;2\n')
        f.write('3;AR10000003BR;ANA PAULA COSTA;extra;3\n')

    ctk.set_appearance_mode('dark')
    master = _MockMaster()
    win = RemakeWindow(master, sample, 'WO98765', 'Branco', pdf_mode_label())
    win.range_input.insert(0, '1-3')
    win.search()
    win.lift()
    win.focus_force()
    master.mainloop()


if __name__ == '__main__':
    main()
