import json
import os
import traceback

import customtkinter as ctk
from tkinter.filedialog import askdirectory, askopenfilename, asksaveasfilename

from app.services import admin_service
from app.services.settings_service import (
    get_database_location,
    get_search_folder,
    save_database_location,
    save_search_folder,
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
        self.title('Configurações')

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

        label = ctk.CTkLabel(self, text="Configurações", font=(FONT, 18, "bold"))
        label.grid(row=0, column=0, columnspan=2, padx=10, pady=10)

        self.frame = ctk.CTkFrame(self, fg_color='transparent')
        self.frame.grid(row=1, column=0, padx=10, sticky='W')

        self.btn_add_client = ctk.CTkButton(self.frame, text='Adicionar Cliente', command=self.create_client)
        self.btn_add_client.grid(row=0, column=0, sticky='W')

        client_names = admin_service.list_client_names()
        self.client_list = ListBox(
            self, items=client_names, label_text='Clientes', width=345, height=150,
            on_select=lambda _child: self.refresh(),
        )
        self.client_list.grid(row=2, column=0, columnspan=1, padx=10, pady=10)

        self.product_list = ListBox(
            self, [], child=True, width=345, height=150, label_text='Produtos',
            on_select=lambda _child: self.refresh(True),
        )
        self.product_list.grid(row=2, column=1, columnspan=1, padx=10, pady=10)

        # ############################# Config Frame ##################################################

        self.main_frame = ctk.CTkScrollableFrame(self, height=230)
        self.main_frame.grid(row=3, column=0, padx=10, columnspan=2, sticky='NSEW')

        ctk.CTkLabel(self.main_frame, text="Importar e Exportar", font=(FONT, 15, "bold")) \
            .grid(row=1, column=0, columnspan=2, padx=10, sticky='W')

        ctk.CTkButton(self.main_frame, text='Importar', command=self.import_product). \
            grid(row=2, padx=10, pady=5, column=0, sticky='W')

        ctk.CTkButton(self.main_frame, text='Exportar',
                      command=lambda: ExportProductWindow(self)).grid(row=3, padx=10, pady=5, column=0, sticky='W')

        # ------------------------------- Search Folder -------------------------------------------------

        ctk.CTkLabel(self.main_frame, text="Caminho para Buscar Arquivos", font=(FONT, 15, "bold")) \
            .grid(row=4, column=0, columnspan=2, padx=10, sticky='W')

        self.inpt_search_folder = ctk.CTkEntry(self.main_frame, width=220)
        self.inpt_search_folder.grid(row=5, column=0, padx=10, sticky='W')
        search_folder = get_search_folder()
        if search_folder:
            self.inpt_search_folder.insert(0, search_folder)

        self.btn_save_folder = ctk.CTkButton(self.main_frame, text='Salvar', width=80,
                                             state='disabled', command=self.save_folder)
        self.btn_save_folder.grid(row=5, column=1, sticky='W')

        # ------------------------------- DataBase Location --------------------------------------------
        ctk.CTkLabel(self.main_frame, text="Caminho para o Database", font=(FONT, 15, "bold")) \
            .grid(row=6, column=0, columnspan=2, padx=10, sticky='W')

        self.inpt_db_location = ctk.CTkEntry(self.main_frame, width=220)
        self.inpt_db_location.grid(row=7, column=0, padx=10, sticky='W')
        database_location = get_database_location()
        if database_location:
            self.inpt_db_location.insert(0, database_location)

        self.btn_save_db = ctk.CTkButton(self.main_frame, text='Salvar', width=80,
                                         state='disabled', command=self.save_database_location)
        self.btn_save_db.grid(row=7, column=1, sticky='W')

        # ------------------------------- Config Access --------------------------------------------
        ctk.CTkLabel(self.main_frame, text="Acesso à Configuração", font=(FONT, 15, "bold")) \
            .grid(row=8, column=0, columnspan=2, padx=10, sticky='W')

        current_user = admin_service.get_current_windows_user()
        admin_hint = ' (administrador Windows)' if admin_service.is_windows_admin() else ''
        ctk.CTkLabel(
            self.main_frame,
            text=f'Usuário atual: {current_user}{admin_hint}',
            font=(FONT, 11),
        ).grid(row=9, column=0, columnspan=2, padx=10, sticky='W')

        ctk.CTkLabel(
            self.main_frame,
            text='Administradores do PC/rede sempre têm acesso.',
            font=(FONT, 11),
            text_color='gray',
        ).grid(row=10, column=0, columnspan=2, padx=10, sticky='W')

        self.btn_manage_access = ctk.CTkButton(
            self.main_frame, text='Gerenciar Acesso', width=120,
            command=lambda: ManageAccessWindow(self),
        )
        self.btn_manage_access.grid(row=11, column=0, padx=10, pady=5, sticky='W')

        # ------------------------------- Printers ---------------------------------------------
        ctk.CTkLabel(self.main_frame, text="Impressoras", font=(FONT, 15, "bold")) \
            .grid(row=1, column=2, padx=50, sticky='W')

        count = len(admin_service.list_registered_printers())
        ctk.CTkLabel(
            self.main_frame,
            text=f'{count} cadastrada(s)',
            font=(FONT, 11),
            text_color='gray',
        ).grid(row=2, column=2, padx=50, sticky='W')

        self.btn_manage_printers = ctk.CTkButton(
            self.main_frame, text='Gerenciar Impressoras', width=140,
            command=lambda: ManagePrintersWindow(self),
        )
        self.btn_manage_printers.grid(row=3, column=2, padx=50, pady=5, sticky='W')

        # ------------------------------- List or Printing Groups ---------------------------------------------
        ctk.CTkLabel(self.main_frame, text="Gerenciar Grupos de Impressão", font=(FONT, 15, "bold")) \
            .grid(row=6, column=2, padx=50, sticky='W')

        self.btn_manage_groups = ctk.CTkButton(self.main_frame, text='Gerenciar Grupos', width=80,
                                               command=lambda: ManageGroupWindow(self, 'Gerenciar Grupos de Impressão'))
        self.btn_manage_groups.grid(row=7, column=2, padx=50, sticky='W')
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
            PopUpWindow(self, 'Erro', result.error)
            return
        if result.message:
            self.update_save_button()
            self.exit()
            PopUpWindow(self.master, 'Sucesso', result.message)

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
            PopUpWindow(self, 'Erro', result.error)
            return
        if result.message:
            self.update_save_button()
            PopUpWindow(self, 'Sucesso', result.message)

    def create_client(self):
        self.client = AddClientWindow(self, 'Nome do Cliente', self.delete_buttons)

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
            self, products, child=True, width=345, height=150, label_text='Produtos',
            on_select=lambda _child: self.refresh(True),
        )
        self.product_list.grid(row=2, column=1, columnspan=1, padx=10, pady=10)

    def update_client_list(self):
        clients = admin_service.list_client_names()
        self.client_list.destroy()
        self.client_list = ListBox(
            self, clients, width=345, height=150, label_text='Clientes',
            on_select=lambda _child: self.refresh(),
        )
        self.client_list.grid(row=2, column=0, columnspan=1, padx=10, pady=10)

    def show_edit_button(self):
        if self.btn_edit:
            self.btn_edit.destroy()
            self.btn_duplicate.destroy()

        self.btn_duplicate = ctk.CTkButton(self, text="Duplicar", width=80,
                                           command=self.duplicate_product_window)
        self.btn_duplicate.grid(row=1, column=1, padx=100, sticky='E')

        self.btn_edit = ctk.CTkButton(self, text="Editar", width=80, command=lambda: self.open_edit_window('edit'))
        self.btn_edit.grid(row=1, column=1, padx=10, sticky='E')

    def duplicate_product_window(self):
        DuplicateProductWindow(self, 'Duplicar Produto', self.client_list.radio_var.get(),
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

            self.btn_delete_client = ctk.CTkButton(self, text='Deletar Cliente', fg_color=BTN_RED,
                                                   hover_color=BTN_HOVER_RED,
                                                   command=self.confirm_delete)
            self.btn_delete_client.grid(row=1, column=0, padx=10, sticky='E')

            self.btn_add_product = ctk.CTkButton(self, text="Adicionar Produto",
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
        ConfirmWindow(self, 'Você tem certeza?', f'Você realmente deseja deletar o cliente {client}?',
                      self.delete_client)

    def delete_client(self):
        client = self.client_list.radio_var.get()
        if admin_service.delete_client(client):
            self.reset_all()
        else:
            PopUpWindow(self, 'Erro', f'Cliente não encontrado na base: {client}')

    def import_product(self):
        file_path = askopenfilename(filetypes=[("Arquivos JSON", "*.json")])
        if not file_path:
            return

        try:
            product_file = parse_import_file(file_path)
        except Exception as e:
            PopUpWindow(self, 'Erro', f'Erro ao ler o arquivo.\n{e}')
            return

        client_name = product_file['cliente']
        product_name = product_file['produto']
        paper_size = product_file['paper_size']
        color = product_file['color']
        orientation = product_file['orientation']
        items = product_file['items']

        if admin_service.list_client_names(client_name):
            if product_name in admin_service.list_products(client_name):
                def replace_drawing():
                    try:
                        replace_imported_drawings(client_name, product_name, items, admin_service.get_db())
                        PopUpWindow(self, 'Sucesso', 'Produto Substituído com sucesso!')
                    except Exception as e:
                        PopUpWindow(self, 'Erro', f'Não foi possível salvar o produto.\n{e}')

                text = f'Produto "{product_name}" já existente na base.\nDeseja Substituí-lo?'
                ConfirmWindow(self, 'Produto já existente', text, replace_drawing)
            else:
                try:
                    import_product_for_existing_client(
                        client_name, product_name, color, orientation, paper_size, items, admin_service.get_db()
                    )
                    PopUpWindow(self, 'Sucesso', 'Produto salvo com sucesso!')
                except Exception as e:
                    PopUpWindow(self, 'Erro', f'Erro ao salvar o produto.\n{e}')
        else:
            try:
                import_product_with_new_client(
                    client_name, product_name, color, orientation, paper_size, items, admin_service.get_db()
                )
                PopUpWindow(self, 'Sucesso', 'Cliente e Produto importados com sucesso!')
            except Exception as e:
                PopUpWindow(self, 'Erro', f'Erro ao criar um novo Cliente e Produto.\n{e}')

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
        self.title('Editar impressora' if (printer and printer.get('id')) else 'Cadastrar impressora')
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

        ctk.CTkLabel(self, text='Nome Windows (rede/local)').grid(row=1, column=0, columnspan=2, padx=10, sticky='w')
        self.entry_name = ctk.CTkEntry(self, width=360)
        self.entry_name.grid(row=2, column=0, columnspan=2, padx=10, pady=(0, 8))

        ctk.CTkLabel(self, text='Apelido (aparece na combo)').grid(row=3, column=0, columnspan=2, padx=10, sticky='w')
        self.entry_display = ctk.CTkEntry(self, width=360)
        self.entry_display.grid(row=4, column=0, columnspan=2, padx=10, pady=(0, 8))

        self.checkbox_enabled = ctk.CTkCheckBox(self, text='Ativa na tela de produção')
        self.checkbox_enabled.grid(row=5, column=0, columnspan=2, padx=10, sticky='w')

        ctk.CTkLabel(self, text='Observações').grid(row=6, column=0, columnspan=2, padx=10, sticky='w')
        self.entry_notes = ctk.CTkEntry(self, width=360)
        self.entry_notes.grid(row=7, column=0, columnspan=2, padx=10, pady=(0, 8))

        if printer:
            self.entry_name.insert(0, printer.get('name', ''))
            self.entry_display.insert(0, printer.get('display_name', ''))
            if printer.get('enabled', True):
                self.checkbox_enabled.select()
            if printer.get('notes'):
                self.entry_notes.insert(0, printer['notes'])

        ctk.CTkButton(self, text='Salvar', width=100, command=self.save) \
            .grid(row=8, column=0, padx=20, pady=15, sticky='e')
        ctk.CTkButton(self, text='Cancelar', width=100, fg_color=BTN_RED,
                      hover_color=BTN_HOVER_RED, command=self.destroy) \
            .grid(row=8, column=1, padx=20, pady=15, sticky='w')

    def save(self):
        name = self.entry_name.get().strip()
        display_name = self.entry_display.get().strip()
        enabled = bool(self.checkbox_enabled.get())
        notes = self.entry_notes.get().strip()

        if not name:
            PopUpWindow(self, 'Erro', 'Informe o nome Windows da impressora.')
            return
        if not display_name:
            display_name = name

        if not admin_service.verify_printer_available(name):
            PopUpWindow(
                self, 'Impressora não encontrada',
                f'O Windows não encontrou a impressora:\n{name}\n\n'
                'Verifique o nome ou instale a impressora neste PC.',
            )
            return

        if self.printer and self.printer.get('id'):
            ok = admin_service.update_registered_printer(
                self.printer['id'], name, display_name, enabled, notes,
            )
            if not ok:
                PopUpWindow(self, 'Erro', 'Não foi possível salvar. Nome Windows já cadastrado?')
                return
        else:
            ok = admin_service.add_registered_printer(name, display_name, enabled, notes)
            if not ok:
                PopUpWindow(self, 'Erro', f'A impressora "{name}" já está cadastrada.')
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
        self.title('Gerenciar Impressoras')
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

        ctk.CTkLabel(body, text='Impressoras cadastradas', font=('Arial', 16, 'bold')) \
            .grid(row=0, column=0, columnspan=2, pady=(0, 5), padx=5, sticky='w')

        self.table_frame = ctk.CTkFrame(body, width=500, height=self._FRAME_H, corner_radius=0)
        self.table_frame.grid_propagate(False)
        self.table_frame.pack_propagate(False)
        self.table_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky='ew')

        self.table = Table(
            self.table_frame, ['Apelido', 'Nome Windows', 'Ativa', 'Obs.'],
            show='headings', height=self._TABLE_HEIGHT,
        )
        self.table.column('#1', width=120)
        self.table.column('#2', width=180)
        self.table.column('#3', width=50)
        self.table.column('#4', width=120)
        self.table.pack(expand=True, fill='both', padx=2, pady=2)

        btn_row = ctk.CTkFrame(body, fg_color='transparent')
        btn_row.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky='ew')

        ctk.CTkButton(btn_row, text='Nova', width=80, command=self.add_printer) \
            .pack(side='left', padx=(0, 5))
        ctk.CTkButton(btn_row, text='Editar', width=80, command=self.edit_printer) \
            .pack(side='left', padx=5)
        ctk.CTkButton(btn_row, text='Remover', width=80, fg_color=BTN_RED,
                      hover_color=BTN_HOVER_RED, command=self.remove_printer) \
            .pack(side='left', padx=5)
        ctk.CTkButton(btn_row, text='Verificar', width=90, command=self.verify_selected) \
            .pack(side='right')

        self.refresh_table()

        ctk.CTkLabel(body, text='Descobrir impressoras neste PC', font=(FONT, 13, 'bold')) \
            .grid(row=3, column=0, columnspan=2, padx=5, sticky='w', pady=(10, 0))

        discover_row = ctk.CTkFrame(body, fg_color='transparent')
        discover_row.grid(row=4, column=0, columnspan=2, padx=5, sticky='ew')

        ctk.CTkButton(discover_row, text='Buscar no Windows', width=130, command=self.discover) \
            .pack(side='left')
        ctk.CTkButton(discover_row, text='Adicionar selecionada', width=140, command=self.add_from_discovery) \
            .pack(side='right')

        self.discover_frame = ctk.CTkFrame(body, width=500, height=self._FRAME_H, corner_radius=0)
        self.discover_frame.grid_propagate(False)
        self.discover_frame.pack_propagate(False)
        self.discover_frame.grid(row=5, column=0, columnspan=2, padx=5, pady=5, sticky='ew')

        self.discover_table = Table(
            self.discover_frame, ['Impressora instalada'], show='headings', height=self._TABLE_HEIGHT,
        )
        self.discover_table.column('#1', width=460)
        self.discover_table.pack(expand=True, fill='both', padx=2, pady=2)
        self._discovered = []

        ctk.CTkButton(body, text='Fechar', width=90, command=self.destroy) \
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
                'Sim' if item['enabled'] else 'Não',
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
            PopUpWindow(self, 'Aviso', 'Selecione uma impressora na lista.')
            return
        EditRegisteredPrinterWindow(self, on_save=self.refresh_table, printer=printer)

    def remove_printer(self):
        printer = self._selected_registered()
        if not printer:
            PopUpWindow(self, 'Aviso', 'Selecione uma impressora para remover.')
            return
        if admin_service.delete_registered_printer(printer['id']):
            self.refresh_table()
        else:
            PopUpWindow(self, 'Erro', 'Não foi possível remover a impressora.')

    def verify_selected(self):
        printer = self._selected_registered()
        if not printer:
            PopUpWindow(self, 'Aviso', 'Selecione uma impressora para verificar.')
            return
        if admin_service.verify_printer_available(printer['name']):
            PopUpWindow(self, 'OK', f'Impressora encontrada no Windows:\n{printer["name"]}')
        else:
            PopUpWindow(
                self, 'Não encontrada',
                f'O Windows não encontrou:\n{printer["name"]}\n\n'
                'Instale ou corrija o nome da impressora neste PC.',
            )

    def discover(self):
        self._registered = admin_service.list_registered_printers()
        self._discovered = admin_service.discover_installed_printers()
        self.discover_table.remove_all()
        registered_names = {p['name'].lower() for p in self._registered}
        for name in self._discovered:
            suffix = ' (já cadastrada)' if name.lower() in registered_names else ''
            self.discover_table.add_item([name + suffix], item_id=name)
        if not self._discovered:
            PopUpWindow(self, 'Descoberta', 'Nenhuma impressora instalada encontrada neste PC.')

    def add_from_discovery(self):
        selected = self.discover_table.get_selected_items()
        if not selected:
            PopUpWindow(self, 'Aviso', 'Selecione uma impressora descoberta.')
            return
        name = selected[0][0].replace(' (já cadastrada)', '').strip()
        if any(p['name'].lower() == name.lower() for p in self._registered):
            PopUpWindow(self, 'Aviso', f'"{name}" já está cadastrada.')
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
        self.title('Gerenciar Acesso à Configuração')
        self.master = master
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        body = ctk.CTkScrollableFrame(self, width=self._WINDOW_W - 20, height=self._WINDOW_H - 20)
        body.grid(row=0, column=0, padx=10, pady=10, sticky='nsew')
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(body, text='Usuários e grupos autorizados', font=('Arial', 16, 'bold')) \
            .grid(row=0, column=0, columnspan=2, pady=(0, 5), padx=5, sticky='w')

        self.table_frame = ctk.CTkFrame(
            body, width=480, height=self._AUTHORIZED_FRAME_H, corner_radius=0,
        )
        self.table_frame.grid_propagate(False)
        self.table_frame.pack_propagate(False)
        self.table_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky='ew')
        self.table = Table(
            self.table_frame, ['Nome', 'Tipo'], show='headings', height=self._TABLE_HEIGHT,
        )
        self.table.column('#1', width=320)
        self.table.column('#2', width=80)
        self.table.pack(expand=True, fill='both', padx=2, pady=2)
        self.refresh_table()

        self.btn_delete = ctk.CTkButton(
            body, text='Remover selecionado', width=140, fg_color=BTN_RED,
            hover_color=BTN_HOVER_RED, command=self.remove_selected,
        )
        self.btn_delete.grid(row=2, column=1, padx=5, pady=5, sticky='e')

        ctk.CTkLabel(body, text='Pesquisar na rede / neste PC', font=(FONT, 13, 'bold')) \
            .grid(row=3, column=0, columnspan=2, padx=5, sticky='w', pady=(10, 0))

        search_frame = ctk.CTkFrame(body, fg_color='transparent')
        search_frame.grid(row=4, column=0, columnspan=2, padx=5, sticky='ew')

        self.entry_search = ctk.CTkEntry(search_frame, width=220, placeholder_text='Nome ou login')
        self.entry_search.pack(side='left', padx=(0, 5))
        self.entry_search.bind('<Return>', self.search_principals)

        self.combo_type = ctk.CTkComboBox(
            search_frame, width=100, values=['Usuário e Grupo', 'Usuário', 'Grupo'],
        )
        self.combo_type.pack(side='left', padx=5)

        ctk.CTkButton(search_frame, text='Pesquisar', width=90, command=self.search_principals) \
            .pack(side='left', padx=5)

        self.results_frame = ctk.CTkFrame(
            body, width=480, height=self._RESULTS_FRAME_H, corner_radius=0,
        )
        self.results_frame.grid_propagate(False)
        self.results_frame.pack_propagate(False)
        self.results_frame.grid(row=5, column=0, columnspan=2, padx=5, pady=5, sticky='ew')
        self.results_table = Table(
            self.results_frame, ['Resultado', 'Tipo'], show='headings', height=self._TABLE_HEIGHT,
        )
        self.results_table.column('#1', width=320)
        self.results_table.column('#2', width=80)
        self.results_table.pack(expand=True, fill='both', padx=2, pady=2)
        self._search_results = []

        ctk.CTkButton(body, text='Adicionar selecionado', width=140, command=self.add_selected) \
            .grid(row=6, column=1, padx=5, pady=5, sticky='e')

        ctk.CTkLabel(body, text='Ou informe manualmente (DOMÍNIO\\conta)', font=(FONT, 11)) \
            .grid(row=7, column=0, columnspan=2, padx=5, sticky='w', pady=(8, 0))

        manual_frame = ctk.CTkFrame(body, fg_color='transparent')
        manual_frame.grid(row=8, column=0, columnspan=2, padx=5, sticky='ew')

        self.entry_manual = ctk.CTkEntry(manual_frame, width=280, placeholder_text='EX: EMPRESA\\joao.silva')
        self.entry_manual.pack(side='left', padx=(0, 5))
        self.entry_manual.bind('<Return>', self.add_manual)

        ctk.CTkButton(manual_frame, text='Adicionar', width=90, command=self.add_manual) \
            .pack(side='left')

        #ctk.CTkButton(body, text='Fechar', width=90, command=self.destroy) \
        #    .grid(row=9, column=1, padx=5, pady=(10, 5), sticky='e')

    def _type_filter(self):
        mapping = {'Usuário': 'user', 'Grupo': 'group', 'Usuário e Grupo': 'both'}
        return mapping.get(self.combo_type.get(), 'both')

    def refresh_table(self):
        self.table.remove_all()
        for entry in admin_service.list_config_access():
            tipo = 'Usuário' if entry['type'] == 'user' else 'Grupo'
            self.table.add_item([entry['name'], tipo])

    def search_principals(self, *args):
        query = self.entry_search.get().strip()
        if len(query) < 2:
            PopUpWindow(self, 'Aviso', 'Digite pelo menos 2 caracteres para pesquisar.')
            return
        self._search_results = admin_service.search_windows_principals(query, self._type_filter())
        self.results_table.remove_all()
        for item in self._search_results:
            tipo = 'Usuário' if item['type'] == 'user' else 'Grupo'
            self.results_table.add_item([item['display'], tipo])
        if not self._search_results:
            PopUpWindow(self, 'Pesquisa', 'Nenhum usuário ou grupo encontrado.')

    def _add_principal(self, name, ptype):
        if not admin_service.add_config_access(name, ptype):
            PopUpWindow(self, 'Aviso', f'"{name}" já está na lista de acesso.')
            return
        self.refresh_table()
        PopUpWindow(self, 'Sucesso', f'"{name}" adicionado com sucesso.')

    def add_selected(self):
        selected = self.results_table.get_selected_items()
        if not selected:
            PopUpWindow(self, 'Aviso', 'Selecione um resultado da pesquisa.')
            return
        display = selected[0][0]
        for item in self._search_results:
            if item['display'] == display:
                self._add_principal(item['name'], item['type'])
                return
        PopUpWindow(self, 'Erro', 'Não foi possível identificar o item selecionado.')

    def add_manual(self, *args):
        resolved = admin_service.resolve_windows_principal(self.entry_manual.get())
        if not resolved:
            PopUpWindow(self, 'Erro', 'Conta inválida. Use o formato DOMÍNIO\\usuário ou DOMÍNIO\\grupo.')
            return
        self._add_principal(resolved['name'], resolved['type'])
        self.entry_manual.delete(0, 'end')

    def remove_selected(self):
        selected = self.table.get_selected_items()
        if not selected:
            PopUpWindow(self, 'Aviso', 'Selecione um usuário ou grupo para remover.')
            return
        name = selected[0][0]
        if admin_service.delete_config_access(name):
            self.refresh_table()
        else:
            PopUpWindow(self, 'Erro', f'Não foi possível remover "{name}".')


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

        self.btn_incluir = ctk.CTkButton(self, text="Incluir", width=120, command=self.add_group)
        self.btn_incluir.grid(row=1, column=1, pady=10, padx=5)

        self.btn_delete = ctk.CTkButton(self, text="Deletar", width=120, fg_color=BTN_RED,
                                        hover_color=BTN_HOVER_RED, command=self.delete_group)

        self.btn_delete.grid(row=2, column=1, pady=10, padx=5, sticky='S')
        # ################## List ##############################
        self.table_frame = ctk.CTkFrame(self, width=500, height=310, corner_radius=0)
        self.table_frame.grid(row=2, rowspan=5, column=0, padx=5, pady=5, sticky="nwse")

        self.table = Table(self.table_frame, ['Nome do Grupo'], show="headings")
        self.table.pack(expand=True, fill="both")

        self.refresh_table()

        self.entry_name.bind('<Return>', self.add_group)

    def add_group(self, *args):
        name = self.entry_name.get().upper()
        if name in admin_service.list_print_groups():
            PopUpWindow(self, 'Erro', f'Grupo {name} Já existe na Base')
            return

        try:
            admin_service.insert_print_group(name)
            self.refresh_table()
            self.entry_name.delete(0, 'end')

        except Exception as e:
            PopUpWindow(self, 'Erro', f'Não foi possível adicionar grupo à base\n {e}')

    def delete_group(self):
        try:
            for i in self.table.get_selected_items():
                admin_service.delete_print_group(i[0])

            self.refresh_table()
        except Exception as e:
            PopUpWindow(self, 'Erro', f'Não foi possível deletar o grupo.\n{e}')

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

        ctk.CTkLabel(self, text='Cliente:').grid(row=3, column=0, pady=5, padx=10)
        self.entry_clientname = ctk.CTkComboBox(self, width=140, values=admin_service.list_client_names())
        self.entry_clientname.grid(row=3, column=1, sticky='W')

        ctk.CTkLabel(self, text='Nome do Produto').grid(row=4, column=0, columnspan=2, pady=5, padx=10)
        self.entry_productname = ctk.CTkEntry(self, width=300)
        self.entry_productname.grid(row=5, column=0, columnspan=2, padx=10)
        self.entry_productname.insert(0, original_product_name + '(1)')

        self.btn_ok = ctk.CTkButton(self, text="OK", width=120, command=self.duplicate_product)
        self.btn_ok.grid(row=6, column=0, pady=10, padx=20)

        self.btn_cancelar = ctk.CTkButton(self, width=120, text="Cancelar", fg_color=BTN_RED,
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
            PopUpWindow(self, 'Erro', error)
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
        self.title('Exportar Produto')
        self.master = master
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text='Exportar Produto', font=('Arial', 18, 'bold')). \
            grid(row=0, column=0, columnspan=2, pady=5, padx=10)

        ctk.CTkLabel(self, text='Cliente:').grid(row=3, column=0, pady=5, padx=10)
        self.entry_clientname = ctk.CTkComboBox(self, width=140, values=admin_service.list_client_names(),
                                                command=self.refresh_combobox)
        self.entry_clientname.grid(row=3, column=1, sticky='W')
        self.entry_clientname.set('')

        ctk.CTkLabel(self, text='Produtos:').grid(row=4, column=0, pady=5, padx=10)

        self.entry_productname = ctk.CTkComboBox(self, width=140, state='disabled', command=self.refresh_btn_ok)
        self.entry_productname.grid(row=4, column=1, sticky='W')

        self.btn_ok = ctk.CTkButton(self, text="Salvar", width=120, state='disabled', command=self.export_product)
        self.btn_ok.grid(row=6, column=0, pady=10, padx=20)

        self.btn_cancelar = ctk.CTkButton(self, width=120, text="Cancelar", fg_color=BTN_RED,
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
        path = asksaveasfilename(defaultextension=".json", filetypes=[("Arquivos JSON", "*.json")],
                                 initialfile=f'{client}-{product}')
        try:
            if path:
                result = build_export_payload(client, product, admin_service.get_db())
                with open(path, 'w') as arquivo_json:
                    json.dump(result, arquivo_json, indent=4)

                self.destroy()
                PopUpWindow(self.master, 'Sucesso', f'Produto Salvo com Sucesso!\n{path}')
        except Exception as e:
            PopUpWindow(self.master, 'ERRO!', f'ERROR - {e}')


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

        self.btn_ok = ctk.CTkButton(self, text="OK", width=120, command=self.add_client)
        self.btn_ok.grid(row=6, column=0, pady=10, padx=20)

        self.btn_cancelar = ctk.CTkButton(self, width=120, text="Cancelar", fg_color=BTN_RED,
                                          hover_color=BTN_HOVER_RED, command=self.destroy)
        self.btn_cancelar.grid(row=6, column=1, pady=10, padx=20)

    def add_client(self):
        if self.entry_name.get() in admin_service.list_client_names():
            PopUpWindow(self, 'Nome Duplicado', 'Nome Duplicado')
        else:
            admin_service.insert_client(self.entry_name.get())
            self.master.update_client_list()
            self.func()
            self.destroy()


