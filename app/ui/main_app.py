import os
import traceback
from threading import Thread

import customtkinter as ctk

from app import audit
from app.i18n import (
    PDF_MODE_SENTINEL,
    available_languages,
    get_i18n,
    is_pdf_mode_label,
    paper_color_label,
    pdf_mode_label,
    t,
)
from app.services.print_job_coordinator import start_pdf_generation
from app.services.print_service import finish_print_job, get_printer_paper_error_message, validate_printer_paper
from app.services.production_service import (
    ensure_output_directories,
    get_drawings_and_orientations,
    get_paper_size_from_path,
    get_work_product_info,
    load_worklist_file_lines,
    is_empty_file as work_is_empty_file,
    ProductNotFoundError,
    validate_duplex_batch,
    validate_landscape_batch,
)
from app.services.print_group_service import normalize_group_flag, resolve_work_search_path
from app.utils.printing.base import ORIENTATION_PORTRAIT
from app.utils.printing.virtual_printers import is_interactive_virtual_printer
from app.ui.components import PopUpWindow, WORK_QUEUE_WIDTH, WorkQueueList
from app.ui.config_window import ConfigPanel
from app.ui.constants import (
    APP_NAME,
    BTN_HOVER_RED,
    BTN_RED,
    DEFAULT_HEIGHT,
    DEFAULT_WIDTH,
    FONT,
    ICON,
    PAPER_COLOR_LIST,
    SIDEBAR_WIDTH,
    THEME_ACCENT,
    THEME_ACCENT_HOVER,
    THEME_ACCENT_SECONDARY,
    THEME_BG,
    THEME_CARD,
    THEME_CARD_BORDER,
    THEME_NAV_ACTIVE,
    THEME_PROGRESS_BG,
    THEME_SIDEBAR,
    THEME_TEXT_SECONDARY,
)
from app.ui.custom_titlebar import attach_custom_titlebar
from app.ui.theme_assets import gradient_ctk_image
from app.ui.remake_window import RemakeWindow
from app.ui.ttk_theme import apply_azure_dark_theme
from app.utils.document_delivery import open_path
from app.utils.file_parser import FileUtils
from app.services import admin_service
from app.services.settings_service import get_print_backend, get_search_folder, save_language
from app.services.work_queue_service import search_work_for_queue
from app.utils.window_geometry import calculate_center_screen


