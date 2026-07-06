import json
import os
import textwrap
import traceback
from threading import Thread

import customtkinter as ctk
from tkinter import ttk
from tkinter.filedialog import askdirectory, askopenfilename, asksaveasfilename

from app import audit
from app.i18n import available_languages, get_i18n, t
from app.services import admin_service
from app.services.settings_service import (
    get_audit_central_location,
    get_database_location,
    get_language,
    get_locales_folder,
    get_print_backend_label,
    get_search_folder,
    get_ui_theme,
    save_audit_central_location,
    save_database_location,
    save_language,
    save_locales_folder,
    save_print_backend,
    save_search_folder,
    save_ui_theme,
    PRINT_BACKEND_LABELS,
)
from app.services.designer_service import (
    build_export_payload,
    duplicate_product as designer_duplicate_product,
    import_product_for_existing_client,
    import_product_with_new_client,
    parse_import_file,
    replace_imported_drawings,
)
from app.services.layout_service import resolve_product_paper_size
from app.ui.components import ConfirmWindow, ListBox, PopUpWindow, Table
from app.ui.constants import (
    BTN_HOVER_RED,
    BTN_RED,
    CONFIG_HEIGHT,
    CONFIG_WIDTH,
    FONT,
    ICON,
    THEME_ACCENT,
    THEME_ACCENT_HOVER,
    THEME_BG,
    THEME_CARD,
    THEME_CARD_BORDER,
    THEME_ERROR_TEXT,
    THEME_NAV_ACTIVE,
    THEME_NAV_TEXT_ACCENT,
    THEME_TABLE_ROW_A,
    THEME_TABLE_ROW_B,
    THEME_TEXT_SECONDARY,
)
from app.ui.designer_window import EditWindow
from app.ui.theme import available_theme_ids
from app.utils.window_geometry import calculate_center_screen_with_monitor, get_monitor


def _entry_kwargs(**extra):
    return dict(
        fg_color=THEME_BG, border_color=THEME_CARD_BORDER,
        border_width=2, corner_radius=8, height=32,
        text_color='white', placeholder_text_color=THEME_TEXT_SECONDARY,
        **extra,
    )


def _combo_kwargs(**extra):
    return dict(
        fg_color=THEME_BG, border_color=THEME_CARD_BORDER,
        button_color=THEME_ACCENT, button_hover_color=THEME_ACCENT_HOVER,
        height=32, **extra,
    )


def _secondary_btn_kwargs(**extra):
    return dict(
        fg_color=THEME_NAV_ACTIVE, hover_color=THEME_CARD_BORDER,
        border_width=1, border_color=THEME_CARD_BORDER,
        corner_radius=8, height=32, **extra,
    )


def _section_card(parent, title: str):
    card = ctk.CTkFrame(
        parent, fg_color=THEME_CARD, corner_radius=12,
        border_width=1, border_color=THEME_CARD_BORDER,
    )
    ctk.CTkLabel(
        card, text=title, font=(FONT, 13, 'bold'), text_color='white', anchor='w',
    ).pack(fill='x', padx=12, pady=(10, 6))
    body = ctk.CTkFrame(card, fg_color='transparent')
    body.pack(fill='x', padx=12, pady=(0, 12))
    return card, body


def _table_host(parent, height: int):
    host = ctk.CTkFrame(
        parent, fg_color=THEME_BG, corner_radius=8,
        border_width=1, border_color=THEME_CARD_BORDER, height=height,
    )
    host.pack_propagate(False)
    host.grid_propagate(False)
    return host


def _build_dialog_header(parent, title: str, subtitle: str):
    header = ctk.CTkFrame(parent, fg_color=THEME_CARD, corner_radius=0, height=56)
    header.grid(row=0, column=0, sticky='ew')
    header.grid_propagate(False)
    title_col = ctk.CTkFrame(header, fg_color='transparent')
    title_col.pack(side='left', padx=16, pady=10)
    ctk.CTkLabel(
        title_col, text=title, font=(FONT, 15, 'bold'), text_color='white',
    ).pack(anchor='w')
    ctk.CTkLabel(
        title_col, text=subtitle, font=(FONT, 11), text_color=THEME_TEXT_SECONDARY,
    ).pack(anchor='w')


def _dialog_action_row(parent, window, ok_text: str, ok_command, ok_kwargs=None):
    actions = ctk.CTkFrame(parent, fg_color='transparent')
    actions.pack(fill='x', pady=(10, 0))
    actions.grid_columnconfigure(0, weight=1)
    actions.grid_columnconfigure(1, weight=1)
    ok_opts = dict(
        width=110, fg_color=THEME_ACCENT, hover_color=THEME_ACCENT_HOVER,
        corner_radius=8, height=32, command=ok_command,
    )
    if ok_kwargs:
        ok_opts.update(ok_kwargs)
    btn_ok = ctk.CTkButton(actions, text=ok_text, **ok_opts)
    btn_ok.grid(row=0, column=0, padx=(0, 6), sticky='e')
    ctk.CTkButton(
        actions, text=t('common.cancel'), width=110,
        fg_color=BTN_RED, hover_color=BTN_HOVER_RED,
        corner_radius=8, height=32, command=window.destroy,
    ).grid(row=0, column=1, padx=(6, 0), sticky='w')
    return btn_ok


