from typing import Optional

from app.services import admin_service
import customtkinter as ctk

from app.i18n import PDF_MODE_SENTINEL, pdf_mode_label, t
from app.services.production_service import build_remake_file_lines
from app.services.remake_service import prepare_remake_job
from app.ui.components import PopUpWindow, Table
from app.ui.constants import (
    BTN_HOVER_RED,
    BTN_RED,
    DEFAULT_WIDTH,
    FONT,
    PAPER_COLOR_LIST,
    THEME_ACCENT,
    THEME_ACCENT_HOVER,
    THEME_BG,
    THEME_CARD,
    THEME_CARD_BORDER,
    THEME_NAV_ACTIVE,
    THEME_TEXT_SECONDARY,
)
from app.utils.file_parser import FileUtils, get_sequence_from_str
from app.utils.window_geometry import calculate_center_screen_with_monitor, get_monitor

_REMAKE_HEIGHT = 600
_ACTIONS_WIDTH = 132


def _entry_kwargs(**extra):
    return dict(
        fg_color=THEME_BG, border_color=THEME_CARD_BORDER,
        border_width=1, corner_radius=8, height=32, **extra,
    )


def _combo_kwargs(**extra):
    return dict(
        fg_color=THEME_BG, border_color=THEME_CARD_BORDER,
        button_color=THEME_ACCENT, button_hover_color=THEME_ACCENT_HOVER,
        height=32, corner_radius=8, **extra,
    )


def _secondary_btn_kwargs(**extra):
    return dict(
        fg_color=THEME_NAV_ACTIVE, hover_color=THEME_CARD_BORDER,
        border_width=1, border_color=THEME_CARD_BORDER,
        corner_radius=8, height=32, **extra,
    )


def _remake_card(parent, title: Optional[str] = None):
    card = ctk.CTkFrame(
        parent, fg_color=THEME_CARD, corner_radius=12,
        border_width=1, border_color=THEME_CARD_BORDER,
    )
    pad_top, pad_bottom = (8, 8) if title is None else (10, 12)
    if title:
        ctk.CTkLabel(
            card, text=title, font=(FONT, 13, 'bold'), text_color='white', anchor='w',
        ).pack(fill='x', padx=12, pady=(10, 4))
        pad_top, pad_bottom = 0, 10
    body = ctk.CTkFrame(card, fg_color='transparent')
    body.pack(fill='both', expand=True, padx=12, pady=(pad_top, pad_bottom))
    return card, body