class App(ctk.CTk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title(APP_NAME)
        self.iconbitmap(ICON)
        ctk.set_default_color_theme("dark-blue")
        ctk.set_appearance_mode("dark")
        apply_azure_dark_theme(self)
        self.option_add("*Font", ("Segoe UI", 15))
        self.configure(fg_color=THEME_BG)

        self.geometry(calculate_center_screen(DEFAULT_WIDTH, DEFAULT_HEIGHT, self))
        self.minsize(DEFAULT_WIDTH, DEFAULT_HEIGHT)

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.title_bar = attach_custom_titlebar(self, APP_NAME, row=0, columnspan=2)

        self.config_panel = None
        self._active_view = 'production'
        self.file_lines = None
        self.progressbar = None
        self.lbl_progressbar = None
        self._nav_buttons = {}
        self._card_titles = {}

        self._build_sidebar()
        self._build_content()
        self._prime_config_panel_layout()
        self.verify_directorys()

    def _prime_config_panel_layout(self):
        """Monta o painel de config com geometria real antes da primeira exibição."""
        self.production_view.grid_remove()
        self.settings_view.grid()
        self.update_idletasks()
        if self.config_panel is not None:
            self.config_panel.refresh_layout()
        self.settings_view.grid_remove()
        self.production_view.grid()

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=SIDEBAR_WIDTH, corner_radius=0, fg_color=THEME_SIDEBAR)
        self.sidebar.grid(row=1, column=0, sticky='nswe')
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(2, weight=1)

        logo_frame = ctk.CTkFrame(self.sidebar, fg_color='transparent')
        logo_frame.grid(row=0, column=0, sticky='ew', padx=12, pady=(16, 20))

        logo_img = gradient_ctk_image(36, 36, THEME_ACCENT, THEME_ACCENT_SECONDARY, radius=18)
        logo_mark = ctk.CTkLabel(
            logo_frame, image=logo_img, text='A',
            font=(FONT, 18, 'bold'), text_color='white', width=36, height=36,
            fg_color='transparent',
        )
        logo_mark.pack(side='left')
        logo_mark.image = logo_img

        ctk.CTkLabel(logo_frame, text=APP_NAME, font=(FONT, 20, 'bold'), text_color='white').pack(side='left', padx=(10, 0))

        nav_frame = ctk.CTkFrame(self.sidebar, fg_color='transparent')
        nav_frame.grid(row=1, column=0, sticky='new', padx=8)

        self._nav_buttons['production'] = self._nav_item(
            nav_frame, 'main.nav_production', active=True, command=self._nav_production,
        )

        self.loading_frame = LoadingBarFrame(
            self.sidebar,
            fg_color='transparent',
            width=SIDEBAR_WIDTH - 16,
        )
        self.loading_frame.grid(row=2, column=0, sticky='sw', padx=8, pady=8)

        footer = ctk.CTkFrame(self.sidebar, fg_color='transparent')
        footer.grid(row=3, column=0, sticky='ew', padx=12, pady=(0, 12))

        self._settings_wrapper = ctk.CTkFrame(footer, fg_color='transparent', corner_radius=8, height=34)
        self._settings_wrapper.pack(fill='x', pady=(0, 12))
        self._settings_wrapper.pack_propagate(False)

        self._btn_settings = ctk.CTkButton(
            self._settings_wrapper,
            text=t('main.nav_settings'),
            anchor='w',
            height=30,
            corner_radius=8,
            fg_color='transparent',
            hover_color=THEME_NAV_ACTIVE,
            text_color=THEME_TEXT_SECONDARY,
            font=(FONT, 12),
            command=self._nav_settings,
        )
        self._btn_settings.pack(fill='x', padx=(6, 6), pady=2)
        self._btn_settings._nav_wrapper = self._settings_wrapper
        self._btn_settings._nav_active = False
        self._btn_settings._i18n_key = 'main.nav_settings'
        self._settings_accent = None

        self.lbl_language = ctk.CTkLabel(footer, text=t('main.language'), text_color=THEME_TEXT_SECONDARY, font=(FONT, 11))
        self.lbl_language.pack(anchor='w')

        self._lang_code_by_label = {label: code for code, label in available_languages()}
        self.language_combo = ctk.CTkComboBox(
            footer,
            width=SIDEBAR_WIDTH - 40,
            height=28,
            values=[label for _, label in available_languages()],
            command=self._on_language_changed,
            fg_color=THEME_CARD,
            border_color=THEME_CARD_BORDER,
            button_color=THEME_ACCENT,
            button_hover_color=THEME_ACCENT_HOVER,
        )
        self.language_combo.pack(anchor='w', pady=(4, 8))
        self.language_combo.set(get_i18n().language_label())

        user = admin_service.get_current_windows_user()
        account = user.split('\\')[-1] if user else t('main.user_fallback')
        parts = [p[0].upper() for p in account.replace('_', '.').split('.') if p]
        initials = ''.join(parts[:2]) or t('main.user_fallback')[:1].upper()
        user_row = ctk.CTkFrame(footer, fg_color='transparent')
        user_row.pack(fill='x', pady=(4, 0))
        avatar_img = gradient_ctk_image(28, 28, THEME_ACCENT, THEME_ACCENT_SECONDARY, radius=14)
        avatar = ctk.CTkLabel(
            user_row, image=avatar_img, text=initials,
            font=(FONT, 10, 'bold'), text_color='white', width=28, height=28,
        )
        avatar.pack(side='left')
        avatar.image = avatar_img
        ctk.CTkLabel(
            user_row, text=account, font=(FONT, 10), text_color=THEME_TEXT_SECONDARY, anchor='w',
        ).pack(side='left', padx=(8, 0))

    def _nav_item(self, parent, text_key, *, active=False, command=None):
        text = t(text_key)

        wrapper = ctk.CTkFrame(
            parent,
            fg_color=THEME_NAV_ACTIVE if active else 'transparent',
            corner_radius=8,
            height=34,
        )
        wrapper.pack(fill='x', pady=1)
        wrapper.pack_propagate(False)

        btn = ctk.CTkButton(
            wrapper,
            text=text,
            anchor='w',
            height=30,
            corner_radius=8,
            fg_color='transparent',
            hover_color=THEME_NAV_ACTIVE,
            text_color='white' if active else THEME_TEXT_SECONDARY,
            font=(FONT, 12),
            command=command or (lambda: None),
        )
        btn.pack(fill='x', padx=(8 if active else 6, 6), pady=2)
        btn._nav_wrapper = wrapper
        btn._nav_active = active
        btn._nav_accent = None
        btn._i18n_key = text_key
        if active:
            btn._nav_accent = ctk.CTkFrame(
                wrapper, width=3, height=24, corner_radius=2, fg_color=THEME_ACCENT,
            )
            btn._nav_accent.place(x=0, rely=0.5, anchor='w')
        return btn

    def _nav_production(self):
        self._set_active_view('production')

    def _nav_settings(self):
        self._set_active_view('settings')

    def _set_active_view(self, view: str):
        if view == 'settings':
            if not admin_service.can_access_config():
                user = admin_service.get_current_windows_user()
                PopUpWindow(
                    self,
                    t('main.access_denied_title'),
                    t('main.access_denied_body', user=user),
                )
                return
            self.production_view.grid_remove()
            self.settings_view.grid()
            self.update_idletasks()
            if self.config_panel is not None:
                self.config_panel.refresh_layout()
        else:
            self.settings_view.grid_remove()
            self.production_view.grid()
            self.refresh_production_combos()

        self._active_view = view
        self._update_nav_active(view)
        self._update_page_header(view)

    def _update_nav_active(self, view: str):
        production_active = view == 'production'
        settings_active = view == 'settings'

        prod_btn = self._nav_buttons.get('production')
        if prod_btn is not None:
            prod_btn._nav_active = production_active
            wrapper = prod_btn._nav_wrapper
            wrapper.configure(fg_color=THEME_NAV_ACTIVE if production_active else 'transparent')
            prod_btn.configure(text_color='white' if production_active else THEME_TEXT_SECONDARY)
            prod_btn.pack_configure(padx=(8 if production_active else 6, 6))
            if prod_btn._nav_accent is not None:
                prod_btn._nav_accent.destroy()
                prod_btn._nav_accent = None
            if production_active:
                prod_btn._nav_accent = ctk.CTkFrame(
                    wrapper, width=3, height=24, corner_radius=2, fg_color=THEME_ACCENT,
                )
                prod_btn._nav_accent.place(x=0, rely=0.5, anchor='w')

        self._btn_settings._nav_active = settings_active
        self._settings_wrapper.configure(
            fg_color=THEME_NAV_ACTIVE if settings_active else 'transparent',
        )
        self._btn_settings.configure(
            text_color='white' if settings_active else THEME_TEXT_SECONDARY,
        )
        if self._settings_accent is not None:
            self._settings_accent.destroy()
            self._settings_accent = None
        if settings_active:
            self._settings_accent = ctk.CTkFrame(
                self._settings_wrapper, width=3, height=24, corner_radius=2, fg_color=THEME_ACCENT,
            )
            self._settings_accent.place(x=0, rely=0.5, anchor='w')
            self._btn_settings.pack_configure(padx=(8, 6))
        else:
            self._btn_settings.pack_configure(padx=(6, 6))

    def _update_page_header(self, view: str):
        if view == 'settings':
            self.lbl_page_title.configure(text=t('config.title'))
            user = admin_service.get_current_windows_user()
            admin_hint = t('config.admin_suffix') if admin_service.is_windows_admin() else ''
            self.lbl_page_subtitle.configure(
                text=t('config.current_user', user=user, admin=admin_hint),
            )
        else:
            self.lbl_page_title.configure(text=t('main.production_title'))
            self.lbl_page_subtitle.configure(text=t('main.production_subtitle'))

    def _card(self, parent, title_key):
        title = t(title_key)
        outer = ctk.CTkFrame(
            parent, fg_color=THEME_CARD, corner_radius=12,
            border_width=1, border_color=THEME_CARD_BORDER,
        )
        header = ctk.CTkFrame(outer, fg_color='transparent')
        header.pack(fill='x', padx=16, pady=(12, 6))
        title_lbl = ctk.CTkLabel(
            header, text=title, font=(FONT, 13, 'bold'),
            text_color='white', anchor='w',
        )
        title_lbl.pack(anchor='w')
        self._card_titles[title_key] = title_lbl
        body = ctk.CTkFrame(outer, fg_color='transparent')
        body.pack(fill='both', expand=True, padx=16, pady=(0, 14))
        return outer, body

    def _build_content(self):
        self.content = ctk.CTkFrame(self, fg_color=THEME_BG, corner_radius=0)
        self.content.grid(row=1, column=1, sticky='nswe', padx=(0, 0), pady=0)
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self.content, fg_color='transparent')
        header.grid(row=0, column=0, sticky='ew', padx=24, pady=(20, 12))

        self.lbl_page_title = ctk.CTkLabel(
            header, text=t('main.production_title'), font=(FONT, 26, 'bold'), text_color='white', anchor='w',
        )
        self.lbl_page_title.pack(anchor='w')
        self.lbl_page_subtitle = ctk.CTkLabel(
            header, text=t('main.production_subtitle'), font=(FONT, 12),
            text_color=THEME_TEXT_SECONDARY, anchor='w',
        )
        self.lbl_page_subtitle.pack(anchor='w', pady=(2, 0))

        self.production_view = ctk.CTkFrame(self.content, fg_color=THEME_BG)
        self.production_view.grid(row=1, column=0, sticky='nsew')
        self.production_view.grid_columnconfigure(0, weight=3)
        self.production_view.grid_columnconfigure(1, weight=2)
        self.production_view.grid_rowconfigure(0, weight=1)

        self.settings_view = ctk.CTkFrame(self.content, fg_color=THEME_BG)
        self.settings_view.grid(row=1, column=0, sticky='nsew')
        self.settings_view.grid_rowconfigure(0, weight=1)
        self.settings_view.grid_columnconfigure(0, weight=1)
        self.settings_view.grid_remove()

        self.update_idletasks()
        self.config_panel = ConfigPanel(self.settings_view, app=self)
        self.config_panel.grid(row=0, column=0, sticky='nsew')

        left_col = ctk.CTkFrame(self.production_view, fg_color='transparent')
        left_col.grid(row=0, column=0, sticky='nsew', padx=(24, 8), pady=(0, 20))
        left_col.grid_columnconfigure(0, weight=1)

        card_print, body_print = self._card(left_col, 'main.card_printing')
        card_print.pack(fill='x', pady=(0, 12))

        self.lbl_select_printer = ctk.CTkLabel(body_print, text=t('main.select_printer'), anchor='w', text_color=THEME_TEXT_SECONDARY)
        self.lbl_select_printer.pack(fill='x')
        self.printers_list = ctk.CTkComboBox(
            body_print, values=self._printer_combo_values(), width=WORK_QUEUE_WIDTH,
            fg_color=THEME_BG, border_color=THEME_CARD_BORDER,
            button_color=THEME_ACCENT, button_hover_color=THEME_ACCENT_HOVER,
        )
        self.printers_list.pack(fill='x', pady=(4, 10))

        self.lbl_select_group = ctk.CTkLabel(body_print, text=t('main.select_group'), anchor='w', text_color=THEME_TEXT_SECONDARY)
        self.lbl_select_group.pack(fill='x')
        groups = admin_service.list_print_groups()
        self.print_group_list = ctk.CTkComboBox(
            body_print, values=groups, width=WORK_QUEUE_WIDTH,
            fg_color=THEME_BG, border_color=THEME_CARD_BORDER,
            button_color=THEME_ACCENT, button_hover_color=THEME_ACCENT_HOVER,
            command=self._on_print_group_changed,
        )
        self.print_group_list.pack(fill='x', pady=(4, 0))
        self.lbl_select_group_hint = ctk.CTkLabel(
            body_print, text='', anchor='w',
            font=(FONT, 10), text_color=THEME_TEXT_SECONDARY, justify='left', wraplength=420,
        )
        self.lbl_select_group_hint.pack(fill='x', pady=(4, 0))
        if groups:
            self.print_group_list.set(groups[0])

        card_queue, body_queue = self._card(left_col, 'main.card_queue')
        card_queue.pack(fill='both', expand=True)

        self.lbl_scan_work = ctk.CTkLabel(body_queue, text=t('main.scan_workorders'), anchor='w', text_color=THEME_TEXT_SECONDARY)
        self.lbl_scan_work.pack(fill='x')

        self.entry_work = ctk.CTkEntry(
            body_queue,
            border_width=2,
            corner_radius=8,
            border_color=THEME_CARD_BORDER,
            fg_color=THEME_BG,
            width=WORK_QUEUE_WIDTH,
        )
        self.entry_work.pack(fill='x', pady=(4, 8))
        self.entry_work.bind('<Return>', self.search_work)
        self.entry_work.bind('<FocusIn>', lambda _e: self.entry_work.configure(border_color=THEME_ACCENT))
        self.entry_work.bind('<FocusOut>', lambda _e: self.entry_work.configure(border_color=THEME_CARD_BORDER))

        self.remake_frame = ctk.CTkFrame(body_queue, fg_color='transparent')
        self.remake_frame.pack(side='bottom', fill='x', pady=(12, 0))
        self.checkbox_remake = ctk.CTkCheckBox(
            self.remake_frame, text=t('main.enable_remake'), command=self.remake_checkbox_event,
            fg_color=THEME_ACCENT, hover_color=THEME_ACCENT_HOVER,
        )
        self.checkbox_remake.pack(side='left')
        self.checkbox_remake_refazer = None

        worklist_actions = ctk.CTkFrame(body_queue, fg_color='transparent')
        worklist_actions.pack(side='bottom', fill='x')

        self.btn_remove_work = ctk.CTkButton(
            worklist_actions, text=t('main.remove'), width=80, height=28, corner_radius=8,
            fg_color=THEME_CARD, hover_color=THEME_CARD_BORDER, border_width=1, border_color=THEME_CARD_BORDER,
            command=self.remove_selected_works,
        )
        self.btn_remove_work.pack(side='left', padx=(0, 8))
        self.btn_clear_works = ctk.CTkButton(
            worklist_actions, text=t('main.clear'), width=80, height=28, corner_radius=8,
            fg_color=THEME_CARD, hover_color=THEME_CARD_BORDER, border_width=1, border_color=THEME_CARD_BORDER,
            command=self.clean_worklist,
        )
        self.btn_clear_works.pack(side='left')

        self.work_queue = WorkQueueList(body_queue, width=WORK_QUEUE_WIDTH, height=122, visible_rows=6)
        self.work_queue.pack(fill='both', expand=True, pady=(0, 8))

        right_col = ctk.CTkFrame(self.production_view, fg_color='transparent')
        right_col.grid(row=0, column=1, sticky='nsew', padx=(8, 24), pady=(0, 20))
        right_col.grid_rowconfigure(1, weight=1)

        card_status, body_status = self._card(right_col, 'main.card_status')
        card_status.pack(fill='x')

        self.status_content = ctk.CTkFrame(body_status, fg_color='transparent', height=106)
        self.status_content.pack(fill='x')
        self.status_content.pack_propagate(False)

        self.lbl_status_empty = ctk.CTkLabel(
            self.status_content,
            text=t('main.status_empty'),
            font=(FONT, 11),
            text_color=THEME_TEXT_SECONDARY,
            wraplength=240,
            justify='left',
            anchor='nw',
        )
        self.lbl_status_empty.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.frame_papercolor = ctk.CTkFrame(
            self.status_content, fg_color=THEME_BG, corner_radius=10,
            border_width=1, border_color=THEME_CARD_BORDER,
        )
        inner_color = ctk.CTkFrame(self.frame_papercolor, fg_color='transparent')
        inner_color.pack(fill='both', expand=True, padx=12, pady=8)

        self.lbl_paper_color = ctk.CTkLabel(
            inner_color, text=t('main.paper_color'),
            font=(FONT, 11), text_color=THEME_TEXT_SECONDARY, anchor='w',
        )
        self.lbl_paper_color.pack(anchor='w')

        color_row = ctk.CTkFrame(inner_color, fg_color='transparent')
        color_row.pack(anchor='w', pady=(4, 0))
        self.paper_color = ctk.CTkFrame(color_row, height=36, width=36, fg_color='#3CB371', corner_radius=8)
        self.paper_color.pack(side='left')
        self.paper_color.pack_propagate(False)

        name_col = ctk.CTkFrame(color_row, fg_color='transparent')
        name_col.pack(side='left', padx=(10, 0))
        self.lbl_paper_color_name = ctk.CTkLabel(
            name_col, text=t('main.no_value'), font=(FONT, 14, 'bold'), text_color='white', anchor='w',
        )
        self.lbl_paper_color_name.pack(anchor='w')
        self.lbl_paper_color_hint = ctk.CTkLabel(
            name_col, text=t('main.paper_color_hint'),
            font=(FONT, 10), text_color=THEME_TEXT_SECONDARY, anchor='w', wraplength=190,
        )
        self.lbl_paper_color_hint.pack(anchor='w', pady=(2, 0))

        self.defined_color = None
        self.defined_paper_size = None

        self.printing_label = None

        self.btn_start = ctk.CTkButton(
            right_col,
            text=t('main.start'),
            font=(FONT, 16, 'bold'),
            state='disabled',
            height=48,
            corner_radius=10,
            fg_color=THEME_ACCENT,
            hover_color=THEME_ACCENT_HOVER,
            command=self._on_start_click,
        )
        self.btn_start.pack(fill='x', pady=(12, 0), side='bottom')

        self._sync_print_group_combo()

    def remake_checkbox_event(self, event=None):
        self._update_group_search_path_hint()
        if self.checkbox_remake.get():
            self.checkbox_remake_refazer = ctk.CTkCheckBox(
                self.remake_frame, text=t('main.skip_remake_screen'), command=self.clean_worklist,
                fg_color=THEME_ACCENT, hover_color=THEME_ACCENT_HOVER,
            )
            self.checkbox_remake_refazer.pack(side='left', padx=8)
        else:
            self.checkbox_remake_refazer.destroy()
            self.checkbox_remake_refazer = None

        self.clean_worklist()

    def _group_search_path(self) -> str:
        combo = getattr(self, 'print_group_list', None)
        group_name = combo.get() if combo is not None else ''
        group_flag = normalize_group_flag(group_name)
        checkbox = getattr(self, 'checkbox_remake', None)
        is_remake = bool(checkbox.get()) if checkbox is not None else False
        return resolve_work_search_path(get_search_folder(), group_flag, is_remake)

    def _update_group_search_path_hint(self):
        hint = getattr(self, 'lbl_select_group_hint', None)
        if hint is None:
            return
        hint.configure(text=self._group_search_path())

    def _on_print_group_changed(self, _choice=None):
        self._update_group_search_path_hint()

    def create_printing_label(self):
        self.printing_label = ctk.CTkLabel(
            self.content,
            text=t('main.printing_wait'),
            font=('Arial', 30, 'bold'),
            fg_color=THEME_BG,
            bg_color=THEME_BG,
        )
        self.printing_label.place(relx=0.5, rely=0.5, anchor='center')

    def remove_printing_label(self):
        if self.printing_label:
            self.printing_label.destroy()
            self.printing_label = None

    def show_color(self, color):
        self.lbl_status_empty.place_forget()
        self.frame_papercolor.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.defined_color = color
        label = paper_color_label(color)
        self.lbl_paper_color.configure(text=t('main.paper_color'))
        self.lbl_paper_color_name.configure(text=label)
        self.lbl_paper_color_hint.configure(text=t('main.paper_color_hint'))
        self.paper_color.configure(fg_color=PAPER_COLOR_LIST[color])

    def _show_status_empty(self):
        self.frame_papercolor.place_forget()
        self.lbl_status_empty.place(relx=0, rely=0, relwidth=1, relheight=1)

    def remake_widget_update(self):
        if self.remake_var.get() == 1:
            self.txtbox_ar.focus()
            self.entry_range.delete(0, "end")
        else:
            self.txtbox_ar.delete('0.0', 'end')

    def open_toplevel(self):
        self._nav_settings()

    @staticmethod
    def _printer_combo_values():
        labels, _name_map = admin_service.get_printer_combo_options()
        return [pdf_mode_label()] + labels

    def _selected_printer_name(self):
        selected = self.printers_list.get()
        if is_pdf_mode_label(selected):
            return PDF_MODE_SENTINEL
        return admin_service.resolve_printer_name(selected)

    def _on_language_changed(self, label: str):
        code = self._lang_code_by_label.get(label)
        if not code:
            return
        result = save_language(code)
        if not result.ok and result.error:
            PopUpWindow(self, t('main.error'), result.error)
            self.language_combo.set(get_i18n().language_label())
            return
        self._lang_code_by_label = {lbl: c for c, lbl in available_languages()}
        self.apply_language()

    def apply_language(self):
        """Refresh main screen texts after a language change."""
        self._lang_code_by_label = {label: code for code, label in available_languages()}
        self.lbl_language.configure(text=t('main.language'))
        self.language_combo.configure(values=[label for _, label in available_languages()])
        self.language_combo.set(get_i18n().language_label())

        self._update_page_header(self._active_view)
        self._update_nav_active(self._active_view)
        for btn in self._nav_buttons.values():
            btn.configure(text=t(btn._i18n_key))
        self._btn_settings.configure(text=t(self._btn_settings._i18n_key))
        if self.config_panel is not None:
            self.config_panel.apply_language()
        for key, lbl in self._card_titles.items():
            lbl.configure(text=t(key))
        self.lbl_status_empty.configure(text=t('main.status_empty'))
        self.lbl_paper_color_hint.configure(text=t('main.paper_color_hint'))

        self.lbl_select_printer.configure(text=t('main.select_printer'))
        self.lbl_select_group.configure(text=t('main.select_group'))
        self.refresh_production_combos()
        self.lbl_scan_work.configure(text=t('main.scan_workorders'))
        self.checkbox_remake.configure(text=t('main.enable_remake'))
        if self.checkbox_remake_refazer is not None:
            self.checkbox_remake_refazer.configure(text=t('main.skip_remake_screen'))
        self.btn_remove_work.configure(text=t('main.remove'))
        self.btn_clear_works.configure(text=t('main.clear'))
        self.btn_start.configure(text=t('main.start'))

        if self.defined_color:
            self.lbl_paper_color.configure(text=t('main.paper_color'))
            self.lbl_paper_color_name.configure(text=paper_color_label(self.defined_color))
        else:
            self.lbl_paper_color.configure(text=t('main.paper_color'))

        if self.printing_label is not None:
            try:
                self.printing_label.configure(text=t('main.printing_wait'))
            except Exception:
                pass

    def get_work_paths(self):
        return self.work_queue.get_paths()

    def get_paper_size_from_worklist(self):
        return get_paper_size_from_path(self.get_work_paths()[0], admin_service.get_db())

    def _on_start_click(self):
        printer_name = self._selected_printer_name()
        if printer_name != PDF_MODE_SENTINEL:
            paper_size = self.get_paper_size_from_worklist()
            if not validate_printer_paper(printer_name, paper_size):
                PopUpWindow(self, t('main.error'), get_printer_paper_error_message(paper_size))
                return

        lines = self.open_files_from_worklist()
        try:
            items, orientations, layout_configs = self.get_items_and_orientation_from_worklist(lines)
        except ProductNotFoundError as exc:
            PopUpWindow(
                self, t('common.error'),
                t('work.product_missing', client=exc.client, product=exc.product),
            )
            return

        self.create_pdf(lines, items, orientations, self.checkbox_remake.get(), printer=printer_name,
                        layout_config_list=layout_configs)

    def _build_pdf_callbacks(self, progress_slot, printer):
        def on_progress(_printer_name, progress, text):
            self.after(0, lambda: self._on_pdf_progress(progress_slot, progress, text))

        def on_error(_printer_name, error_traceback):
            self.after(0, lambda: self.loading_frame.show_error(progress_slot, error_traceback))

        def on_complete(pdf_bytes, files_to_move, is_remake_flag, _printer_name,
                        requires_duplex=False, print_orientation=ORIENTATION_PORTRAIT,
                        paper_size='9', paper_dimensions_mm=None):
            self.after(0, lambda: self.open_or_print_pdf(
                pdf_bytes, files_to_move, is_remake_flag, printer, progress_slot,
                requires_duplex, print_orientation, paper_size, paper_dimensions_mm))

        return on_progress, on_error, on_complete

    def _on_pdf_progress(self, progress_slot, progress, text):
        self.loading_frame.update_progressbar(progress_slot, progress, text)
        self.update_idletasks()

    def create_pdf(self, lines, items, orientations, is_remake=False, printer=None,
                   layout_config_list=None, error_parent=None):
        popup_parent = error_parent or self
        duplex_error = validate_duplex_batch(items, get_print_backend())
        if duplex_error:
            PopUpWindow(popup_parent, t('main.error'), t(duplex_error))
            return False
        landscape_error = validate_landscape_batch(
            orientations, layout_config_list, get_print_backend(),
        )
        if landscape_error:
            PopUpWindow(popup_parent, t('main.error'), t(landscape_error))
            return False
        try:
            progress_slot = self.loading_frame.add_progressbar(printer)
        except Exception as e:
            PopUpWindow(popup_parent, t('main.error'), str(e))
            return False

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
            layout_config_list=layout_config_list,
        )

        if not is_remake:
            self.refresh()
        return True

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
            self._show_status_empty()
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
            PopUpWindow(self, t('main.error'), t('main.work_duplicate'))
            self.entry_work.delete('0', 'end')
            return
        if result.status == 'path_missing':
            err = result.error
            PopUpWindow(
                self, t(err.title_key),
                t(err.message_key, **(err.message_params or {})),
            )
            return
        if result.status == 'not_found':
            self.entry_work.delete('0', 'end')
            PopUpWindow(
                self,
                t('main.work_not_found_title'),
                t('main.work_not_found_body', work=result.work, folder=result.search_folder),
            )
            return
        if result.status == 'empty_file':
            PopUpWindow(self, t('main.error'), t('main.empty_file'))
            self.entry_work.delete('0', 'end')
            return
        if result.status == 'product_missing':
            err = result.error
            PopUpWindow(
                self, t(err.title_key),
                t(err.message_key, **(err.message_params or {})),
            )
            return
        if result.status == 'inconsistent':
            self.entry_work.delete('0', 'end')
            err = result.error
            PopUpWindow(
                self, t(err.title_key),
                t(err.message_key, **(err.message_params or {})),
            )
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

    def open_or_print_pdf(self, pdf_data, file_to_move=[], is_remake=None, printer=None, progress_slot=None,
                          requires_duplex=False, print_orientation=ORIENTATION_PORTRAIT,
                          paper_size=None, paper_dimensions_mm=None):
        slot = progress_slot if progress_slot is not None else printer
        progress_text = t('main.printing')
        if printer and printer != PDF_MODE_SENTINEL and is_interactive_virtual_printer(printer):
            progress_text = t('main.interactive_virtual_printer_progress', printer=printer)
        self.loading_frame.update_progressbar(slot, 1, progress_text)

        exe_index = None
        if printer != PDF_MODE_SENTINEL:
            exe_index = self.loading_frame.get_exe_index(slot)

        resolved_paper_size = paper_size or self.defined_paper_size or '9'
        orientation = print_orientation or ORIENTATION_PORTRAIT
        paper_width_mm = None
        paper_height_mm = None
        if paper_dimensions_mm:
            paper_width_mm, paper_height_mm = paper_dimensions_mm

        def _print_worker():
            try:
                finish_print_job(
                    pdf_data, file_to_move, is_remake, printer, exe_index,
                    paper_size=resolved_paper_size,
                    paper_width_mm=paper_width_mm,
                    paper_height_mm=paper_height_mm,
                    requires_duplex=requires_duplex,
                    orientation=orientation,
                )
            except Exception:
                tb = traceback.format_exc()
                self.after(0, lambda: self.loading_frame.show_error(slot, tb))
            else:
                self.after(0, lambda: self.loading_frame.remove_progressbar(slot))

        Thread(target=_print_worker, daemon=True).start()

    def create_progress_bar(self):
        self.progressbar = ctk.CTkProgressBar(
            self.loading_frame, orientation="horizontal", height=20,
            corner_radius=6, width=SIDEBAR_WIDTH - 40, border_width=0,
            progress_color=THEME_ACCENT, fg_color=THEME_PROGRESS_BG,
        )
        self.progressbar.pack()

        self.lbl_progressbar = ctk.CTkLabel(self.content, text='', font=('Arial', 15, 'bold'))
        self.lbl_progressbar.place(relx=0.5, rely=0.5, anchor='center')

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

    def refresh_production_combos(self):
        """Atualiza combos de impressora e grupo na produção (sem limpar a fila)."""
        current_printer = self._selected_printer_name()
        self.printers_list.configure(values=self._printer_combo_values())
        if current_printer == PDF_MODE_SENTINEL:
            self.printers_list.set(pdf_mode_label())
        elif current_printer:
            _labels, name_map = admin_service.get_printer_combo_options()
            for label, name in name_map.items():
                if name == current_printer:
                    self.printers_list.set(label)
                    break
            else:
                values = self._printer_combo_values()
                self.printers_list.set(values[0] if values else pdf_mode_label())
        else:
            values = self._printer_combo_values()
            if values:
                self.printers_list.set(values[0])
        self._sync_print_group_combo()

    def refresh(self, *args):
        self.btn_start.configure(state='disabled')
        self._btn_settings.configure(state='normal')
        self.printers_list.configure(state='normal')

        self.printers_list.configure(values=self._printer_combo_values())

        self.remove_printing_label()
        if self.progressbar:
            self.progressbar.destroy()

        if self.checkbox_remake_refazer:
            self.checkbox_remake_refazer.destroy()
            self.checkbox_remake_refazer = None

        self.checkbox_remake.deselect()
        self.clean_worklist()
        self._sync_print_group_combo()

    def _sync_print_group_combo(self):
        current = self.print_group_list.get()
        groups = admin_service.list_print_groups()
        self.print_group_list.configure(values=groups)
        if not groups:
            return
        if current in groups:
            self.print_group_list.set(current)
        else:
            self.print_group_list.set(groups[0])
        self._update_group_search_path_hint()


