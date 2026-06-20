from PIL import ImageTk, Image, ImageFilter
from datetime import datetime
import customtkinter as ctk
from tkinter.filedialog import askopenfilename, askdirectory, asksaveasfilename
from utils import *
from tkinter import Canvas
from tkinter import ttk
from Database import *
from pdf_utils import *
from app.services.print_service import finish_print_job, validate_printer_paper, get_printer_paper_error_message
from app.services.production_service import (
    normalize_group_flag,
    resolve_work_search_path,
    ensure_output_directories,
    is_empty_file as work_is_empty_file,
    get_product_from_file as production_get_product_from_file,
    find_work_in_directory,
    get_work_product_info,
    validate_queue_consistency,
    load_worklist_file_lines,
    get_drawings_and_orientations,
    get_paper_size_from_path,
    build_remake_file_lines,
)
from app.services.designer_service import (
    ORIENTATION_LABELS,
    validate_product_name,
    orientation_index_from_label,
    load_product_drawings,
    save_product_with_drawings,
    delete_product as designer_delete_product,
    duplicate_product as designer_duplicate_product,
    build_export_payload,
    parse_import_file,
    replace_imported_drawings,
    import_product_for_existing_client,
    import_product_with_new_client,
    has_unsaved_changes,
    serialize_canvas_to_dict,
)
from app.ui.components import (
    ConfirmWindow,
    ListBox,
    PopUpWindow,
    SpinBox,
    Table,
    Tooltip,
)
from threading import Thread
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


class App(ctk.CTk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title(nome_do_programa)
        self.iconbitmap(icone)
        ctk.set_default_color_theme("dark-blue")
        ctk.set_appearance_mode("dark")
        self.option_add("*Font", ("Segoe UI", 15))

        self.winfo_screenwidth()
        self.geometry(calculate_center_screen(default_width, default_height, self))
        self.minsize(default_width, default_height)
        self.maxsize(default_width, default_height)

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)
        self.grid_columnconfigure(3, weight=1)

        self.config_window = None
        self.file_lines = None
        self.progressbar = None
        self.lbl_progressbar = None
        self.works_paths = []

        # ################## Title ##############################
        self.lbl_title = ctk.CTkLabel(self, text=nome_do_programa, font=(font, 45, "bold"), fg_color="transparent")
        self.lbl_title.grid(row=0, column=0, columnspan=4, padx=10, pady=10)

        # ############# Botão config ############################
        self.btn_config = ctk.CTkButton(self, text="⚙", font=(font, 18, "normal"),
                                        width=35, height=35, fg_color='transparent',
                                        hover=False, command=self.open_toplevel)
        self.btn_config.bind("<Enter>", lambda x: self.btn_config.configure(text_color='gray'))
        self.btn_config.bind("<Leave>", lambda x: self.btn_config.configure(text_color='white'))
        self.btn_config.grid(row=0, column=3, padx=10, pady=10, sticky="ne")

        # ########### Selecione a impressora ####################
        self.frame_printers = ctk.CTkFrame(self, fg_color='transparent')
        self.frame_printers.grid(row=1, column=0, columnspan=4, pady=10)

        self.lbl_select_printer = ctk.CTkLabel(self.frame_printers, text="Selecione a impressora:")
        self.lbl_select_printer.grid(row=0, column=0, padx=10)

        printers_list = ['Criar PDF']
        printers_list.extend(db.search_printers())
        self.printers_list = ctk.CTkComboBox(self.frame_printers, values=printers_list, width=210)
        self.printers_list.grid(row=0, column=1, padx=15)

        self.lbl_select_group = ctk.CTkLabel(self.frame_printers, text="Selecione Grupo:")
        self.lbl_select_group.grid(row=1, column=0, padx=10)

        self.print_group_list = ctk.CTkComboBox(self.frame_printers, values=db.search_print_group(), width=210)
        self.print_group_list.grid(row=1, column=1, padx=15, pady=5)

        # ######################## Remake Checkbox ##############################
        self.checkbox_remake = ctk.CTkCheckBox(self, text='Habilitar Remake', command=self.remake_checkbox_event)
        self.checkbox_remake.grid(row=2, column=0, columnspan=4, pady=10)

        self.checkbox_remake_refazer = None

        # ################ Selecione Works #####################
        frame_works = ctk.CTkFrame(self, fg_color="transparent")
        frame_works.grid(row=3, column=0, columnspan=4, pady=10)

        ctk.CTkLabel(frame_works, text="Escaneie as Workorders: ").grid(row=0, sticky='w')

        self.entry_work = ctk.CTkEntry(frame_works, border_width=2, corner_radius=0, width=370)
        self.entry_work.grid(row=1)
        self.entry_work.bind('<Return>', self.search_work)

        self.worklist = ctk.CTkTextbox(frame_works, corner_radius=0, height=122, width=370, state='disabled')
        self.worklist.grid(row=2, column=0, columnspan=4)
        self.worklist.bind('<FocusIn>', self.refresh)

        ctk.CTkButton(frame_works, text="Limpar", width=50, height=20, corner_radius=0,
                      command=self.clean_worklist).grid(row=2, sticky='ES')

        # ######################## Paper Color ##############################
        self.frame_papercolor = ctk.CTkFrame(self, height=60, fg_color='transparent', corner_radius=0)

        self.lbl_paper_color = ctk.CTkLabel(self.frame_papercolor, text="Cor do Papel:", font=('Arial', 13, 'bold'))
        self.lbl_paper_color.grid(row=5, padx=10, column=0)

        self.paper_color = ctk.CTkFrame(self.frame_papercolor, height=60, width=60, fg_color='#3CB371', corner_radius=0)
        self.paper_color.grid(row=5, column=1)

        self.defined_color = None
        self.defined_paper_size = None
        # ######################## Label Impressão ################################
        self.printing_label = None
        # ######################## Botão Start ################################
        self.grid_rowconfigure(7, weight=1)
        self.btn_start = ctk.CTkButton(self, text="Start", font=(font, 14, "bold"), state='disabled',
                                       command=self.btn_start)
        self.btn_start.grid(row=7, column=0, columnspan=4, padx=10, pady=10, sticky="s")

        ctk.CTkLabel(self, text='Developed By Nathan - V1.0.9', text_color='grey').grid(row=7, column=0,
                                                                                        columnspan=4, padx=5,
                                                                                        sticky='SE')

        # ######################## Frame Loading ################################
        self.loading_frame = LoadingBarFrame(self, fg_color='transparent')
        self.loading_frame.grid(row=0, column=0, rowspan=8, padx=10, pady=5, sticky='NSW')

        self.verify_directorys()

    def remake_checkbox_event(self, event=None):
        if self.checkbox_remake.get():
            self.checkbox_remake_refazer = ctk.CTkCheckBox(self, text='Não Utilizar Tela Secundária',
                                                           command=self.clean_worklist)
            self.checkbox_remake_refazer.grid(row=2, column=2, columnspan=2, pady=10)
        else:
            self.checkbox_remake_refazer.destroy()
            self.checkbox_remake_refazer = None

        self.clean_worklist()

    def create_printing_label(self):
        self.printing_label = ctk.CTkLabel(self, text="Realizando Impressão\nAguarde...", font=('Arial', 30, 'bold'),
                                           fg_color='transparent', bg_color='transparent')
        self.printing_label.grid(row=0, column=0, rowspan=7, columnspan=4)

    def remove_printing_label(self):
        if self.printing_label:
            self.printing_label.destroy()

    def show_color(self, color):
        self.frame_papercolor.grid(row=5, column=0, columnspan=4, pady=10)
        self.defined_color = color
        self.lbl_paper_color.configure(text=f'Cor do Papel:\n{color}')
        self.paper_color.configure(fg_color=paper_color_list[color])

    def remake_widget_update(self):
        if self.remake_var.get() == 1:
            self.txtbox_ar.focus()
            self.entry_range.delete(0, "end")
        else:
            self.txtbox_ar.delete('0.0', 'end')

    def open_toplevel(self):
        def open_config():
            self.config_window = ConfigWindow(self)
            self.withdraw()

        if db.has_login():
            LoginWindow(self, open_config)
        else:
            RegisterWindow(self, open_config, first_login=True)

    def get_paper_size_from_worklist(self):
        return get_paper_size_from_path(self.works_paths[0], db)

    def btn_start(self):
        if self.printers_list.get() != 'Criar PDF':
            paper_size = self.get_paper_size_from_worklist()
            if not validate_printer_paper(self.printers_list.get(), paper_size):
                PopUpWindow(self, 'Erro', get_printer_paper_error_message(paper_size))
                return

        lines = self.open_files_from_worklist()
        items, orientations = self.get_items_and_orientation_from_worklist(lines)

        self.create_pdf(lines, items, orientations, self.checkbox_remake.get(), printer=self.printers_list.get())

    def _build_pdf_callbacks(self, printer):
        def on_progress(printer_name, progress, text):
            self.after(0, lambda: self._on_pdf_progress(printer_name, progress, text))

        def on_error(printer_name, error_traceback):
            self.after(0, lambda: self.loading_frame.show_error(printer_name, error_traceback))

        def on_complete(joined_pdf_filepath, files_to_move, is_remake_flag, printer_name):
            self.after(0, lambda: self.open_or_print_pdf(
                joined_pdf_filepath, files_to_move, is_remake_flag, printer_name))

        return on_progress, on_error, on_complete

    def _on_pdf_progress(self, printer, progress, text):
        self.loading_frame.update_progressbar(printer, progress, text)
        self.update_idletasks()

    def create_pdf(self, lines, items, orientations, is_remake=False, printer=None):
        # this function must be separeted from btn star, due to the remake window

        # setting PDF folder
        folder_destination = os.path.join(config['search_folder'], 'PDFs')

        try:
            self.loading_frame.add_progressbar(printer)
        except Exception as e:
            PopUpWindow(self, "Erro", e)
            return

        on_progress, on_error, on_complete = self._build_pdf_callbacks(printer)

        t = Thread(
            target=write_text_to_pdf,
            kwargs={
                'items': items,
                'files_lines': lines,
                'orientation_list': orientations,
                'path': folder_destination,
                'is_remake': is_remake,
                'printer': printer,
                'on_progress': on_progress,
                'on_error': on_error,
                'on_complete': on_complete,
            }
        )
        t.start()

        self.refresh()

    def get_items_and_orientation_from_worklist(self, files):
        return get_drawings_and_orientations(files, db)

    def open_files_from_worklist(self, *args):
        return load_worklist_file_lines(self.works_paths)

    def clean_worklist(self):
        self.worklist.configure(state='normal')
        self.worklist.delete('0.0', 'end')
        self.worklist.configure(state='disabled')
        self.works_paths = []
        self.btn_start.configure(state='disabled')
        self.frame_papercolor.grid_forget()
        self.defined_color = None
        self.defined_paper_size = None
        self.entry_work.focus()

    def is_empty_file(self, path):
        return work_is_empty_file(path)

    def get_product_from_file(self, path):
        return production_get_product_from_file(path)

    def search_work(self, *args):
        # If entry is empty, do nothing
        work = self.entry_work.get().upper()
        if not work:
            return

        if self.worklist.get('0.0', 'end').strip():
            self.btn_start.configure(state='normal')

        # Works that's already in the list
        founded_works = self.worklist.get('0.0', 'end').split('\n')
        founded_works = [i for i in founded_works if i]

        group_flag = normalize_group_flag(self.print_group_list.get())
        path = resolve_work_search_path(config['search_folder'], group_flag, self.checkbox_remake.get())

        if not os.path.exists(path):
            PopUpWindow(self, 'Erro', f'Caminho "{path}" não existe!')
            return

        if work not in founded_works:
            full_path = find_work_in_directory(path, work)

            if full_path is None:
                self.entry_work.delete('0', 'end')
                PopUpWindow(self, 'Work não encontrada', f'Work "{work}" não foi encontrada.\n'
                                                         f'Por favor selecionar o arquivo manualmente\n'
                                                         f'Ou Contactar PreProd\n'
                                                         f'Caminho: {config["search_folder"]}')
                return

            if self.is_empty_file(full_path):
                PopUpWindow(self, 'Erro', 'Arquivo encontrado está vazio - Verificar')
                self.entry_work.delete('0', 'end')
                return

            work_info = get_work_product_info(full_path, db)
            if work_info is None:
                client, product = production_get_product_from_file(full_path)
                PopUpWindow(self, 'Erro',
                            f'Cliente: "{client}" e Produto: "{product}" não existem no banco')
                return

            consistency = validate_queue_consistency(
                work_info.paper_size,
                work_info.color,
                self.defined_paper_size,
                self.defined_color,
            )
            if not consistency.ok:
                self.entry_work.delete('0', 'end')
                PopUpWindow(self, consistency.error.title, consistency.error.message)
                return

            self.defined_paper_size = consistency.defined_paper_size
            self.defined_color = consistency.defined_color
            if consistency.show_color:
                self.show_color(consistency.defined_color)

            if full_path not in self.works_paths:
                self.works_paths.append(full_path)

            self.entry_work.delete('0', 'end')

            self.worklist.configure(state='normal')
            self.worklist.delete('0.0', 'end')
            founded_works.append(work)
            self.worklist.insert('0.0', '\n'.join(founded_works))
            self.worklist.configure(state='disabled')
            if self.worklist.get('0.0', 'end').strip():
                self.btn_start.configure(state='normal')
            self.btn_start.configure(state='normal')
            if self.checkbox_remake.get() and not self.checkbox_remake_refazer.get():
                RemakeWindow(self, full_path, work.upper(), self.defined_color, self.printers_list.get())
                self.withdraw()
        else:
            PopUpWindow(self, 'Erro', 'Work já está na lista')
            self.entry_work.delete('0', 'end')

    def open_or_print_pdf(self, filename='', file_to_move=[], is_remake=None, printer=None):
        try:
            self.loading_frame.update_progressbar(printer, 1, 'Imprimindo...')

            exe_index = None
            if printer != 'Criar PDF':
                exe_index = self.loading_frame.get_exe_index(printer)

            finish_print_job(filename, file_to_move, is_remake, printer, exe_index)
            self.loading_frame.remove_progressbar(printer)
        except Exception:
            self.loading_frame.show_error(printer, traceback.format_exc())

    def create_progress_bar(self):
        self.progressbar = ctk.CTkProgressBar(self.loading_frame, orientation="horizontal", height=30,
                                              corner_radius=0, width=150, border_width=2)
        self.progressbar.pack()
        # self.progressbar.grid(row=0, column=0, columnspan=4, rowspan=7, pady=10)

        self.lbl_progressbar = ctk.CTkLabel(self, text='', font=('Arial', 15, 'bold'))
        self.lbl_progressbar.grid(row=0, column=0, columnspan=4, rowspan=7, pady=10)

    def destroy_progress_bar(self):
        if self.progressbar:
            self.progressbar.destroy()
        if self.lbl_progressbar:
            self.lbl_progressbar.destroy()

    def refresh_progress_bar(self, value, lbl_text):
        self.progressbar.set(value)
        self.lbl_progressbar.configure(text=lbl_text)

    @staticmethod
    def verify_directorys():
        ensure_output_directories(config['search_folder'])

    def refresh(self, *args):
        self.btn_start.configure(state='disabled')
        self.btn_config.configure(state='normal')
        self.printers_list.configure(state='normal')

        # update the printers list, when it's included in the Printer List in configs
        printers_list = ['Criar PDF']
        printers_list.extend(db.search_printers())
        self.printers_list.configure(values=printers_list)

        self.remove_printing_label()
        if self.progressbar:
            self.progressbar.destroy()

        if self.checkbox_remake_refazer:
            self.checkbox_remake_refazer.destroy()
            self.checkbox_remake_refazer = None

        self.checkbox_remake.deselect()
        self.clean_worklist()


