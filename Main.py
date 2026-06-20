from PIL import ImageTk, Image, ImageFilter
import customtkinter as ctk
from tkinter.filedialog import askopenfilename, askdirectory, asksaveasfilename
from utils import *
from tkinter import ttk
from Database import *
from app.services.designer_service import (
    duplicate_product as designer_duplicate_product,
    build_export_payload,
    parse_import_file,
    replace_imported_drawings,
    import_product_for_existing_client,
    import_product_with_new_client,
)
from app.ui.components import (
    ConfirmWindow,
    ListBox,
    PopUpWindow,
    Table,
)
from app.ui.main_app import App, LoadingBarFrame
from app.ui.designer_window import EditWindow
import tkinter
import traceback
import os
import json
import base64
import shutil
import re
from PIL import Image

nome_do_programa = "ArtemiS"
icone = 'img/favicon3.ico'
font = "Segoe UI"
btn_red = '#732425'
btn_hover_red = '#4a191a'
default_width, default_height = 850, 570
font_list = ["Arial", "Trebuchet MS", "Helvetica", "Arial Narrow", "Times New Roman", "Saira Extracondensed"]
paper_color_list = {
    'Branco': '#FFFFFF', 'Verde': '#3CB371', 'Azul': '#87CEFA', 'Rosa': '#EE82EE', 'Amarelo': '#FFFF00', 'Marfim':
        '#eee9b4'
}
paper_size_tip = """
Segue lista de papeis:
00 - (Aceita Qualquer Papel)
01 - (Letter)
02 - (Letter Small)
03 - (Tabloid)
04 - (Ledger)
05 - (Legal)
06 - (Statement)
07 - (A5)
08 - (A3)
09 - (A4)
10 - (B4)
11 - (B5)
12 - (Folio)
13 - (Quarto)
14 - (10x14 inches)
15 - (11x17 inches)
16 - (Note)
17 - (Envelope #9)
18 - (Envelope #10)
19 - (Envelope #11)
20 - (Envelope #12)
21 - (Envelope #14)
"""