class LoadingBarFrame(ctk.CTkFrame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.printers_status = {}
        self._pdf_slot_counter = 0

    def add_progressbar(self, printer_name):
        if printer_name == PDF_MODE_SENTINEL:
            self._pdf_slot_counter += 1
            slot_id = f'{PDF_MODE_SENTINEL} #{self._pdf_slot_counter}'
            display_name = pdf_mode_label()
            exe_index = None
        else:
            if printer_name in self.printers_status:
                raise Exception(t('main.printer_in_use'))
            slot_id = printer_name
            display_name = printer_name
            exe_index = self.__get_exe_to_use()

        frame = ctk.CTkFrame(self, fg_color='transparent')
        frame.pack(fill='x', pady=(0, 8))

        lbl_printer = ctk.CTkLabel(
            frame, text=t('main.printer_label', name=display_name), font=(FONT, 10),
            text_color=THEME_TEXT_SECONDARY, anchor='w',
        )
        lbl_printer.pack(fill='x')

        bar_row = ctk.CTkFrame(frame, fg_color='transparent')
        bar_row.pack(fill='x', pady=(2, 0))

        loadingbar = ctk.CTkProgressBar(
            bar_row, orientation="horizontal", height=18,
            width=SIDEBAR_WIDTH - 48, corner_radius=6,
            progress_color=THEME_ACCENT, fg_color=THEME_PROGRESS_BG,
        )
        loadingbar.pack(fill='x')
        loadingbar.set(0)

        progress_lbl = ctk.CTkLabel(
            bar_row, text=t('main.progress_step'), font=(FONT, 10, 'bold'),
            text_color='white',
        )
        progress_lbl.place(relx=0.5, rely=0.5, anchor='center')

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

        raise Exception(t('main.max_print_jobs'))

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

        ctk.CTkLabel(frame, font=(FONT, 10), text=t('main.create_error'), text_color=BTN_RED).pack()

        path = 'Errors_Logs.txt'
        FileUtils.write_log_file(path, error_tracebak)
        audit.log_error(detail=error_tracebak, printer=str(slot_id))

        ctk.CTkButton(
            frame, text=t('main.view'), fg_color=BTN_RED, hover_color=BTN_HOVER_RED,
            height=24, corner_radius=6,
            command=lambda: self.visualize_error(slot_id, path),
        ).pack(pady=(4, 0))

    def visualize_error(self, slot_id, path):
        self.remove_progressbar(slot_id)

        open_path(path)