class LoadingBarFrame(ctk.CTkFrame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.printers_status = {}

    def add_progressbar(self, printer_name):
        if printer_name in self.printers_status:
            raise Exception('Impressora já está em uso')

        exe_index = self.__get_exe_to_use()

        frame = ctk.CTkFrame(self, fg_color='transparent')
        frame.pack()

        ctk.CTkLabel(frame, text=45 * '-', bg_color='transparent').grid(row=0)

        lbl_printer = ctk.CTkLabel(frame, text=f'Impressora\n{printer_name}', font=('Arial', 10),
                                   bg_color='transparent')
        lbl_printer.grid(row=1)

        loadingbar = ctk.CTkProgressBar(frame, orientation="horizontal", height=30, width=150, corner_radius=0)
        loadingbar.grid(row=2, column=0)

        progress_lbl = ctk.CTkLabel(frame, text='1/2', font=('Arial', 13), bg_color='#1F538D')
        progress_lbl.grid(row=2, column=0)

        self.printers_status[printer_name] = {
            'ProgressBar': loadingbar,
            'Label': progress_lbl,
            'Frame': frame,
            'Exe_to_use': exe_index
        }

    def get_exe_index(self, printer_name):
        return self.printers_status[printer_name]['Exe_to_use']

    def __get_exe_to_use(self):
        exe = []
        for i in self.printers_status:
            exe.append(self.printers_status[i]['Exe_to_use'])

        for i in range(5):
            if i not in exe:
                return i

        raise Exception('Máximo de 5 processos de impressão por vez.\nAguardar')

    def update_progressbar(self, printer_name, loadingbar_progress, lbl_text):
        progress_bar = self.printers_status[printer_name]['ProgressBar']
        progress_lbl = self.printers_status[printer_name]['Label']

        progress_bar.set(loadingbar_progress)
        progress_lbl.configure(text=lbl_text)

    def remove_progressbar(self, printer_name):
        frame = self.printers_status[printer_name]['Frame']
        frame.destroy()

        self.printers_status.pop(printer_name)

    def show_error(self, printer_name, error_tracebak):
        frame = self.printers_status[printer_name]['Frame']

        ctk.CTkLabel(frame, font=('Arial', 10), text='ERRO AO CRIAR').grid(row=0)

        path = 'Errors_Logs.txt'
        FileUtils.write_log_file(path, error_tracebak)

        ctk.CTkButton(frame, text='Visualizar', fg_color=btn_red, hover_color=btn_hover_red,
                      command=lambda: self.visualize_error(printer_name, path)).grid(row=1)

    def visualize_error(self, printer_name, path):
        self.remove_progressbar(printer_name)

        os.startfile(os.path.abspath(path))


class RemakeWindow(ctk.CTkToplevel):
    def __init__(self, master, filepath, work_order, color, printer, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title('Remake')

        self.master = master

        self.geometry(calculate_center_screen_with_monitor(master, default_width, 550, get_monitor(master)))
        self.minsize(default_width, 550)
        self.maxsize(default_width, 550)
        self.resizable(False, False)
        self.printer = printer

        self.grid_columnconfigure(0, weight=10)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(4, weight=1)

        self.file = FileUtils(filepath)
        self.filepath = filepath

        # Getting the first column from file and splitting '-'
        # E.g. Santander - Correios
        self.client = self.file.get_first_line_column(0).split('-')[0].strip()
        self.product = self.file.get_first_line_column(0).split('-')[1].strip()
        # ################## Title ##############################
        self.lbl_title = ctk.CTkLabel(self, text="Selecionar Remake", font=(font, 25, "bold"))
        self.lbl_title.grid(row=0, column=0, columnspan=2, pady=5, sticky='ew')

        # ################## infos##############################
        self.frame_info = ctk.CTkFrame(self)
        self.frame_info.grid(row=1, column=0, columnspan=2, sticky='ew')

        self.frame_info.grid_columnconfigure(0, weight=4)
        self.frame_info.grid_columnconfigure(1, weight=1)
        self.frame_info.grid_columnconfigure(2, weight=1)

        work = self.file.get_first_line_column(3)
        text = f'WO:{work} - (Total: {len(self.file.lines)})'
        self.lbl_title = ctk.CTkLabel(self.frame_info, text=text, font=(font, 15, "bold"))
        self.lbl_title.grid(row=0, column=0)

        self.frame_printers = ctk.CTkFrame(self.frame_info, fg_color='transparent')
        self.frame_printers.grid(row=0, column=1)

        self.lbl_select_printer = ctk.CTkLabel(self.frame_printers, text="Impressora: ")
        self.lbl_select_printer.grid(row=0, column=0, padx=5)

        printers_list = ['Criar PDF']
        printers_list.extend(db.search_printers())
        self.printers_list = ctk.CTkComboBox(self.frame_printers, values=printers_list, width=200)
        self.printers_list.grid(row=0, column=1, padx=5)
        self.printers_list.set(self.printer)

        color_frame = ctk.CTkFrame(self.frame_info, fg_color='transparent')
        color_frame.grid(row=0, column=2)
        ctk.CTkLabel(color_frame, text='Cor do Papel:').grid(row=0, column=0)
        ctk.CTkFrame(color_frame, fg_color=paper_color_list[color], width=20, height=20, corner_radius=0) \
            .grid(row=0, column=1, padx=10)

        # ################## Inputs ##############################
        self.inputs_frame = ctk.CTkFrame(self, fg_color='transparent', border_width=1)
        self.inputs_frame.grid(row=2, column=0, columnspan=2, padx=5, sticky='ew')

        self.inputs_frame.grid_columnconfigure(0, weight=1)
        self.inputs_frame.grid_columnconfigure(1, weight=1)
        self.inputs_frame.grid_columnconfigure(2, weight=1)
        self.inputs_frame.grid_columnconfigure(3, weight=1)

        # Validation Function to Range Input and RankJob Input
        validation = self.register(lambda i: i.isdigit() or ',' in i or '-' in i or i == '')

        ctk.CTkLabel(self.inputs_frame, text='Range (ex.: 1-3,5,10)').grid(row=0, column=0, padx=5, pady=2, sticky='w')
        self.range_input = ctk.CTkEntry(self.inputs_frame, width=150, border_width=2, corner_radius=0,
                                        validate='key', validatecommand=(validation, "%P"))
        self.range_input.bind('<FocusIn>', self.clear_other_entries)
        self.range_input.grid(row=1, column=0, padx=5, sticky='w')

        ctk.CTkLabel(self.inputs_frame, text='RankInJob (ex.: 1-3,5,10)').grid(row=0, column=1, padx=5, sticky='w')
        self.rankjob_input = ctk.CTkEntry(self.inputs_frame, width=150, border_width=2, corner_radius=0,
                                          validate='key', validatecommand=(validation, "%P"))
        self.rankjob_input.bind('<FocusIn>', self.clear_other_entries)
        self.rankjob_input.grid(row=1, column=1, padx=5, sticky='w')

        ctk.CTkLabel(self.inputs_frame, text='Número do AR:').grid(row=0, column=2, padx=5, sticky='w')
        self.ar_input = ctk.CTkEntry(self.inputs_frame, width=170, border_width=2, corner_radius=0)
        self.ar_input.bind('<FocusIn>', self.clear_other_entries)
        self.ar_input.grid(row=1, column=2, padx=5, sticky='w')

        ctk.CTkLabel(self.inputs_frame, text='Nome Embossing:').grid(row=0, column=3, padx=5, sticky='w')
        self.name_input = ctk.CTkEntry(self.inputs_frame, width=205, border_width=2, corner_radius=0)
        self.name_input.bind('<FocusIn>', self.clear_other_entries)
        self.name_input.grid(row=1, column=3, padx=5, sticky='w')

        self.btn_search = ctk.CTkButton(self.inputs_frame, text="Procurar", font=(font, 14, "bold"),
                                        width=110, command=self.search)
        self.btn_search.grid(row=2, column=0, columnspan=4, padx=20, pady=10, sticky='e')

        # ################## Founded Table ##############################
        self.table_frame = ctk.CTkFrame(self, width=500, height=310, corner_radius=0)
        self.table_frame.grid(row=3, rowspan=5, column=0, padx=10, pady=5, sticky="nwse")

        columns = ['ID', 'RankJob', 'Nª AR', 'Nome']
        self.table = Table(self.table_frame, columns, show="headings")
        self.table.pack(expand=True, fill="both")
        # ################## Control Buttons ###########################
        self.btn_frame = ctk.CTkFrame(self, fg_color='transparent')
        self.btn_frame.grid(row=3, rowspan=5, column=1, pady=5, sticky="nwse")
        self.btn_frame.grid_rowconfigure(6, weight=1)

        self.btn_remove = ctk.CTkButton(self.btn_frame, text="Remover", font=(font, 14, "bold"),
                                        width=110, command=self.btn_remove)
        self.btn_remove.grid(row=3, column=0, pady=3, sticky='N')

        self.btn_clean_all = ctk.CTkButton(self.btn_frame, text="Limpar Tudo",
                                           font=(font, 14, "bold"), width=110, command=self.btn_remove_all)
        self.btn_clean_all.grid(row=4, column=0, pady=3, sticky='N')

        self.btn_start = ctk.CTkButton(self.btn_frame, text="Start", fg_color='green', hover_color='dark green',
                                       font=(font, 14, "bold"), width=110, command=self.btn_start)
        self.btn_start.grid(row=5, column=0, pady=3, sticky='N')

        self.qtd_label = ctk.CTkLabel(self.btn_frame, text='Quantidade: 0')
        self.qtd_label.grid(row=6, column=0, pady=3, sticky='S')

        # ################## Binds ###########################
        self.bind('<Return>', self.search)
        self.protocol("WM_DELETE_WINDOW", self.exit)

    def clear_other_entries(self, event=None):
        all_entries = self.inputs_frame.winfo_children()
        for widget in all_entries:
            if isinstance(widget, ctk.CTkEntry):
                widget.delete(0, 'end')

    def search(self, *args):
        range_str = self.range_input.get()
        rankjob_str = self.rankjob_input.get()
        ar_str = self.ar_input.get()
        name_str = self.name_input.get()

        if range_str:
            items = self.file.search_by_rangelist(get_sequence_from_str(range_str))
        elif rankjob_str:
            items = self.file.search_int_with_list(get_sequence_from_str(rankjob_str), 4)
        elif ar_str:
            items = self.file.search_string_in_column(1, ar_str)
        elif name_str:
            items = self.file.search_string_in_column(2, name_str)
        else:
            items = []

        if not items:
            PopUpWindow(self, 'Não Encontrado', 'Registro não encontrado')

        for item in items:
            infos = [item[0] + 1, item[1][4], item[1][1], item[1][2]]
            self.table.add_item(infos)

        self.clear_other_entries()
        self.update_quantity()

    def get_lines_to_remake(self):
        position_list = []

        items_to_remake = self.table.get_items()
        if items_to_remake:
            for item in items_to_remake:
                position_list.append(int(item[0]))

            return build_remake_file_lines(self.file, self.filepath, position_list)

    def btn_start(self):
        lines = [self.get_lines_to_remake()]
        db_items = [db.consult_drawings_from_product(self.client, self.product)]
        product = db.search_product(self.client, self.product)

        if self.printers_list.get() != 'Criar PDF':
            if not validate_printer_paper(self.printers_list.get(), product.paper_size):
                PopUpWindow(
                    self, 'Erro',
                    get_printer_paper_error_message(product.paper_size, wording='cadastrado')
                )
                return

        db_orientation = [product.orientation]  # The function receive a list, in this case is only one orientation
        if lines[0]:
            self.master.create_pdf(lines, db_items, db_orientation, is_remake=True, printer=self.printers_list.get())
            self.exit()
        else:
            PopUpWindow(self, 'Erro!', 'Lista não pode estar vazia!')

    def btn_remove(self):
        self.table.remove_selected_items()
        self.update_quantity()

    def btn_remove_all(self):
        self.table.remove_all()
        self.update_quantity()

    def update_quantity(self):
        total = len(self.table.get_children())
        self.qtd_label.configure(text=f'Quantidade: {total}')

    def exit(self):
        self.master.focus_set()
        self.master.deiconify()
        self.master.clean_worklist()
        self.master.refresh()
        self.destroy()


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


class EditWindow(ctk.CTkToplevel):
    def __init__(self, master, mode, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mode = mode
        self.iconbitmap(icone)
        ctk.deactivate_automatic_dpi_awareness()

        self.geometry(calculate_center_screen_with_monitor(master, 1220, 750, get_monitor(master)))
        self.minsize(1220, 750)
        self.maxsize(1220, 750)
        self.resizable(False, False)
        self.master = master
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.client = master.client_list.radio_var.get()
        self.id_selected_item = None
        self.copied_item = None
        self.set_title(master, mode)
        if mode == 'add':
            self.product_name = 'Novo Produto'
        else:
            self.product_name = master.product_list.radio_var.get()

        self.history = []

        # ------------------------ Name Frame ------------------------------------------------
        self.name_frame = ctk.CTkFrame(self, fg_color='transparent', width=500, height=100)
        self.name_frame.grid(row=0, column=0, columnspan=2, pady=10)

        ctk.CTkLabel(self.name_frame, text='Nome do produto:').grid(row=0, column=0, padx=10)

        self.entry_name_value = ctk.StringVar(value=self.product_name)
        self.entry_name = ctk.CTkEntry(self.name_frame, width=250, textvariable=self.entry_name_value)
        self.entry_name.grid(row=0, column=1, padx=10)

        self.btn_save = ctk.CTkButton(self.name_frame, text='Salvar', state='disabled', width=100,
                                      command=self.save_changes)
        self.btn_save.grid(row=0, column=2, padx=10)

        self.btn_delete = ctk.CTkButton(self.name_frame, text='Deletar', width=100,
                                        fg_color=btn_red,
                                        hover_color=btn_hover_red,
                                        command=self.confirm_delete)
        self.btn_delete.grid(row=0, column=3, padx=10)
        self.btn_visualize = ctk.CTkButton(self.name_frame, text='Visualizar', width=100,
                                           command=self.show_pdf, fg_color='#3F644B', hover_color='#688A76')
        self.btn_visualize.grid(row=0, column=4, padx=10)

        self.lbl_id = ctk.CTkLabel(self, text=f'ID: {self.client} - {self.product_name}', font=('arial', 13, 'bold'))
        self.lbl_id.grid(row=1, column=0, columnspan=2, padx=10)

        # ------------------------ Buttons ------------------------------------------------

        self.btn_tools = ctk.CTkSegmentedButton(self,
                                                values=['Selecionar', 'Mover', 'Linha', 'Quadrado',
                                                        'Texto Fixo', 'Segmento', 'Código Barras', 'Imagem'],
                                                command=self.reset_all
                                                )
        self.btn_tools.grid(row=2, column=0, columnspan=2, padx=0, pady=0)
        self.btn_tools.set(value='Selecionar')


        # ------------------------ Paper Color --------------------------------------------
        self.frame_paper_color = ctk.CTkFrame(self, fg_color='transparent')
        self.frame_paper_color.grid(row=2, column=1, padx=30, sticky='E')

        product = db.search_product(self.client, self.product_name)
        if product:
            product_color = product.paper_color
            product_orientation = product.orientation
            product_paper_size = product.paper_size
        else:
            product_orientation = '0'
            product_color = 'Branco'
            product_paper_size = '9'

        ctk.CTkLabel(self.frame_paper_color, text='Cor do Papel: ').grid(row=0, column=0, padx=2)
        self.paper_color_list = ctk.CTkComboBox(self.frame_paper_color, values=list(paper_color_list.keys()),
                                                command=self.change_color)
        self.paper_color_list.grid(column=1, row=0)
        self.paper_color_list.set(product_color)

        self.color = ctk.CTkFrame(self.frame_paper_color, fg_color=paper_color_list[product_color], width=30, height=30,
                                  corner_radius=0)
        self.color.grid(column=2, row=0, padx=5)

        # ------------------------ Paper Size --------------------------------------------
        self.frame_paper_size = ctk.CTkFrame(self, fg_color='transparent')
        self.frame_paper_size.grid(row=1, column=1, padx=70, sticky='E')

        lbl_paper_size = ctk.CTkLabel(self.frame_paper_size, text='Tamanho Papel: ')
        lbl_paper_size.grid(row=0, column=0, padx=2)
        self.paper_size_list = ctk.CTkComboBox(self.frame_paper_size, values=[str(i) for i in range(21)],
                                               command=self.update_save_button)
        self.paper_size_list.grid(column=1, row=0)
        self.paper_size_list.set(product_paper_size)

        tooltip = Tooltip(lbl_paper_size, paper_size_tip)

        # ------------------------ Frame Choose Type Orientation --------------------------------------
        self.frame_type = ctk.CTkFrame(self, fg_color='transparent')
        self.frame_type.grid(row=2, column=0, padx=30, sticky='W')

        ctk.CTkLabel(self.frame_type, text='Orientação:').grid(row=0, column=0, padx=10)

        self.orient_values = ORIENTATION_LABELS

        self.combobox_type = ctk.CTkComboBox(self.frame_type, values=self.orient_values, width=180,
                                             command=self.change_orientation)
        self.combobox_type.grid(row=0, column=1)
        self.combobox_type.set(self.orient_values[int(product_orientation)])
        # ----------------------------- Canvas -------------------------------------------
        self.grid_rowconfigure(3, weight=1)

        frame = ctk.CTkScrollableFrame(self)
        frame.grid(row=3, column=0, columnspan=5, padx=5, pady=10, sticky="nswe")

        # Resolution changes according to the orientation values from the product # see self.orient_values
        self.resolution = {
            '0': {'width': 1180, 'height': 560},  # 3 ARs Vertical -> Default
            '1': {'width': 590, 'height': 1680},  # 2 ARs Horizontal
            '2': {'width': 1180, 'height': 1680}, # Full A4 AR
            '3': {'width': 1180, 'height': 840}  # 2 ARs folha - Vertical
        }
        canvas_width = self.resolution[product_orientation]['width']
        canvas_height = self.resolution[product_orientation]['height']

        self.canvas = Canvas(frame, width=canvas_width, height=canvas_height, bg='white')
        self.canvas.pack()

        self.canvas_images = []
        self.canvas_dict_images = {}
        self.canvas_db_saved_items = self.consult_drawings_from_db()
        self.history.append(self.canvas_db_saved_items)
        self.lbl_testes = ctk.CTkLabel(self, text='X: , Y:', width=150)
        self.lbl_testes.grid(row=4, column=1, padx=10, sticky='SE')
        # --------------------- Variables and Windows ------------------------------------
        self.properties_window = ListOfPropertiesWindow(self)
        self.start_x = None
        self.start_y = None
        self.draw_object = None
        self.ctrl_z = None
        # ------------------------------- Events ----------------------------------------
        self.canvas.bind("<Button-1>", self.click_mouse_m1)
        self.canvas.bind("<B1-Motion>", self.move_mouse_m1)
        self.canvas.bind("<Motion>", self.canvas_mouse_motion)
        self.canvas.bind("<ButtonRelease-1>", self.mouse_release_m1)
        self.bind("<Key>", self.keyboard_shortcuts)
        self.bind("<Control-c>", self.control_c)
        self.bind("<Control-C>", self.control_c)
        self.bind("<Control-z>", self.control_z)
        self.bind("<Control-Z>", self.control_z)
        self.bind("<Return>", self.reset_all)
        self.bind("<F4>", self.testes)
        self.bind("<Map>", self.bring_windows_back)
        self.bind("<Unmap>", self.minimize_windows)
        self.protocol("WM_DELETE_WINDOW", self.confirm_exit)

        # Any Event That Occurs
        self.entry_name.bind('<KeyRelease>', self.update_save_button)
        self.canvas.bind('<Button>', self.update_save_button)

        self.draw_items_into_canvas(self.canvas_db_saved_items)
        self.focus_force()

    def change_orientation(self, event):
        index = self.orient_values.index(self.combobox_type.get())
        canvas_width = self.resolution[str(index)]['width']
        canvas_height = self.resolution[str(index)]['height']

        self.canvas.configure(width=canvas_width, height=canvas_height)
        self.update_save_button()

    def change_color(self, event):
        color = self.paper_color_list.get()
        self.color.configure(fg_color=paper_color_list[color])
        self.update_save_button()

    def set_title(self, master, mode):
        if mode == 'add':
            self.title(f'{self.client} - Novo Produto')
        elif mode == 'edit':
            product = master.product_list.radio_var.get()
            self.title(f'{self.client} - {product}')
        else:
            raise f'mode invalid: {mode}, use "edit" or "add"'

    def verify_changes(self):
        return has_unsaved_changes(
            self.client,
            self.product_name,
            self.entry_name.get(),
            self.paper_color_list.get(),
            orientation_index_from_label(self.combobox_type.get()),
            self.paper_size_list.get(),
            self.pass_canvas_to_dict(),
            self.consult_drawings_from_db(),
            db,
        )

    def testes(self, *args):
        self.clean_canvas()

    def control_z(self, *args):
        if len(self.history) > 1:
            self.clean_canvas()
            self.history.pop()
            self.draw_items_into_canvas(self.history[-1])
            self.ctrl_z = True
            self.reset_all()

    def show_pdf(self, *args):
        try:
            orientation = self.orient_values.index(self.combobox_type.get())

            generate_test_pdf(self.pass_canvas_to_dict(), orientation=orientation)
            os.startfile(os.path.abspath('temp/text.pdf'))
        except PermissionError:
            PopUpWindow(self, 'Erro', 'Erro ao abrir o PDF, por favor fechar o aplicativo de PDF\n'
                                      'Ou configure o Navegador como aplicativo padrão de PDF')
        except ValueError as e:
            PopUpWindow(self, 'Erro', e)

        except Exception as e:
            PopUpWindow(self, 'Erro', traceback.format_exc())

    def consult_drawings_from_db(self):
        return load_product_drawings(self.client, self.product_name, db)

    def update_save_button(self, *args):
        if self.verify_changes():
            self.btn_save.configure(state='normal')
        else:
            self.btn_save.configure(state='disabled')

    def confirm_delete(self):
        ConfirmWindow(self, 'Você tem certeza?', f'Você realmente deseja deletar o produto {self.product_name}?',
                      self.delete_product)

    def delete_product(self):
        if designer_delete_product(self.client, self.product_name, db):
            self.master.refresh()
            self.exit()
            PopUpWindow(self.master, 'Sucesso', 'Produto deletado com Sucesso!')
        else:
            error_msg = f'Não foi possível deletar o produto "{self.product_name}" do cliente "{self.client}"'
            PopUpWindow(self, 'Erro ao deletar', error_msg)

    def save_changes(self):
        try:
            validation_error = validate_product_name(
                self.product_name,
                self.entry_name.get(),
                db.search_products(self.client),
            )
            if validation_error:
                raise ValueError(validation_error)

            color = self.paper_color_list.get()
            orientation_type = orientation_index_from_label(self.combobox_type.get())
            paper_size = self.paper_size_list.get()
            new_name = self.entry_name.get()

            save_product_with_drawings(
                self.client,
                self.product_name,
                new_name,
                color,
                orientation_type,
                paper_size,
                self.pass_canvas_to_dict(),
                db,
            )

            self.product_name = new_name
            self.title(f'{self.client} - {self.product_name}')
            self.lbl_id.configure(text=f'ID: {self.client} - {self.product_name}')

            self.master.refresh()
            self.update_save_button()
            self.reset_all()
            PopUpWindow(self, 'Sucesso', 'Produto salvo com Sucesso!')
        except PermissionError:
            PopUpWindow(self, 'Erro', 'Erro ao abrir o PDF, por favor fechar o aplicativo de PDF\n'
                                      'Ou configure o Navegador como aplicativo padrão de PDF')
        except ValueError as e:
            PopUpWindow(self, 'Erro', e)

        except Exception as e:
            PopUpWindow(self, 'Erro', traceback.format_exc())

    def pass_canvas_to_dict(self, *args):
        return serialize_canvas_to_dict(self.canvas, self.canvas_dict_images)

    def draw_items_into_canvas(self, items):
        for item in items:
            fonte = (item['font_name'], item['font_size'], item['font_style'])
            tag = item['tag']
            if item['item_type'] == 'line':
                self.canvas.create_line(item['x1'], item['y1'], item['x2'], item['y2'],
                                        width=item['thickness'], dash=item['dashed'])

            elif item['item_type'] == 'rectangle':
                self.canvas.create_rectangle(item['x1'], item['y1'], item['x2'], item['y2'],
                                             width=item['thickness'], dash=item['dashed'])

            elif item['item_type'] in ['text', 'counter', 'segment', 'barcode_text']:
                self.canvas.create_text(item['x1'], item['y1'], text=item['text'], font=fonte,
                                        angle=item['orientation'], anchor="sw", tags=tag)

            elif item['item_type'] == 'barcode':
                create_barcode(item['text'], item['barcode_width'], item['barcode_height'])
                img = get_image('temp/codigo_de_barras.png')
                img = change_proportion(img[2], int(item['proportion']), orientation=int(item['orientation']))
                img_id = self.canvas.create_image(item['x1'], item['y1'], image=img[0], tags=item['tag'], anchor='sw')
                self.canvas_dict_images[img_id] = img

            elif item['item_type'] == 'barcode39':
                create_barcode39(item['text'], item['barcode_width'], item['barcode_height'])
                img = get_image('temp/codigo_de_barras39.png')
                img = change_proportion(img[2], int(item['proportion']), orientation=int(item['orientation']))
                img_id = self.canvas.create_image(item['x1'], item['y1'], image=img[0], tags=item['tag'], anchor='sw')
                self.canvas_dict_images[img_id] = img

            elif item['item_type'] == 'barcodeQR':
                create_qrcode(item['text'])
                img = get_image('temp/qr_code.png')
                img = change_proportion(img[2], int(item['proportion']), orientation=int(item['orientation']))
                img_id = self.canvas.create_image(item['x1'], item['y1'], image=img[0], tags=item['tag'], anchor='sw')
                self.canvas_dict_images[img_id] = img

            elif item['item_type'] == 'barcodeMatrix':
                create_datamatrix(item['text'])
                img = get_image('temp/dmtx.png')
                img = change_proportion(img[2], int(item['proportion']), orientation=int(item['orientation']))
                img_id = self.canvas.create_image(item['x1'], item['y1'], image=img[0], tags=item['tag'], anchor='sw')
                self.canvas_dict_images[img_id] = img

            elif item['item_type'] == 'image':
                img = get_image(blob=item['image'])
                img = change_proportion(img[2], int(item['proportion']), orientation=int(item['orientation']))
                img_id = self.canvas.create_image(item['x1'], item['y1'], image=img[0], anchor='sw')

                self.canvas_dict_images[img_id] = img

    def canvas_mouse_motion(self, event):
        self.lbl_testes.configure(text=f"X: {event.x}, Y: {event.y}")

    def control_c(self, event):
        if self.id_selected_item:
            tag = self.canvas.gettags(self.id_selected_item)
            segment = False
            cordenadas = self.canvas.coords(self.id_selected_item)
            if tag:
                tag = tag[0]
                if tag.startswith('segment'):
                    segment = True

            if segment:
                pass  # Nao utilizar Control-C com Segmento
            elif self.canvas.type(self.id_selected_item) == 'text':
                fonte = self.canvas.itemconfig(self.id_selected_item, 'font')
                texto = self.canvas.itemconfig(self.id_selected_item, 'text')
                self.canvas.create_text(cordenadas[0], cordenadas[1] + 15, text=texto[4], font=fonte[4], anchor="sw")

            elif self.canvas.type(self.id_selected_item) == 'line':
                width = self.canvas.itemconfig(self.id_selected_item, 'width')[4]
                self.canvas.create_line(cordenadas[0] + 5, cordenadas[1] + 5,
                                        cordenadas[2] + 5, cordenadas[3] + 5, width=width)

            elif self.canvas.type(self.id_selected_item) == 'rectangle':
                width = self.canvas.itemconfig(self.id_selected_item, 'width')[4]
                self.canvas.create_rectangle(cordenadas[0], cordenadas[1] + 18,
                                             cordenadas[2], cordenadas[3] + 18, width=width)
            self.reset_all()

    def keyboard_shortcuts(self, event):
        if self.id_selected_item:
            tag = self.canvas.gettags(self.id_selected_item)
            if event.keysym == 'Delete':
                self.delete_object()
            elif event.keysym == 'Left':
                if tag:
                    tag = tag[0]
                    for i in self.canvas.find_withtag(tag):
                        self.canvas.move(i, -1, 0)
                else:
                    self.canvas.move(self.id_selected_item, -1, 0)
            elif event.keysym == 'Right':
                if tag:
                    tag = tag[0]
                    for i in self.canvas.find_withtag(tag):
                        self.canvas.move(i, 1, 0)
                else:
                    self.canvas.move(self.id_selected_item, 1, 0)
            elif event.keysym == 'Up':
                if tag:
                    tag = tag[0]
                    for i in self.canvas.find_withtag(tag):
                        self.canvas.move(i, 0, -1)
                else:
                    self.canvas.move(self.id_selected_item, 0, -1)
            elif event.keysym == 'Down':
                if tag:
                    tag = tag[0]
                    for i in self.canvas.find_withtag(tag):
                        self.canvas.move(i, 0, 1)
                else:
                    self.canvas.move(self.id_selected_item, 0, 1)
            self.properties_window.update_xy_entrys()

    def minimize_windows(self, event):
        if hasattr(self, 'properties_window'):
            self.properties_window.iconify()

    def bring_windows_back(self, event):
        if hasattr(self, 'properties_window'):
            self.properties_window.deiconify()
            self.properties_window.lift()

    def delete_object(self):
        if self.id_selected_item:
            tag = self.canvas.gettags(self.id_selected_item)
            if tag:
                tag = tag[0]
                for i in self.canvas.find_withtag(tag):
                    self.canvas.delete(i)
            else:
                self.canvas.delete(self.id_selected_item)
            self.id_selected_item = None
            self.refresh()

            self.properties_window.refresh()

    def click_mouse_m1(self, event):
        self.properties_window.wm_state('normal')
        self.properties_window.lift()
        self.start_x = event.x
        self.start_y = event.y
        if self.btn_tools.get() in ['Linha', 'Quadrado']:
            self.reset_all()

        elif self.btn_tools.get() in ['Selecionar', 'Mover']:
            id_item = self.canvas.find_closest(event.x, event.y)
            if id_item:
                id_item = id_item[0]
                self.id_selected_item = id_item
                self.refresh()
                self.properties_window.refresh()

        elif self.btn_tools.get() == 'Código Barras':
            GetBarcodeWindow(self, self.start_x, self.start_y)
            self.btn_tools.set(value='Mover')

        elif self.btn_tools.get() == 'Texto Fixo':
            GetTextWindow(self, self.start_x, self.start_y)
            self.refresh()
            self.properties_window.refresh()
            self.btn_tools.set(value='Mover')

        elif self.btn_tools.get() == 'Imagem':
            GetImageWindow(self, self.start_x, self.start_y)
            self.btn_tools.set(value='Mover')

        elif self.btn_tools.get() == 'Segmento':
            GetSegmentWindow(self, self.start_x, self.start_y)
            self.btn_tools.set(value='Mover')

    def move_mouse_m1(self, event):
        self.lbl_testes.configure(text=f"X: {event.x}, Y: {event.y}")
        if self.btn_tools.get() == 'Linha':
            if self.draw_object:
                self.canvas.delete(self.draw_object)
            # If Shift is being Pressed
            if event.state & 0x1:
                if abs(self.start_x - event.x) > abs(self.start_y - event.y):
                    self.draw_object = self.canvas.create_line(self.start_x, self.start_y, event.x, self.start_y,
                                                               width=1)
                else:
                    self.draw_object = self.canvas.create_line(self.start_x, self.start_y, self.start_x, event.y,
                                                               width=1)
            else:
                self.draw_object = self.canvas.create_line(self.start_x, self.start_y, event.x, event.y, width=1)

        elif self.btn_tools.get() == 'Quadrado':
            if self.draw_object:
                self.canvas.delete(self.draw_object)
            self.draw_object = self.canvas.create_rectangle(self.start_x, self.start_y, event.x, event.y, width=1)

        elif self.btn_tools.get() == 'Mover':
            if self.id_selected_item:
                tag = self.canvas.gettags(self.id_selected_item)
                if tag:
                    tag = tag[0]
                    for i in self.canvas.find_withtag(tag):
                        self.canvas.move(i, event.x - self.start_x, event.y - self.start_y)
                else:
                    self.canvas.move(self.id_selected_item, event.x - self.start_x, event.y - self.start_y)
                self.start_x = event.x
                self.start_y = event.y

    def mouse_release_m1(self, event):
        self.update_save_button()
        if self.btn_tools.get() in ['Linha', 'Quadrado']:
            if self.draw_object is not None:
                self.id_selected_item = self.draw_object
            if self.btn_tools.get() == 'Linha':
                self.canvas.itemconfig(self.id_selected_item, fill='red')
            else:
                self.canvas.itemconfig(self.id_selected_item, outline='red')
            self.btn_tools.set(value='Mover')

        self.refresh()
        self.properties_window.refresh()
        self.draw_object = None

    def reset_all(self, *args):
        self.id_selected_item = None
        self.refresh()
        self.properties_window.refresh()

    def paint_object(self, object_id, color):
        if object_id:
            tag = self.canvas.gettags(object_id)
            if tag:
                tag = tag[0]

                for i in self.canvas.find_withtag(tag):
                    if self.canvas.type(i) == 'rectangle':
                        self.canvas.itemconfig(i, outline=color)
                    elif self.canvas.type(i) == 'image' and color == 'red':
                        self.canvas.itemconfig(i, image=self.canvas_dict_images[i][1])
                    elif self.canvas.type(i) == 'image' and color == 'black':
                        self.canvas.itemconfig(i, image=self.canvas_dict_images[i][0])
                    else:
                        self.canvas.itemconfig(i, fill=color)
            else:
                if self.canvas.type(object_id) == 'rectangle':
                    self.canvas.itemconfig(object_id, outline=color)
                elif self.canvas.type(object_id) == 'image' and color == 'red':
                    self.canvas.itemconfig(object_id, image=self.canvas_dict_images[object_id][1])
                elif self.canvas.type(object_id) == 'image' and color == 'black':
                    self.canvas.itemconfig(object_id, image=self.canvas_dict_images[object_id][0])
                else:
                    self.canvas.itemconfig(object_id, fill=color)

    def refresh(self, *args):
        self.update_save_button()
        for i in self.canvas.find_all():
            self.paint_object(i, 'black')

        if self.pass_canvas_to_dict() != self.history[-1] and not self.ctrl_z:
            if len(self.history) > 10:
                self.history.pop(0)

            self.history.append(self.pass_canvas_to_dict())

        self.ctrl_z = None
        if self.id_selected_item:
            self.paint_object(self.id_selected_item, 'red')

    def clean_canvas(self):
        for i in self.canvas.find_all():
            self.canvas.delete(i)

    def confirm_exit(self):
        if self.verify_changes():
            ConfirmWindow(self, 'Produto não salvo', 'O produto não está salvo, você tem certeza?',
                          self.exit, has_confirm=False)
        else:
            self.exit()

    def exit(self):
        
        #ctk.activate_automatic_dpi_awareness()
        self.properties_window.destroy()
        self.destroy()
        self.master.focus_set()
        self.master.deiconify()


class ListOfPropertiesWindow(ctk.CTkToplevel):
    def __init__(self, master, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title('Lista de Propriedades')
        self.iconbitmap(icone)
        self.width, self.height = 300, 550
        self.minsize(self.width, self.height)
        self.maxsize(self.width, self.height)
        self.resizable(False, False)
        self.master = master
        self.last_id = master.id_selected_item

        self.geometry(calculate_center_screen_with_monitor(master, 300, 550, get_monitor(master),
                                                           move_x=-470))
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.frame = ctk.CTkFrame(self, width=280, height=self.height - 20)
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_columnconfigure(1, weight=1)
        self.frame.grid(row=0, column=0, padx=10, pady=10)
        self.validation = self.register(self.is_valid_input)

        self.is_segment = False
        self.segment_properties = None
        self.is_counter = False
        self.segment_itens = []
        self.is_barcode = False
        self.barcode_properties = None
        self.barcode_width = None
        self.barcode_height = None
        self.barcode_column = None
        # ---------------- Widgets for Text -----------------------------------------
        self.entry_x1 = None
        self.entry_y1 = None
        self.entry_x2 = None
        self.entry_y2 = None
        self.combobox_width = None
        self.combobox_dash = None
        self.font_family_combobox = None
        self.font_size_combobox = None
        self.font_style_combobox = None
        self.entry_text = None
        self.orientation = None
        self.distance = None
        self.char_limit = None
        self.btn_ok = None
        self.btn_cancel = None
        self.entry_proportion = None
        self.last_proportion = 100
        self.last_orientation = 0
        self.bind("<Return>", self.update_item)
        self.btn_save_img = None
        self.btn_lift_up = None
        self.btn_lift_down = None

        self.refresh()
        self.protocol('WM_DELETE_WINDOW', lambda: None)

    @staticmethod
    def is_valid_input(input_str):
        return input_str.isdigit() or input_str == ""

    def images_properties(self, selected_object):
        x, y = self.master.canvas.coords(selected_object)

        proportion = self.master.canvas_dict_images[selected_object][3]
        orientation = self.master.canvas_dict_images[selected_object][4]

        lbl_position_x = ctk.CTkLabel(self.frame, text='Posição X:')
        lbl_position_x.grid(row=0, column=0, padx=10, pady=10, sticky="W")

        self.entry_x1 = SpinBox(self.frame, func=self.update_item)
        self.entry_x1.grid(row=0, column=1, pady=10, padx=10)
        self.entry_x1.set(int(x))

        lbl_position_y = ctk.CTkLabel(self.frame, text='Posição Y:')
        lbl_position_y.grid(row=1, column=0, padx=10, pady=10, sticky="W")

        self.entry_y1 = SpinBox(self.frame, func=self.update_item)
        self.entry_y1.grid(row=1, column=1, pady=10, padx=10)
        self.entry_y1.set(int(y))

        ctk.CTkLabel(self.frame, text='Proporção').grid(row=2, column=0, padx=10, pady=10, sticky="W")
        self.entry_proportion = SpinBox(self.frame, func=self.update_item)
        self.entry_proportion.grid(row=2, column=1, pady=10, padx=10)
        self.entry_proportion.set(int(proportion))

        ctk.CTkLabel(self.frame, text='Orientação:').grid(row=3, column=0, padx=10, pady=10, sticky="W")
        self.orientation = ctk.CTkComboBox(self.frame, values=['0', '90', '180', '270'], width=100,
                                           command=self.update_item)
        self.orientation.grid(row=3, column=1, pady=10, padx=10)
        self.orientation.set(orientation)

        if self.is_barcode:
            properties_list = self.barcode_properties[0].split('§')
            w = properties_list[1]  # width
            h = properties_list[2]  # height
            f = properties_list[3]  # field
            ctk.CTkLabel(self.frame, text='Largura:').grid(row=4, column=0, padx=10, pady=10, sticky="W")

            barcode_widths = ['0.17', '0.18', '0.19', '0.20']

            self.barcode_width = ctk.CTkComboBox(self.frame, width=100, values=barcode_widths,
                                                 command=self.update_item)
            self.barcode_width.grid(row=4, column=1, pady=10, padx=10)
            self.barcode_width.set(w)

            # --------------------------------------------------------------------------------------------------

            ctk.CTkLabel(self.frame, text='Altura:').grid(row=5, column=0, padx=10, pady=10, sticky="W")

            self.barcode_height = SpinBox(self.frame, func=self.update_item, step=0.1)
            self.barcode_height.grid(row=5, column=1, pady=10, padx=10)
            self.barcode_height.set(h)

            # --------------------------------------------------------------------------------------------------
            ctk.CTkLabel(self.frame, text='Coluna:').grid(row=6, column=0, padx=10, pady=10, sticky="W")

            columns = [f'Coluna_{i}' for i in range(1, 21)]

            self.barcode_column = ctk.CTkComboBox(self.frame, width=100, values=columns,
                                                  command=self.update_item)
            self.barcode_column.grid(row=6, column=1, pady=10, padx=10)
            self.barcode_column.set(f)

            # --------------------------------------------------------------------------------------------------

        self.btn_ok = ctk.CTkButton(self.frame, text='OK', width=100, command=self.update_item)
        self.btn_ok.grid(row=7, column=1, padx=10, pady=10)

        self.btn_cancel = ctk.CTkButton(self.frame, text='Deletar', fg_color=btn_red, hover_color=btn_hover_red,
                                        width=100, command=self.master.delete_object)
        self.btn_cancel.grid(row=7, column=0, padx=10, pady=10)

        self.btn_lift_up = ctk.CTkButton(self.frame, text='Trazer para frente', width=100, command=self.bring_to_front)
        self.btn_lift_up.grid(row=8, column=1, padx=10, pady=10)

        self.btn_lift_down = ctk.CTkButton(self.frame, text='Enviar para trás', width=100, command=self.send_to_back)
        self.btn_lift_down.grid(row=8, column=0, padx=10, pady=10)

        self.btn_save_img = ctk.CTkButton(self.frame, text='Salvar Imagem', width=100, command=self.save_img)
        self.btn_save_img.grid(row=9, column=0, columnspan=2, padx=10, pady=10)

        tags = self.master.canvas.gettags(self.master.id_selected_item)
        tags_frame = ctk.CTkScrollableFrame(self.frame, height=30, orientation='horizontal')
        tags_frame.grid(row=10, column=0, columnspan=2, padx=10, pady=10)
        ctk.CTkLabel(tags_frame, text=tags).pack()

    def line_properties(self, selected_object):
        x1, y1, x2, y2 = [int(i) for i in self.master.canvas.coords(selected_object)]
        line_width = int(float(self.master.canvas.itemconfig(selected_object, 'width')[4]))
        dash = self.master.canvas.itemconfig(selected_object, 'dash')[4]
        dash = '0' if not dash else dash
        dash_values = {'0': 'Normal', '4': 'Pequeno', '40': 'Grande'}

        lbl_width = ctk.CTkLabel(self.frame, text='Espessura:')
        lbl_width.grid(row=0, column=0, padx=10, pady=10, sticky="W")

        self.combobox_width = ctk.CTkComboBox(self.frame, width=100, values=list(map(str, range(1, 10))),
                                              command=self.update_item)
        self.combobox_width.grid(row=0, column=1, padx=10, pady=10)
        self.combobox_width.set(line_width)

        lbl_dash = ctk.CTkLabel(self.frame, text='Traçejado:')
        lbl_dash.grid(row=1, column=0, padx=10, pady=10, sticky="W")

        self.combobox_dash = ctk.CTkComboBox(self.frame, width=100, values=list(dash_values.values()),
                                             command=self.update_item)
        self.combobox_dash.grid(row=1, column=1, padx=10, pady=10)
        self.combobox_dash.set(dash_values[dash])

        lbl_x_initial = ctk.CTkLabel(self.frame, text='Posição X1:')
        lbl_x_initial.grid(row=2, column=0, padx=10, pady=10, sticky="W")

        self.entry_x1 = SpinBox(self.frame, func=self.update_item)
        self.entry_x1.grid(row=2, column=1, padx=10, pady=10)
        self.entry_x1.set(int(x1))

        lbl_x_initial = ctk.CTkLabel(self.frame, text='Posição Y1:')
        lbl_x_initial.grid(row=3, column=0, padx=10, pady=10, sticky="W")

        self.entry_y1 = SpinBox(self.frame, func=self.update_item)
        self.entry_y1.grid(row=3, column=1, padx=10, pady=10)
        self.entry_y1.set(int(y1))

        lbl_y_final = ctk.CTkLabel(self.frame, text='Posição X2:')
        lbl_y_final.grid(row=4, column=0, padx=10, pady=10, sticky="W")

        self.entry_x2 = SpinBox(self.frame, func=self.update_item)
        self.entry_x2.grid(row=4, column=1, padx=10, pady=10)
        self.entry_x2.set(int(x2))

        lbl_y_final = ctk.CTkLabel(self.frame, text='Posição Y2:')
        lbl_y_final.grid(row=5, column=0, padx=10, pady=10, sticky="W")

        self.entry_y2 = SpinBox(self.frame, func=self.update_item)
        self.entry_y2.grid(row=5, column=1, padx=10, pady=10)
        self.entry_y2.set(int(y2))

        self.btn_ok = ctk.CTkButton(self.frame, text='OK', width=100, command=self.update_item)
        self.btn_ok.grid(row=6, column=1, padx=10, pady=10)

        self.btn_cancel = ctk.CTkButton(self.frame, text='Deletar', fg_color=btn_red, hover_color=btn_hover_red,
                                        width=100, command=self.master.delete_object)
        self.btn_cancel.grid(row=6, column=0, padx=10, pady=10)

        tags = self.master.canvas.gettags(self.master.id_selected_item)
        tags_frame = ctk.CTkScrollableFrame(self.frame, height=30, orientation='horizontal')
        tags_frame.grid(row=7, column=0, columnspan=2, padx=10, pady=10)
        ctk.CTkLabel(tags_frame, text=tags).pack()

    def text_properties(self, selected_object):
        fonte = self.master.canvas.itemconfig(selected_object, 'font')[4]
        if '{' in fonte:
            fontname = fonte.split('}')[0].replace('{', '')
            fontsize = fonte.split('}')[1].split()[0]
            font_style = fonte.split('}')[1].split()[1]
            fonte = [fontname, fontsize, font_style]
        else:
            fonte = self.master.canvas.itemconfig(selected_object, 'font')[4].split()
        texto = self.master.canvas.itemconfig(selected_object, 'text')[4]
        orientacao = self.master.canvas.itemconfig(selected_object, 'angle')[4].replace('.0', '')
        font_family = fonte[0]
        font_size = fonte[1]
        font_style = fonte[2]

        if self.is_segment:
            x, y = self.master.canvas.coords(self.segment_itens[0])
        else:
            x, y = self.master.canvas.coords(selected_object)

        ctk.CTkLabel(self.frame, text='Fonte:').grid(row=0, column=0, padx=10, pady=10, sticky="W")
        self.font_family_combobox = ctk.CTkComboBox(self.frame, values=font_list, width=100, command=self.update_item)
        self.font_family_combobox.grid(row=0, column=1, pady=10, padx=10)
        self.font_family_combobox.set(font_family)

        ctk.CTkLabel(self.frame, text='Tamanho:').grid(row=1, column=0, padx=10, pady=10, sticky="W")
        self.font_size_combobox = ctk.CTkComboBox(self.frame, width=100, values=list(map(str, range(6, 28))),
                                                  command=self.update_item)
        self.font_size_combobox.grid(row=1, column=1, pady=10, padx=10)
        self.font_size_combobox.set(font_size)

        ctk.CTkLabel(self.frame, text='Estilo:').grid(row=2, column=0, padx=10, pady=10, sticky="W")
        self.font_style_combobox = ctk.CTkComboBox(self.frame, values=['Bold', 'Normal'], width=100,
                                                   command=self.update_item)
        self.font_style_combobox.grid(row=2, column=1, pady=10, padx=10)
        self.font_style_combobox.set(font_style.capitalize())

        ctk.CTkLabel(self.frame, text='Orientação:').grid(row=3, column=0, padx=10, pady=10, sticky="W")
        self.orientation = ctk.CTkComboBox(self.frame, values=['0', '90', '180', '270'], width=100,
                                           command=self.update_item)
        self.orientation.grid(row=3, column=1, pady=10, padx=10)
        self.orientation.set(orientacao)
        if self.is_segment:
            segment_distance = self.segment_properties[0].split('§')[2]
            char_limit = self.segment_properties[0].split('§')[4]

            ctk.CTkLabel(self.frame, text='Distância Entre linhas:').grid(row=4, column=0, padx=10, pady=10, sticky="W")
            self.distance = SpinBox(self.frame, func=self.update_item)
            self.distance.grid(row=4, column=1, pady=10, padx=10)
            self.distance.set(segment_distance)

            ctk.CTkLabel(self.frame, text='Limite Caracteres:').grid(row=5, column=0, padx=10, pady=10, sticky="W")
            self.char_limit = SpinBox(self.frame, func=self.update_item)
            self.char_limit.grid(row=5, column=1, pady=10, padx=10)
            self.char_limit.set(char_limit)

        ctk.CTkLabel(self.frame, text='Posição X:').grid(row=6, column=0, padx=10, pady=10, sticky="W")
        self.entry_x1 = SpinBox(self.frame, func=self.update_item)
        self.entry_x1.grid(row=6, column=1, pady=10, padx=10)
        self.entry_x1.set(int(x))

        ctk.CTkLabel(self.frame, text='Posição Y:').grid(row=7, column=0, padx=10, pady=10, sticky="W")
        self.entry_y1 = SpinBox(self.frame, func=self.update_item)
        self.entry_y1.grid(row=7, column=1, pady=10, padx=10)
        self.entry_y1.set(int(y))

        if not self.is_barcode and not self.is_counter and not self.is_segment:
            ctk.CTkLabel(self.frame, text='Texto').grid(row=8, column=0, columnspan=2, padx=10)

            self.entry_text = ctk.CTkEntry(self.frame, width=self.width - 80, justify='center')
            self.entry_text.grid(row=9, column=0, columnspan=2, padx=10, pady=5)
            self.entry_text.configure(textvariable=ctk.StringVar(value=texto))
            self.entry_text.bind("<KeyRelease>", self.update_item)

        self.btn_ok = ctk.CTkButton(self.frame, text='OK', width=100, command=self.update_item)
        self.btn_ok.grid(row=10, column=1, padx=10, pady=10)

        self.btn_cancel = ctk.CTkButton(self.frame, text='Deletar', fg_color=btn_red, hover_color=btn_hover_red,
                                        width=100, command=self.master.delete_object)
        self.btn_cancel.grid(row=10, column=0, padx=10, pady=10)

        tags = self.master.canvas.gettags(self.master.id_selected_item)
        tags_frame = ctk.CTkScrollableFrame(self.frame, height=30, orientation='horizontal')
        tags_frame.grid(row=11, column=0, columnspan=2, padx=10, pady=10)
        ctk.CTkLabel(tags_frame, text=tags).pack()

    def refresh(self):
        if self.master.id_selected_item:
            if self.master.id_selected_item != self.last_id:
                self.last_id = self.master.id_selected_item
                self.frame.destroy()
                self.frame = ctk.CTkFrame(self, width=280, height=self.height - 20, fg_color='transparent')
                self.frame.grid(row=0, column=0, padx=10, pady=10)

                tag_type = self.master.canvas.itemcget(self.master.id_selected_item, "tags")
                print(tag_type)
                self.is_segment = tag_type.startswith('segment')
                print(self.is_segment)
                self.is_barcode = tag_type.startswith('barcode#') or tag_type.startswith('barcode39')
                self.is_counter = tag_type.startswith('counter')
                if self.is_barcode:
                    self.barcode_properties = self.master.canvas.gettags(self.master.id_selected_item)
                elif self.is_segment:
                    tag = self.master.canvas.gettags(self.master.id_selected_item)[0]

                    self.segment_itens = self.master.canvas.find_withtag(tag)
                    self.segment_properties = self.master.canvas.gettags(self.master.id_selected_item)

                if self.master.canvas.type(self.master.id_selected_item) == 'text':
                    self.text_properties(self.master.id_selected_item)
                elif self.master.canvas.type(self.master.id_selected_item) in ['line', 'rectangle']:
                    self.line_properties(self.master.id_selected_item)
                elif self.master.canvas.type(self.master.id_selected_item) == 'image':
                    self.images_properties(self.master.id_selected_item)
            else:
                self.update_xy_entrys()
        else:
            self.last_id = None
            self.frame.destroy()
            self.frame = ctk.CTkFrame(self, width=280, height=self.height - 20, fg_color='transparent')
            self.frame.grid(row=0, column=0, padx=10, pady=10)
            lbl_no_selection = ctk.CTkLabel(self.frame, text='Nenhum item selecionado', font=('Lato', 16, 'bold'))
            self.frame.rowconfigure(0, weight=1)
            lbl_no_selection.grid(row=0, column=0, padx=30, sticky="NSWE")

    def update_xy_entrys(self):
        item_id = self.master.id_selected_item
        if self.is_segment:
            item_id = self.segment_itens[0]
        if item_id:
            coords = list(map(int, self.master.canvas.coords(item_id)))
            if len(coords) == 2:
                x1, y1 = coords
                x2, y2 = None, None
            else:
                x1, y1, x2, y2 = coords

            type_id = self.master.canvas.type(item_id)
            if type_id in ['text', 'image']:
                self.entry_x1.set(x1)
                self.entry_y1.set(y1)
            else:
                self.entry_x1.set(x1)
                self.entry_y1.set(y1)
                self.entry_x2.set(x2)
                self.entry_y2.set(y2)

    def update_item(self, *args):
        item_id = self.master.id_selected_item

        if self.master.canvas.type(item_id) == 'text':
            if self.is_segment:
                self.segment_properties = self.master.canvas.gettags(self.master.id_selected_item)
                fields = self.segment_properties[0].split('§')[3]
                text = self.segment_properties[0].split('§')[1]
                limit = self.char_limit.get()

                x = int(self.entry_x1.get())
                y = int(self.entry_y1.get())
                tag = f"segment{self.entry_x1.get()}{self.entry_y1.get()}§{text}§{self.distance.get()}§{fields}§{limit}"

                for i in self.segment_itens:
                    self.master.canvas.itemconfig(i,
                                                  font=(self.font_family_combobox.get(),
                                                        int(self.font_size_combobox.get()),
                                                        self.font_style_combobox.get().lower()),
                                                  angle=self.orientation.get())
                    self.master.canvas.coords(i, str(x), str(y))

                    self.master.canvas.dtag(i, 'current')
                    self.master.canvas.dtag(i, self.segment_properties[0])

                    self.master.canvas.addtag(tag, "withtag", i)

                    if self.orientation.get() == '90':
                        x += int(self.distance.get())
                    elif self.orientation.get() == '180':
                        y -= int(self.distance.get())
                    elif self.orientation.get() == '270':
                        x -= int(self.distance.get())
                    else:
                        y += int(self.distance.get())
            else:
                if not self.is_counter:
                    self.master.canvas.itemconfig(item_id, text=self.entry_text.get())
                self.master.canvas.itemconfig(item_id,
                                              font=(self.font_family_combobox.get(),
                                                    int(self.font_size_combobox.get()),
                                                    self.font_style_combobox.get().lower()),
                                              angle=self.orientation.get())
                self.master.canvas.coords(item_id, self.entry_x1.get(), self.entry_y1.get())

        elif self.master.canvas.type(item_id) == 'image':
            proportion = int(self.entry_proportion.get())
            orientation = int(self.orientation.get())
            if proportion != self.last_proportion or orientation != self.last_orientation:
                img = change_proportion(self.master.canvas_dict_images[item_id][2], proportion, orientation=orientation)

                self.master.canvas.itemconfig(item_id, image=img[1])
                self.master.canvas_dict_images[item_id] = img
                self.last_proportion = proportion
                self.last_orientation = orientation

            if self.is_barcode:
                self.barcode_properties = self.master.canvas.gettags(self.master.id_selected_item)
                barcode_text = self.barcode_properties[0].split('§')[4]

                w, h, f = self.barcode_width.get(), self.barcode_height.get(), self.barcode_column.get()
                # replace usado pois o tkinter entende o espaco como separador de tag

                if self.barcode_properties[0].startswith('barcode#'):
                    create_barcode(barcode_text.replace('_', ' '), w, h)
                    img = get_image('temp/codigo_de_barras.png')
                    tag_to_add = f"barcode#{self.entry_x1.get()}{self.entry_y1.get()}§{w}§{h}§{f}§{barcode_text}"
                else:
                    create_barcode39(barcode_text.replace('_', ' '), w, h)
                    img = get_image('temp/codigo_de_barras39.png')
                    tag_to_add = f"barcode39{self.entry_x1.get()}{self.entry_y1.get()}§{w}§{h}§{f}§{barcode_text}"

                img = change_proportion(img[2], proportion, orientation)
                self.master.canvas_dict_images[item_id] = img
                self.master.canvas.itemconfig(item_id, image=img[1])
                self.master.canvas.dtag(item_id, 'current')
                self.master.canvas.dtag(item_id, self.barcode_properties[0])

                self.master.canvas.addtag(tag_to_add, "withtag", item_id)
                self.barcode_properties = self.master.canvas.gettags(self.master.id_selected_item)

            self.master.canvas.coords(item_id, self.entry_x1.get(), self.entry_y1.get())

        elif self.master.canvas.type(item_id) in ['line', 'rectangle']:
            dash = self.combobox_dash.get()
            dash_values = {'Normal': '', 'Pequeno': '4', 'Grande': '40'}

            self.master.canvas.itemconfig(item_id,
                                          dash=dash_values[dash],
                                          width=self.combobox_width.get())
            self.master.canvas.coords(item_id, self.entry_x1.get(), self.entry_y1.get(),
                                      self.entry_x2.get(), self.entry_y2.get())
        self.master.update_save_button()

    def save_img(self):
        item_id = self.master.id_selected_item
        path = asksaveasfilename(defaultextension=".png", filetypes=[("Arquivos Imagem", "*.png")],
                                 initialfile=f'Img_{datetime.today().strftime("%Y%m%d%H%M%S")}')

        img = self.master.canvas_dict_images[item_id][2]

        img.save(path)
        os.startfile(path)

    def bring_to_front(self):
        self.master.canvas.lift(self.master.id_selected_item)

    def send_to_back(self):
        self.master.canvas.lower(self.master.id_selected_item)


class GetImageWindow(ctk.CTkToplevel):
    def __init__(self, master, x, y, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iconbitmap(icone)

        self.geometry(calculate_center_screen_with_monitor(master, 250, 150, get_monitor(master)))
        self.minsize(250, 150)
        self.maxsize(250, 150)
        self.resizable(False, False)
        self.master = master
        self.grab_set()
        self.x = x
        self.y = y
        self.filepath = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.btn_select_image = ctk.CTkButton(self, text='Selecione um arquivo', command=self.select_file)
        self.btn_select_image.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky='S')

        self.lbl_image_name = ctk.CTkLabel(self, text='')
        self.lbl_image_name.grid(row=1, column=0, columnspan=2, padx=10, sticky='N')

        self.btn_ok = ctk.CTkButton(self, text="OK", width=80, state="disabled", command=self.draw_image)
        self.btn_ok.grid(row=2, column=0, pady=10)

        self.btn_cancelar = ctk.CTkButton(self, width=80, text="Cancelar", fg_color=btn_red,
                                          hover_color=btn_hover_red)
        self.btn_cancelar.grid(row=2, column=1, pady=10)

    def select_file(self):
        self.filepath = askopenfilename(filetypes=[("Image files", ["*.png", "*.jpg"])])
        self.lbl_image_name.configure(text=os.path.basename(self.filepath))
        if self.filepath:
            self.btn_ok.configure(state="normal")

    def draw_image(self):
        img = get_image(self.filepath)
        img_id = self.master.canvas.create_image(self.x, self.y, image=img[0], anchor='sw')

        self.master.canvas_dict_images[img_id] = img

        # Refresh
        self.master.refresh()
        self.master.properties_window.refresh()
        self.destroy()


class GetTextWindow(ctk.CTkToplevel):
    def __init__(self, master, x, y, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iconbitmap(icone)

        self.geometry(calculate_center_screen_with_monitor(master, 420, 300, get_monitor(master)))
        self.minsize(420, 300)
        self.maxsize(420, 300)
        self.resizable(False, False)
        self.master = master
        self.grab_set()
        self.x = x
        self.y = y

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text='Fonte:').grid(row=0, column=0, pady=10, padx=10)
        self.font_list = ctk.CTkComboBox(self, values=font_list)
        self.font_list.grid(row=0, column=1, pady=10, padx=10, sticky='W')

        ctk.CTkLabel(self, text='Tamanho:').grid(row=1, column=0, pady=10, padx=10)
        self.fontsize = ctk.CTkComboBox(self, values=list(map(str, range(6, 28))))
        self.fontsize.set('10')
        self.fontsize.grid(row=1, column=1, pady=10, padx=10, sticky='W')

        ctk.CTkLabel(self, text='Orientação:').grid(row=2, column=0, pady=10, padx=10)
        self.orientation = ctk.CTkComboBox(self, values=['0', '90', '180', '270'])
        self.orientation.grid(row=2, column=1, pady=10, padx=10, sticky='W')

        self.counter_var = ctk.IntVar()
        self.counter = ctk.CTkCheckBox(self, text='Counter', command=self.verify_counter, variable=self.counter_var)
        self.counter.grid(row=3, column=0, padx=30, sticky='E')

        self.bold = ctk.CTkCheckBox(self, text='Bold')
        self.bold.grid(row=3, column=1, padx=10)

        ctk.CTkLabel(self, text='Texto').grid(row=4, column=0, columnspan=2, padx=10)
        self.text = ctk.CTkEntry(self, width=300)
        self.text.grid(row=5, column=0, columnspan=2, padx=10)

        self.btn_ok = ctk.CTkButton(self, text="OK", width=120, command=self.draw_text)
        self.btn_ok.grid(row=6, column=0, pady=20, padx=20)

        self.btn_cancelar = ctk.CTkButton(self, width=120, text="Cancelar", fg_color=btn_red,
                                          hover_color=btn_hover_red, command=self.destroy)
        self.btn_cancelar.grid(row=6, column=1, pady=20, padx=20)

    def draw_text(self):
        tag = ''
        if self.counter_var.get():
            tag = f'counter{self.x}{self.y}§§§§'
        weight = "bold" if self.bold.get() else "normal"
        fonte = (self.font_list.get(), self.fontsize.get(), weight)
        if self.text.get().strip() == "":
            PopUpWindow(self, "Erro!", "O campo TEXTO não pode estar vazio")
        else:
            self.master.canvas.create_text(self.x, self.y, text=self.text.get(), font=fonte,
                                           angle=self.orientation.get(), anchor="sw", tag=tag)
            self.master.reset_all()
            self.destroy()

    def verify_counter(self):
        if self.counter_var.get():
            self.text.delete('0', 'end')
            self.text.insert('0', '0000001')
            self.text.configure(state='disabled')
        else:
            self.text.configure(state='normal')
            self.text.delete('0', 'end')


class GetBarcodeWindow(ctk.CTkToplevel):
    def __init__(self, master, x, y, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iconbitmap(icone)

        self.geometry(calculate_center_screen_with_monitor(master, 380, 540, get_monitor(master)))
        self.minsize(380, 540)
        self.maxsize(380, 540)
        self.resizable(False, False)
        self.master = master
        self.grab_set()
        self.x = x
        self.y = y

        self.title("Código de Barras")

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text='Modelo:').grid(row=0, column=0, padx=10, pady=10, sticky='E')

        barcode_models = ['Barcode 128', 'Barcode 39', 'QRCode', 'Matrix']
        self.entry_model = ctk.CTkComboBox(self, values=barcode_models, width=120, command=self.enable_disable_config)
        self.entry_model.grid(row=0, column=1, padx=10, pady=10, sticky='W')

        ctk.CTkLabel(self, text='Espessura:').grid(row=1, column=0, padx=10, pady=10, sticky='E')

        barcode_widths = ['0.17', '0.18', '0.19', '0.20']
        self.entry_width = ctk.CTkComboBox(self, values=barcode_widths, width=120)
        self.entry_width.grid(row=1, column=1, padx=10, pady=10, sticky='W')

        ctk.CTkLabel(self, text='Altura:').grid(row=2, column=0, padx=10, pady=10, sticky='E')

        barcode_heights = ['1.1', '1.2', '1.3', '1.4', '1.5', '1.6', '1.7', '1.8', '1.9',
                           '2.0', '2.1', '2.2', '2.3', '2.4', '2.5', '2.6', '2.7', '2.8',
                           '2.9']

        self.entry_height = ctk.CTkComboBox(self, values=barcode_heights, width=120)
        self.entry_height.set('5')
        self.entry_height.grid(row=2, column=1, padx=10, pady=10, sticky='W')

        ctk.CTkLabel(self, text='Texto (Placeholder)').grid(row=3, column=0, columnspan=2, padx=10)

        self.text = ctk.CTkEntry(self, width=200)
        self.text.insert(0, 'FS123456789BR')
        self.text.grid(row=4, column=0, columnspan=2, padx=10)

        help_text = 'Selecione a coluna  do arquivo a ser usada no texto variavel'
        ctk.CTkLabel(self, text=help_text).grid(row=5, column=0, columnspan=2, pady=5)

        self.fields = ListBox(self, [f'Coluna_{i}' for i in range(1, 100)])
        self.fields.grid(row=6, column=0, columnspan=2)

        self.btn_ok = ctk.CTkButton(self, text="OK", width=120, state='disabled', command=self.create_barcode)
        self.btn_ok.grid(row=7, column=0, pady=20, padx=20)

        self.btn_cancelar = ctk.CTkButton(self, width=120, text="Cancelar", fg_color=btn_red,
                                          hover_color=btn_hover_red, command=self.destroy)
        self.btn_cancelar.grid(row=7, column=1, pady=20, padx=20)

    def create_barcode(self):
        if self.text.get():
            w, h, f = self.entry_width.get(), self.entry_height.get(), self.fields.radio_var.get()
            # Replace usado devido Tkinter entender o espaço como separador de tags
            text = self.text.get().replace(' ', '_')
            if self.entry_model.get() == 'Barcode 128':
                tag = f"barcode#{self.x}{self.y}§{w}§{h}§{f}§{text}"
                create_barcode(self.text.get(), w, h)
                img = get_image('temp/codigo_de_barras.png')

            elif self.entry_model.get() == 'Barcode 39':
                tag = f"barcode39{self.x}{self.y}§{w}§{h}§{f}§{text}"
                create_barcode39(self.text.get(), w, h)
                img = get_image('temp/codigo_de_barras39.png')

            elif self.entry_model.get() == 'QRCode':
                tag = f"barcodeQR{self.x}{self.y}§§§{f}§{text}"
                create_qrcode(self.text.get())
                img = get_image('temp/qr_code.png')

            else:
                tag = f"barcodeMatrix{self.x}{self.y}§§§{f}§{text}"
                create_datamatrix(self.text.get())
                img = get_image('temp/dmtx.png')

            img_id = self.master.canvas.create_image(self.x, self.y, image=img[0], tags=tag, anchor='sw')
            if self.entry_model.get() in ['Barcode 128', 'Barcode 39']:
                self.master.canvas.create_text(self.x, self.y + 22, text=self.text.get(),
                                               fill="black", font=("arial", 10, "normal"),
                                               tags=f"barcode_text{self.x}{self.y}§§§{f}§{text}",
                                               anchor='sw')
            self.master.canvas_dict_images[img_id] = img

            self.master.properties_window.refresh()
            self.destroy()
        else:
            PopUpWindow(self, 'Erro', 'Placeholder deve ser preenchido')

    def enable_disable_config(self, *args):
        if self.entry_model.get() in ['Barcode 128', 'Barcode 39']:
            self.entry_width.configure(state="normal")
            self.entry_height.configure(state="normal")
        else:
            self.entry_width.configure(state="disabled")
            self.entry_height.configure(state="disabled")

    def refresh(self, *args):
        self.btn_ok.configure(state='normal')


class GetSegmentWindow(ctk.CTkToplevel):
    def __init__(self, master, x, y, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iconbitmap(icone)

        self.geometry(calculate_center_screen_with_monitor(master, 600, 350, get_monitor(master)))
        self.minsize(600, 350)
        self.maxsize(600, 350)
        self.resizable(False, False)
        self.title('Configurar Segmento')
        self.master = master
        self.grab_set()
        self.x = x
        self.y = y

        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=3)
        self.grid_columnconfigure(2, weight=2)
        self.grid_columnconfigure(3, weight=2)

        self.validation = self.register(self.is_valid_input)
        self.list = []
        self.checkbox_list = {}
        self.placeholders_list = []
        # ------------------ Fields Frame -----------------------------------------------
        self.fields_frame = ctk.CTkScrollableFrame(self, label_text='Selecionar campos do arquivo',
                                                   width=100, height=220)
        self.fields_frame.grid(padx=15, pady=15, row=0, column=0, rowspan=4)

        for i in range(1, 100):
            checkbox = ctk.CTkCheckBox(self.fields_frame, text=f'Coluna_{i}', border_width=1, corner_radius=3,
                                       checkbox_height=20, checkbox_width=20, border_color='white')
            checkbox.configure(command=lambda z=checkbox: self.update_placeholder_frame(z))

            checkbox.grid(padx=2, pady=5)
            self.checkbox_list[i] = checkbox

        # ------------------ Placeholders Frame -----------------------------------------
        self.placeholders_frame = None
        self.no_selection_lbl()

        # ------------------ First Row (Labels and Input) -------------------------------
        ctk.CTkLabel(self, text='Placeholders', font=(font, 20, 'bold')).grid(row=0, column=1, sticky='W')

        ctk.CTkLabel(self, text='Limite caracteres:').grid(row=0, column=2, padx=5, sticky='E')

        self.input_largura = ctk.CTkEntry(self, width=50, height=10, fg_color='white', text_color='black',
                                          border_width=1, corner_radius=0, validate='key',
                                          validatecommand=(self.validation, '%S'))

        self.input_largura.grid(row=0, column=3, sticky='W')
        self.input_largura.insert(0, '0')

        # ------------------ Line Height ----------------------------------------------
        ctk.CTkLabel(self, text='Distância linhas:').grid(row=3, column=1, sticky='W')
        self.input_distancia = ctk.CTkEntry(self, width=50, height=10, fg_color='white', text_color='black',
                                            border_width=1, corner_radius=0, validate='key',
                                            validatecommand=(self.validation, '%S'))

        self.input_distancia.grid(row=3, column=1, sticky='E')
        self.input_distancia.insert(0, '15')

        # ------------------ Ok Button ------------------------------------------------
        self.btn_ok = ctk.CTkButton(self, text="OK", width=80, command=self.place_segment)
        self.btn_ok.grid(row=3, column=2, columnspan=2, sticky='E', padx=25)

        # ---------------- Font Properties -------------------------------------------
        ctk.CTkLabel(self, text='Fonte:').grid(padx=20, row=4, column=0, sticky='W')
        self.font = ctk.CTkComboBox(self, width=100, height=20, fg_color='white', text_color='black',
                                    border_width=1, corner_radius=0, values=font_list)
        self.font.grid(padx=20, row=4, column=0)

        ctk.CTkLabel(self, text='Tamanho:').grid(row=4, column=1, sticky='W')
        self.size = ctk.CTkComboBox(self, width=70, height=20, fg_color='white', text_color='black',
                                    border_width=1, corner_radius=0, values=[str(i) for i in range(6, 20)])
        self.size.set('10')
        self.size.grid(padx=20, row=4, column=1, sticky='E')

        self.bold = ctk.CTkCheckBox(self, checkbox_width=20, checkbox_height=20,
                                    corner_radius=0, text='Bold', border_width=2)
        self.bold.grid(row=4, column=2, sticky='W')

    def place_segment(self):
        char_limit = self.input_largura.get()
        id = f'{self.x}{self.y}'

        # Retrieve the texts first
        tag_text = []
        for entry in self.placeholders_list:
            tag_text.append(entry.get().replace(' ', '_'))
        tag_text = '.'.join(tag_text)

        for entry in self.placeholders_list:
            text = break_line(entry.get(), char_limit)
            tag_id = f"segment{id}§{tag_text}§{self.input_distancia.get()}§{self.get_selected_checkbox()}§" \
                     f"{char_limit}"
            self.master.canvas.create_text(self.x, self.y, text=text[0],
                                           fill="black", anchor='sw', justify='left', tags=tag_id,
                                           font=(self.font.get(), self.size.get(),
                                                 "bold" if self.bold.get() else "normal"))

            # Verificar se tem quebra de linha
            if text[1]:
                tag_id = f"segment{id}§{tag_text}§{self.input_distancia.get()}§{self.get_selected_checkbox()}§" \
                         f"{char_limit} IGNORE"
                self.y += int(self.input_distancia.get())
                self.master.canvas.create_text(self.x, self.y, text=text[1],
                                               fill="black", anchor='sw', justify='left', tags=tag_id,
                                               font=(self.font.get(), self.size.get(),
                                                     "bold" if self.bold.get() else "normal"))

            self.master.properties_window.refresh()
            self.y += int(self.input_distancia.get())
        self.get_selected_checkbox()
        self.destroy()

    def get_selected_checkbox(self):
        selected_checkbox = [i.cget('text') for i in self.checkbox_list.values() if i.get()]
        return '.'.join(self.list)

    def update_placeholder_frame(self, widget):
        placeholders_content = [entry.get() for entry in self.placeholders_list]
        placeholders_content = dict(enumerate(placeholders_content))
        if widget.get():
            self.list.append(widget.cget('text'))
        else:
            self.list.remove(widget.cget('text'))

        self.placeholders_frame.destroy()
        self.placeholders_frame = ctk.CTkScrollableFrame(self, width=320, height=210)
        self.placeholders_frame.grid(row=1, column=1, columnspan=3, rowspan=2, sticky='W')
        self.placeholders_frame.columnconfigure(0, weight=1)
        self.placeholders_frame.columnconfigure(1, weight=3)

        self.placeholders_list = []
        for i, checkbox in enumerate(self.list):
            ctk.CTkLabel(self.placeholders_frame, text=checkbox).grid(padx=10, row=i, column=0)
            entry = ctk.CTkEntry(self.placeholders_frame, width=230, height=10,
                                 fg_color='white', text_color='black',
                                 border_width=1, corner_radius=0)
            self.placeholders_list.append(entry)
            entry.insert(0, placeholders_content.get(i, f'Placeholder {i}'))
            entry.grid(column=1, row=i, sticky='W')

        if not self.list:
            self.no_selection_lbl()

    def no_selection_lbl(self):
        self.placeholders_frame = ctk.CTkScrollableFrame(self, width=320, height=210)
        self.placeholders_frame.grid(row=1, column=1, columnspan=3, rowspan=2, sticky='W')
        self.placeholders_frame.columnconfigure(0, weight=1)

        ctk.CTkLabel(self.placeholders_frame, text='SELECIONE UM CAMPO', font=(font, 25, 'bold'),
                     text_color='#161616', height=180).grid(row=0, column=0)

    @staticmethod
    def is_valid_input(input_str):
        return input_str.isdigit() or input_str == ""


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