class ConfigPanel(ctk.CTkFrame):
    def __init__(self, parent, app, *args, **kwargs):
        super().__init__(parent, fg_color=THEME_BG, *args, **kwargs)
        self.app = app
        self.grid_columnconfigure(0, weight=3, minsize=380)
        self.grid_columnconfigure(1, weight=4, minsize=480)
        self.grid_rowconfigure(0, weight=1)

        self.edit_window = None
        self.btn_edit = None
        self.btn_duplicate = None
        self.btn_delete_client = None
        self.btn_add_product = None
        self.btn_edit_product = None
        self._search_query = ''
        self._i18n_labels: list[tuple] = []
        self._i18n_buttons: list[tuple] = []
        self._tab_keys: list[str] = []

        self._build_left_panel()
        self._build_settings_tabs()

        self.inpt_db_location.bind('<KeyRelease>', self.update_save_button)
        self.inpt_search_folder.bind('<KeyRelease>', self.update_save_button)
        self.inpt_db_location.bind('<Return>', self.save_database_location)
        self.inpt_search_folder.bind('<Return>', self.save_folder)

        self._apply_search_filter()
        self.bind('<Map>', self._on_panel_mapped, add='+')

    def refresh_production_combos(self):
        """Propaga atualização dos combos da tela de produção."""
        if self.app is not None:
            self.app.refresh_production_combos()

    def refresh_layout(self):
        """Recalcula geometria após a view de configurações ficar visível."""
        self.update_idletasks()
        tabs = getattr(self, 'tabs', None)
        if tabs is None:
            return
        tab_frames = list(getattr(tabs, '_tab_dict', {}).values())
        if not tab_frames:
            tab_frames = [tabs.tab(name) for name in getattr(tabs, '_name_list', [])]
        for tab in tab_frames:
            tab.update_idletasks()
            for child in tab.winfo_children():
                child.update_idletasks()
                canvas = getattr(child, '_parent_canvas', None)
                if canvas is not None:
                    try:
                        canvas.configure(scrollregion=canvas.bbox('all'))
                    except Exception:
                        pass

    def _on_panel_mapped(self, _event=None):
        if getattr(self, '_restoring_from_editor', False):
            self._restoring_from_editor = False
            return
        self.after_idle(self.refresh_layout)

    def deiconify(self):
        """Restaura o app após fechar o editor (compatível com EditWindow)."""
        self._restoring_from_editor = True
        self.app.deiconify()
        self.app.focus_set()

    def exit(self):
        """Volta à produção (ex.: após salvar database)."""
        self.app._set_active_view('production')
        self.app.focus_set()
        self.app.refresh()

    def _register_label(self, widget, key: str, *, formatter=None):
        self._i18n_labels.append((widget, key, formatter))

    def _register_button(self, widget, key: str, *, prefix: str = ''):
        self._i18n_buttons.append((widget, key, prefix))

    def _settings_card(self, parent, title_key: str):
        card = ctk.CTkFrame(
            parent, fg_color=THEME_CARD, corner_radius=12,
            border_width=1, border_color=THEME_CARD_BORDER,
        )
        title_lbl = ctk.CTkLabel(
            card, text=t(title_key), font=(FONT, 15, 'bold'), text_color='white', anchor='w',
        )
        title_lbl.pack(fill='x', padx=16, pady=(12, 8))
        self._register_label(title_lbl, title_key)
        body = ctk.CTkFrame(card, fg_color='transparent')
        body.pack(fill='x', padx=16, pady=(0, 14))
        return card, body

    def _build_left_panel(self):
        left = ctk.CTkFrame(self, fg_color='transparent')
        left.grid(row=0, column=0, sticky='nsew', padx=(16, 8), pady=(12, 16))

        card, body = self._settings_card(left, 'config.clients_products')
        card.pack(fill='both', expand=True)

        self.entry_search = ctk.CTkEntry(
            body, placeholder_text=t('config.search_placeholder'), **_entry_kwargs(),
        )
        self.entry_search.pack(fill='x', pady=(0, 6))
        self.entry_search.bind('<KeyRelease>', self._on_search_changed)

        self.lbl_search_count = ctk.CTkLabel(
            body, text='', font=(FONT, 10), text_color=THEME_TEXT_SECONDARY, anchor='w',
        )
        self.lbl_search_count.pack(fill='x', pady=(0, 8))

        lists_row = ctk.CTkFrame(body, fg_color='transparent')
        lists_row.pack(fill='both', expand=True)
        lists_row.grid_columnconfigure(0, weight=1)
        lists_row.grid_columnconfigure(1, weight=1)
        lists_row.grid_rowconfigure(1, weight=1)

        self.lbl_clients_header = ctk.CTkLabel(
            lists_row, text=t('config.clients'), font=(FONT, 11, 'bold'),
            text_color=THEME_TEXT_SECONDARY, anchor='w',
        )
        self.lbl_clients_header.grid(row=0, column=0, sticky='w', padx=(0, 4))
        self._register_label(self.lbl_clients_header, 'config.clients')
        self.lbl_products_header = ctk.CTkLabel(
            lists_row, text=t('config.products'), font=(FONT, 11, 'bold'),
            text_color=THEME_TEXT_SECONDARY, anchor='w',
        )
        self.lbl_products_header.grid(row=0, column=1, sticky='w', padx=(4, 0))
        self._register_label(self.lbl_products_header, 'config.products')

        self.clients_list_host = ctk.CTkFrame(
            lists_row, fg_color=THEME_BG, corner_radius=8,
            border_width=1, border_color=THEME_CARD_BORDER,
        )
        self.clients_list_host.grid(row=1, column=0, sticky='nsew', padx=(0, 4), pady=(4, 0))
        self.products_list_host = ctk.CTkFrame(
            lists_row, fg_color=THEME_BG, corner_radius=8,
            border_width=1, border_color=THEME_CARD_BORDER,
        )
        self.products_list_host.grid(row=1, column=1, sticky='nsew', padx=(4, 0), pady=(4, 0))

        self.actions_frame = ctk.CTkFrame(body, fg_color='transparent')
        self.actions_frame.pack(fill='x', pady=(12, 0))
        self.actions_frame.grid_columnconfigure(0, weight=1)
        self.actions_frame.grid_columnconfigure(1, weight=1)

        self.client_actions = ctk.CTkFrame(self.actions_frame, fg_color='transparent')
        self.client_actions.grid(row=0, column=0, sticky='nsew', padx=(0, 4))

        self.product_actions = ctk.CTkFrame(self.actions_frame, fg_color='transparent')
        self.product_actions.grid(row=0, column=1, sticky='nsew', padx=(4, 0))

        self.btn_add_client = ctk.CTkButton(
            self.client_actions, text=f'+ {t("config.add_client")}', height=30, corner_radius=8,
            fg_color=THEME_NAV_ACTIVE, hover_color=THEME_CARD_BORDER,
            border_width=1, border_color=THEME_CARD_BORDER,
            command=self.create_client,
        )
        self.btn_add_client.pack(fill='x', pady=(0, 4))
        self._register_button(self.btn_add_client, 'config.add_client', prefix='+ ')

    def _build_settings_tabs(self):
        right = ctk.CTkFrame(self, fg_color='transparent')
        right.grid(row=0, column=1, sticky='nsew', padx=(8, 16), pady=(12, 16))

        self.tabs = ctk.CTkTabview(
            right,
            fg_color=THEME_CARD,
            border_width=1,
            border_color=THEME_CARD_BORDER,
            corner_radius=12,
            segmented_button_fg_color=THEME_BG,
            segmented_button_selected_color=THEME_NAV_ACTIVE,
            segmented_button_selected_hover_color=THEME_NAV_ACTIVE,
            segmented_button_unselected_color=THEME_CARD,
            segmented_button_unselected_hover_color=THEME_NAV_ACTIVE,
            text_color=THEME_TEXT_SECONDARY,
        )
        self.tabs.pack(fill='both', expand=True)

        self._tab_keys = [
            'config.tab_general',
            'config.tab_printing',
            'config.tab_access',
            'config.tab_language',
        ]
        tab_general = self.tabs.add(t(self._tab_keys[0]))
        tab_printing = self.tabs.add(t(self._tab_keys[1]))
        tab_access = self.tabs.add(t(self._tab_keys[2]))
        tab_language = self.tabs.add(t(self._tab_keys[3]))

        for tab in (tab_general, tab_printing, tab_access, tab_language):
            tab.configure(fg_color='transparent')

        self._build_tab_general(tab_general)
        self._build_tab_printing(tab_printing)
        self._build_tab_access(tab_access)
        self._build_tab_language(tab_language)

    def _tab_scroll(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color='transparent')
        scroll.pack(fill='both', expand=True, padx=4, pady=4)
        return scroll

    def _build_tab_general(self, parent):
        scroll = self._tab_scroll(parent)

        card_files, body_files = self._settings_card(scroll, 'config.card_files')
        card_files.pack(fill='x', pady=(0, 10))

        self.lbl_search_folder = ctk.CTkLabel(
            body_files, text=t('config.search_folder'), anchor='w', text_color=THEME_TEXT_SECONDARY,
        )
        self.lbl_search_folder.pack(fill='x')
        self._register_label(self.lbl_search_folder, 'config.search_folder')
        row_sf = ctk.CTkFrame(body_files, fg_color='transparent')
        row_sf.pack(fill='x', pady=(4, 10))
        self.inpt_search_folder = ctk.CTkEntry(row_sf, **_entry_kwargs())
        self.inpt_search_folder.pack(side='left', fill='x', expand=True, padx=(0, 8))
        self.btn_save_folder = ctk.CTkButton(
            row_sf, text=t('config.save'), width=80, height=32, corner_radius=8,
            fg_color=THEME_ACCENT, hover_color=THEME_ACCENT_HOVER,
            state='disabled', command=self.save_folder,
        )
        self.btn_save_folder.pack(side='left')
        self._register_button(self.btn_save_folder, 'config.save')
        search_folder = get_search_folder()
        if search_folder:
            self.inpt_search_folder.insert(0, search_folder)
        self.lbl_search_folder_hint = ctk.CTkLabel(
            body_files, text=t('config.search_folder_hint'), font=(FONT, 10),
            text_color=THEME_TEXT_SECONDARY, justify='left', wraplength=520, anchor='w',
        )
        self.lbl_search_folder_hint.pack(fill='x', pady=(0, 10))
        self._register_label(self.lbl_search_folder_hint, 'config.search_folder_hint')

        self.lbl_database = ctk.CTkLabel(
            body_files, text=t('config.database'), anchor='w', text_color=THEME_TEXT_SECONDARY,
        )
        self.lbl_database.pack(fill='x')
        self._register_label(self.lbl_database, 'config.database')
        row_db = ctk.CTkFrame(body_files, fg_color='transparent')
        row_db.pack(fill='x', pady=(4, 0))
        self.inpt_db_location = ctk.CTkEntry(row_db, **_entry_kwargs())
        self.inpt_db_location.pack(side='left', fill='x', expand=True, padx=(0, 8))
        self.btn_save_db = ctk.CTkButton(
            row_db, text=t('config.save'), width=80, height=32, corner_radius=8,
            fg_color=THEME_ACCENT, hover_color=THEME_ACCENT_HOVER,
            state='disabled', command=self.save_database_location,
        )
        self.btn_save_db.pack(side='left')
        self._register_button(self.btn_save_db, 'config.save')
        database_location = get_database_location()
        if database_location:
            self.inpt_db_location.insert(0, database_location)

        card_audit, body_audit = self._settings_card(scroll, 'config.card_audit')
        card_audit.pack(fill='x', pady=(0, 10))
        self.lbl_audit_db = ctk.CTkLabel(
            body_audit, text=t('config.audit_db'), anchor='w', text_color=THEME_TEXT_SECONDARY,
        )
        self.lbl_audit_db.pack(fill='x')
        self._register_label(self.lbl_audit_db, 'config.audit_db')
        row_au = ctk.CTkFrame(body_audit, fg_color='transparent')
        row_au.pack(fill='x', pady=(4, 6))
        self.inpt_audit_location = ctk.CTkEntry(
            row_au,
            placeholder_text=t('config.audit_db_placeholder'),
            **_entry_kwargs(),
        )
        self.inpt_audit_location.pack(side='left', fill='x', expand=True, padx=(0, 8))
        self.btn_save_audit_location = ctk.CTkButton(
            row_au, text=t('config.save'), width=80, height=32, corner_radius=8,
            fg_color=THEME_ACCENT, hover_color=THEME_ACCENT_HOVER,
            command=self.save_audit_location,
        )
        self.btn_save_audit_location.pack(side='left')
        self._register_button(self.btn_save_audit_location, 'config.save')
        audit_location = get_audit_central_location()
        if audit_location:
            self.inpt_audit_location.insert(0, audit_location)
        self.lbl_audit_hint = ctk.CTkLabel(
            body_audit, text=t('config.audit_hint'), font=(FONT, 10),
            text_color=THEME_TEXT_SECONDARY, justify='left', anchor='w', wraplength=520,
        )
        self.lbl_audit_hint.pack(fill='x', pady=(0, 8))
        self._register_label(self.lbl_audit_hint, 'config.audit_hint')
        self.btn_audit_logs = ctk.CTkButton(
            body_audit, text=t('config.audit_logs'), width=160, height=32, corner_radius=8,
            fg_color=THEME_NAV_ACTIVE, hover_color=THEME_CARD_BORDER,
            border_width=1, border_color=THEME_CARD_BORDER,
            command=lambda: AuditWindow(self),
        )
        self.btn_audit_logs.pack(anchor='w')
        self._register_button(self.btn_audit_logs, 'config.audit_logs')

        card_ie, body_ie = self._settings_card(scroll, 'config.card_import_export')
        card_ie.pack(fill='x', pady=(0, 10))
        btns = ctk.CTkFrame(body_ie, fg_color='transparent')
        btns.pack(fill='x')
        self.btn_import = ctk.CTkButton(
            btns, text=t('config.import'), width=120, height=32, corner_radius=8,
            fg_color=THEME_NAV_ACTIVE, hover_color=THEME_CARD_BORDER,
            border_width=1, border_color=THEME_CARD_BORDER,
            command=self.import_product,
        )
        self.btn_import.pack(side='left', padx=(0, 8))
        self._register_button(self.btn_import, 'config.import')
        self.btn_export = ctk.CTkButton(
            btns, text=t('config.export'), width=120, height=32, corner_radius=8,
            fg_color=THEME_NAV_ACTIVE, hover_color=THEME_CARD_BORDER,
            border_width=1, border_color=THEME_CARD_BORDER,
            command=lambda: ExportProductWindow(self),
        )
        self.btn_export.pack(side='left')
        self._register_button(self.btn_export, 'config.export')

    def _build_tab_printing(self, parent):
        scroll = self._tab_scroll(parent)

        card, body = self._settings_card(scroll, 'config.printers')
        card.pack(fill='x', pady=(0, 10))
        count = len(admin_service.list_registered_printers())
        self.lbl_printers_count = ctk.CTkLabel(
            body, text=t('config.printers_count', count=count),
            font=(FONT, 11), text_color=THEME_TEXT_SECONDARY, anchor='w',
        )
        self.lbl_printers_count.pack(fill='x', pady=(0, 8))
        self._register_label(
            self.lbl_printers_count, 'config.printers_count',
            formatter=lambda: {'count': len(admin_service.list_registered_printers())},
        )
        self.btn_manage_printers = ctk.CTkButton(
            body, text=t('config.manage_printers'), width=180, height=32, corner_radius=8,
            fg_color=THEME_NAV_ACTIVE, hover_color=THEME_CARD_BORDER,
            border_width=1, border_color=THEME_CARD_BORDER,
            command=lambda: ManagePrintersWindow(self),
        )
        self.btn_manage_printers.pack(anchor='w')
        self._register_button(self.btn_manage_printers, 'config.manage_printers')

        card_be, body_be = self._settings_card(scroll, 'config.print_backend')
        card_be.pack(fill='x', pady=(0, 10))
        backend_values = self._available_backend_labels()
        self.combo_print_backend = ctk.CTkComboBox(body_be, width=280, values=backend_values, **_combo_kwargs())
        self.combo_print_backend.pack(anchor='w', pady=(0, 6))
        self.combo_print_backend.set(get_print_backend_label())
        self.lbl_print_backend_hint = ctk.CTkLabel(
            body_be, text=t('config.print_backend_hint'), font=(FONT, 10),
            text_color=THEME_TEXT_SECONDARY, justify='left', wraplength=420, anchor='w',
        )
        self.lbl_print_backend_hint.pack(fill='x', pady=(0, 4))
        self._register_label(self.lbl_print_backend_hint, 'config.print_backend_hint')
        self.lbl_ghostscript_status = ctk.CTkLabel(
            body_be, text='', font=(FONT, 10),
            text_color=THEME_TEXT_SECONDARY, justify='left', wraplength=420, anchor='w',
        )
        self.lbl_ghostscript_status.pack(fill='x', pady=(0, 8))
        self._refresh_ghostscript_status()
        self.btn_save_print_backend = ctk.CTkButton(
            body_be, text=t('config.save_backend'), width=140, height=32, corner_radius=8,
            fg_color=THEME_ACCENT, hover_color=THEME_ACCENT_HOVER,
            command=self.save_print_backend,
        )
        self.btn_save_print_backend.pack(anchor='w')
        self._register_button(self.btn_save_print_backend, 'config.save_backend')

        card_gr, body_gr = self._settings_card(scroll, 'config.print_groups')
        card_gr.pack(fill='x')
        self.btn_manage_groups = ctk.CTkButton(
            body_gr, text=t('config.manage_groups_btn'), width=180, height=32, corner_radius=8,
            fg_color=THEME_NAV_ACTIVE, hover_color=THEME_CARD_BORDER,
            border_width=1, border_color=THEME_CARD_BORDER,
            command=lambda: ManageGroupWindow(self, t('group.manage_title')),
        )
        self.btn_manage_groups.pack(anchor='w')
        self._register_button(self.btn_manage_groups, 'config.manage_groups_btn')
        self.lbl_print_groups_hint = ctk.CTkLabel(
            body_gr, text=t('config.print_groups_hint'), font=(FONT, 10),
            text_color=THEME_TEXT_SECONDARY, justify='left', wraplength=420, anchor='w',
        )
        self.lbl_print_groups_hint.pack(fill='x', pady=(8, 0))
        self._register_label(self.lbl_print_groups_hint, 'config.print_groups_hint')

    def _build_tab_access(self, parent):
        scroll = self._tab_scroll(parent)

        card, body = self._settings_card(scroll, 'config.config_access')
        card.pack(fill='x')

        self.var_block_config = ctk.BooleanVar(
            value=admin_service.is_config_access_blocked(),
        )
        self.chk_block_config = ctk.CTkCheckBox(
            body,
            text=t('config.block_config_access'),
            variable=self.var_block_config,
            command=self._on_block_config_changed,
            fg_color=THEME_ACCENT,
            hover_color=THEME_ACCENT_HOVER,
            border_color=THEME_CARD_BORDER,
            text_color='white',
        )
        self.chk_block_config.pack(fill='x', pady=(0, 6))
        self._register_label(self.chk_block_config, 'config.block_config_access')

        self.lbl_access_mode = ctk.CTkLabel(
            body, text='', font=(FONT, 11),
            text_color=THEME_TEXT_SECONDARY, justify='left', anchor='w',
        )
        self.lbl_access_mode.pack(fill='x', pady=(0, 8))
        self._update_access_mode_labels()

        self.lbl_admin_always_access = ctk.CTkLabel(
            body, text=t('config.admin_always_access'),
            font=(FONT, 11), text_color=THEME_TEXT_SECONDARY, justify='left', anchor='w',
        )
        self.lbl_admin_always_access.pack(fill='x', pady=(0, 10))
        self._register_label(self.lbl_admin_always_access, 'config.admin_always_access')
        self.btn_manage_access = ctk.CTkButton(
            body, text=t('config.manage_access'), width=180, height=32, corner_radius=8,
            fg_color=THEME_ACCENT, hover_color=THEME_ACCENT_HOVER,
            command=lambda: ManageAccessWindow(self),
        )
        self.btn_manage_access.pack(anchor='w', pady=(0, 8))
        self._register_button(self.btn_manage_access, 'config.manage_access')

    def _update_access_mode_labels(self):
        if not hasattr(self, 'lbl_access_mode'):
            return
        if admin_service.is_config_access_blocked():
            self.lbl_access_mode.configure(text=t('config.access_mode_restricted'))
        else:
            self.lbl_access_mode.configure(text=t('config.access_mode_open'))

    def _on_block_config_changed(self):
        want_block = bool(self.var_block_config.get())
        if want_block == admin_service.is_config_access_blocked():
            return
        if want_block:
            self.var_block_config.set(False)
            ConfirmWindow(
                self,
                t('config.block_confirm_title'),
                t('config.block_confirm_body'),
                self._apply_enable_config_block,
                has_confirm=False,
            )
            return
        admin_service.disable_config_access_block()
        self._update_access_mode_labels()

    def _apply_enable_config_block(self):
        added = admin_service.enable_config_access_block()
        self.var_block_config.set(True)
        self._update_access_mode_labels()
        if added:
            detail = '\n'.join(f'• {name}' for name in added)
            PopUpWindow(
                self,
                t('common.success'),
                t('config.block_enabled_success', added=detail),
            )

    def _build_tab_language(self, parent):
        scroll = self._tab_scroll(parent)

        card, body = self._settings_card(scroll, 'config.language_section')
        card.pack(fill='x')

        self.lbl_language_label = ctk.CTkLabel(
            body, text=t('config.language_label'), anchor='w', text_color=THEME_TEXT_SECONDARY,
        )
        self.lbl_language_label.pack(fill='x')
        self._register_label(self.lbl_language_label, 'config.language_label')
        self._lang_labels = {label: code for code, label in available_languages()}
        self.combo_default_language = ctk.CTkComboBox(
            body, width=280, values=[label for _, label in available_languages()],
            command=self._on_default_language_pick, **_combo_kwargs(),
        )
        self.combo_default_language.pack(anchor='w', pady=(4, 12))
        current_code = get_language()
        self.combo_default_language.set(get_i18n().language_label(current_code))

        self.lbl_locales_folder = ctk.CTkLabel(
            body, text=t('config.locales_folder'), anchor='w', text_color=THEME_TEXT_SECONDARY,
        )
        self.lbl_locales_folder.pack(fill='x')
        self._register_label(self.lbl_locales_folder, 'config.locales_folder')
        row_loc = ctk.CTkFrame(body, fg_color='transparent')
        row_loc.pack(fill='x', pady=(4, 8))
        self.inpt_locales_folder = ctk.CTkEntry(row_loc, **_entry_kwargs())
        self.inpt_locales_folder.pack(side='left', fill='x', expand=True, padx=(0, 8))
        self.btn_save_locales_folder = ctk.CTkButton(
            row_loc, text=t('config.save'), width=80, height=32, corner_radius=8,
            fg_color=THEME_ACCENT, hover_color=THEME_ACCENT_HOVER,
            command=self.save_locales_folder,
        )
        self.btn_save_locales_folder.pack(side='left')
        self._register_button(self.btn_save_locales_folder, 'config.save')
        locales_folder = get_locales_folder()
        if locales_folder:
            self.inpt_locales_folder.insert(0, locales_folder)

        self.lbl_locales_hint = ctk.CTkLabel(
            body, text=t('config.locales_hint'), font=(FONT, 10),
            text_color=THEME_TEXT_SECONDARY, justify='left', anchor='w',
        )
        self.lbl_locales_hint.pack(fill='x', pady=(0, 8))
        self._register_label(self.lbl_locales_hint, 'config.locales_hint')

        locales_row = ctk.CTkFrame(body, fg_color='transparent')
        locales_row.pack(fill='x', pady=(0, 8))
        self.btn_open_locales_folder = ctk.CTkButton(
            locales_row, text=t('config.open_locales_folder'), width=170, height=32, corner_radius=8,
            fg_color=THEME_NAV_ACTIVE, hover_color=THEME_CARD_BORDER,
            border_width=1, border_color=THEME_CARD_BORDER,
            command=self.open_locales_folder,
        )
        self.btn_open_locales_folder.pack(side='left', padx=(0, 8))
        self._register_button(self.btn_open_locales_folder, 'config.open_locales_folder')
        self.btn_reload_locales = ctk.CTkButton(
            locales_row, text=t('config.reload_locales'), width=140, height=32, corner_radius=8,
            fg_color=THEME_NAV_ACTIVE, hover_color=THEME_CARD_BORDER,
            border_width=1, border_color=THEME_CARD_BORDER,
            command=self.reload_locales,
        )
        self.btn_reload_locales.pack(side='left')
        self._register_button(self.btn_reload_locales, 'config.reload_locales')

        self.lbl_available_locales = ctk.CTkLabel(
            body, text=self._available_locales_text(),
            font=(FONT, 10), text_color=THEME_TEXT_SECONDARY, justify='left', anchor='w',
        )
        self.lbl_available_locales.pack(fill='x')

        card_theme, body_theme = self._settings_card(scroll, 'config.theme_section')
        card_theme.pack(fill='x', pady=(12, 0))

        self.lbl_theme_label = ctk.CTkLabel(
            body_theme, text=t('config.theme_label'), anchor='w', text_color=THEME_TEXT_SECONDARY,
        )
        self.lbl_theme_label.pack(fill='x')
        self._register_label(self.lbl_theme_label, 'config.theme_label')
        self._theme_labels = self._theme_label_map()
        self.combo_ui_theme = ctk.CTkComboBox(
            body_theme, width=280,
            values=list(self._theme_labels.keys()),
            command=self._on_ui_theme_pick, **_combo_kwargs(),
        )
        self.combo_ui_theme.pack(anchor='w', pady=(4, 8))
        self.combo_ui_theme.set(self._theme_combo_label(get_ui_theme()))

        self.lbl_theme_hint = ctk.CTkLabel(
            body_theme, text=t('config.theme_hint'), font=(FONT, 10),
            text_color=THEME_TEXT_SECONDARY, justify='left', anchor='w',
        )
        self.lbl_theme_hint.pack(fill='x')
        self._register_label(self.lbl_theme_hint, 'config.theme_hint')

    @staticmethod
    def _theme_combo_label(theme_id: str) -> str:
        key = f'theme.preset.{theme_id}'
        label = t(key)
        return label if label != key else theme_id

    def _theme_label_map(self) -> dict[str, str]:
        return {self._theme_combo_label(tid): tid for tid in available_theme_ids()}

    def _refresh_theme_combo(self):
        current_id = self._theme_labels.get(self.combo_ui_theme.get(), get_ui_theme())
        self._theme_labels = self._theme_label_map()
        self.combo_ui_theme.configure(values=list(self._theme_labels.keys()))
        self.combo_ui_theme.set(self._theme_combo_label(current_id))

    def _on_ui_theme_pick(self, label: str):
        theme_id = self._theme_labels.get(label)
        if not theme_id:
            return
        result = save_ui_theme(theme_id)
        if not result.ok:
            PopUpWindow(self, t('popup.error'), result.error)
            self.combo_ui_theme.set(self._theme_combo_label(get_ui_theme()))
            return
        self.combo_ui_theme.set(self._theme_combo_label(theme_id))
        if result.message:
            PopUpWindow(self, t('popup.ok'), result.message)

    def _on_search_changed(self, *_args):
        self._search_query = self.entry_search.get().strip().lower()
        self._apply_search_filter()

    def _filter_clients(self, query: str) -> list[str]:
        clients = admin_service.list_client_names()
        if not query:
            return clients
        filtered = []
        for client in clients:
            if query in client.lower():
                filtered.append(client)
                continue
            products = admin_service.list_products(client)
            if any(query in product.lower() for product in products):
                filtered.append(client)
        return filtered

    def _filter_products(self, client: str, query: str) -> list[str]:
        products = admin_service.list_products(client)
        if not query:
            return products
        if query in client.lower():
            return products
        return [product for product in products if query in product.lower()]

    def _update_search_count(self, clients: list[str], products_count: int):
        if not clients and self._search_query:
            self.lbl_search_count.configure(text=t('config.search_no_results'))
            return
        self.lbl_search_count.configure(
            text=t('config.search_count', clients=len(clients), products=products_count),
        )

    @staticmethod
    def _clear_host(host):
        for child in host.winfo_children():
            child.destroy()

    def _mount_client_list(self, items: list[str]):
        selected = ''
        if hasattr(self, 'client_list'):
            try:
                selected = self.client_list.radio_var.get()
            except Exception:
                selected = ''
        self._clear_host(self.clients_list_host)
        self.client_list = ListBox(
            self.clients_list_host,
            items,
            height=240,
            border_width=0,
            fg_color=THEME_BG,
            on_select=lambda _child: self.refresh(),
        )
        self.client_list.pack(fill='both', expand=True, padx=2, pady=2)
        if items:
            pick = selected if selected in items else items[0]
            self.client_list.radio_var.set(pick)
            for name, widget in self.client_list.radio_list.items():
                if name == pick:
                    widget.configure(font=(FONT, 13, 'bold'), text_color=THEME_NAV_TEXT_ACCENT)

    def _mount_product_list(self, items: list[str]):
        selected = ''
        if hasattr(self, 'product_list'):
            try:
                selected = self.product_list.radio_var.get()
            except Exception:
                selected = ''
        self._clear_host(self.products_list_host)
        self.product_list = ListBox(
            self.products_list_host,
            items,
            child=True,
            height=240,
            border_width=0,
            fg_color=THEME_BG,
            on_select=lambda _child: self.refresh(True),
        )
        self.product_list.pack(fill='both', expand=True, padx=2, pady=2)
        if items:
            pick = selected if selected in items else items[0]
            self.product_list.radio_var.set(pick)
            for name, widget in self.product_list.radio_list.items():
                if name == pick:
                    widget.configure(font=(FONT, 13, 'bold'), text_color=THEME_NAV_TEXT_ACCENT)

    def _apply_search_filter(self):
        clients = self._filter_clients(self._search_query)
        self._mount_client_list(clients)

        if self.btn_edit:
            self.btn_edit.destroy()
            self.btn_duplicate.destroy()
            self.btn_edit = None
            self.btn_duplicate = None

        if clients:
            total_products = sum(
                len(self._filter_products(c, self._search_query)) for c in clients
            )
            self._update_search_count(clients, total_products)
            self.refresh()
        else:
            self._clear_host(self.products_list_host)
            self.product_list = None
            self._update_search_count([], 0)
            self.delete_buttons()

    def save_database_location(self):
        folder = self.inpt_db_location.get()
        result = save_database_location(folder)
        if not result.ok:
            PopUpWindow(self, t('common.error'), result.error)
            return
        if result.message:
            self.update_save_button()
            self.exit()
            PopUpWindow(self.app, t('common.success'), result.message)

    def save_audit_location(self):
        result = save_audit_central_location(self.inpt_audit_location.get())
        if not result.ok:
            PopUpWindow(self, t('common.error'), result.error)
            return
        if result.message:
            PopUpWindow(self, t('common.success'), result.message)

    def _refresh_ghostscript_status(self):
        from app.utils.ghostscript_paths import (
            bundled_ghostscript_root,
            ghostscript_files_present,
            ghostscript_is_available,
        )
        if not hasattr(self, 'lbl_ghostscript_status'):
            return
        try:
            if not self.lbl_ghostscript_status.winfo_exists():
                return
        except Exception:
            return
        gs_root = bundled_ghostscript_root()
        if ghostscript_is_available():
            text = t('config.ghostscript_ok', path=gs_root)
            color = THEME_TEXT_SECONDARY
        elif ghostscript_files_present():
            text = t('config.ghostscript_smoke_failed', path=gs_root)
            color = THEME_ERROR_TEXT
        else:
            text = t('config.ghostscript_missing')
            color = THEME_ERROR_TEXT
        self.lbl_ghostscript_status.configure(text=text, text_color=color)

    @staticmethod
    def _available_backend_labels():
        """Labels for print backends available on this machine (always includes current)."""
        from app.services.settings_service import localized_backend_label
        try:
            from app.utils.printing.registry import list_backends
            labels = [
                localized_backend_label(name, label)
                for name, label, available, _exp in list_backends() if available
            ]
        except Exception:
            labels = []
        current = get_print_backend_label()
        if not labels:
            labels = [localized_backend_label(k, v) for k, v in PRINT_BACKEND_LABELS.items()]
        if current not in labels:
            labels.insert(0, current)
        return labels

    @staticmethod
    def _available_locales_text() -> str:
        names = [label for _, label in available_languages()]
        return t('config.available_locales', list=', '.join(names))

    def _on_default_language_pick(self, label: str):
        code = self._lang_labels.get(label)
        if not code:
            return
        result = save_language(code)
        if not result.ok:
            PopUpWindow(self, t('popup.error'), result.error)
            return
        if hasattr(self.app, 'apply_language'):
            self.app.apply_language()
        if hasattr(self, 'edit_window'):
            try:
                if self.edit_window.winfo_exists():
                    self.edit_window.apply_language()
            except Exception:
                pass
        self._lang_labels = {lbl: c for c, lbl in available_languages()}
        self.combo_default_language.configure(values=[lbl for _, lbl in available_languages()])
        self.combo_default_language.set(get_i18n().language_label(code))
        self.lbl_available_locales.configure(text=self._available_locales_text())
        self._refresh_theme_combo()
        if result.message:
            PopUpWindow(self, t('popup.ok'), result.message)

    def save_locales_folder(self):
        folder = self.inpt_locales_folder.get().strip()
        result = save_locales_folder(folder)
        if not result.ok:
            PopUpWindow(self, t('popup.error'), result.error)
            return
        self._lang_labels = {lbl: c for c, lbl in available_languages()}
        self.combo_default_language.configure(values=[lbl for _, lbl in available_languages()])
        self.lbl_available_locales.configure(text=self._available_locales_text())
        self._refresh_theme_combo()
        if result.message:
            PopUpWindow(self, t('popup.ok'), result.message)

    def open_locales_folder(self):
        folder = self.inpt_locales_folder.get().strip() or str(get_i18n().default_user_locales_dir())
        os.makedirs(folder, exist_ok=True)
        os.startfile(folder)

    def reload_locales(self):
        from app.i18n import reload_locales as reload_i18n_locales
        reload_i18n_locales(self.inpt_locales_folder.get().strip())
        self._lang_labels = {lbl: c for c, lbl in available_languages()}
        self.combo_default_language.configure(values=[lbl for _, lbl in available_languages()])
        self.combo_default_language.set(get_i18n().language_label())
        self.lbl_available_locales.configure(text=self._available_locales_text())
        self._refresh_theme_combo()
        if hasattr(self.app, 'apply_language'):
            self.app.apply_language()
        if hasattr(self, 'edit_window'):
            try:
                if self.edit_window.winfo_exists():
                    self.edit_window.apply_language()
            except Exception:
                pass

    def save_print_backend(self):
        label = self.combo_print_backend.get()
        backend = next(
            (key for key, value in PRINT_BACKEND_LABELS.items() if value == label),
            'pdftoprinter',
        )
        result = save_print_backend(backend)
        if not result.ok:
            PopUpWindow(self, t('common.error'), result.error)
            return
        if result.message:
            PopUpWindow(self, t('common.success'), result.message)

    def update_save_button(self, *args):
        folder = self.inpt_search_folder.get()
        config_folder = get_search_folder()

        config_db_location = get_database_location()
        database_folder = self.inpt_db_location.get()

        if config_db_location != database_folder:
            self.btn_save_db.configure(state='normal')
        else:
            self.btn_save_db.configure(state='disabled')

        if config_folder != folder:
            self.btn_save_folder.configure(state='normal')
        else:
            self.btn_save_folder.configure(state='disabled')

    def save_folder(self, *arg):
        folder = self.inpt_search_folder.get()
        result = save_search_folder(folder)
        if not result.ok:
            PopUpWindow(self, t('common.error'), result.error)
            return
        if result.message:
            self.update_save_button()
            PopUpWindow(self, t('common.success'), result.message)

    def create_client(self):
        self.client = AddClientWindow(self, t('config.client_name_prompt'), self.delete_buttons)

    def delete_buttons(self):
        if self.btn_add_product:
            self.btn_add_product.destroy()
            self.btn_add_product = None
        if self.btn_delete_client:
            self.btn_delete_client.destroy()
            self.btn_delete_client = None
        if self.btn_edit:
            self.btn_edit.destroy()
            self.btn_edit = None
            self.btn_duplicate.destroy()
            self.btn_duplicate = None
        self.update_product_list([])

    def open_edit_window(self, mode):
        self.edit_window = EditWindow(self, mode)
        self.winfo_toplevel().withdraw()

    def update_product_list(self, products):
        self._mount_product_list(products)

    def update_client_list(self):
        self._apply_search_filter()

    def show_edit_button(self):
        if self.btn_edit:
            self.btn_edit.destroy()
            self.btn_duplicate.destroy()

        self.btn_edit = ctk.CTkButton(
            self.product_actions, text=t('config.edit'), height=30, corner_radius=8,
            fg_color=THEME_ACCENT, hover_color=THEME_ACCENT_HOVER,
            command=lambda: self.open_edit_window('edit'),
        )
        self.btn_edit.pack(fill='x', pady=(0, 4))

        self.btn_duplicate = ctk.CTkButton(
            self.product_actions, text=t('config.duplicate'), height=30, corner_radius=8,
            fg_color=THEME_NAV_ACTIVE, hover_color=THEME_CARD_BORDER,
            border_width=1, border_color=THEME_CARD_BORDER,
            command=self.duplicate_product_window,
        )
        self.btn_duplicate.pack(fill='x')

    def duplicate_product_window(self):
        DuplicateProductWindow(self, t('config.duplicate_product_title'), self.client_list.radio_var.get(),
                               self.product_list.radio_var.get())

    def reset_all(self):
        self.delete_buttons()
        self.update_client_list()

    def refresh(self, child=False):
        if not child:
            if self.btn_delete_client:
                self.btn_delete_client.destroy()
                self.btn_delete_client = None
            if self.btn_add_product:
                self.btn_add_product.destroy()
                self.btn_add_product = None

            if hasattr(self, 'client_list') and self.client_list.radio_var.get():
                self.btn_add_product = ctk.CTkButton(
                    self.client_actions, text=f'+ {t("config.add_product")}', height=30, corner_radius=8,
                    fg_color=THEME_NAV_ACTIVE, hover_color=THEME_CARD_BORDER,
                    border_width=1, border_color=THEME_CARD_BORDER,
                    command=lambda: self.open_edit_window('add'),
                )
                self.btn_add_product.pack(fill='x', pady=(0, 4))

                self.btn_delete_client = ctk.CTkButton(
                    self.client_actions, text=t('config.delete_client'), height=30, corner_radius=8,
                    fg_color=BTN_RED, hover_color=BTN_HOVER_RED,
                    command=self.confirm_delete,
                )
                self.btn_delete_client.pack(fill='x')

                client = self.client_list.radio_var.get()
                products = self._filter_products(client, self._search_query)
                self._mount_product_list(products)
                total_products = sum(
                    len(self._filter_products(c, self._search_query))
                    for c in self._filter_clients(self._search_query)
                )
                self._update_search_count(self._filter_clients(self._search_query), total_products)
            else:
                self._clear_host(self.products_list_host)
                self.product_list = None

            if self.btn_edit:
                self.btn_edit.destroy()
                self.btn_duplicate.destroy()
                self.btn_edit = None
                self.btn_duplicate = None
        else:
            self.show_edit_button()

    def confirm_delete(self):
        client = self.client_list.radio_var.get()
        ConfirmWindow(self, t('common.confirm_title'), t('config.delete_client_confirm', client=client),
                      self.delete_client)

    def delete_client(self):
        client = self.client_list.radio_var.get()
        if admin_service.delete_client(client):
            self.reset_all()
        else:
            PopUpWindow(self, t('common.error'), t('config.client_not_found', client=client))

    def import_product(self):
        file_path = askopenfilename(filetypes=[(t('config.import_file_filter'), "*.json")])
        if not file_path:
            return

        try:
            product_file = parse_import_file(file_path)
        except Exception as e:
            PopUpWindow(self, t('common.error'), t('config.import_read_error', error=e))
            return

        client_name = product_file['cliente']
        product_name = product_file['produto']
        paper_size = resolve_product_paper_size(int(orientation), layout_config)
        color = product_file['color']
        orientation = product_file['orientation']
        layout_config = product_file.get('layout_config')
        items = product_file['items']

        if admin_service.list_client_names(client_name):
            if product_name in admin_service.list_products(client_name):
                def replace_drawing():
                    try:
                        replace_imported_drawings(client_name, product_name, items, admin_service.get_db())
                        PopUpWindow(self, t('common.success'), t('config.product_replaced'))
                    except Exception as e:
                        PopUpWindow(self, t('common.error'), t('config.product_save_error', error=e))

                text = t('config.product_exists_confirm', product=product_name)
                ConfirmWindow(self, t('config.product_exists_title'), text, replace_drawing)
            else:
                try:
                    import_product_for_existing_client(
                        client_name, product_name, color, orientation, paper_size, items,
                        admin_service.get_db(), layout_config=layout_config,
                    )
                    PopUpWindow(self, t('common.success'), t('config.product_saved'))
                except Exception as e:
                    PopUpWindow(self, t('common.error'), t('config.product_save_error', error=e))
        else:
            try:
                import_product_with_new_client(
                    client_name, product_name, color, orientation, paper_size, items,
                    admin_service.get_db(), layout_config=layout_config,
                )
                PopUpWindow(self, t('common.success'), t('config.import_client_product_ok'))
            except Exception as e:
                PopUpWindow(self, t('common.error'), t('config.import_client_product_error', error=e))

        self.reset_all()

    def _retitle_tabs(self):
        tabs = getattr(self, 'tabs', None)
        if tabs is None or not self._tab_keys:
            return
        current_key = None
        current_name = tabs.get()
        for i, key in enumerate(self._tab_keys):
            if tabs._name_list[i] == current_name:
                current_key = key
            old_name = tabs._name_list[i]
            new_name = t(key)
            if old_name == new_name:
                continue
            frame = tabs._tab_dict.pop(old_name, None)
            if frame is not None:
                tabs._tab_dict[new_name] = frame
                tabs._name_list[i] = new_name
        tabs._segmented_button.configure(values=list(tabs._name_list))
        if current_key is not None:
            tabs.set(t(current_key))

    def apply_language(self):
        """Atualiza textos do painel após troca de idioma."""
        self._retitle_tabs()

        for widget, key, formatter in self._i18n_labels:
            try:
                if formatter is not None:
                    widget.configure(text=t(key, **formatter()))
                else:
                    widget.configure(text=t(key))
            except Exception:
                pass

        seen_buttons = set()
        for widget, key, prefix in self._i18n_buttons:
            if widget in seen_buttons:
                continue
            seen_buttons.add(widget)
            try:
                if not widget.winfo_exists():
                    continue
                widget.configure(text=f'{prefix}{t(key)}')
            except Exception:
                pass

        if hasattr(self, 'entry_search'):
            self.entry_search.configure(placeholder_text=t('config.search_placeholder'))
        if hasattr(self, 'inpt_audit_location'):
            self.inpt_audit_location.configure(placeholder_text=t('config.audit_db_placeholder'))

        if hasattr(self, '_lang_labels'):
            old_label = self.combo_default_language.get()
            current_code = self._lang_labels.get(old_label, get_language())
            self._lang_labels = {label: code for code, label in available_languages()}
            self.combo_default_language.configure(values=[label for _, label in available_languages()])
            self.combo_default_language.set(get_i18n().language_label(current_code))

        for attr, key, prefix in (
            ('btn_add_product', 'config.add_product', '+ '),
            ('btn_delete_client', 'config.delete_client', ''),
            ('btn_edit', 'config.edit', ''),
            ('btn_duplicate', 'config.duplicate', ''),
        ):
            btn = getattr(self, attr, None)
            if btn is not None:
                try:
                    if btn.winfo_exists():
                        btn.configure(text=f'{prefix}{t(key)}' if prefix else t(key))
                except Exception:
                    pass

        if hasattr(self, 'lbl_available_locales'):
            self.lbl_available_locales.configure(text=self._available_locales_text())

        if hasattr(self, 'combo_print_backend'):
            current_backend = self.combo_print_backend.get()
            backend_values = self._available_backend_labels()
            self.combo_print_backend.configure(values=backend_values)
            if current_backend in backend_values:
                self.combo_print_backend.set(current_backend)
            else:
                self.combo_print_backend.set(get_print_backend_label())

        self._refresh_ghostscript_status()
        self._refresh_theme_combo()
        if hasattr(self, 'var_block_config'):
            self.var_block_config.set(admin_service.is_config_access_blocked())
            self._update_access_mode_labels()
        self._apply_search_filter()
        self.after_idle(self.refresh_layout)


