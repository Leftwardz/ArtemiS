"""Abre popups temáticos para captura de tela (dev/Linux)."""

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
from app.ui.theme import init_theme_from_config


class _MockMaster(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.withdraw()


def main():
    with open('config.json', encoding='utf-8') as f:
        config = json.load(f)
    init_theme_from_config(config)
    runtime.init(config, DataBase(config['database_location']))
    init_i18n(config)

    from app.ui.components.popup import ConfirmWindow, PopUpWindow

    ctk.set_appearance_mode('dark')
    master = _MockMaster()

    PopUpWindow(
        master,
        t('common.success'),
        t('designer.product_saved'),
    )

    def _noop():
        pass

    ConfirmWindow(
        master,
        t('common.confirm_title'),
        t('config.delete_client_confirm', client='Cliente Demo'),
        _noop,
        has_confirm=True,
    )

    master.mainloop()


if __name__ == '__main__':
    main()