class RemakeWindow(ctk.CTkToplevel):
    def __init__(self, master, filepath, work_order, color, printer, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title(t('remake.title'))
        self.configure(fg_color=THEME_BG)

        self.master = master

        self.geometry(calculate_center_screen_with_monitor(
            master, DEFAULT_WIDTH, _REMAKE_HEIGHT, get_monitor(master),
        ))
        self.minsize(DEFAULT_WIDTH, _REMAKE_HEIGHT)
        self.maxsize(DEFAULT_WIDTH, _REMAKE_HEIGHT)
        self.resizable(False, False)
        self.printer = printer

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.file = FileUtils(filepath)
        self.filepath = filepath

        self.client = self.file.get_first_line_column(0).split('-')[0].strip()
        self.product = self.file.get_first_line_column(0).split('-')[1].strip()

        self._build_header()
        self._build_body(color)

        self.bind('<Return>', self.search)
        self.protocol("WM_DELETE_WINDOW", self.exit)

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=THEME_CARD, corner_radius=0, height=56)
        header.grid(row=0, column=0, sticky='ew')
        header.grid_propagate(False)

        left = ctk.CTkFrame(header, fg_color='transparent')
        left.pack(side='left', padx=16, pady=10)
        ctk.CTkLabel(left, text=t('remake.title'), font=(FONT, 18, 'bold'), text_color='white').pack(anchor='w')
        ctk.CTkLabel(
            left, text=t('remake.select_title'), font=(FONT, 11),
            text_color=THEME_TEXT_SECONDARY,
        ).pack(anchor='w')

    def _build_body(self, color):
        body = ctk.CTkFrame(self, fg_color='transparent')
        body.grid(row=1, column=0, sticky='nsew', padx=14, pady=(8, 10))
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(2, weight=1)

        card_ctx, ctx = _remake_card(body)
        card_ctx.grid(row=0, column=0, sticky='ew', pady=(0, 6))
        ctx.grid_columnconfigure(0, weight=1)
        ctx.grid_columnconfigure(1, weight=0)
        ctx.grid_columnconfigure(2, weight=0)

        work = self.file.get_first_line_column(3)
        text = t('remake.work_total', work=work, total=len(self.file.lines))
        ctk.CTkLabel(ctx, text=text, font=(FONT, 12, 'bold'), text_color='white', anchor='w').grid(
            row=0, column=0, sticky='w',
        )

        printer_row = ctk.CTkFrame(ctx, fg_color='transparent')
        printer_row.grid(row=0, column=1, padx=(12, 16))
        ctk.CTkLabel(printer_row, text=t('remake.printer'), text_color=THEME_TEXT_SECONDARY).grid(
            row=0, column=0, padx=(0, 6),
        )
        printers_list = self.master._printer_combo_values()
        self.printers_list = ctk.CTkComboBox(printer_row, values=printers_list, width=200, **_combo_kwargs())
        self.printers_list.grid(row=0, column=1)
        if self.printer in printers_list:
            self.printers_list.set(self.printer)
        elif self.printer != PDF_MODE_SENTINEL:
            _labels, name_map = admin_service.get_printer_combo_options()
            for label, name in name_map.items():
                if name == self.printer:
                    self.printers_list.set(label)
                    break
            else:
                self.printers_list.set(self.printer)
        else:
            self.printers_list.set(pdf_mode_label())

        color_row = ctk.CTkFrame(ctx, fg_color='transparent')
        color_row.grid(row=0, column=2)
        ctk.CTkLabel(color_row, text=t('main.paper_color'), text_color=THEME_TEXT_SECONDARY).grid(
            row=0, column=0, padx=(0, 6),
        )
        ctk.CTkFrame(
            color_row, fg_color=PAPER_COLOR_LIST[color], width=22, height=22, corner_radius=4,
        ).grid(row=0, column=1)

        card_search, search_body = _remake_card(body)
        card_search.grid(row=1, column=0, sticky='ew', pady=(0, 6))
        for col in range(4):
            search_body.grid_columnconfigure(col, weight=1)
        search_body.grid_columnconfigure(4, weight=0)

        validation = self.register(lambda i: i.isdigit() or ',' in i or '-' in i or i == '')

        ctk.CTkLabel(
            search_body, text=t('remake.range_label'), font=(FONT, 11),
            text_color=THEME_TEXT_SECONDARY,
        ).grid(row=0, column=0, padx=(0, 6), pady=(0, 2), sticky='w')
        self.range_input = ctk.CTkEntry(
            search_body, validate='key', validatecommand=(validation, '%P'), **_entry_kwargs(),
        )
        self.range_input.bind('<FocusIn>', self.clear_other_entries)
        self.range_input.grid(row=1, column=0, padx=(0, 6), sticky='ew')

        ctk.CTkLabel(
            search_body, text=t('remake.rankjob_label'), font=(FONT, 11),
            text_color=THEME_TEXT_SECONDARY,
        ).grid(row=0, column=1, padx=(0, 6), pady=(0, 2), sticky='w')
        self.rankjob_input = ctk.CTkEntry(
            search_body, validate='key', validatecommand=(validation, '%P'), **_entry_kwargs(),
        )
        self.rankjob_input.bind('<FocusIn>', self.clear_other_entries)
        self.rankjob_input.grid(row=1, column=1, padx=(0, 6), sticky='ew')

        ctk.CTkLabel(
            search_body, text=t('remake.ar_label'), font=(FONT, 11),
            text_color=THEME_TEXT_SECONDARY,
        ).grid(row=0, column=2, padx=(0, 6), pady=(0, 2), sticky='w')
        self.ar_input = ctk.CTkEntry(search_body, **_entry_kwargs())
        self.ar_input.bind('<FocusIn>', self.clear_other_entries)
        self.ar_input.grid(row=1, column=2, padx=(0, 6), sticky='ew')

        ctk.CTkLabel(
            search_body, text=t('remake.name_label'), font=(FONT, 11),
            text_color=THEME_TEXT_SECONDARY,
        ).grid(row=0, column=3, padx=(0, 6), pady=(0, 2), sticky='w')
        self.name_input = ctk.CTkEntry(search_body, **_entry_kwargs())
        self.name_input.bind('<FocusIn>', self.clear_other_entries)
        self.name_input.grid(row=1, column=3, padx=(0, 6), sticky='ew')

        self.btn_search = ctk.CTkButton(
            search_body, text=t('remake.search'), width=108, height=32, corner_radius=8,
            fg_color=THEME_ACCENT, hover_color=THEME_ACCENT_HOVER, command=self.search,
        )
        self.btn_search.grid(row=1, column=4, sticky='e')

        workspace = ctk.CTkFrame(body, fg_color='transparent')
        workspace.grid(row=2, column=0, sticky='nsew')
        workspace.grid_columnconfigure(0, weight=1)
        workspace.grid_columnconfigure(1, weight=0, minsize=_ACTIONS_WIDTH)
        workspace.grid_rowconfigure(0, weight=1)

        card_table, table_body = _remake_card(workspace)
        card_table.grid(row=0, column=0, sticky='nsew', padx=(0, 8))
        table_body.grid_rowconfigure(0, weight=1)
        table_body.grid_columnconfigure(0, weight=1)

        table_host = ctk.CTkFrame(
            table_body, fg_color=THEME_BG, corner_radius=8,
            border_width=1, border_color=THEME_CARD_BORDER,
        )
        table_host.grid(row=0, column=0, sticky='nsew')
        table_host.grid_rowconfigure(0, weight=1)
        table_host.grid_columnconfigure(0, weight=1)

        columns = [t('remake.col_id'), t('remake.col_rankjob'), t('remake.col_ar'), t('remake.col_name')]
        self.table = Table(table_host, columns, show='headings')
        self.table.grid(row=0, column=0, sticky='nsew', padx=4, pady=4)

        card_actions, actions = _remake_card(workspace)
        card_actions.grid(row=0, column=1, sticky='ns')
        actions.grid_rowconfigure(4, weight=1)

        self.btn_remove = ctk.CTkButton(
            actions, text=t('remake.remove'), width=_ACTIONS_WIDTH - 28,
            command=self.btn_remove, **_secondary_btn_kwargs(),
        )
        self.btn_remove.grid(row=0, column=0, pady=(0, 6), sticky='ew')

        self.btn_clean_all = ctk.CTkButton(
            actions, text=t('remake.clear_all'), width=_ACTIONS_WIDTH - 28,
            command=self.btn_remove_all, **_secondary_btn_kwargs(),
        )
        self.btn_clean_all.grid(row=1, column=0, pady=(0, 6), sticky='ew')

        self.btn_start = ctk.CTkButton(
            actions, text=t('remake.start'), width=_ACTIONS_WIDTH - 28,
            fg_color=THEME_ACCENT, hover_color=THEME_ACCENT_HOVER, corner_radius=8, height=36,
            font=(FONT, 13, 'bold'), command=self.btn_start,
        )
        self.btn_start.grid(row=2, column=0, pady=(0, 8), sticky='ew')

        self.qtd_label = ctk.CTkLabel(
            actions, text=t('remake.quantity', count=0),
            font=(FONT, 11), text_color=THEME_TEXT_SECONDARY,
        )
        self.qtd_label.grid(row=3, column=0, sticky='s')

    def clear_other_entries(self, event=None):
        for entry in (self.range_input, self.rankjob_input, self.ar_input, self.name_input):
            entry.delete(0, 'end')

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
            PopUpWindow(self, t('common.not_found'), t('remake.not_found'))

        for item in items:
            row = item[1]
            infos = [
                item[0] + 1,
                self.file.get_element(row, 4, ''),
                self.file.get_element(row, 1, ''),
                self.file.get_element(row, 2, ''),
            ]
            self.table.add_item(infos)

        for entry in (self.range_input, self.rankjob_input, self.ar_input, self.name_input):
            entry.delete(0, 'end')
        self.update_quantity()

    def get_lines_to_remake(self):
        position_list = []

        items_to_remake = self.table.get_items()
        if items_to_remake:
            for item in items_to_remake:
                position_list.append(int(item[0]))

            return build_remake_file_lines(self.file, self.filepath, position_list)

    def btn_start(self):
        position_list = []
        items_to_remake = self.table.get_items()
        for item in items_to_remake:
            position_list.append(int(item[0]))

        printer_name = admin_service.resolve_printer_name(self.printers_list.get())

        result = prepare_remake_job(
            admin_service.get_db(),
            self.client,
            self.product,
            self.file,
            self.filepath,
            position_list,
            printer_name,
        )
        if not result.ok:
            PopUpWindow(self, result.error_title, result.error_message)
            return

        self.master.create_pdf(
            result.lines,
            result.items,
            result.orientations,
            is_remake=True,
            printer=printer_name,
            layout_config_list=result.layout_configs,
        )
        self.exit()

    def btn_remove(self):
        self.table.remove_selected_items()
        self.update_quantity()

    def btn_remove_all(self):
        self.table.remove_all()
        self.update_quantity()

    def update_quantity(self):
        total = len(self.table.get_children())
        self.qtd_label.configure(text=t('remake.quantity', count=total))

    def exit(self):
        self.master.focus_set()
        self.master.deiconify()
        self.master.clean_worklist()
        self.master.refresh()
        self.destroy()