ConfigWindow = ConfigPanel


class EditRegisteredPrinterWindow(ctk.CTkToplevel):
    def __init__(self, master, on_save, printer=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iconbitmap(ICON)
        self.title(t('printer.edit_title_edit') if (printer and printer.get('id')) else t('printer.edit_title_register'))
        self.master = master
        self.on_save = on_save
        self.printer = printer
        self.grab_set()
        self.configure(fg_color=THEME_BG)

        self.geometry(calculate_center_screen_with_monitor(master, 440, 400, get_monitor(master)))
        self.minsize(440, 400)
        self.maxsize(440, 400)
        self.resizable(False, False)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=0)

        header = ctk.CTkFrame(self, fg_color=THEME_CARD, corner_radius=0, height=48)
        header.grid(row=0, column=0, sticky='ew')
        header.grid_propagate(False)
        ctk.CTkLabel(
            header, text=self.title(), font=(FONT, 15, 'bold'), text_color='white', anchor='w',
        ).pack(side='left', padx=16, pady=10)

        body = ctk.CTkFrame(self, fg_color='transparent')
        body.grid(row=1, column=0, sticky='ew', padx=16, pady=(12, 0))
        body.grid_columnconfigure(0, weight=1)

        card, form = _section_card(body, t('printer.edit_form_title'))
        card.pack(fill='x')
        form.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            form, text=t('printer.win_name_label'), font=(FONT, 11),
            text_color=THEME_TEXT_SECONDARY, anchor='w',
        ).grid(row=0, column=0, sticky='ew', pady=(0, 4))
        self.entry_name = ctk.CTkEntry(form, **_entry_kwargs())
        self.entry_name.grid(row=1, column=0, sticky='ew', pady=(0, 8))

        ctk.CTkLabel(
            form, text=t('printer.display_name_label'), font=(FONT, 11),
            text_color=THEME_TEXT_SECONDARY, anchor='w',
        ).grid(row=2, column=0, sticky='ew', pady=(0, 4))
        self.entry_display = ctk.CTkEntry(form, **_entry_kwargs())
        self.entry_display.grid(row=3, column=0, sticky='ew', pady=(0, 8))

        self.checkbox_enabled = ctk.CTkCheckBox(
            form, text=t('printer.enabled_production'),
            font=(FONT, 12), text_color='white',
            fg_color=THEME_ACCENT, hover_color=THEME_ACCENT_HOVER,
            border_color=THEME_CARD_BORDER,
        )
        self.checkbox_enabled.grid(row=4, column=0, sticky='w', pady=(0, 8))

        ctk.CTkLabel(
            form, text=t('printer.notes_label'), font=(FONT, 11),
            text_color=THEME_TEXT_SECONDARY, anchor='w',
        ).grid(row=5, column=0, sticky='ew', pady=(0, 4))
        self.entry_notes = ctk.CTkEntry(form, **_entry_kwargs())
        self.entry_notes.grid(row=6, column=0, sticky='ew', pady=(0, 4))

        if printer:
            self.entry_name.insert(0, printer.get('name', ''))
            self.entry_display.insert(0, printer.get('display_name', ''))
            if printer.get('enabled', True):
                self.checkbox_enabled.select()
            if printer.get('notes'):
                self.entry_notes.insert(0, printer['notes'])

        actions = ctk.CTkFrame(self, fg_color='transparent')
        actions.grid(row=2, column=0, sticky='ew', padx=16, pady=(12, 16))
        _dialog_action_row(actions, self, t('common.save'), self.save)

    def save(self):
        name = self.entry_name.get().strip()
        display_name = self.entry_display.get().strip()
        enabled = bool(self.checkbox_enabled.get())
        notes = self.entry_notes.get().strip()

        if not name:
            PopUpWindow(self, t('common.error'), t('printer.name_required'))
            return
        if not display_name:
            display_name = name

        if not admin_service.verify_printer_available(name):
            PopUpWindow(
                self, t('printer.not_found_title'),
                t('printer.not_found_verify_body', name=name),
            )
            return

        if self.printer and self.printer.get('id'):
            ok = admin_service.update_registered_printer(
                self.printer['id'], name, display_name, enabled, notes,
            )
            if not ok:
                PopUpWindow(self, t('common.error'), t('printer.save_failed'))
                return
        else:
            ok = admin_service.add_registered_printer(name, display_name, enabled, notes)
            if not ok:
                PopUpWindow(self, t('common.error'), t('printer.already_registered', name=name))
                return

        self.on_save()
        self.destroy()


