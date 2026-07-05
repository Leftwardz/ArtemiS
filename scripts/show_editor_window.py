"""Abre o editor de produto para captura de tela (dev/Linux)."""

import json
import os
import sys
import tkinter as tk

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
from app.models.sheet_layout import CUSTOM_ORIENTATION_INDEX
from app.i18n.designer_labels import orientation_labels
from app.ui.designer_window import EditWindow


class _MockList:
  def __init__(self, value: str):
    self.radio_var = tk.StringVar(value=value)


def main():
  with open('config.json', encoding='utf-8') as f:
    config = json.load(f)
  runtime.init(config, DataBase(config['database_location']))
  runtime.context.db.create_tables()
  init_i18n(config)

  db = runtime.context.db
  if not db.search_clients():
    db.insert_client('DEMO')

  ctk.set_appearance_mode('dark')
  root = ctk.CTk()
  root.withdraw()

  master = ctk.CTkFrame(root)
  master.client_list = _MockList('DEMO')
  master.product_list = _MockList('Novo Produto')
  master.refresh = lambda: None

  editor = EditWindow(master, 'add')
  editor.title('ArtemiS — Editor de Produto')
  editor.combobox_type.set(orientation_labels()[CUSTOM_ORIENTATION_INDEX])
  editor.change_orientation(None)
  editor.geometry('1280x800')
  editor.lift()
  editor.focus_force()
  root.mainloop()


if __name__ == '__main__':
  main()
