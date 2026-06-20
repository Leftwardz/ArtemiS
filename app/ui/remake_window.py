import sys

import customtkinter as ctk

from app.services.print_service import get_printer_paper_error_message, validate_printer_paper
from app.services.production_service import build_remake_file_lines
from app.ui.components import PopUpWindow, Table
from app.ui.constants import DEFAULT_WIDTH, FONT, PAPER_COLOR_LIST
from app.utils.file_parser import FileUtils, get_sequence_from_str
from app.utils.window_geometry import calculate_center_screen_with_monitor, get_monitor


class RemakeWindow(ctk.CTkToplevel):
    def __init__(self, master, filepath, work_order, color, printer, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title('Remake')

        self.master = master
        self.db = sys.modules['__main__'].db

        self.geometry(calculate_center_screen_with_monitor(master, DEFAULT_WIDTH, 550, get_monitor(master)))
        self.minsize(DEFAULT_WIDTH, 550)
        self.maxsize(DEFAULT_WIDTH, 550)
        self.resizable(False, False)
        self.printer = printer

        self.grid_columnconfigure(0, weight=10)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(4, weight=1)

        self.file = FileUtils(filepath)
        self.filepath = filepath

        self.client = self.file.get_first_line_column(0).split('-')[0].strip()
        self.product = self.file.get_first_line_column(0).split('-')[1].strip()

        self.lbl_title = ctk.CTkLabel(self, text="Selecionar Remake", font=(FONT, 25, "bold"))
        self.lbl_title.grid(row=0, column=0, columnspan=2, pady=5, sticky='ew')

        self.frame_info = ctk.CTkFrame(self)
        self.frame_info.grid(row=1, column=0, columnspan=2, sticky='ew')

        self.frame_info.grid_columnconfigure(0, weight=4)
        self.frame_info.grid_columnconfigure(1, weight=1)
        self.frame_info.grid_columnconfigure(2, weight=1)

        work = self.file.get_first_line_column(3)
        text = f'WO:{work} - (Total: {len(self.file.lines)})'
        self.lbl_title = ctk.CTkLabel(self.frame_info, text=text, font=(FONT, 15, "bold"))
        self.lbl_title.grid(row=0, column=0)

        self.frame_printers = ctk.CTkFrame(self.frame_info, fg_color='transparent')
        self.frame_printers.grid(row=0, column=1)

        ctk.CTkLabel(self.frame_printers, text="Impressora: ").grid(row=0, column=0, padx=5)

        printers_list = ['Criar PDF']
        printers_list.extend(self.db.search_printers())
        self.printers_list = ctk.CTkComboBox(self.frame_printers, values=printers_list, width=200)
        self.printers_list.grid(row=0, column=1, padx=5)
        self.printers_list.set(self.printer)

        color_frame = ctk.CTkFrame(self.frame_info, fg_color='transparent')
        color_frame.grid(row=0, column=2)
        ctk.CTkLabel(color_frame, text='Cor do Papel:').grid(row=0, column=0)
        ctk.CTkFrame(color_frame, fg_color=PAPER_COLOR_LIST[color], width=20, height=20, corner_radius=0) \
            .grid(row=0, column=1, padx=10)

        self.inputs_frame = ctk.CTkFrame(self, fg_color='transparent', border_width=1)
        self.inputs_frame.grid(row=2, column=0, columnspan=2, padx=5, sticky='ew')

        self.inputs_frame.grid_columnconfigure(0, weight=1)
        self.inputs_frame.grid_columnconfigure(1, weight=1)
        self.inputs_frame.grid_columnconfigure(2, weight=1)
        self.inputs_frame.grid_columnconfigure(3, weight=1)

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

        self.btn_search = ctk.CTkButton(self.inputs_frame, text="Procurar", font=(FONT, 14, "bold"),
                                        width=110, command=self.search)
        self.btn_search.grid(row=2, column=0, columnspan=4, padx=20, pady=10, sticky='e')

        self.table_frame = ctk.CTkFrame(self, width=500, height=310, corner_radius=0)
        self.table_frame.grid(row=3, rowspan=5, column=0, padx=10, pady=5, sticky="nwse")

        columns = ['ID', 'RankJob', 'Nª AR', 'Nome']
        self.table = Table(self.table_frame, columns, show="headings")
        self.table.pack(expand=True, fill="both")

        self.btn_frame = ctk.CTkFrame(self, fg_color='transparent')
        self.btn_frame.grid(row=3, rowspan=5, column=1, pady=5, sticky="nwse")
        self.btn_frame.grid_rowconfigure(6, weight=1)

        self.btn_remove = ctk.CTkButton(self.btn_frame, text="Remover", font=(FONT, 14, "bold"),
                                        width=110, command=self.btn_remove)
        self.btn_remove.grid(row=3, column=0, pady=3, sticky='N')

        self.btn_clean_all = ctk.CTkButton(self.btn_frame, text="Limpar Tudo",
                                           font=(FONT, 14, "bold"), width=110, command=self.btn_remove_all)
        self.btn_clean_all.grid(row=4, column=0, pady=3, sticky='N')

        self.btn_start = ctk.CTkButton(self.btn_frame, text="Start", fg_color='green', hover_color='dark green',
                                       font=(FONT, 14, "bold"), width=110, command=self.btn_start)
        self.btn_start.grid(row=5, column=0, pady=3, sticky='N')

        self.qtd_label = ctk.CTkLabel(self.btn_frame, text='Quantidade: 0')
        self.qtd_label.grid(row=6, column=0, pady=3, sticky='S')

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
            row = item[1]
            infos = [
                item[0] + 1,
                self.file.get_element(row, 4, ''),
                self.file.get_element(row, 1, ''),
                self.file.get_element(row, 2, ''),
            ]
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
        db_items = [self.db.consult_drawings_from_product(self.client, self.product)]
        product = self.db.search_product(self.client, self.product)

        if self.printers_list.get() != 'Criar PDF':
            if not validate_printer_paper(self.printers_list.get(), product.paper_size):
                PopUpWindow(
                    self, 'Erro',
                    get_printer_paper_error_message(product.paper_size, wording='cadastrado')
                )
                return

        db_orientation = [product.orientation]
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