class ManagePrintersWindow(ctk.CTkToplevel):
    _TABLE_HEIGHT = 4
    _FRAME_H = 110
    _WINDOW_W = 560
    _WINDOW_H = 600

    def __init__(self, master, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iconbitmap(ICON)
        self.title(t('printer.manage_title'))
        self.master = master
        self.grab_set()
        self.configure(fg_color=THEME_BG)

        self.geometry(calculate_center_screen_with_monitor(
            master, self._WINDOW_W, self._WINDOW_H, get_monitor(master),
        ))
        self.minsize(self._WINDOW_W, self._WINDOW_H)
        self.maxsize(self._WINDOW_W, self._WINDOW_H)
        self.resizable(False, False)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color=THEME_CARD, corner_radius=0, height=56)
        header.grid(row=0, column=0, sticky='ew')
        header.grid_propagate(False)
        title_col = ctk.CTkFrame(header, fg_color='transparent')
        title_col.pack(side='left', padx=16, pady=10)
        ctk.CTkLabel(
            title_col, text=t('printer.manage_title'), font=(FONT, 18, 'bold'), text_color='white',
        ).pack(anchor='w')
        ctk.CTkLabel(
            title_col, text=t('printer.manage_subtitle'), font=(FONT, 11),
            text_color=THEME_TEXT_SECONDARY,
        ).pack(anchor='w')

        body = ctk.CTkScrollableFrame(
            self, fg_color='transparent',
            width=self._WINDOW_W - 28, height=self._WINDOW_H - 120,
        )
        body.grid(row=1, column=0, padx=14, pady=(10, 8), sticky='nsew')
        body.grid_columnconfigure(0, weight=1)

        reg_card, reg_body = _section_card(body, t('printer.registered_title'))
        reg_card.pack(fill='x', pady=(0, 10))

        self.table_frame = _table_host(reg_body, self._FRAME_H)
        self.table_frame.pack(fill='x', pady=(0, 0))
        self.table = Table(
            self.table_frame,
            [t('printer.col_display'), t('printer.col_name'), t('printer.col_enabled'), t('printer.col_notes')],
            show='headings', height=self._TABLE_HEIGHT,
        )
        self.table.column('#1', width=120)
        self.table.column('#2', width=180)
        self.table.column('#3', width=50)
        self.table.column('#4', width=120)
        self.table.pack(expand=True, fill='both', padx=4, pady=4)

        btn_row = ctk.CTkFrame(reg_body, fg_color='transparent')
        btn_row.pack(fill='x', pady=(8, 0))

        ctk.CTkButton(
            btn_row, text=t('common.new'), width=84, command=self.add_printer, **_secondary_btn_kwargs(),
        ).pack(side='left', padx=(0, 6))
        ctk.CTkButton(
            btn_row, text=t('common.edit'), width=84, command=self.edit_printer, **_secondary_btn_kwargs(),
        ).pack(side='left', padx=(0, 6))
        ctk.CTkButton(
            btn_row, text=t('common.remove'), width=84, fg_color=BTN_RED,
            hover_color=BTN_HOVER_RED, corner_radius=8, height=32, command=self.remove_printer,
        ).pack(side='left')
        ctk.CTkButton(
            btn_row, text=t('common.verify'), width=96, command=self.verify_selected, **_secondary_btn_kwargs(),
        ).pack(side='right')

        self.refresh_table()

        disc_card, disc_body = _section_card(body, t('printer.discover_title'))
        disc_card.pack(fill='x')

        discover_row = ctk.CTkFrame(disc_body, fg_color='transparent')
        discover_row.pack(fill='x', pady=(0, 8))

        ctk.CTkButton(
            discover_row, text=t('printer.discover_windows'), width=140, command=self.discover,
            fg_color=THEME_ACCENT, hover_color=THEME_ACCENT_HOVER, corner_radius=8, height=32,
        ).pack(side='left')
        ctk.CTkButton(
            discover_row, text=t('printer.add_selected'), width=150, command=self.add_from_discovery,
            **_secondary_btn_kwargs(),
        ).pack(side='right')

        self.discover_frame = _table_host(disc_body, self._FRAME_H)
        self.discover_frame.pack(fill='x')
        self.discover_table = Table(
            self.discover_frame, [t('printer.col_installed')], show='headings', height=self._TABLE_HEIGHT,
        )
        self.discover_table.column('#1', width=460)
        self.discover_table.pack(expand=True, fill='both', padx=4, pady=4)
        self._discovered = []

        footer = ctk.CTkFrame(self, fg_color='transparent')
        footer.grid(row=2, column=0, sticky='e', padx=14, pady=(0, 12))
        ctk.CTkButton(
            footer, text=t('common.close'), width=100, command=self.destroy,
            fg_color=THEME_ACCENT, hover_color=THEME_ACCENT_HOVER, corner_radius=8, height=32,
        ).pack(side='right')

    def refresh_table(self):
        self.table.remove_all()
        self._registered = admin_service.list_registered_printers()
        for item in self._registered:
            notes = item['notes']
            if len(notes) > 40:
                notes = notes[:37] + '...'
            self.table.add_item([
                item['display_name'],
                item['name'],
                t('common.yes') if item['enabled'] else t('common.no'),
                notes,
            ], item_id=item['id'])
        if hasattr(self.master, 'refresh_production_combos'):
            self.master.refresh_production_combos()

    def _selected_registered(self):
        selected = self.table.get_selected_items()
        if not selected:
            return None
        row_id = self.table.selection()[0]
        try:
            printer_id = int(row_id)
        except ValueError:
            return None
        for item in self._registered:
            if item['id'] == printer_id:
                return item
        return None

    def add_printer(self):
        EditRegisteredPrinterWindow(self, on_save=self.refresh_table)

    def edit_printer(self):
        printer = self._selected_registered()
        if not printer:
            PopUpWindow(self, t('common.warning'), t('printer.select_in_list'))
            return
        EditRegisteredPrinterWindow(self, on_save=self.refresh_table, printer=printer)

    def remove_printer(self):
        printer = self._selected_registered()
        if not printer:
            PopUpWindow(self, t('common.warning'), t('printer.select_to_remove'))
            return
        if admin_service.delete_registered_printer(printer['id']):
            self.refresh_table()
        else:
            PopUpWindow(self, t('common.error'), t('printer.remove_failed'))

    def verify_selected(self):
        printer = self._selected_registered()
        if not printer:
            PopUpWindow(self, t('common.warning'), t('printer.select_to_verify'))
            return
        if admin_service.verify_printer_available(printer['name']):
            PopUpWindow(self, t('common.ok'), t('printer.found_on_windows', name=printer['name']))
        else:
            PopUpWindow(
                self, t('common.not_found'),
                t('printer.not_found_on_windows', name=printer['name']),
            )

    def discover(self):
        self._registered = admin_service.list_registered_printers()
        self._discovered = admin_service.discover_installed_printers()
        self.discover_table.remove_all()
        registered_names = {p['name'].lower() for p in self._registered}
        for name in self._discovered:
            suffix = t('printer.already_registered_suffix') if name.lower() in registered_names else ''
            self.discover_table.add_item([name + suffix], item_id=name)
        if not self._discovered:
            PopUpWindow(self, t('common.discovery'), t('printer.none_installed'))

    def add_from_discovery(self):
        selected = self.discover_table.get_selected_items()
        if not selected:
            PopUpWindow(self, t('common.warning'), t('printer.select_discovered'))
            return
        suffix = t('printer.already_registered_suffix')
        name = selected[0][0].replace(suffix, '').strip()
        if any(p['name'].lower() == name.lower() for p in self._registered):
            PopUpWindow(self, t('common.warning'), t('printer.already_registered_name', name=name))
            return
        EditRegisteredPrinterWindow(
            self,
            on_save=self.refresh_table,
            printer={'name': name, 'display_name': name, 'enabled': True, 'notes': ''},
        )


