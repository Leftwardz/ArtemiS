import os
import sys
import traceback
from threading import Thread

import customtkinter as ctk

from app.services.print_service import finish_print_job, get_printer_paper_error_message, validate_printer_paper
from app.services.production_service import (
    ensure_output_directories,
    find_work_in_directory,
    get_drawings_and_orientations,
    get_paper_size_from_path,
    get_product_from_file as production_get_product_from_file,
    get_work_product_info,
    load_worklist_file_lines,
    normalize_group_flag,
    resolve_work_search_path,
    validate_queue_consistency,
    work_is_empty_file,
)
from app.ui.components import PopUpWindow
from app.ui.constants import (
    APP_NAME,
    BTN_HOVER_RED,
    BTN_RED,
    DEFAULT_HEIGHT,
    DEFAULT_WIDTH,
    FONT,
    ICON,
    PAPER_COLOR_LIST,
)
from app.ui.remake_window import RemakeWindow
from app.utils.file_parser import FileUtils
from app.utils.window_geometry import calculate_center_screen
from pdf_utils import write_text_to_pdf


def _runtime():
    return sys.modules["__main__"]


class App(ctk.CTk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title(APP_NAME)
        self.iconbitmap(ICON)
        ctk.set_default_color_theme("dark-blue")
        ctk.set_appearance_mode("dark")
        self.option_add("*Font", ("Segoe UI", 15))

        self.winfo_screenwidth()
        self.geometry(calculate_center_screen(DEFAULT_WIDTH, DEFAULT_HEIGHT, self))
        self.minsize(DEFAULT_WIDTH, DEFAULT_HEIGHT)
        self.maxsize(DEFAULT_WIDTH, DEFAULT_HEIGHT)

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
        self.lbl_title = ctk.CTkLabel(self, text=APP_NAME, font=(FONT, 45, "bold"), fg_color="transparent")
        self.lbl_title.grid(row=0, column=0, columnspan=4, padx=10, pady=10)

        # ############# Botão config ############################
        self.btn_config = ctk.CTkButton(self, text="⚙", font=(FONT, 18, "normal"),
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
        printers_list.extend(_runtime().db.search_printers())
        self.printers_list = ctk.CTkComboBox(self.frame_printers, values=printers_list, width=210)
        self.printers_list.grid(row=0, column=1, padx=15)

        self.lbl_select_group = ctk.CTkLabel(self.frame_printers, text="Selecione Grupo:")
        self.lbl_select_group.grid(row=1, column=0, padx=10)

        self.print_group_list = ctk.CTkComboBox(self.frame_printers, values=_runtime().db.search_print_group(), width=210)
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
        self.btn_start = ctk.CTkButton(self, text="Start", font=(FONT, 14, "bold"), state='disabled',
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
        self.paper_color.configure(fg_color=PAPER_COLOR_LIST[color])

    def remake_widget_update(self):
        if self.remake_var.get() == 1:
            self.txtbox_ar.focus()
            self.entry_range.delete(0, "end")
        else:
            self.txtbox_ar.delete('0.0', 'end')

    def open_toplevel(self):
        runtime = _runtime()

        def open_config():
            self.config_window = runtime.ConfigWindow(self)
            self.withdraw()

        if _runtime().db.has_login():
            runtime.LoginWindow(self, open_config)
        else:
            runtime.RegisterWindow(self, open_config, first_login=True)

    def get_paper_size_from_worklist(self):
        return get_paper_size_from_path(self.works_paths[0], _runtime().db)

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
        folder_destination = os.path.join(_runtime().config['search_folder'], 'PDFs')

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
        return get_drawings_and_orientations(files, _runtime().db)

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
        path = resolve_work_search_path(_runtime().config['search_folder'], group_flag, self.checkbox_remake.get())

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
                                                         f'Caminho: {_runtime().config["search_folder"]}')
                return

            if self.is_empty_file(full_path):
                PopUpWindow(self, 'Erro', 'Arquivo encontrado está vazio - Verificar')
                self.entry_work.delete('0', 'end')
                return

            work_info = get_work_product_info(full_path, _runtime().db)
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
        ensure_output_directories(_runtime().config['search_folder'])

    def refresh(self, *args):
        self.btn_start.configure(state='disabled')
        self.btn_config.configure(state='normal')
        self.printers_list.configure(state='normal')

        # update the printers list, when it's included in the Printer List in configs
        printers_list = ['Criar PDF']
        printers_list.extend(_runtime().db.search_printers())
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

        ctk.CTkButton(frame, text='Visualizar', fg_color=BTN_RED, hover_color=BTN_HOVER_RED,
                      command=lambda: self.visualize_error(printer_name, path)).grid(row=1)

    def visualize_error(self, printer_name, path):
        self.remove_progressbar(printer_name)

        os.startfile(os.path.abspath(path))
