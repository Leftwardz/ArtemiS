import json
import os
import textwrap
import traceback

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
    save_audit_central_location,
    save_database_location,
    save_language,
    save_locales_folder,
    save_print_backend,
    save_search_folder,
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
from app.ui.components import ConfirmWindow, ListBox, PopUpWindow, Table
from app.ui.constants import (
    BTN_HOVER_RED,
    BTN_RED,
    DEFAULT_WIDTH,
    FONT,
    ICON,
)
from app.ui.designer_window import EditWindow
from app.utils.window_geometry import calculate_center_screen_with_monitor, get_monitor


class ConfigWindow(ctk.CTkToplevel):
    def __init__(self, master, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title(t('config.title'))

        self.geometry(calculate_center_screen_with_monitor(master, DEFAULT_WIDTH, 600, get_monitor(master)))
        self.minsize(DEFAULT_WIDTH, 600)
        self.maxsize(DEFAULT_WIDTH, 600)
        self.resizable(False, False)
        self.master = master
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        ctk.deactivate_automatic_dpi_awareness()

        self.edit_window = None
        self.btn_edit = None
        self.btn_duplicate = None
        self.btn_delete_client = None
        self.btn_add_product = None
        self.btn_edit_product = None

        label = ctk.CTkLabel(self, text=t('config.title'), font=(FONT, 18, "bold"))
        label.grid(row=0, column=0, columnspan=2, padx=10, pady=10)

        self.frame = ctk.CTkFrame(self, fg_color='transparent')
        self.frame.grid(row=1, column=0, padx=10, sticky='W')

        self.btn_add_client = ctk.CTkButton(self.frame, text=t('config.add_client'), command=self.create_client)
        self.btn_add_client.grid(row=0, column=0, sticky='W')

        client_names = admin_service.list_client_names()
        self.client_list = ListBox(
            self, items=client_names, label_text=t('config.clients'), width=345, height=150,
            on_select=lambda _child: self.refresh(),
        )
        self.client_list.grid(row=2, column=0, columnspan=1, padx=10, pady=10)

        self.product_list = ListBox(
            self, [], child=True, width=345, height=150, label_text=t('config.products'),
            on_select=lambda _child: self.refresh(True),
        )
        self.product_list.grid(row=2, column=1, columnspan=1, padx=10, pady=10)

        # ############################# Config Frame ##################################################

        self.main_frame = ctk.CTkScrollableFrame(self, height=280)
        self.main_frame.grid(row=3, column=0, padx=10, columnspan=2, sticky='NSEW')

        ctk.CTkLabel(self.main_frame, text=t('config.import_export'), font=(FONT, 15, "bold")) \
            .grid(row=1, column=0, columnspan=2, padx=10, sticky='W')

        ctk.CTkButton(self.main_frame, text=t('config.import'), command=self.import_product). \
            grid(row=2, padx=10, pady=5, column=0, sticky='W')

        ctk.CTkButton(self.main_frame, text=t('config.export'),
                      command=lambda: ExportProductWindow(self)).grid(row=3, padx=10, pady=5, column=0, sticky='W')

        # ------------------------------- Search Folder -------------------------------------------------

        ctk.CTkLabel(self.main_frame, text=t('config.search_folder'), font=(FONT, 15, "bold")) \
            .grid(row=4, column=0, columnspan=2, padx=10, sticky='W')

        self.inpt_search_folder = ctk.CTkEntry(self.main_frame, width=220)
        self.inpt_search_folder.grid(row=5, column=0, padx=10, sticky='W')
        search_folder = get_search_folder()
        if search_folder:
            self.inpt_search_folder.insert(0, search_folder)

        self.btn_save_folder = ctk.CTkButton(self.main_frame, text=t('config.save'), width=80,
                                             state='disabled', command=self.save_folder)
        self.btn_save_folder.grid(row=5, column=1, sticky='W')

        # ------------------------------- DataBase Location --------------------------------------------
        ctk.CTkLabel(self.main_frame, text=t('config.database'), font=(FONT, 15, "bold")) \
            .grid(row=6, column=0, columnspan=2, padx=10, sticky='W')

        self.inpt_db_location = ctk.CTkEntry(self.main_frame, width=220)
        self.inpt_db_location.grid(row=7, column=0, padx=10, sticky='W')
        database_location = get_database_location()
        if database_location:
            self.inpt_db_location.insert(0, database_location)

        self.btn_save_db = ctk.CTkButton(self.main_frame, text=t('config.save'), width=80,
                                         state='disabled', command=self.save_database_location)
        self.btn_save_db.grid(row=7, column=1, sticky='W')

        # ------------------------------- Config Access --------------------------------------------
        ctk.CTkLabel(self.main_frame, text=t('config.config_access'), font=(FONT, 15, "bold")) \
            .grid(row=8, column=0, columnspan=2, padx=10, sticky='W')

        current_user = admin_service.get_current_windows_user()
        admin_hint = t('config.admin_suffix') if admin_service.is_windows_admin() else ''
        ctk.CTkLabel(
            self.main_frame,
            text=t('config.current_user', user=current_user, admin=admin_hint),
            font=(FONT, 11),
        ).grid(row=9, column=0, columnspan=2, padx=10, sticky='W')

        ctk.CTkLabel(
            self.main_frame,
            text=t('config.admin_always_access'),
            font=(FONT, 11),
            text_color='gray',
        ).grid(row=10, column=0, columnspan=2, padx=10, sticky='W')

        self.btn_manage_access = ctk.CTkButton(
            self.main_frame, text=t('config.manage_access'), width=120,
            command=lambda: ManageAccessWindow(self),
        )
        self.btn_manage_access.grid(row=11, column=0, padx=10, pady=5, sticky='W')

        self.btn_audit = ctk.CTkButton(
            self.main_frame, text=t('config.audit_logs'), width=120,
            command=lambda: AuditWindow(self),
        )
        self.btn_audit.grid(row=12, column=0, padx=10, pady=5, sticky='W')

        ctk.CTkLabel(self.main_frame, text=t('config.audit_db'), font=(FONT, 15, "bold")) \
            .grid(row=13, column=0, columnspan=2, padx=10, sticky='W')

        self.inpt_audit_location = ctk.CTkEntry(
            self.main_frame, width=220,
            placeholder_text=r'\\servidor\pasta\artemis_audit_central.db',
        )
        self.inpt_audit_location.grid(row=14, column=0, padx=10, sticky='W')
        audit_location = get_audit_central_location()
        if audit_location:
            self.inpt_audit_location.insert(0, audit_location)

        self.btn_save_audit_location = ctk.CTkButton(
            self.main_frame, text=t('config.save'), width=80,
            command=self.save_audit_location,
        )
        self.btn_save_audit_location.grid(row=14, column=1, sticky='W')

        ctk.CTkLabel(
            self.main_frame,
            text=t('config.audit_hint'),
            font=(FONT, 10),
            text_color='gray',
        ).grid(row=15, column=0, columnspan=2, padx=10, sticky='W')

        # ------------------------------- Language / i18n --------------------------------------------
        ctk.CTkLabel(self.main_frame, text=t('config.language_section'), font=(FONT, 15, "bold")) \
            .grid(row=16, column=0, columnspan=2, padx=10, sticky='W', pady=(8, 0))

        ctk.CTkLabel(self.main_frame, text=t('config.language_label'), font=(FONT, 11)) \
            .grid(row=17, column=0, padx=10, sticky='W')

        self._lang_labels = {label: code for code, label in available_languages()}
        self.combo_default_language = ctk.CTkComboBox(
            self.main_frame, width=220,
            values=[label for _, label in available_languages()],
            command=self._on_default_language_pick,
        )
        self.combo_default_language.grid(row=17, column=1, padx=10, sticky='W')
        current_code = get_language()
        self.combo_default_language.set(get_i18n().language_label(current_code))

        ctk.CTkLabel(self.main_frame, text=t('config.locales_folder'), font=(FONT, 11)) \
            .grid(row=18, column=0, padx=10, sticky='W', pady=(6, 0))

        self.inpt_locales_folder = ctk.CTkEntry(self.main_frame, width=220)
        self.inpt_locales_folder.grid(row=18, column=1, padx=10, sticky='W', pady=(6, 0))
        locales_folder = get_locales_folder()
        if locales_folder:
            self.inpt_locales_folder.insert(0, locales_folder)

        self.btn_save_locales_folder = ctk.CTkButton(
            self.main_frame, text=t('config.save'), width=80,
            command=self.save_locales_folder,
        )
        self.btn_save_locales_folder.grid(row=19, column=1, sticky='W', pady=4)

        ctk.CTkLabel(
            self.main_frame,
            text=t('config.locales_hint'),
            font=(FONT, 10),
            text_color='gray',
            justify='left',
        ).grid(row=20, column=0, columnspan=2, padx=10, sticky='W')

        locales_row = ctk.CTkFrame(self.main_frame, fg_color='transparent')
        locales_row.grid(row=21, column=0, columnspan=2, padx=10, pady=4, sticky='W')
        ctk.CTkButton(
            locales_row, text=t('config.open_locales_folder'), width=160,
            command=self.open_locales_folder,
        ).pack(side='left', padx=(0, 8))
        ctk.CTkButton(
            locales_row, text=t('config.reload_locales'), width=120,
            command=self.reload_locales,
        ).pack(side='left')

        self.lbl_available_locales = ctk.CTkLabel(
            self.main_frame,
            text=self._available_locales_text(),
            font=(FONT, 10),
            text_color='gray',
            justify='left',
        )
        self.lbl_available_locales.grid(row=22, column=0, columnspan=2, padx=10, sticky='W', pady=(0, 8))

        # ------------------------------- Printers ---------------------------------------------
        ctk.CTkLabel(self.main_frame, text=t('config.printers'), font=(FONT, 15, "bold")) \
            .grid(row=1, column=2, padx=50, sticky='W')

        count = len(admin_service.list_registered_printers())
        ctk.CTkLabel(
            self.main_frame,
            text=t('config.printers_count', count=count),
            font=(FONT, 11),
            text_color='gray',
        ).grid(row=2, column=2, padx=50, sticky='W')

        self.btn_manage_printers = ctk.CTkButton(
            self.main_frame, text=t('config.manage_printers'), width=140,
            command=lambda: ManagePrintersWindow(self),
        )
        self.btn_manage_printers.grid(row=3, column=2, padx=50, pady=5, sticky='W')

        ctk.CTkLabel(self.main_frame, text=t('config.print_backend'), font=(FONT, 15, "bold")) \
            .grid(row=4, column=2, padx=50, sticky='W')

        backend_values = self._available_backend_labels()
        self.combo_print_backend = ctk.CTkComboBox(
            self.main_frame, width=200, values=backend_values,
        )
        self.combo_print_backend.grid(row=5, column=2, padx=50, sticky='W')
        self.combo_print_backend.set(get_print_backend_label())

        ctk.CTkLabel(
            self.main_frame,
            text=t('config.print_backend_hint'),
            font=(FONT, 10),
            text_color='gray',
            wraplength=280,
        ).grid(row=6, column=2, padx=50, sticky='W')

        self.btn_save_print_backend = ctk.CTkButton(
            self.main_frame, text=t('config.save_backend'), width=100,
            command=self.save_print_backend,
        )
        self.btn_save_print_backend.grid(row=7, column=2, padx=50, pady=5, sticky='W')

        # ------------------------------- List or Printing Groups ---------------------------------------------
        ctk.CTkLabel(self.main_frame, text=t('config.print_groups'), font=(FONT, 15, "bold")) \
            .grid(row=8, column=2, padx=50, sticky='W')

        self.btn_manage_groups = ctk.CTkButton(self.main_frame, text=t('config.manage_groups_btn'), width=80,
                                               command=lambda: ManageGroupWindow(self, t('group.manage_title')))
        self.btn_manage_groups.grid(row=9, column=2, padx=50, sticky='W')
        # #################### Event Binds ##########################################
        self.inpt_db_location.bind('<KeyRelease>', self.update_save_button)
        self.inpt_search_folder.bind('<KeyRelease>', self.update_save_button)
        self.inpt_db_location.bind('<Return>', self.save_database_location)
        self.inpt_search_folder.bind('<Return>', self.save_folder)

        self.protocol("WM_DELETE_WINDOW", self.exit)

    def save_database_location(self):
        folder = self.inpt_db_location.get()
        result = save_database_location(folder)
        if not result.ok:
            PopUpWindow(self, t('common.error'), result.error)
            return
        if result.message:
            self.update_save_button()
            self.exit()
            PopUpWindow(self.master, t('common.success'), result.message)

    def save_audit_location(self):
        result = save_audit_central_location(self.inpt_audit_location.get())
        if not result.ok:
            PopUpWindow(self, t('common.error'), result.error)
            return
        if result.message:
            PopUpWindow(self, t('common.success'), result.message)

    @staticmethod
    def _available_backend_labels():
        """Rótulos dos backends disponíveis na máquina (sempre inclui o atual)."""
        try:
            from app.utils.printing.registry import list_backends
            labels = [label for _name, label, available, _exp in list_backends() if available]
        except Exception:
            labels = []
        current = get_print_backend_label()
        if not labels:
            labels = list(PRINT_BACKEND_LABELS.values())
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
        if hasattr(self.master, 'apply_language'):
            self.master.apply_language()
        self._lang_labels = {lbl: c for c, lbl in available_languages()}
        self.combo_default_language.configure(values=[lbl for _, lbl in available_languages()])
        self.combo_default_language.set(get_i18n().language_label(code))
        self.lbl_available_locales.configure(text=self._available_locales_text())
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
        if hasattr(self.master, 'apply_language'):
            self.master.apply_language()

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
        self.withdraw()

    def update_product_list(self, products):
        self.product_list.destroy()
        self.product_list = ListBox(
            self, products, child=True, width=345, height=150, label_text=t('config.products'),
            on_select=lambda _child: self.refresh(True),
        )
        self.product_list.grid(row=2, column=1, columnspan=1, padx=10, pady=10)

    def update_client_list(self):
        clients = admin_service.list_client_names()
        self.client_list.destroy()
        self.client_list = ListBox(
            self, clients, width=345, height=150, label_text=t('config.clients'),
            on_select=lambda _child: self.refresh(),
        )
        self.client_list.grid(row=2, column=0, columnspan=1, padx=10, pady=10)

    def show_edit_button(self):
        if self.btn_edit:
            self.btn_edit.destroy()
            self.btn_duplicate.destroy()

        self.btn_duplicate = ctk.CTkButton(self, text=t('config.duplicate'), width=80,
                                           command=self.duplicate_product_window)
        self.btn_duplicate.grid(row=1, column=1, padx=100, sticky='E')

        self.btn_edit = ctk.CTkButton(self, text=t('config.edit'), width=80, command=lambda: self.open_edit_window('edit'))
        self.btn_edit.grid(row=1, column=1, padx=10, sticky='E')

    def duplicate_product_window(self):
        DuplicateProductWindow(self, t('config.duplicate_product_title'), self.client_list.radio_var.get(),
                               self.product_list.radio_var.get())

    def reset_all(self):
        self.delete_buttons()
        self.update_client_list()
        self.update_product_list([])

    def refresh(self, child=False):
        if not child:
            # We always need to destroy before create another one, because we will have more than one instance
            if self.btn_delete_client:
                self.btn_delete_client.destroy()
            if self.btn_add_product:
                self.btn_add_product.destroy()

            self.btn_delete_client = ctk.CTkButton(self, text=t('config.delete_client'), fg_color=BTN_RED,
                                                   hover_color=BTN_HOVER_RED,
                                                   command=self.confirm_delete)
            self.btn_delete_client.grid(row=1, column=0, padx=10, sticky='E')

            self.btn_add_product = ctk.CTkButton(self, text=t('config.add_product'),
                                                 command=lambda: self.open_edit_window('add'))
            self.btn_add_product.grid(row=1, column=1, padx=10, sticky='W')

            client = self.client_list.radio_var.get()
            self.update_product_list(admin_service.list_products(client))
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
        paper_size = product_file['paper_size']
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

    def exit(self):
        self.master.deiconify()
        self.master.focus_set()
        self.master.refresh()
        self.destroy()


class EditRegisteredPrinterWindow(ctk.CTkToplevel):
    def __init__(self, master, on_save, printer=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iconbitmap(ICON)
        self.title(t('printer.edit_title_edit') if (printer and printer.get('id')) else t('printer.edit_title_register'))
        self.master = master
        self.on_save = on_save
        self.printer = printer
        self.grab_set()

        self.geometry(calculate_center_screen_with_monitor(master, 420, 320, get_monitor(master)))
        self.minsize(420, 320)
        self.maxsize(420, 320)
        self.resizable(False, False)

        ctk.CTkLabel(self, text=self.title(), font=('Arial', 16, 'bold')) \
            .grid(row=0, column=0, columnspan=2, pady=10, padx=10)

        ctk.CTkLabel(self, text=t('printer.win_name_label')).grid(row=1, column=0, columnspan=2, padx=10, sticky='w')
        self.entry_name = ctk.CTkEntry(self, width=360)
        self.entry_name.grid(row=2, column=0, columnspan=2, padx=10, pady=(0, 8))

        ctk.CTkLabel(self, text=t('printer.display_name_label')).grid(row=3, column=0, columnspan=2, padx=10, sticky='w')
        self.entry_display = ctk.CTkEntry(self, width=360)
        self.entry_display.grid(row=4, column=0, columnspan=2, padx=10, pady=(0, 8))

        self.checkbox_enabled = ctk.CTkCheckBox(self, text=t('printer.enabled_production'))
        self.checkbox_enabled.grid(row=5, column=0, columnspan=2, padx=10, sticky='w')

        ctk.CTkLabel(self, text=t('printer.notes_label')).grid(row=6, column=0, columnspan=2, padx=10, sticky='w')
        self.entry_notes = ctk.CTkEntry(self, width=360)
        self.entry_notes.grid(row=7, column=0, columnspan=2, padx=10, pady=(0, 8))

        if printer:
            self.entry_name.insert(0, printer.get('name', ''))
            self.entry_display.insert(0, printer.get('display_name', ''))
            if printer.get('enabled', True):
                self.checkbox_enabled.select()
            if printer.get('notes'):
                self.entry_notes.insert(0, printer['notes'])

        ctk.CTkButton(self, text=t('common.save'), width=100, command=self.save) \
            .grid(row=8, column=0, padx=20, pady=15, sticky='e')
        ctk.CTkButton(self, text=t('common.cancel'), width=100, fg_color=BTN_RED,
                      hover_color=BTN_HOVER_RED, command=self.destroy) \
            .grid(row=8, column=1, padx=20, pady=15, sticky='w')

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
    _WINDOW_W = 540
    _WINDOW_H = 560

    def __init__(self, master, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iconbitmap(ICON)
        self.title(t('printer.manage_title'))
        self.master = master
        self.grab_set()

        self.geometry(calculate_center_screen_with_monitor(
            master, self._WINDOW_W, self._WINDOW_H, get_monitor(master),
        ))
        self.minsize(self._WINDOW_W, self._WINDOW_H)
        self.maxsize(self._WINDOW_W, self._WINDOW_H)
        self.resizable(False, False)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        body = ctk.CTkScrollableFrame(self, width=self._WINDOW_W - 20, height=self._WINDOW_H - 20)
        body.grid(row=0, column=0, padx=10, pady=10, sticky='nsew')
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(body, text=t('printer.registered_title'), font=('Arial', 16, 'bold')) \
            .grid(row=0, column=0, columnspan=2, pady=(0, 5), padx=5, sticky='w')

        self.table_frame = ctk.CTkFrame(body, width=500, height=self._FRAME_H, corner_radius=0)
        self.table_frame.grid_propagate(False)
        self.table_frame.pack_propagate(False)
        self.table_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky='ew')

        self.table = Table(
            self.table_frame, [t('printer.col_display'), t('printer.col_name'), t('printer.col_enabled'), t('printer.col_notes')],
            show='headings', height=self._TABLE_HEIGHT,
        )
        self.table.column('#1', width=120)
        self.table.column('#2', width=180)
        self.table.column('#3', width=50)
        self.table.column('#4', width=120)
        self.table.pack(expand=True, fill='both', padx=2, pady=2)

        btn_row = ctk.CTkFrame(body, fg_color='transparent')
        btn_row.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky='ew')

        ctk.CTkButton(btn_row, text=t('common.new'), width=80, command=self.add_printer) \
            .pack(side='left', padx=(0, 5))
        ctk.CTkButton(btn_row, text=t('common.edit'), width=80, command=self.edit_printer) \
            .pack(side='left', padx=5)
        ctk.CTkButton(btn_row, text=t('common.remove'), width=80, fg_color=BTN_RED,
                      hover_color=BTN_HOVER_RED, command=self.remove_printer) \
            .pack(side='left', padx=5)
        ctk.CTkButton(btn_row, text=t('common.verify'), width=90, command=self.verify_selected) \
            .pack(side='right')

        self.refresh_table()

        ctk.CTkLabel(body, text=t('printer.discover_title'), font=(FONT, 13, 'bold')) \
            .grid(row=3, column=0, columnspan=2, padx=5, sticky='w', pady=(10, 0))

        discover_row = ctk.CTkFrame(body, fg_color='transparent')
        discover_row.grid(row=4, column=0, columnspan=2, padx=5, sticky='ew')

        ctk.CTkButton(discover_row, text=t('printer.discover_windows'), width=130, command=self.discover) \
            .pack(side='left')
        ctk.CTkButton(discover_row, text=t('printer.add_selected'), width=140, command=self.add_from_discovery) \
            .pack(side='right')

        self.discover_frame = ctk.CTkFrame(body, width=500, height=self._FRAME_H, corner_radius=0)
        self.discover_frame.grid_propagate(False)
        self.discover_frame.pack_propagate(False)
        self.discover_frame.grid(row=5, column=0, columnspan=2, padx=5, pady=5, sticky='ew')

        self.discover_table = Table(
            self.discover_frame, [t('printer.col_installed')], show='headings', height=self._TABLE_HEIGHT,
        )
        self.discover_table.column('#1', width=460)
        self.discover_table.pack(expand=True, fill='both', padx=2, pady=2)
        self._discovered = []

        ctk.CTkButton(body, text=t('common.close'), width=90, command=self.destroy) \
            .grid(row=6, column=1, padx=5, pady=(10, 5), sticky='e')

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
        name = selected[0][0].replace(' (já cadastrada)', '').strip()
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
    _WINDOW_W = 520
    _WINDOW_H = 580

    def __init__(self, master, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iconbitmap(ICON)

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
        self.grid_rowconfigure(0, weight=1)

        body = ctk.CTkScrollableFrame(self, width=self._WINDOW_W - 20, height=self._WINDOW_H - 20)
        body.grid(row=0, column=0, padx=10, pady=10, sticky='nsew')
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(body, text=t('access.authorized_title'), font=('Arial', 16, 'bold')) \
            .grid(row=0, column=0, columnspan=2, pady=(0, 5), padx=5, sticky='w')

        self.table_frame = ctk.CTkFrame(
            body, width=480, height=self._AUTHORIZED_FRAME_H, corner_radius=0,
        )
        self.table_frame.grid_propagate(False)
        self.table_frame.pack_propagate(False)
        self.table_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky='ew')
        self.table = Table(
            self.table_frame, [t('access.col_principal'), t('access.col_type')], show='headings', height=self._TABLE_HEIGHT,
        )
        self.table.column('#1', width=320)
        self.table.column('#2', width=80)
        self.table.pack(expand=True, fill='both', padx=2, pady=2)
        self.refresh_table()

        self.btn_delete = ctk.CTkButton(
            body, text=t('access.remove_selected'), width=140, fg_color=BTN_RED,
            hover_color=BTN_HOVER_RED, command=self.remove_selected,
        )
        self.btn_delete.grid(row=2, column=1, padx=5, pady=5, sticky='e')

        ctk.CTkLabel(body, text=t('access.search_title'), font=(FONT, 13, 'bold')) \
            .grid(row=3, column=0, columnspan=2, padx=5, sticky='w', pady=(10, 0))

        search_frame = ctk.CTkFrame(body, fg_color='transparent')
        search_frame.grid(row=4, column=0, columnspan=2, padx=5, sticky='ew')

        self.entry_search = ctk.CTkEntry(search_frame, width=220, placeholder_text=t('access.search_hint'))
        self.entry_search.pack(side='left', padx=(0, 5))
        self.entry_search.bind('<Return>', self.search_principals)

        self._type_combo_labels = {
            t('access.type_both'): 'both',
            t('access.type_user'): 'user',
            t('access.type_group'): 'group',
        }
        self.combo_type = ctk.CTkComboBox(
            search_frame, width=100, values=list(self._type_combo_labels.keys()),
        )
        self.combo_type.set(t('access.type_both'))
        self.combo_type.pack(side='left', padx=5)

        ctk.CTkButton(search_frame, text=t('access.search_btn'), width=90, command=self.search_principals) \
            .pack(side='left', padx=5)

        self.results_frame = ctk.CTkFrame(
            body, width=480, height=self._RESULTS_FRAME_H, corner_radius=0,
        )
        self.results_frame.grid_propagate(False)
        self.results_frame.pack_propagate(False)
        self.results_frame.grid(row=5, column=0, columnspan=2, padx=5, pady=5, sticky='ew')
        self.results_table = Table(
            self.results_frame, [t('access.col_search_result'), t('access.col_type')], show='headings', height=self._TABLE_HEIGHT,
        )
        self.results_table.column('#1', width=320)
        self.results_table.column('#2', width=80)
        self.results_table.pack(expand=True, fill='both', padx=2, pady=2)
        self._search_results = []

        ctk.CTkButton(body, text=t('access.add_selected'), width=140, command=self.add_selected) \
            .grid(row=6, column=1, padx=5, pady=5, sticky='e')

        ctk.CTkLabel(body, text=t('access.manual_hint'), font=(FONT, 11)) \
            .grid(row=7, column=0, columnspan=2, padx=5, sticky='w', pady=(8, 0))

        manual_frame = ctk.CTkFrame(body, fg_color='transparent')
        manual_frame.grid(row=8, column=0, columnspan=2, padx=5, sticky='ew')

        self.entry_manual = ctk.CTkEntry(manual_frame, width=280, placeholder_text=t('access.manual_placeholder'))
        self.entry_manual.pack(side='left', padx=(0, 5))
        self.entry_manual.bind('<Return>', self.add_manual)

        ctk.CTkButton(manual_frame, text=t('common.add'), width=90, command=self.add_manual) \
            .pack(side='left')

        #ctk.CTkButton(body, text=t('common.close'), width=90, command=self.destroy) \
        #    .grid(row=9, column=1, padx=5, pady=(10, 5), sticky='e')

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
        self._search_results = admin_service.search_windows_principals(query, self._type_filter())
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
    def __init__(self, master, title, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iconbitmap(ICON)

        self.geometry(calculate_center_screen_with_monitor(master, 400, 250, get_monitor(master)))
        self.minsize(400, 320)
        self.maxsize(400, 250)
        self.resizable(False, False)
        self.title(title)
        self.master = master
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(2, weight=1)

        lbl_client_name = ctk.CTkLabel(self, text=title, font=('Arial', 18, 'bold'))
        lbl_client_name.grid(row=0, column=0, columnspan=2, pady=5, padx=10)

        self.entry_name = ctk.CTkEntry(self, width=300)
        self.entry_name.grid(row=1, column=0, padx=10)

        self.btn_incluir = ctk.CTkButton(self, text=t("group.include"), width=120, command=self.add_group)
        self.btn_incluir.grid(row=1, column=1, pady=10, padx=5)

        self.btn_delete = ctk.CTkButton(self, text=t("group.delete_btn"), width=120, fg_color=BTN_RED,
                                        hover_color=BTN_HOVER_RED, command=self.delete_group)

        self.btn_delete.grid(row=2, column=1, pady=10, padx=5, sticky='S')
        # ################## List ##############################
        self.table_frame = ctk.CTkFrame(self, width=500, height=310, corner_radius=0)
        self.table_frame.grid(row=2, rowspan=5, column=0, padx=5, pady=5, sticky="nwse")

        self.table = Table(self.table_frame, [t('group.col_name')], show="headings")
        self.table.pack(expand=True, fill="both")

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


class DuplicateProductWindow(ctk.CTkToplevel):
    def __init__(self, master, title, original_client, original_product_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iconbitmap(ICON)

        self.geometry(calculate_center_screen_with_monitor(master, 400, 220, get_monitor(master)))
        self.minsize(400, 220)
        self.maxsize(400, 220)
        self.resizable(False, False)
        self.title(title)
        self.master = master
        self.product_name = original_product_name
        self.original_client = original_client
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text=title, font=('Arial', 18, 'bold')).grid(row=0, column=0, columnspan=2, pady=5, padx=10)

        ctk.CTkLabel(self, text=t('config.client_label')).grid(row=3, column=0, pady=5, padx=10)
        self.entry_clientname = ctk.CTkComboBox(self, width=140, values=admin_service.list_client_names())
        self.entry_clientname.grid(row=3, column=1, sticky='W')

        ctk.CTkLabel(self, text=t('config.product_name')).grid(row=4, column=0, columnspan=2, pady=5, padx=10)
        self.entry_productname = ctk.CTkEntry(self, width=300)
        self.entry_productname.grid(row=5, column=0, columnspan=2, padx=10)
        self.entry_productname.insert(0, original_product_name + '(1)')

        self.btn_ok = ctk.CTkButton(self, text=t("common.ok"), width=120, command=self.duplicate_product)
        self.btn_ok.grid(row=6, column=0, pady=10, padx=20)

        self.btn_cancelar = ctk.CTkButton(self, width=120, text=t("common.cancel"), fg_color=BTN_RED,
                                          hover_color=BTN_HOVER_RED, command=self.destroy)
        self.btn_cancelar.grid(row=6, column=1, pady=10, padx=20)

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

        self.geometry(calculate_center_screen_with_monitor(master, 400, 220, get_monitor(master)))
        self.minsize(400, 180)
        self.maxsize(400, 180)
        self.resizable(False, False)
        self.title(t('import_export.export_title'))
        self.master = master
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text=t('import_export.export_title'), font=('Arial', 18, 'bold')). \
            grid(row=0, column=0, columnspan=2, pady=5, padx=10)

        ctk.CTkLabel(self, text=t('config.client_label')).grid(row=3, column=0, pady=5, padx=10)
        self.entry_clientname = ctk.CTkComboBox(self, width=140, values=admin_service.list_client_names(),
                                                command=self.refresh_combobox)
        self.entry_clientname.grid(row=3, column=1, sticky='W')
        self.entry_clientname.set('')

        ctk.CTkLabel(self, text=t('config.products_label')).grid(row=4, column=0, pady=5, padx=10)

        self.entry_productname = ctk.CTkComboBox(self, width=140, state='disabled', command=self.refresh_btn_ok)
        self.entry_productname.grid(row=4, column=1, sticky='W')

        self.btn_ok = ctk.CTkButton(self, text=t("common.save"), width=120, state='disabled', command=self.export_product)
        self.btn_ok.grid(row=6, column=0, pady=10, padx=20)

        self.btn_cancelar = ctk.CTkButton(self, width=120, text=t("common.cancel"), fg_color=BTN_RED,
                                          hover_color=BTN_HOVER_RED, command=self.destroy)
        self.btn_cancelar.grid(row=6, column=1, pady=10, padx=20)

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
            PopUpWindow(self.master, t('import_export.error_title'), f'ERROR - {e}')


class AddClientWindow(ctk.CTkToplevel):
    def __init__(self, master, title, func, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iconbitmap(ICON)

        self.geometry(calculate_center_screen_with_monitor(master, 300, 130, get_monitor(master)))
        self.minsize(300, 120)
        self.maxsize(300, 120)
        self.resizable(False, False)
        self.title(title)
        self.master = master
        self.grab_set()
        self.func = func

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        lbl_client_name = ctk.CTkLabel(self, text=title, font=('Arial', 18, 'bold'))
        lbl_client_name.grid(row=0, column=0, columnspan=2, pady=5, padx=10)

        self.entry_name = ctk.CTkEntry(self, width=200)
        self.entry_name.grid(row=2, column=0, columnspan=2, padx=10)

        self.btn_ok = ctk.CTkButton(self, text=t("common.ok"), width=120, command=self.add_client)
        self.btn_ok.grid(row=6, column=0, pady=10, padx=20)

        self.btn_cancelar = ctk.CTkButton(self, width=120, text=t("common.cancel"), fg_color=BTN_RED,
                                          hover_color=BTN_HOVER_RED, command=self.destroy)
        self.btn_cancelar.grid(row=6, column=1, pady=10, padx=20)

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
        self.grid_rowconfigure(1, weight=1)

        filters = ctk.CTkFrame(self, fg_color='transparent')
        filters.grid(row=0, column=0, padx=10, pady=10, sticky='ew')

        ctk.CTkLabel(filters, text=t('audit.date_from')).pack(side='left', padx=(0, 3))
        self.entry_from = ctk.CTkEntry(filters, width=105)
        self.entry_from.pack(side='left', padx=(0, 8))

        ctk.CTkLabel(filters, text=t('audit.date_to')).pack(side='left', padx=(0, 3))
        self.entry_to = ctk.CTkEntry(filters, width=105)
        self.entry_to.pack(side='left', padx=(0, 8))

        ctk.CTkLabel(filters, text=t('audit.user')).pack(side='left', padx=(0, 3))
        self.entry_user = ctk.CTkEntry(filters, width=110)
        self.entry_user.pack(side='left', padx=(0, 8))

        ctk.CTkLabel(filters, text=t('audit.printer')).pack(side='left', padx=(0, 3))
        self.entry_printer = ctk.CTkEntry(filters, width=110)
        self.entry_printer.pack(side='left', padx=(0, 8))

        ctk.CTkLabel(filters, text=t('audit.file')).pack(side='left', padx=(0, 3))
        self.entry_file = ctk.CTkEntry(filters, width=120, placeholder_text=t('audit.file_placeholder'))
        self.entry_file.pack(side='left', padx=(0, 8))
        self.entry_file.bind('<Return>', lambda _e: self.refresh())

        self.combo_category = ctk.CTkComboBox(
            filters, width=130, values=list(self._category_labels.keys()),
        )
        self.combo_category.set(t('audit.category_all'))
        self.combo_category.pack(side='left', padx=(0, 8))

        ctk.CTkButton(filters, text=t('audit.search'), width=80, command=self.refresh) \
            .pack(side='left', padx=5)

        ctk.CTkButton(filters, text=t('audit.copy_all'), width=90, command=self.copy_all) \
            .pack(side='left', padx=(12, 3))
        ctk.CTkButton(filters, text=t('audit.copy_selection'), width=100, command=self.copy_selected) \
            .pack(side='left', padx=3)

        self._rows = []
        self._item_to_index = {}

        table_frame = ctk.CTkFrame(self, corner_radius=0)
        table_frame.grid(row=1, column=0, padx=10, pady=(0, 5), sticky='nsew')

        try:
            style = ttk.Style(self)
            style.configure('Audit.Treeview', rowheight=22)
        except Exception:
            pass

        self.table = Table(table_frame, list(self._columns), show='headings', style='Audit.Treeview')
        for i, width in enumerate(self._WIDTHS, start=1):
            anchor = 'w' if i in (3, 5, 8) else 'center'
            self.table.column(f'#{i}', width=width, anchor=anchor)
        self.table.tag_configure('rec_a', background='#242729')
        self.table.tag_configure('rec_b', background='#1b1d1e')
        self.table.bind('<Control-c>', lambda _e: self.copy_selected())
        self.table.bind('<Control-C>', lambda _e: self.copy_selected())
        self.table.pack(expand=True, fill='both', padx=2, pady=2)

        self.lbl_status = ctk.CTkLabel(self, text='', font=(FONT, 11), text_color='gray')
        self.lbl_status.grid(row=2, column=0, padx=10, pady=(0, 8), sticky='w')

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
            ok = '' if success is None else ('OK' if success else 'X')
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
        ok = '' if success is None else ('OK' if success else 'X')
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
            self.update()  # garante que o clipboard persista após fechar a janela
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