class ManageAccessWindow(ctk.CTkToplevel):
    _TABLE_HEIGHT = 4
    _AUTHORIZED_FRAME_H = 110
    _RESULTS_FRAME_H = 110
    _WINDOW_W = 560
    _WINDOW_H = 620

    def __init__(self, master, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iconbitmap(ICON)
        self.configure(fg_color=THEME_BG)

        self.geometry(calculate_center_screen_with_monitor(
            master, self._WINDOW_W, self._WINDOW_H, get_monitor(master),
        ))
        self.minsize(self._WINDOW_W, self._WINDOW_H)
        self.maxsize(self._WINDOW_W, self._WINDOW_H)
        self.resizable(False, False)
        self.title(t('access.manage_title'))
        self.master = master
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color=THEME_CARD, corner_radius=0, height=56)
        header.grid(row=0, column=0, sticky='ew')
        header.grid_propagate(False)
        title_col = ctk.CTkFrame(header, fg_color='transparent')
        title_col.pack(side='left', padx=16, pady=10)
        ctk.CTkLabel(
            title_col, text=t('access.manage_title'), font=(FONT, 17, 'bold'), text_color='white',
        ).pack(anchor='w')
        ctk.CTkLabel(
            title_col, text=t('access.manage_subtitle'), font=(FONT, 11),
            text_color=THEME_TEXT_SECONDARY,
        ).pack(anchor='w')

        body = ctk.CTkScrollableFrame(
            self, fg_color='transparent',
            width=self._WINDOW_W - 28, height=self._WINDOW_H - 120,
        )
        body.grid(row=1, column=0, padx=14, pady=(10, 8), sticky='nsew')
        body.grid_columnconfigure(0, weight=1)

        auth_card, auth_body = _section_card(body, t('access.authorized_title'))
        auth_card.pack(fill='x', pady=(0, 10))

        self.table_frame = _table_host(auth_body, self._AUTHORIZED_FRAME_H)
        self.table_frame.pack(fill='x')
        self.table = Table(
            self.table_frame,
            [t('access.col_principal'), t('access.col_type')],
            show='headings', height=self._TABLE_HEIGHT,
        )
        self.table.column('#1', width=320)
        self.table.column('#2', width=80)
        self.table.pack(expand=True, fill='both', padx=4, pady=4)
        self.refresh_table()

        self.btn_delete = ctk.CTkButton(
            auth_body, text=t('access.remove_selected'), width=150,
            fg_color=BTN_RED, hover_color=BTN_HOVER_RED,
            corner_radius=8, height=32, command=self.remove_selected,
        )
        self.btn_delete.pack(anchor='e', pady=(8, 0))

        search_card, search_body = _section_card(body, t('access.search_title'))
        search_card.pack(fill='x', pady=(0, 10))

        search_row = ctk.CTkFrame(search_body, fg_color='transparent')
        search_row.pack(fill='x', pady=(0, 8))
        search_row.grid_columnconfigure(0, weight=1)

        self.entry_search = ctk.CTkEntry(
            search_row, placeholder_text=t('access.search_hint'), **_entry_kwargs(),
        )
        self.entry_search.grid(row=0, column=0, sticky='ew', padx=(0, 8))
        self.entry_search.bind('<Return>', self.search_principals)

        self._type_combo_labels = {
            t('access.type_both'): 'both',
            t('access.type_user'): 'user',
            t('access.type_group'): 'group',
        }
        self.combo_type = ctk.CTkComboBox(
            search_row, width=150, values=list(self._type_combo_labels.keys()), **_combo_kwargs(),
        )
        self.combo_type.set(t('access.type_both'))
        self.combo_type.grid(row=0, column=1, padx=(0, 8))

        self.btn_search = ctk.CTkButton(
            search_row, text=t('access.search_btn'), width=96,
            fg_color=THEME_ACCENT, hover_color=THEME_ACCENT_HOVER,
            corner_radius=8, height=32, command=self.search_principals,
        )
        self.btn_search.grid(row=0, column=2)

        self.results_frame = _table_host(search_body, self._RESULTS_FRAME_H)
        self.results_frame.pack(fill='x', pady=(0, 8))
        self.results_table = Table(
            self.results_frame,
            [t('access.col_search_result'), t('access.col_type')],
            show='headings', height=self._TABLE_HEIGHT,
        )
        self.results_table.column('#1', width=320)
        self.results_table.column('#2', width=80)
        self.results_table.pack(expand=True, fill='both', padx=4, pady=4)
        self._search_results = []

        ctk.CTkButton(
            search_body, text=t('access.add_selected'), width=150, command=self.add_selected,
            **_secondary_btn_kwargs(),
        ).pack(anchor='e')

        manual_card, manual_body = _section_card(body, t('access.manual_hint'))
        manual_card.pack(fill='x')

        manual_row = ctk.CTkFrame(manual_body, fg_color='transparent')
        manual_row.pack(fill='x')
        manual_row.grid_columnconfigure(0, weight=1)

        self.entry_manual = ctk.CTkEntry(
            manual_row, placeholder_text=t('access.manual_placeholder'), **_entry_kwargs(),
        )
        self.entry_manual.grid(row=0, column=0, sticky='ew', padx=(0, 8))
        self.entry_manual.bind('<Return>', self.add_manual)

        ctk.CTkButton(
            manual_row, text=t('common.add'), width=96, command=self.add_manual,
            fg_color=THEME_ACCENT, hover_color=THEME_ACCENT_HOVER, corner_radius=8, height=32,
        ).grid(row=0, column=1)

        footer = ctk.CTkFrame(self, fg_color='transparent')
        footer.grid(row=2, column=0, sticky='e', padx=14, pady=(0, 12))
        ctk.CTkButton(
            footer, text=t('common.close'), width=100, command=self.destroy,
            fg_color=THEME_ACCENT, hover_color=THEME_ACCENT_HOVER, corner_radius=8, height=32,
        ).pack(side='right')

    def _type_filter(self):
        return self._type_combo_labels.get(self.combo_type.get(), 'both')

    def _type_label(self, ptype):
        return t('access.type_user') if ptype == 'user' else t('access.type_group')

    def refresh_table(self):
        self.table.remove_all()
        for entry in admin_service.list_config_access():
            self.table.add_item([entry['name'], self._type_label(entry['type'])])

    def search_principals(self, *args):
        query = self.entry_search.get().strip()
        if len(query) < 2:
            PopUpWindow(self, t('common.warning'), t('access.search_min_chars'))
            return
        principal_type = self._type_filter()
        self.btn_search.configure(state='disabled', text=t('access.searching'))

        def worker():
            try:
                results = admin_service.search_windows_principals(query, principal_type)
            except Exception:
                results = []
            self.after(0, lambda: self._finish_search_principals(results))

        Thread(target=worker, daemon=True).start()

    def _finish_search_principals(self, results):
        self.btn_search.configure(state='normal', text=t('access.search_btn'))
        self._search_results = results
        self.results_table.remove_all()
        for item in self._search_results:
            self.results_table.add_item([item['display'], self._type_label(item['type'])])
        if not self._search_results:
            PopUpWindow(self, t('access.search_btn'), t('access.search_empty'))

    def _add_principal(self, name, ptype):
        if not admin_service.add_config_access(name, ptype):
            PopUpWindow(self, t('common.warning'), t('access.already_in_list', name=name))
            return
        self.refresh_table()
        PopUpWindow(self, t('common.success'), t('access.added_success', name=name))

    def add_selected(self):
        selected = self.results_table.get_selected_items()
        if not selected:
            PopUpWindow(self, t('common.warning'), t('access.select_to_add'))
            return
        display = selected[0][0]
        for item in self._search_results:
            if item['display'] == display:
                self._add_principal(item['name'], item['type'])
                return
        PopUpWindow(self, t('common.error'), t('access.cannot_identify'))

    def add_manual(self, *args):
        resolved = admin_service.resolve_windows_principal(self.entry_manual.get())
        if not resolved:
            PopUpWindow(self, t('common.error'), t('access.invalid_account'))
            return
        self._add_principal(resolved['name'], resolved['type'])
        self.entry_manual.delete(0, 'end')

    def remove_selected(self):
        selected = self.table.get_selected_items()
        if not selected:
            PopUpWindow(self, t('common.warning'), t('access.select_to_remove'))
            return
        name = selected[0][0]
        if admin_service.delete_config_access(name):
            self.refresh_table()
        else:
            PopUpWindow(self, t('common.error'), t('access.remove_named_failed', name=name))