class ConfigWindow(ctk.CTkToplevel):
    def __init__(self, master, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title('Configurações')

        self.geometry(calculate_center_screen_with_monitor(master, default_width, 600, get_monitor(master)))
        self.minsize(default_width, 600)
        self.maxsize(default_width, 600)
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

        label = ctk.CTkLabel(self, text="Configurações", font=(font, 18, "bold"))
        label.grid(row=0, column=0, columnspan=2, padx=10, pady=10)

        self.frame = ctk.CTkFrame(self, fg_color='transparent')
        self.frame.grid(row=1, column=0, padx=10, sticky='W')

        self.btn_add_client = ctk.CTkButton(self.frame, text='Adicionar Cliente', command=self.create_client)
        self.btn_add_client.grid(row=0, column=0, sticky='W')

        client_names = db.search_clients_names()
        self.client_list = ListBox(self, items=client_names, label_text='Clientes', width=345, height=150)
        self.client_list.grid(row=2, column=0, columnspan=1, padx=10, pady=10)

        self.product_list = ListBox(self, [], child=True, width=345, height=150, label_text='Produtos')
        self.product_list.grid(row=2, column=1, columnspan=1, padx=10, pady=10)

        # ############################# Config Frame ##################################################

        self.main_frame = ctk.CTkScrollableFrame(self, height=230)
        self.main_frame.grid(row=3, column=0, padx=10, columnspan=2, sticky='NSEW')

        ctk.CTkLabel(self.main_frame, text="Importar e Exportar", font=(font, 15, "bold")) \
            .grid(row=1, column=0, columnspan=2, padx=10, sticky='W')

        ctk.CTkButton(self.main_frame, text='Importar', command=self.import_product). \
            grid(row=2, padx=10, pady=5, column=0, sticky='W')

        ctk.CTkButton(self.main_frame, text='Exportar',
                      command=lambda: ExportProductWindow(self)).grid(row=3, padx=10, pady=5, column=0, sticky='W')

        # ------------------------------- Search Folder -------------------------------------------------

        ctk.CTkLabel(self.main_frame, text="Caminho para Buscar Arquivos", font=(font, 15, "bold")) \
            .grid(row=4, column=0, columnspan=2, padx=10, sticky='W')

        self.inpt_search_folder = ctk.CTkEntry(self.main_frame, width=220)
        self.inpt_search_folder.grid(row=5, column=0, padx=10, sticky='W')
        if config.get('search_folder'):
            self.inpt_search_folder.insert(0, config.get('search_folder'))

        self.btn_save_folder = ctk.CTkButton(self.main_frame, text='Salvar', width=80,
                                             state='disabled', command=self.save_folder)
        self.btn_save_folder.grid(row=5, column=1, sticky='W')

        # ------------------------------- DataBase Location --------------------------------------------
        ctk.CTkLabel(self.main_frame, text="Caminho para o Database", font=(font, 15, "bold")) \
            .grid(row=6, column=0, columnspan=2, padx=10, sticky='W')

        self.inpt_db_location = ctk.CTkEntry(self.main_frame, width=220)
        self.inpt_db_location.grid(row=7, column=0, padx=10, sticky='W')
        if config.get('database_location'):
            self.inpt_db_location.insert(0, config.get('database_location'))

        self.btn_save_db = ctk.CTkButton(self.main_frame, text='Salvar', width=80,
                                         state='disabled', command=self.save_database_location)
        self.btn_save_db.grid(row=7, column=1, sticky='W')

        # ------------------------------- Users --------------------------------------------
        ctk.CTkLabel(self.main_frame, text="Cadastrar ou Excluir usuários", font=(font, 15, "bold")) \
            .grid(row=8, column=0, columnspan=2, padx=10, sticky='W')

        self.btn_register = ctk.CTkButton(self.main_frame, text='Cadastrar', width=80,
                                          command=self.register_user)
        self.btn_register.grid(row=9, column=0, padx=10, sticky='W')

        users = db.users_list()
        self.combo_userlist = ctk.CTkComboBox(self.main_frame, values=users, width=200)
        self.combo_userlist.grid(row=10, column=0, pady=10, padx=10, sticky='W')

        text = f'Você realmente deseja deletar esse usuario?'
        self.btn_delete_user = ctk.CTkButton(self.main_frame, text='Deletar Usuario', fg_color=btn_red,
                                             hover_color=btn_hover_red, width=80,
                                             command=lambda: ConfirmWindow(self, 'Você tem certeza?', text,
                                                                           self.delete_user))
        self.btn_delete_user.grid(row=10, column=0, columnspan=2, sticky='E')
        # ------------------------------- List of Printers ---------------------------------------------
        ctk.CTkLabel(self.main_frame, text="Lista de impressoras", font=(font, 15, "bold")) \
            .grid(row=1, column=2, padx=50, sticky='W')

        printers = db.search_printers()
        printers = '\n'.join(printers)
        self.inpt_printers = ctk.CTkTextbox(self.main_frame, width=330, height=130)
        self.inpt_printers.grid(row=2, column=2, rowspan=3, padx=50, sticky='W')
        self.inpt_printers.insert('0.0', printers)

        self.btn_save_printers = ctk.CTkButton(self.main_frame, text='Salvar', width=80,
                                               command=self.save_printers)
        self.btn_save_printers.grid(row=5, column=2, padx=50, pady=5, sticky='E')

        # ------------------------------- List or Printing Groups ---------------------------------------------
        ctk.CTkLabel(self.main_frame, text="Gerenciar Grupos de Impressão", font=(font, 15, "bold")) \
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

    def update_userlist(self):
        self.combo_userlist.configure(values=db.users_list())

    def register_user(self):
        RegisterWindow(self, func=self.update_userlist, first_login=False)

    def save_database_location(self):
        folder = self.inpt_db_location.get()
        config_folder = config.get('database_location')
        if not os.path.exists(os.path.dirname(folder)) and os.path.dirname(folder):
            PopUpWindow(self, 'Erro', f'Caminho: {folder} não encontrada no sistema')
        else:
            if config_folder != folder:
                config['database_location'] = folder
                try:
                    with open('config.json', 'w') as configfile:
                        json.dump(config, configfile, indent=4)
                    self.update_save_button()

                    # Opening the new database
                    global db
                    db = DataBase(config['database_location'])
                    db.create_tables()
                    self.exit()
                    PopUpWindow(self.master, 'Sucesso', f'Banco de Dados Salvo!')
                except Exception as e:
                    PopUpWindow(self, 'Erro', f'Erro ao salvar o caminho\n{e}')

    def save_printers(self):
        try:
            printers = self.inpt_printers.get("0.0", "end")
            printers_list = [i for i in printers.split('\n') if i.strip() != '']
            db.save_printers(printers_list)
            PopUpWindow(self, 'Sucesso', 'Impressoras Salvas com Sucesso!')
        except Exception as e:
            PopUpWindow(self, 'Erro', f'Erro ao salvar as impressoras.\n{e}')

    def update_save_button(self, *args):
        folder = self.inpt_search_folder.get()
        config_folder = config.get('search_folder')

        config_db_location = config.get('database_location')
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
        config_folder = config.get('search_folder')
        if not os.path.exists(folder):
            PopUpWindow(self, 'Erro', f'Caminho: {folder} não encontrada no sistema')
        else:
            if config_folder != folder:
                config['search_folder'] = folder
                try:
                    with open('config.json', 'w') as configfile:
                        json.dump(config, configfile, indent=4)
                    self.update_save_button()
                    PopUpWindow(self, 'Sucesso', f'Caminho Salvo!')
                except Exception as e:
                    PopUpWindow(self, 'Erro', f'Erro ao salvar o caminho\n{e}')

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
        self.product_list = ListBox(self, products, child=True, width=345, height=150, label_text='Produtos')
        self.product_list.grid(row=2, column=1, columnspan=1, padx=10, pady=10)

    def update_client_list(self):
        clients = db.search_clients_names()
        self.client_list.destroy()
        self.client_list = ListBox(self, clients, width=345, height=150, label_text='Clientes')
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

            self.btn_delete_client = ctk.CTkButton(self, text='Deletar Cliente', fg_color=btn_red,
                                                   hover_color=btn_hover_red,
                                                   command=self.confirm_delete)
            self.btn_delete_client.grid(row=1, column=0, padx=10, sticky='E')

            self.btn_add_product = ctk.CTkButton(self, text="Adicionar Produto",
                                                 command=lambda: self.open_edit_window('add'))
            self.btn_add_product.grid(row=1, column=1, padx=10, sticky='W')

            client = self.client_list.radio_var.get()
            self.update_product_list(db.search_products(client))
            if self.btn_edit:
                self.btn_edit.destroy()
                self.btn_duplicate.destroy()
                self.btn_edit = None
                self.btn_duplicate = None
        else:
            self.show_edit_button()

    def delete_user(self):
        try:
            db.delete_user(self.combo_userlist.get())
            self.combo_userlist.configure(values=db.users_list())
            self.combo_userlist.set('')
        except Exception as e:
            PopUpWindow(self, 'Erro', f'Erro ao excluir o usuário\n{e}')

    def confirm_delete(self):
        client = self.client_list.radio_var.get()
        ConfirmWindow(self, 'Você tem certeza?', f'Você realmente deseja deletar o cliente {client}?',
                      self.delete_client)

    def delete_client(self):
        client = self.client_list.radio_var.get()
        if db.delete_client(client):
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

        if db.search_clients_names(client_name):
            if product_name in db.search_products(client_name):
                def replace_drawing():
                    try:
                        replace_imported_drawings(client_name, product_name, items, db)
                        PopUpWindow(self, 'Sucesso', 'Produto Substituído com sucesso!')
                    except Exception as e:
                        PopUpWindow(self, 'Erro', f'Não foi possível salvar o produto.\n{e}')

                text = f'Produto "{product_name}" já existente na base.\nDeseja Substituí-lo?'
                ConfirmWindow(self, 'Produto já existente', text, replace_drawing)
            else:
                try:
                    import_product_for_existing_client(
                        client_name, product_name, color, orientation, paper_size, items, db
                    )
                    PopUpWindow(self, 'Sucesso', 'Produto salvo com sucesso!')
                except Exception as e:
                    PopUpWindow(self, 'Erro', f'Erro ao salvar o produto.\n{e}')
        else:
            try:
                import_product_with_new_client(
                    client_name, product_name, color, orientation, paper_size, items, db
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


class ManageGroupWindow(ctk.CTkToplevel):
    def __init__(self, master, title, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iconbitmap(icone)

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

        self.btn_delete = ctk.CTkButton(self, text="Deletar", width=120, fg_color=btn_red,
                                        hover_color=btn_hover_red, command=self.delete_group)

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
        if name in db.search_print_group():
            PopUpWindow(self, 'Erro', f'Grupo {name} Já existe na Base')
            return

        try:
            db.insert_print_group(name)
            self.refresh_table()
            self.entry_name.delete(0, 'end')

        except Exception as e:
            PopUpWindow(self, 'Erro', f'Não foi possível adicionar grupo à base\n {e}')

    def delete_group(self):
        try:
            for i in self.table.get_selected_items():
                db.delete_print_group(i[0])

            self.refresh_table()
        except Exception as e:
            PopUpWindow(self, 'Erro', f'Não foi possível deletar o grupo.\n{e}')

    def refresh_table(self):
        self.table.remove_all()
        for i in db.search_print_group():
            self.table.add_item([i])


class DuplicateProductWindow(ctk.CTkToplevel):
    def __init__(self, master, title, original_client, original_product_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iconbitmap(icone)

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
        self.entry_clientname = ctk.CTkComboBox(self, width=140, values=db.search_clients_names())
        self.entry_clientname.grid(row=3, column=1, sticky='W')

        ctk.CTkLabel(self, text='Nome do Produto').grid(row=4, column=0, columnspan=2, pady=5, padx=10)
        self.entry_productname = ctk.CTkEntry(self, width=300)
        self.entry_productname.grid(row=5, column=0, columnspan=2, padx=10)
        self.entry_productname.insert(0, original_product_name + '(1)')

        self.btn_ok = ctk.CTkButton(self, text="OK", width=120, command=self.duplicate_product)
        self.btn_ok.grid(row=6, column=0, pady=10, padx=20)

        self.btn_cancelar = ctk.CTkButton(self, width=120, text="Cancelar", fg_color=btn_red,
                                          hover_color=btn_hover_red, command=self.destroy)
        self.btn_cancelar.grid(row=6, column=1, pady=10, padx=20)

    def duplicate_product(self):
        product_name = self.entry_productname.get()
        client_name = self.entry_clientname.get()
        error = designer_duplicate_product(
            self.original_client,
            self.product_name,
            client_name,
            product_name,
            db,
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
        self.iconbitmap(icone)

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
        self.entry_clientname = ctk.CTkComboBox(self, width=140, values=db.search_clients_names(),
                                                command=self.refresh_combobox)
        self.entry_clientname.grid(row=3, column=1, sticky='W')
        self.entry_clientname.set('')

        ctk.CTkLabel(self, text='Produtos:').grid(row=4, column=0, pady=5, padx=10)

        self.entry_productname = ctk.CTkComboBox(self, width=140, state='disabled', command=self.refresh_btn_ok)
        self.entry_productname.grid(row=4, column=1, sticky='W')

        self.btn_ok = ctk.CTkButton(self, text="Salvar", width=120, state='disabled', command=self.export_product)
        self.btn_ok.grid(row=6, column=0, pady=10, padx=20)

        self.btn_cancelar = ctk.CTkButton(self, width=120, text="Cancelar", fg_color=btn_red,
                                          hover_color=btn_hover_red, command=self.destroy)
        self.btn_cancelar.grid(row=6, column=1, pady=10, padx=20)

    def refresh_combobox(self, *args):
        products = db.search_products(self.entry_clientname.get())
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
                result = build_export_payload(client, product, db)
                with open(path, 'w') as arquivo_json:
                    json.dump(result, arquivo_json, indent=4)

                self.destroy()
                PopUpWindow(self.master, 'Sucesso', f'Produto Salvo com Sucesso!\n{path}')
        except Exception as e:
            PopUpWindow(self.master, 'ERRO!', f'ERROR - {e}')


class AddClientWindow(ctk.CTkToplevel):
    def __init__(self, master, title, func, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iconbitmap(icone)

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

        self.btn_cancelar = ctk.CTkButton(self, width=120, text="Cancelar", fg_color=btn_red,
                                          hover_color=btn_hover_red, command=self.destroy)
        self.btn_cancelar.grid(row=6, column=1, pady=10, padx=20)

    def add_client(self):
        if self.entry_name.get() in db.search_clients_names():
            PopUpWindow(self, 'Nome Duplicado', 'Nome Duplicado')
        else:
            db.insert_client(self.entry_name.get())
            self.master.update_client_list()
            self.func()
            self.destroy()


class RegisterWindow(ctk.CTkToplevel):
    def __init__(self, master, func=None, first_login=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iconbitmap(icone)

        self.geometry(calculate_center_screen_with_monitor(master, 300, 300, get_monitor(master)))
        self.resizable(False, False)
        self.title("Cadastrar-se")
        self.master = master
        self.grab_set()
        self.func = func

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text='Cadastrar-se', font=('Arial', 18, 'bold')) \
            .grid(row=0, column=0, columnspan=2, pady=5, padx=10)

        if first_login:
            text = 'Não há nenhum cadastro no banco ainda,\nrealize o primeiro cadastro'
            ctk.CTkLabel(self, text=text, font=('Arial', 12, 'normal')) \
                .grid(row=1, column=0, columnspan=2, pady=5, padx=10)

        ctk.CTkLabel(self, text='Nome do usuário').grid(row=2, column=0, columnspan=2, padx=10, sticky='S')
        self.entry_user = ctk.CTkEntry(self, width=200)
        self.entry_user.grid(row=3, column=0, columnspan=2, padx=10)

        ctk.CTkLabel(self, text='Senha').grid(row=4, column=0, columnspan=2, padx=10, sticky='S')
        self.entry_password = ctk.CTkEntry(self, width=200, show="*")
        self.entry_password.grid(row=5, column=0, columnspan=2, padx=10)

        ctk.CTkLabel(self, text='Confirme a Senha').grid(row=6, column=0, columnspan=2, padx=10, sticky='S')
        self.entry_confirm_password = ctk.CTkEntry(self, width=200, show="*")
        self.entry_confirm_password.grid(row=7, column=0, columnspan=2, padx=10)

        self.btn_ok = ctk.CTkButton(self, text="OK", width=120, command=self.register_user)
        self.btn_ok.grid(row=8, column=0, pady=15, padx=20)

        self.btn_cancelar = ctk.CTkButton(self, width=120, text="Cancelar", fg_color=btn_red,
                                          hover_color=btn_hover_red, command=self.destroy)
        self.btn_cancelar.grid(row=8, column=1, pady=15, padx=20)

    def register_user(self):
        if len(self.entry_user.get()) < 6:
            PopUpWindow(self, 'Erro', 'A nome do usuário deve ter mais de 5 digitos')
        elif len(self.entry_password.get()) < 7:
            PopUpWindow(self, 'Erro', 'A senha deve ter mais de 6 digitos')
        elif self.entry_password.get() != self.entry_confirm_password.get():
            PopUpWindow(self, 'Erro', 'As senhas não correspondem. Tente novamente.')
        else:
            try:
                db.register_user(self.entry_user.get(), self.entry_password.get(), 'admin')
                self.destroy()
                if self.func:
                    self.func()
            except Exception as e:
                PopUpWindow(self, 'Erro', f'Erro ao cadastrar o usuário\n{e}')


class LoginWindow(ctk.CTkToplevel):
    def __init__(self, master, func, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iconbitmap(icone)

        self.geometry(calculate_center_screen_with_monitor(master, 300, 220, get_monitor(master)))
        self.minsize(300, 220)
        self.maxsize(300, 220)
        self.resizable(False, False)
        self.title("Login")
        self.master = master
        self.grab_set()
        self.func = func

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text='Login', font=('Arial', 18, 'bold')) \
            .grid(row=0, column=0, columnspan=2, pady=5, padx=10)

        ctk.CTkLabel(self, text='Nome do usuário').grid(row=2, column=0, columnspan=2, padx=10, sticky='S')
        self.entry_user = ctk.CTkEntry(self, width=200)
        self.entry_user.grid(row=3, column=0, columnspan=2, padx=10)
        self.entry_user.focus()

        ctk.CTkLabel(self, text='Senha').grid(row=4, column=0, columnspan=2, padx=10, sticky='S')
        self.entry_password = ctk.CTkEntry(self, width=200, show="*")
        self.entry_password.grid(row=5, column=0, columnspan=2, padx=10)

        self.btn_ok = ctk.CTkButton(self, text="OK", width=120, command=self.login_user)
        self.btn_ok.grid(row=8, column=0, pady=15, padx=20)

        self.btn_cancelar = ctk.CTkButton(self, width=120, text="Cancelar", fg_color=btn_red,
                                          hover_color=btn_hover_red, command=self.destroy)
        self.btn_cancelar.grid(row=8, column=1, pady=15, padx=20)

        self.bind("<Return>", self.login_user)

    def login_user(self, *args):
        if db.verify_user(self.entry_user.get().lower(), self.entry_password.get()):
            self.destroy()
            self.func()
        else:
            PopUpWindow(self, 'Erro', 'Credenciais inválidas.')


if __name__ == "__main__":
    try:
        with open('config.json') as config_file:
            config = json.load(config_file)
            if not os.path.exists(config['search_folder']):
                os.mkdir(config['search_folder'])
    except FileNotFoundError:
        with open('config.json', 'w') as config_file:
            config = {
                'database_location': 'database.db',
                'search_folder': 'C:\\AR'
            }
            json.dump(config, config_file, indent=4)
        if not os.path.exists('C:\\AR'):
            os.mkdir('C:\\AR')

    db = DataBase(config['database_location'])
    db.create_tables()
    app = App()
    app.mainloop()
