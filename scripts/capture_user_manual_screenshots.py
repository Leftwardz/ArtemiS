"""Capture ArtemiS UI screenshots for user manuals (English UI).

Requires a running X display (e.g. DISPLAY=:1 on the Linux dev VM).
Writes PNG files to docs/user/assets/en/.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ASSETS = HERE / 'docs' / 'user' / 'assets' / 'en'
CONFIG_PATH = HERE / 'config.json'

sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / 'dev_stubs'))
os.chdir(HERE)

import tkinter as tkmod

tkmod.Wm.wm_iconbitmap = lambda self, *args, **kwargs: None
tkmod.Wm.iconbitmap = lambda self, *args, **kwargs: None

import customtkinter as ctk

ctk.CTk.iconbitmap = lambda self, *args, **kwargs: None
ctk.CTkToplevel.iconbitmap = lambda self, *args, **kwargs: None

from app import runtime
from app.i18n import init_i18n, set_language, t
from app.models.database_manager import DataBase
from app.services import admin_service
from app.ui.theme import init_theme_from_config
from app.ui.ttk_theme import apply_azure_dark_theme


def _load_config() -> dict:
    with open(CONFIG_PATH, encoding='utf-8') as f:
        return json.load(f)


def _save_config(config: dict) -> None:
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4)
        f.write('\n')


def _capture_window(widget, dest: Path, *, delay: float = 0.35) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    widget.update_idletasks()
    widget.update()
    time.sleep(delay)
    wid = widget.winfo_id()
    subprocess.run(
        ['import', '-window', str(wid), str(dest)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print(f'  saved {dest.relative_to(HERE)}')


def _seed_demo_data() -> None:
    if 'DEMO' not in admin_service.list_client_names():
        admin_service.insert_client('DEMO')
    if 'ProdutoAR' not in admin_service.list_products('DEMO'):
        admin_service.get_db().insert_product('ProdutoAR', 'DEMO', 'Verde', 0, 'A4')
    if not admin_service.list_print_groups():
        admin_service.insert_print_group('PADRAO')
    demos = [
        ('DEMO\\operator.one', 'user'),
        ('DEMO\\GRP-AR-ADMINS', 'group'),
    ]
    existing = {e['name'] for e in admin_service.list_config_access()}
    for name, ptype in demos:
        if name not in existing:
            admin_service.add_config_access(name, ptype)


def _prime_production_queue(app) -> None:
    app.work_queue.add('WO-2026-001', r'C:\AR\PADRAO\WO-2026-001.csv')
    app.work_queue.add('WO-2026-002', r'C:\AR\PADRAO\WO-2026-002.csv')
    app.show_color('Verde')
    app.btn_start.configure(state='normal')


class _MockEditorMaster(ctk.CTkFrame):
    def __init__(self, root, client: str, product: str):
        super().__init__(root)
        self.client_list = type('CL', (), {'radio_var': tkmod.StringVar(value=client)})()
        self.product_list = type('PL', (), {'radio_var': tkmod.StringVar(value=product)})()

    def refresh(self):
        pass


def capture_all() -> None:
    config = _load_config()
    config['language'] = 'en'
    _save_config(config)

    init_theme_from_config(config)
    runtime.init(config, DataBase(config['database_location']))
    runtime.context.db.create_tables()
    init_i18n(config)
    set_language('en')
    _seed_demo_data()

    ctk.set_appearance_mode('dark')
    ctk.set_default_color_theme('dark-blue')

    from app.ui.main_app import App
    from app.ui.config_window import ManageAccessWindow, ManageGroupWindow, ManagePrintersWindow
    from app.ui.designer_window import EditWindow
    from app.ui.remake_window import RemakeWindow

    print('Capturing screenshots…')
    app = App()
    apply_azure_dark_theme(app)
    app.update_idletasks()
    app.deiconify()
    app.lift()
    app.focus_force()

    _capture_window(app, ASSETS / 'production-main.png')

    _prime_production_queue(app)
    _capture_window(app, ASSETS / 'production-paper-color.png')

    app._nav_settings()
    app.update_idletasks()
    _capture_window(app, ASSETS / 'settings-overview.png')

    panel = app.config_panel
    if panel is not None and hasattr(panel, 'tabs'):
        panel.tabs.set(t('config.tab_general'))
        panel.update_idletasks()
        _capture_window(app, ASSETS / 'settings-general.png')

        panel.tabs.set(t('config.tab_printing'))
        panel.update_idletasks()
        _capture_window(app, ASSETS / 'settings-printing-tab.png')

    app._nav_production()
    app.update_idletasks()

    # Clients/products panel (settings, left side visible)
    app._nav_settings()
    app.update_idletasks()
    _capture_window(app, ASSETS / 'settings-clients-products.png')
    app._nav_production()

    # Remake window
    sample_csv = HERE / 'demo_remake.csv'
    sample_csv.write_text(
        'DEMO-ProdutoAR;AR10000001BR;MARIA SILVA SANTOS;WO98765;1\n'
        '1;AR10000001BR;MARIA SILVA SANTOS;extra;1\n'
        '2;AR10000002BR;JOAO SOUZA OLIVEIRA;extra;2\n'
        '3;AR10000003BR;ANA PAULA COSTA;extra;3\n',
        encoding='utf-8',
    )
    remake = RemakeWindow(app, str(sample_csv), 'WO98765', 'Verde', t('main.create_pdf'))
    remake.range_input.insert(0, '1-3')
    remake.search()
    remake.update_idletasks()
    remake.lift()
    _capture_window(remake, ASSETS / 'remake-window.png')
    remake.destroy()
    sample_csv.unlink(missing_ok=True)

    # Manage printers
    mp = ManagePrintersWindow(app)
    mp.update_idletasks()
    mp.lift()
    _capture_window(mp, ASSETS / 'settings-manage-printers.png')
    mp.destroy()

    # Manage groups
    mg = ManageGroupWindow(app, t('group.manage_title'))
    mg.update_idletasks()
    mg.lift()
    _capture_window(mg, ASSETS / 'settings-manage-groups.png')
    mg.destroy()

    # Manage access
    ma = ManageAccessWindow(app)
    ma.update_idletasks()
    ma.lift()
    _capture_window(ma, ASSETS / 'settings-manage-access.png')
    ma.destroy()

    # Template editor
    editor_root = ctk.CTk()
    editor_root.withdraw()
    editor_master = _MockEditorMaster(editor_root, 'DEMO', 'ProdutoAR')
    editor = EditWindow(editor_master, 'edit')
    editor.geometry('1280x800')
    editor.update_idletasks()
    editor.lift()
    _capture_window(editor, ASSETS / 'template-editor.png')
    editor.destroy()
    editor_root.destroy()

    app.destroy()
    print('Done.')


if __name__ == '__main__':
    capture_all()