class ManageGroupWindow(ctk.CTkToplevel):
    _WINDOW_W = 420
    _WINDOW_H = 400
    _TABLE_H = 200

    def __init__(self, master, title, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iconbitmap(ICON)
        self.title(title)
        self.master = master
        self.grab_set()
        self.configure(fg_color=THEME_BG)

        self.geometry(calculate_center_screen_with_monitor(
            master, self._WINDOW_W, self._WINDOW_H, get_monitor(master),
        ))
        self.minsize(self._WINDOW_W, self._WINDOW_H)
        self.maxsize(self._WINDOW_W, self._WINDOW_H)
        self.resizable(False, False)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color=THEME_CARD, corner_radius=0, height=56)
        header.grid(row=0, column=0, sticky='ew')
        header.grid_propagate(False)
        title_col = ctk.CTkFrame(header, fg_color='transparent')
        title_col.pack(side='left', padx=16, pady=10)
        ctk.CTkLabel(
            title_col, text=title, font=(FONT, 16, 'bold'), text_color='white',
        ).pack(anchor='w')
        ctk.CTkLabel(
            title_col, text=t('group.manage_subtitle'), font=(FONT, 11),
            text_color=THEME_TEXT_SECONDARY,
        ).pack(anchor='w')

        body = ctk.CTkFrame(self, fg_color='transparent')
        body.grid(row=1, column=0, sticky='nsew', padx=14, pady=12)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        card, card_body = _section_card(body, t('group.list_title'))
        card.pack(fill='both', expand=True)
        card_body.grid_columnconfigure(0, weight=1)
        card_body.grid_rowconfigure(1, weight=1)

        add_row = ctk.CTkFrame(card_body, fg_color='transparent')
        add_row.grid(row=0, column=0, sticky='ew', pady=(0, 8))
        add_row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            add_row, text=t('group.name_prompt'), font=(FONT, 11),
            text_color=THEME_TEXT_SECONDARY, anchor='w',
        ).grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, 4))

        self.entry_name = ctk.CTkEntry(add_row, **_entry_kwargs())
        self.entry_name.grid(row=1, column=0, sticky='ew', padx=(0, 8))

        self.btn_incluir = ctk.CTkButton(
            add_row, text=t('group.include'), width=100,
            fg_color=THEME_ACCENT, hover_color=THEME_ACCENT_HOVER,
            corner_radius=8, height=32, command=self.add_group,
        )
        self.btn_incluir.grid(row=1, column=1, sticky='e')

        self.table_frame = _table_host(card_body, self._TABLE_H)
        self.table_frame.grid(row=1, column=0, sticky='nsew', pady=(0, 8))

        self.table = Table(self.table_frame, [t('group.col_name')], show='headings')
        self.table.pack(expand=True, fill='both', padx=4, pady=4)

        self.btn_delete = ctk.CTkButton(
            card_body, text=t('group.delete_btn'), width=110,
            fg_color=BTN_RED, hover_color=BTN_HOVER_RED,
            corner_radius=8, height=32, command=self.delete_group,
        )
        self.btn_delete.grid(row=2, column=0, sticky='w')

        self.refresh_table()
        self.entry_name.bind('<Return>', self.add_group)

    def add_group(self, *args):
        name = self.entry_name.get().upper()
        if name in admin_service.list_print_groups():
            PopUpWindow(self, t('common.error'), t('group.already_exists', name=name))
            return

        try:
            admin_service.insert_print_group(name)
            self.refresh_table()
            self.entry_name.delete(0, 'end')

        except Exception as e:
            PopUpWindow(self, t('common.error'), t('group.add_error', error=e))

    def delete_group(self):
        try:
            for i in self.table.get_selected_items():
                admin_service.delete_print_group(i[0])

            self.refresh_table()
        except Exception as e:
            PopUpWindow(self, t('common.error'), t('group.delete_error', error=e))

    def refresh_table(self):
        self.table.remove_all()
        for i in admin_service.list_print_groups():
            self.table.add_item([i])
        if hasattr(self.master, 'refresh_production_combos'):
            self.master.refresh_production_combos()


