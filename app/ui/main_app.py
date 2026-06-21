import os
import traceback

import customtkinter as ctk

from app.services.print_job_coordinator import start_pdf_generation
from app.services.print_service import finish_print_job, get_printer_paper_error_message, validate_printer_paper
from app.services.production_service import (
    ensure_output_directories,
    get_drawings_and_orientations,
    get_paper_size_from_path,
    get_work_product_info,
    load_worklist_file_lines,
    is_empty_file as work_is_empty_file,
)
from app.ui.components import PopUpWindow, WORK_QUEUE_WIDTH, WorkQueueList
from app.ui.config_window import ConfigWindow
from app.ui.constants import (
    APP_NAME,
    BTN_HOVER_RED,
    BTN_RED,
    DEFAULT_HEIGHT,
    DEFAULT_WIDTH,
    FONT,
    ICON,
    LOADING_SIDEBAR_WIDTH,
    PAPER_COLOR_LIST,
)
from app.ui.remake_window import RemakeWindow
from app.utils.document_delivery import open_path
from app.utils.file_parser import FileUtils
from app.services import admin_service
from app.services.settings_service import get_search_folder
from app.services.work_queue_service import search_work_for_queue
from app.utils.window_geometry import calculate_center_screen


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

        for col in range(4):
            self.grid_columnconfigure(col, weight=1)
        self.grid_rowconfigure(7, weight=1)

        self.config_window = None
        self.file_lines = None
        self.progressbar = None
        self.lbl_progressbar = None

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

        self.printers_list = ctk.CTkComboBox(self.frame_printers, values=self._printer_combo_values(), width=210)
        self.printers_list.grid(row=0, column=1, padx=15)

        self.lbl_select_group = ctk.CTkLabel(self.frame_printers, text="Selecione Grupo:")
        self.lbl_select_group.grid(row=1, column=0, padx=10)

        self.print_group_list = ctk.CTkComboBox(self.frame_printers, values=admin_service.list_print_groups(), width=210)
        self.print_group_list.grid(row=1, column=1, padx=15, pady=5)

        # ######################## Remake Checkbox ##############################
        self.remake_frame = ctk.CTkFrame(self, fg_color='transparent')
        self.remake_frame.grid(row=2, column=0, columnspan=4, pady=10)

        self.checkbox_remake = ctk.CTkCheckBox(
            self.remake_frame, text='Habilitar Remake', command=self.remake_checkbox_event,
        )
        self.checkbox_remake.pack(side='left', padx=8)

        self.checkbox_remake_refazer = None

        # ################ Selecione Works #####################
        frame_works = ctk.CTkFrame(self, fg_color="transparent")
        frame_works.grid(row=3, column=0, columnspan=4, pady=10)

        ctk.CTkLabel(frame_works, text="Escaneie as Workorders: ").grid(row=0, column=0, sticky='w')

        self.entry_work = ctk.CTkEntry(
            frame_works,
            border_width=2,
            corner_radius=0,
            width=WORK_QUEUE_WIDTH,
        )
        self.entry_work.grid(row=1, column=0, sticky='w')
        self.entry_work.bind('<Return>', self.search_work)

        self.work_queue = WorkQueueList(frame_works, width=WORK_QUEUE_WIDTH, height=122)
        self.work_queue.grid(row=2, column=0, sticky='nw')

        worklist_actions = ctk.CTkFrame(frame_works, fg_color='transparent')
        worklist_actions.grid(row=3, column=0, sticky='w', pady=(4, 0))

        ctk.CTkButton(worklist_actions, text="Remover", width=70, height=24, corner_radius=0,
                      command=self.remove_selected_works).pack(side='left', padx=(0, 6))
        ctk.CTkButton(worklist_actions, text="Limpar", width=70, height=24, corner_radius=0,
                      command=self.clean_worklist).pack(side='left')

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
        self.btn_start = ctk.CTkButton(self, text="Start", font=(FONT, 14, "bold"), state='disabled',
                                       command=self.btn_start)
        self.btn_start.grid(row=7, column=0, columnspan=4, padx=10, pady=10, sticky="s")

        ctk.CTkLabel(self, text='Developed By Nathan - V1.0.9', text_color='grey').grid(
            row=7, column=0, columnspan=4, padx=5, sticky='SE',
        )

        # Barra de progresso à esquerda — não ocupa coluna do grid (evita deslocar o centro visual)
        self.loading_frame = LoadingBarFrame(
            self,
            fg_color='transparent',
            width=LOADING_SIDEBAR_WIDTH,
            height=DEFAULT_HEIGHT,
        )
        self.loading_frame.place(x=0, y=0, relheight=1.0, anchor='nw')

        self.verify_directorys()

    def remake_checkbox_event(self, event=None):
        if self.checkbox_remake.get():
            self.checkbox_remake_refazer = ctk.CTkCheckBox(
                self.remake_frame, text='Não Utilizar Tela Secundária', command=self.clean_worklist,
            )
            self.checkbox_remake_refazer.pack(side='left', padx=8)
        else:
            self.checkbox_remake_refazer.destroy()
            self.checkbox_remake_refazer = None

        self.clean_worklist()

    def create_printing_label(self):
        self.printing_label = ctk.CTkLabel(
            self,
            text="Realizando Impressão\nAguarde...",
            font=('Arial', 30, 'bold'),
            fg_color='transparent',
            bg_color='transparent',
        )
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
        if not admin_service.can_access_config():
            user = admin_service.get_current_windows_user()
            PopUpWindow(
                self,
                'Acesso negado',
                f'Seu usuário Windows ({user}) não tem permissão para abrir as configurações.\n\n'
                'Administradores do PC ou da rede sempre têm acesso.\n'
                'Demais usuários precisam ser liberados por um administrador.',
            )
            return

        self.config_window = ConfigWindow(self)
        self.withdraw()

    @staticmethod
    def _printer_combo_values():
        labels, _name_map = admin_service.get_printer_combo_options()
        return ['Criar PDF'] + labels

    def _selected_printer_name(self):
        return admin_service.resolve_printer_name(self.printers_list.get())

    def get_work_paths(self):
        return self.work_queue.get_paths()

    def get_paper_size_from_worklist(self):
        return get_paper_size_from_path(self.get_work_paths()[0], admin_service.get_db())

    def btn_start(self):
        printer_name = self._selected_printer_name()
        if printer_name != 'Criar PDF':
            paper_size = self.get_paper_size_from_worklist()
            if not validate_printer_paper(printer_name, paper_size):
                PopUpWindow(self, 'Erro', get_printer_paper_error_message(paper_size))
                return

        lines = self.open_files_from_worklist()
        items, orientations = self.get_items_and_orientation_from_worklist(lines)

        self.create_pdf(lines, items, orientations, self.checkbox_remake.get(), printer=printer_name)

    def _build_pdf_callbacks(self, progress_slot, printer):
        def on_progress(_printer_name, progress, text):
            self.after(0, lambda: self._on_pdf_progress(progress_slot, progress, text))

        def on_error(_printer_name, error_traceback):
            self.after(0, lambda: self.loading_frame.show_error(progress_slot, error_traceback))

        def on_complete(pdf_bytes, files_to_move, is_remake_flag, _printer_name):
            self.after(0, lambda: self.open_or_print_pdf(
                pdf_bytes, files_to_move, is_remake_flag, printer, progress_slot))

        return on_progress, on_error, on_complete

    def _on_pdf_progress(self, progress_slot, progress, text):
        self.loading_frame.update_progressbar(progress_slot, progress, text)
        self.update_idletasks()

    def create_pdf(self, lines, items, orientations, is_remake=False, printer=None):
        try:
            progress_slot = self.loading_frame.add_progressbar(printer)
        except Exception as e:
            PopUpWindow(self, "Erro", e)
            return

        on_progress, on_error, on_complete = self._build_pdf_callbacks(progress_slot, printer)

        start_pdf_generation(
            items,
            lines,
            orientations,
            is_remake,
            printer,
            on_progress,
            on_error,
            on_complete,
        )

        self.refresh()

    def get_items_and_orientation_from_worklist(self, files):
        return get_drawings_and_orientations(files, admin_service.get_db())

    def open_files_from_worklist(self, *args):
        return load_worklist_file_lines(self.get_work_paths())

    def remove_selected_works(self):
        if not self.work_queue.has_selection():
            return
        self.work_queue.remove_selected()
        self._sync_queue_state()

    def _sync_queue_state(self):
        paths = self.get_work_paths()
        if not paths:
            self.btn_start.configure(state='disabled')
            self.frame_papercolor.grid_forget()
            self.defined_color = None
            self.defined_paper_size = None
            self.entry_work.focus()
            return

        self.btn_start.configure(state='normal')
        info = get_work_product_info(paths[0], admin_service.get_db())
        if info:
            self.defined_paper_size = info.paper_size
            self.defined_color = info.color
            self.show_color(info.color)

    def clean_worklist(self):
        self.work_queue.clear_all()
        self._sync_queue_state()

    def is_empty_file(self, path):
        return work_is_empty_file(path)

    def get_product_from_file(self, path):
        from app.services.production_service import get_product_from_file
        return get_product_from_file(path)

    def search_work(self, *args):
        work = self.entry_work.get().upper()
        if not work:
            return

        if self.get_work_paths():
            self.btn_start.configure(state='normal')

        skip_remake_screen = bool(
            self.checkbox_remake_refazer and self.checkbox_remake_refazer.get()
        )
        result = search_work_for_queue(
            work,
            get_search_folder(),
            self.print_group_list.get(),
            self.checkbox_remake.get(),
            skip_remake_screen,
            self.get_work_paths(),
            self.defined_paper_size,
            self.defined_color,
            admin_service.get_db(),
        )

        if result.status == 'empty':
            return
        if result.status == 'duplicate':
            PopUpWindow(self, 'Erro', 'Work já está na lista')
            self.entry_work.delete('0', 'end')
            return
        if result.status == 'path_missing':
            PopUpWindow(self, result.error.title, result.error.message)
            return
        if result.status == 'not_found':
            self.entry_work.delete('0', 'end')
            PopUpWindow(self, 'Work não encontrada', f'Work "{work}" não foi encontrada.\n'
                                                     f'Por favor selecionar o arquivo manualmente\n'
                                                     f'Ou Contactar PreProd\n'
                                                     f'Caminho: {get_search_folder()}')
            return
        if result.status == 'empty_file':
            PopUpWindow(self, 'Erro', 'Arquivo encontrado está vazio - Verificar')
            self.entry_work.delete('0', 'end')
            return
        if result.status == 'product_missing':
            PopUpWindow(self, 'Erro', result.error.message)
            return
        if result.status == 'inconsistent':
            self.entry_work.delete('0', 'end')
            PopUpWindow(self, result.error.title, result.error.message)
            return

        self.defined_paper_size = result.defined_paper_size
        self.defined_color = result.defined_color
        if result.show_color:
            self.show_color(result.defined_color)

        self.entry_work.delete('0', 'end')
        self.work_queue.add(result.work, result.full_path)
        self.btn_start.configure(state='normal')

        if result.open_remake:
            RemakeWindow(self, result.full_path, result.work, self.defined_color, self.printers_list.get())
            self.withdraw()

    def open_or_print_pdf(self, pdf_data, file_to_move=[], is_remake=None, printer=None, progress_slot=None):
        slot = progress_slot if progress_slot is not None else printer
        try:
            self.loading_frame.update_progressbar(slot, 1, 'Imprimindo...')

            exe_index = None
            if printer != 'Criar PDF':
                exe_index = self.loading_frame.get_exe_index(slot)

            finish_print_job(pdf_data, file_to_move, is_remake, printer, exe_index)
            self.loading_frame.remove_progressbar(slot)
        except Exception:
            self.loading_frame.show_error(slot, traceback.format_exc())

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
        ensure_output_directories(get_search_folder())

    def refresh(self, *args):
        self.btn_start.configure(state='disabled')
        self.btn_config.configure(state='normal')
        self.printers_list.configure(state='normal')

        # update the printers list, when it's included in the Printer List in configs
        self.printers_list.configure(values=self._printer_combo_values())

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
        self._pdf_slot_counter = 0

    def add_progressbar(self, printer_name):
        if printer_name == 'Criar PDF':
            self._pdf_slot_counter += 1
            slot_id = f'Criar PDF #{self._pdf_slot_counter}'
            display_name = 'Criar PDF'
            exe_index = None
        else:
            if printer_name in self.printers_status:
                raise Exception('Impressora já está em uso')
            slot_id = printer_name
            display_name = printer_name
            exe_index = self.__get_exe_to_use()

        frame = ctk.CTkFrame(self, fg_color='transparent')
        frame.pack()

        ctk.CTkLabel(frame, text=45 * '-', bg_color='transparent').grid(row=0)

        lbl_printer = ctk.CTkLabel(frame, text=f'Impressora\n{display_name}', font=('Arial', 10),
                                   bg_color='transparent')
        lbl_printer.grid(row=1)

        loadingbar = ctk.CTkProgressBar(frame, orientation="horizontal", height=30, width=150, corner_radius=0)
        loadingbar.grid(row=2, column=0)

        progress_lbl = ctk.CTkLabel(frame, text='1/2', font=('Arial', 13), bg_color='#1F538D')
        progress_lbl.grid(row=2, column=0)

        self.printers_status[slot_id] = {
            'ProgressBar': loadingbar,
            'Label': progress_lbl,
            'Frame': frame,
            'Exe_to_use': exe_index,
        }
        return slot_id

    def get_exe_index(self, slot_id):
        return self.printers_status[slot_id]['Exe_to_use']

    def __get_exe_to_use(self):
        exe = []
        for slot in self.printers_status:
            idx = self.printers_status[slot]['Exe_to_use']
            if idx is not None:
                exe.append(idx)

        for i in range(5):
            if i not in exe:
                return i

        raise Exception('Máximo de 5 processos de impressão por vez.\nAguardar')

    def update_progressbar(self, slot_id, loadingbar_progress, lbl_text):
        progress_bar = self.printers_status[slot_id]['ProgressBar']
        progress_lbl = self.printers_status[slot_id]['Label']

        progress_bar.set(loadingbar_progress)
        progress_lbl.configure(text=lbl_text)

    def remove_progressbar(self, slot_id):
        frame = self.printers_status[slot_id]['Frame']
        frame.destroy()

        self.printers_status.pop(slot_id)

    def show_error(self, slot_id, error_tracebak):
        frame = self.printers_status[slot_id]['Frame']

        ctk.CTkLabel(frame, font=('Arial', 10), text='ERRO AO CRIAR').grid(row=0)

        path = 'Errors_Logs.txt'
        FileUtils.write_log_file(path, error_tracebak)

        ctk.CTkButton(frame, text='Visualizar', fg_color=BTN_RED, hover_color=BTN_HOVER_RED,
                      command=lambda: self.visualize_error(slot_id, path)).grid(row=1)

    def visualize_error(self, slot_id, path):
        self.remove_progressbar(slot_id)

        open_path(path)