class DuplicateProductWindow(ctk.CTkToplevel):
    def __init__(self, master, title, original_client, original_product_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iconbitmap(ICON)
        self.configure(fg_color=THEME_BG)

        self.geometry(calculate_center_screen_with_monitor(master, 440, 380, get_monitor(master)))
        self.minsize(440, 380)
        self.maxsize(440, 380)
        self.resizable(False, False)
        self.title(title)
        self.master = master
        self.product_name = original_product_name
        self.original_client = original_client
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=0)

        _build_dialog_header(self, title, t('import_export.duplicate_subtitle'))

        body = ctk.CTkFrame(self, fg_color='transparent')
        body.grid(row=1, column=0, sticky='ew', padx=16, pady=(8, 0))
        body.grid_columnconfigure(0, weight=1)

        card, form = _section_card(body, t('import_export.select_client_product'))
        card.pack(fill='x')
        form.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            form, text=t('config.client_label'), font=(FONT, 11),
            text_color=THEME_TEXT_SECONDARY, anchor='w',
        ).grid(row=0, column=0, sticky='ew', pady=(0, 4))
        self.entry_clientname = ctk.CTkComboBox(
            form, values=admin_service.list_client_names(), **_combo_kwargs(),
        )
        self.entry_clientname.grid(row=1, column=0, sticky='ew', pady=(0, 8))
        if admin_service.list_client_names():
            self.entry_clientname.set(original_client)

        ctk.CTkLabel(
            form, text=t('config.product_name'), font=(FONT, 11),
            text_color=THEME_TEXT_SECONDARY, anchor='w',
        ).grid(row=2, column=0, sticky='ew', pady=(0, 4))
        self.entry_productname = ctk.CTkEntry(form, **_entry_kwargs())
        self.entry_productname.grid(row=3, column=0, sticky='ew')
        self.entry_productname.insert(0, original_product_name + '(1)')

        actions = ctk.CTkFrame(self, fg_color='transparent')
        actions.grid(row=2, column=0, sticky='ew', padx=16, pady=(12, 20))
        _dialog_action_row(actions, self, t('common.ok'), self.duplicate_product)

    def duplicate_product(self):
        product_name = self.entry_productname.get()
        client_name = self.entry_clientname.get()
        error = designer_duplicate_product(
            self.original_client,
            self.product_name,
            client_name,
            product_name,
            admin_service.get_db(),
        )
        if error:
            if error == 'name_exists':
                PopUpWindow(self, t('common.error'), t('designer.validation.name_exists'))
            else:
                PopUpWindow(self, t('common.error'), error)
            return

        self.master.client_list.radio_var.set(client_name)
        self.master.client_list.focus()
        self.master.refresh()
        self.master.product_list.radio_var.set(product_name)
        self.master.product_list.focus()
        self.destroy()


class ExportProductWindow(ctk.CTkToplevel):
    def __init__(self, master, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iconbitmap(ICON)
        self.configure(fg_color=THEME_BG)

        self.geometry(calculate_center_screen_with_monitor(master, 440, 380, get_monitor(master)))
        self.minsize(440, 380)
        self.maxsize(440, 380)
        self.resizable(False, False)
        self.title(t('import_export.export_title'))
        self.master = master
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=0)

        _build_dialog_header(self, t('import_export.export_title'), t('import_export.export_subtitle'))

        body = ctk.CTkFrame(self, fg_color='transparent')
        body.grid(row=1, column=0, sticky='ew', padx=16, pady=(8, 0))
        body.grid_columnconfigure(0, weight=1)

        card, form = _section_card(body, t('import_export.select_client_product'))
        card.pack(fill='x')
        form.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            form, text=t('config.client_label'), font=(FONT, 11),
            text_color=THEME_TEXT_SECONDARY, anchor='w',
        ).grid(row=0, column=0, sticky='ew', pady=(0, 4))
        self.entry_clientname = ctk.CTkComboBox(
            form, values=admin_service.list_client_names(), command=self.refresh_combobox,
            **_combo_kwargs(),
        )
        self.entry_clientname.grid(row=1, column=0, sticky='ew', pady=(0, 8))
        self.entry_clientname.set('')

        ctk.CTkLabel(
            form, text=t('config.products_label'), font=(FONT, 11),
            text_color=THEME_TEXT_SECONDARY, anchor='w',
        ).grid(row=2, column=0, sticky='ew', pady=(0, 4))
        self.entry_productname = ctk.CTkComboBox(
            form, state='disabled', command=self.refresh_btn_ok, **_combo_kwargs(),
        )
        self.entry_productname.grid(row=3, column=0, sticky='ew')

        actions = ctk.CTkFrame(self, fg_color='transparent')
        actions.grid(row=2, column=0, sticky='ew', padx=16, pady=(12, 20))
        self.btn_ok = _dialog_action_row(
            actions, self, t('common.save'), self.export_product, ok_kwargs={'state': 'disabled'},
        )

    def refresh_combobox(self, *args):
        products = admin_service.list_products(self.entry_clientname.get())
        self.entry_productname.set('')
        self.entry_productname.configure(state='normal', values=products)
        self.btn_ok.configure(state='disabled')

    def refresh_btn_ok(self, *args):
        if self.entry_productname.get():
            self.btn_ok.configure(state='normal')

    def export_product(self):
        client = self.entry_clientname.get()
        product = self.entry_productname.get()
        path = asksaveasfilename(defaultextension=".json", filetypes=[(t('config.import_file_filter'), "*.json")],
                                 initialfile=f'{client}-{product}')
        try:
            if path:
                result = build_export_payload(client, product, admin_service.get_db())
                with open(path, 'w') as arquivo_json:
                    json.dump(result, arquivo_json, indent=4)

                self.destroy()
                PopUpWindow(self.master, t('common.success'), t('import_export.saved_with_path', path=path))
        except Exception as e:
            PopUpWindow(self.master, t('import_export.error_title'), t('import_export.export_error_detail', error=e))


class AddClientWindow(ctk.CTkToplevel):
    def __init__(self, master, title, func, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iconbitmap(ICON)
        self.configure(fg_color=THEME_BG)

        self.geometry(calculate_center_screen_with_monitor(master, 400, 300, get_monitor(master)))
        self.minsize(400, 300)
        self.maxsize(400, 300)
        self.resizable(False, False)
        self.title(t('config.add_client'))
        self.master = master
        self.grab_set()
        self.func = func

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=0)

        _build_dialog_header(self, t('config.add_client'), t('client.add_subtitle'))

        body = ctk.CTkFrame(self, fg_color='transparent')
        body.grid(row=1, column=0, sticky='ew', padx=16, pady=(8, 0))
        body.grid_columnconfigure(0, weight=1)

        card, form = _section_card(body, title)
        card.pack(fill='x')
        form.grid_columnconfigure(0, weight=1)

        self.entry_name = ctk.CTkEntry(form, **_entry_kwargs())
        self.entry_name.grid(row=0, column=0, sticky='ew')
        self.entry_name.bind('<Return>', lambda _e: self.add_client())

        actions = ctk.CTkFrame(self, fg_color='transparent')
        actions.grid(row=2, column=0, sticky='ew', padx=16, pady=(12, 20))
        _dialog_action_row(actions, self, t('common.ok'), self.add_client)

    def add_client(self):
        if self.entry_name.get() in admin_service.list_client_names():
            PopUpWindow(self, t('client.duplicate_title'), t('client.duplicate_body'))
        else:
            admin_service.insert_client(self.entry_name.get())
            self.master.update_client_list()
            self.func()
            self.destroy()


class AuditWindow(ctk.CTkToplevel):
    """Tela de auditoria global (somente leitura do banco central).

    Cada registro ocupa duas linhas: a primeira com os metadados e a segunda
    (continuação) com os arquivos impressos / detalhe, evitando corte de texto.
    """

    _WINDOW_W = 1080
    _WINDOW_H = 620
    _INFO_WRAP = 64          # caracteres por linha na coluna de info
    _WIDTHS = (130, 90, 140, 95, 120, 140, 36, 470)

    def __init__(self, master, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iconbitmap(ICON)
        self.configure(fg_color=THEME_BG)
        self._category_labels = {
            t('audit.category_all'): None,
            t('audit.category_print'): 'print',
            t('audit.category_cadastro'): 'cadastro',
            t('audit.category_error'): 'error',
        }
        self._columns = (
            t('audit.col_datetime'), t('audit.col_pc'), t('audit.col_user'),
            t('audit.col_category'), t('audit.col_action'), t('audit.col_printer'),
            t('audit.col_ok'), t('audit.col_info'),
        )
        self._export_headers = (
            t('audit.col_datetime'), t('audit.col_pc'), t('audit.col_user'),
            t('audit.col_category'), t('audit.col_action'), t('audit.col_printer'),
            t('audit.col_ok'), t('audit.export_files'), t('audit.export_detail'),
        )
        self.geometry(calculate_center_screen_with_monitor(
            master, self._WINDOW_W, self._WINDOW_H, get_monitor(master),
        ))
        self.minsize(self._WINDOW_W, self._WINDOW_H)
        self.resizable(True, True)
        self.title(t('audit.title'))
        self.master = master
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(self, fg_color=THEME_CARD, corner_radius=0, height=56)
        header.grid(row=0, column=0, sticky='ew')
        header.grid_propagate(False)
        title_col = ctk.CTkFrame(header, fg_color='transparent')
        title_col.pack(side='left', padx=16, pady=10)
        ctk.CTkLabel(
            title_col, text=t('audit.title'), font=(FONT, 18, 'bold'), text_color='white',
        ).pack(anchor='w')
        ctk.CTkLabel(
            title_col, text=t('audit.subtitle'), font=(FONT, 11),
            text_color=THEME_TEXT_SECONDARY,
        ).pack(anchor='w')

        filter_card = ctk.CTkFrame(
            self, fg_color=THEME_CARD, corner_radius=12,
            border_width=1, border_color=THEME_CARD_BORDER,
        )
        filter_card.grid(row=1, column=0, padx=14, pady=(10, 8), sticky='ew')
        filters = ctk.CTkFrame(filter_card, fg_color='transparent')
        filters.pack(fill='x', padx=12, pady=10)
        filters.grid_columnconfigure(7, weight=1)

        ctk.CTkLabel(filters, text=t('audit.date_from'), font=(FONT, 11), text_color=THEME_TEXT_SECONDARY).grid(
            row=0, column=0, padx=(0, 4), sticky='w',
        )
        self.entry_from = ctk.CTkEntry(filters, width=100, **_entry_kwargs())
        self.entry_from.grid(row=0, column=1, padx=(0, 8), sticky='w')

        ctk.CTkLabel(filters, text=t('audit.date_to'), font=(FONT, 11), text_color=THEME_TEXT_SECONDARY).grid(
            row=0, column=2, padx=(0, 4), sticky='w',
        )
        self.entry_to = ctk.CTkEntry(filters, width=100, **_entry_kwargs())
        self.entry_to.grid(row=0, column=3, padx=(0, 8), sticky='w')

        ctk.CTkLabel(filters, text=t('audit.user'), font=(FONT, 11), text_color=THEME_TEXT_SECONDARY).grid(
            row=0, column=4, padx=(0, 4), sticky='w',
        )
        self.entry_user = ctk.CTkEntry(filters, width=100, **_entry_kwargs())
        self.entry_user.grid(row=0, column=5, padx=(0, 8), sticky='w')

        ctk.CTkLabel(filters, text=t('audit.printer'), font=(FONT, 11), text_color=THEME_TEXT_SECONDARY).grid(
            row=0, column=6, padx=(0, 4), sticky='w',
        )
        self.entry_printer = ctk.CTkEntry(filters, width=100, **_entry_kwargs())
        self.entry_printer.grid(row=0, column=7, padx=(0, 8), sticky='w')

        ctk.CTkLabel(filters, text=t('audit.file'), font=(FONT, 11), text_color=THEME_TEXT_SECONDARY).grid(
            row=1, column=0, padx=(0, 4), pady=(8, 0), sticky='w',
        )
        self.entry_file = ctk.CTkEntry(
            filters, width=160, placeholder_text=t('audit.file_placeholder'), **_entry_kwargs(),
        )
        self.entry_file.grid(row=1, column=1, columnspan=2, padx=(0, 8), pady=(8, 0), sticky='w')
        self.entry_file.bind('<Return>', lambda _e: self.refresh())

        self.combo_category = ctk.CTkComboBox(
            filters, width=120, values=list(self._category_labels.keys()), **_combo_kwargs(),
        )
        self.combo_category.set(t('audit.category_all'))
        self.combo_category.grid(row=1, column=3, padx=(0, 8), pady=(8, 0), sticky='w')

        ctk.CTkButton(
            filters, text=t('audit.search'), width=88,
            fg_color=THEME_ACCENT, hover_color=THEME_ACCENT_HOVER,
            corner_radius=8, height=32, command=self.refresh,
        ).grid(row=1, column=4, padx=(0, 6), pady=(8, 0), sticky='w')

        actions = ctk.CTkFrame(filters, fg_color='transparent')
        actions.grid(row=1, column=5, columnspan=4, pady=(8, 0), sticky='e')
        ctk.CTkButton(
            actions, text=t('audit.copy_all'), width=96, command=self.copy_all, **_secondary_btn_kwargs(),
        ).pack(side='left', padx=(0, 6))
        ctk.CTkButton(
            actions, text=t('audit.copy_selection'), width=110, command=self.copy_selected,
            **_secondary_btn_kwargs(),
        ).pack(side='left')

        self._rows = []
        self._item_to_index = {}

        table_card = ctk.CTkFrame(
            self, fg_color=THEME_CARD, corner_radius=12,
            border_width=1, border_color=THEME_CARD_BORDER,
        )
        table_card.grid(row=2, column=0, padx=14, pady=(0, 8), sticky='nsew')
        table_card.grid_rowconfigure(0, weight=1)
        table_card.grid_columnconfigure(0, weight=1)

        table_host = ctk.CTkFrame(
            table_card, fg_color=THEME_BG, corner_radius=8,
            border_width=1, border_color=THEME_CARD_BORDER,
        )
        table_host.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)
        table_host.grid_rowconfigure(0, weight=1)
        table_host.grid_columnconfigure(0, weight=1)

        try:
            style = ttk.Style(self)
            style.configure('Audit.Treeview', rowheight=22)
        except Exception:
            pass

        self.table = Table(table_host, list(self._columns), show='headings', style='Audit.Treeview')
        for i, width in enumerate(self._WIDTHS, start=1):
            anchor = 'w' if i in (3, 5, 8) else 'center'
            self.table.column(f'#{i}', width=width, anchor=anchor)
        self.table.tag_configure('rec_a', background=THEME_TABLE_ROW_A)
        self.table.tag_configure('rec_b', background=THEME_TABLE_ROW_B)
        self.table.bind('<Control-c>', lambda _e: self.copy_selected())
        self.table.bind('<Control-C>', lambda _e: self.copy_selected())
        self.table.grid(row=0, column=0, sticky='nsew', padx=4, pady=4)

        self.lbl_status = ctk.CTkLabel(
            self, text='', font=(FONT, 11), text_color=THEME_TEXT_SECONDARY,
        )
        self.lbl_status.grid(row=3, column=0, padx=16, pady=(0, 10), sticky='w')

        self.refresh()

    def _date_bounds(self):
        local_from = local_to = None
        date_from = self.entry_from.get().strip()
        date_to = self.entry_to.get().strip()
        if date_from:
            local_from = f'{date_from} 00:00:00'
        if date_to:
            local_to = f'{date_to} 23:59:59'
        return local_from, local_to

    @staticmethod
    def _build_info(row):
        """Texto da coluna larga: arquivos impressos e/ou detalhe."""
        parts = []
        product = (row.get('product') or '').strip()
        if product:
            parts.append(t('audit.info_files', product=product))
        detail = (row.get('detail') or '').replace('\n', ' ').strip()
        if detail:
            parts.append(t('audit.info_detail', detail=detail))
        return '   |   '.join(parts)

    def _wrap_two_lines(self, info):
        if not info:
            return '', ''
        lines = textwrap.wrap(info, width=self._INFO_WRAP) or ['']
        line1 = lines[0]
        line2 = lines[1] if len(lines) > 1 else ''
        if len(lines) > 2:
            line2 = line2[:self._INFO_WRAP - 1] + '…'
        return line1, line2

    def refresh(self):
        for item in self.table.get_children():
            self.table.delete(item)
        self._item_to_index = {}

        local_from, local_to = self._date_bounds()
        rows = audit.query_events(
            local_from=local_from,
            local_to=local_to,
            user=self.entry_user.get().strip() or None,
            printer=self.entry_printer.get().strip() or None,
            product=self.entry_file.get().strip() or None,
            category=self._category_labels.get(self.combo_category.get()),
            limit=1000,
        )
        self._rows = rows

        for index, row in enumerate(rows):
            tag = 'rec_a' if index % 2 == 0 else 'rec_b'
            success = row.get('success')
            ok = t('audit.status_ok') if success else t('audit.status_fail')
            line1, line2 = self._wrap_two_lines(self._build_info(row))

            iid_main = self.table.insert('', 'end', tags=(tag,), values=(
                row.get('ts_local') or '',
                row.get('pc_name') or '',
                row.get('windows_user') or '',
                row.get('category') or '',
                row.get('action') or '',
                row.get('printer') or '',
                ok,
                line1,
            ))
            iid_cont = self.table.insert('', 'end', tags=(tag,), values=(
                '', '', '', '', '', '', '', line2,
            ))
            self._item_to_index[iid_main] = index
            self._item_to_index[iid_cont] = index

        self.lbl_status.configure(text=t('audit.records_status', count=len(rows)))

    @staticmethod
    def _clean_cell(value):
        text = '' if value is None else str(value)
        return text.replace('\t', ' ').replace('\r', ' ').replace('\n', ' ')

    def _record_to_cells(self, row):
        success = row.get('success')
        ok = '' if success is None else (t('audit.status_ok') if success else t('audit.status_fail'))
        return [
            self._clean_cell(row.get('ts_local')),
            self._clean_cell(row.get('pc_name')),
            self._clean_cell(row.get('windows_user')),
            self._clean_cell(row.get('category')),
            self._clean_cell(row.get('action')),
            self._clean_cell(row.get('printer')),
            ok,
            self._clean_cell(row.get('product')),
            self._clean_cell(row.get('detail')),
        ]

    def _rows_to_tsv(self, records):
        lines = ['\t'.join(self._export_headers)]
        for row in records:
            lines.append('\t'.join(self._record_to_cells(row)))
        return '\n'.join(lines)

    def _copy_to_clipboard(self, text, count):
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update()  # ensure clipboard persists after the window closes
            self.lbl_status.configure(text=t('audit.copied_status', count=count))
        except Exception:
            self.lbl_status.configure(text=t('audit.copy_failed'))

    def copy_all(self):
        if not self._rows:
            self.lbl_status.configure(text=t('audit.nothing_to_copy'))
            return
        self._copy_to_clipboard(self._rows_to_tsv(self._rows), len(self._rows))

    def copy_selected(self):
        selection = self.table.selection()
        indexes = []
        for item in selection:
            idx = self._item_to_index.get(item)
            if idx is not None and idx not in indexes:
                indexes.append(idx)
        if not indexes:
            self.copy_all()
            return
        records = [self._rows[i] for i in indexes]
        self._copy_to_clipboard(self._rows_to_tsv(records), len(records))


