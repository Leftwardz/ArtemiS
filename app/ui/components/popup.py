import customtkinter as ctk

from app.i18n import t
from app.ui.constants import (
    BTN_HOVER_RED,
    BTN_RED,
    FONT,
    ICON,
    THEME_ACCENT,
    THEME_ACCENT_HOVER,
    THEME_BG,
    THEME_CARD,
    THEME_CARD_BORDER,
    THEME_NAV_ACTIVE,
    THEME_TEXT_SECONDARY,
)
from app.utils.window_geometry import calculate_center_screen_with_monitor, get_monitor

_POPUP_MIN_W = 280
_POPUP_MAX_W = 520
_POPUP_PAD_X = 24


def _entry_kwargs(**extra):
    return dict(
        fg_color=THEME_BG, border_color=THEME_CARD_BORDER,
        border_width=1, corner_radius=8, height=32, **extra,
    )


def _secondary_btn_kwargs(**extra):
    return dict(
        fg_color=THEME_NAV_ACTIVE, hover_color=THEME_CARD_BORDER,
        border_width=1, border_color=THEME_CARD_BORDER,
        corner_radius=8, height=32, **extra,
    )


class PopUpWindow(ctk.CTkToplevel):
    def __init__(self, master, title, text, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iconbitmap(ICON)
        self.master = master
        self.title(title)
        self.configure(fg_color=THEME_BG)

        measure = ctk.CTkLabel(self, text=text, font=(FONT, 12), wraplength=_POPUP_MAX_W - _POPUP_PAD_X * 2)
        measure.update_idletasks()
        text_w = measure.winfo_reqwidth()
        text_h = measure.winfo_reqheight()
        measure.destroy()

        window_width = min(_POPUP_MAX_W, max(_POPUP_MIN_W, text_w + _POPUP_PAD_X * 2 + 16))
        wraplength = window_width - _POPUP_PAD_X * 2
        window_height = max(140, text_h + 120)

        self.geometry(calculate_center_screen_with_monitor(
            master, window_width, window_height, get_monitor(master),
        ))
        self.minsize(window_width, window_height)
        self.maxsize(window_width, window_height)
        self.resizable(False, False)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color=THEME_CARD, corner_radius=0, height=48)
        header.grid(row=0, column=0, sticky='ew')
        header.grid_propagate(False)
        ctk.CTkLabel(
            header, text=title, font=(FONT, 15, 'bold'), text_color='white', anchor='w',
        ).pack(side='left', padx=16, pady=10)

        body = ctk.CTkFrame(self, fg_color='transparent')
        body.grid(row=1, column=0, sticky='nsew', padx=16, pady=12)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        card = ctk.CTkFrame(
            body, fg_color=THEME_CARD, corner_radius=12,
            border_width=1, border_color=THEME_CARD_BORDER,
        )
        card.grid(row=0, column=0, sticky='nsew')
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text=text, font=(FONT, 12), text_color='white',
            wraplength=wraplength, justify='left', anchor='w',
        ).grid(row=0, column=0, sticky='ew', padx=14, pady=14)

        self.btn_close = ctk.CTkButton(
            body, text=t('popup.close'), width=120,
            fg_color=THEME_ACCENT, hover_color=THEME_ACCENT_HOVER,
            corner_radius=8, height=32, command=self.destroy,
        )
        self.btn_close.grid(row=1, column=0, pady=(10, 0))

        self.grab_set()


class ConfirmWindow(ctk.CTkToplevel):
    def __init__(self, master, title, text, func, has_confirm=True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iconbitmap(ICON)
        height = 220 if has_confirm else 170

        self.geometry(calculate_center_screen_with_monitor(master, 480, height, get_monitor(master)))
        self.minsize(480, height)
        self.maxsize(480, height)
        self.func = func
        self.has_confirm = has_confirm

        self.resizable(False, False)
        self.title(title)
        self.master = master
        self.configure(fg_color=THEME_BG)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color=THEME_CARD, corner_radius=0, height=48)
        header.grid(row=0, column=0, sticky='ew')
        header.grid_propagate(False)
        ctk.CTkLabel(
            header, text=title, font=(FONT, 15, 'bold'), text_color='white', anchor='w',
        ).pack(side='left', padx=16, pady=10)

        body = ctk.CTkFrame(self, fg_color='transparent')
        body.grid(row=1, column=0, sticky='nsew', padx=16, pady=12)
        body.grid_columnconfigure(0, weight=1)

        card = ctk.CTkFrame(
            body, fg_color=THEME_CARD, corner_radius=12,
            border_width=1, border_color=THEME_CARD_BORDER,
        )
        card.pack(fill='both', expand=True)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text=text, font=(FONT, 12), text_color='white',
            wraplength=420, justify='left', anchor='w',
        ).grid(row=0, column=0, sticky='ew', padx=14, pady=(12, 8))

        row = 1
        if has_confirm:
            ctk.CTkLabel(
                card, text=t('popup.confirm_prompt'), font=(FONT, 11),
                text_color=THEME_TEXT_SECONDARY, anchor='w',
            ).grid(row=row, column=0, sticky='ew', padx=14, pady=(0, 4))
            row += 1
            self.entry_confirm = ctk.CTkEntry(card, **_entry_kwargs())
            self.entry_confirm.grid(row=row, column=0, sticky='ew', padx=14, pady=(0, 12))
            row += 1

        actions = ctk.CTkFrame(body, fg_color='transparent')
        actions.pack(fill='x', pady=(10, 0))
        actions.grid_columnconfigure(0, weight=1)
        actions.grid_columnconfigure(1, weight=1)

        self.btn_ok = ctk.CTkButton(
            actions, text=t('popup.ok'), width=120,
            fg_color=THEME_ACCENT, hover_color=THEME_ACCENT_HOVER,
            corner_radius=8, height=32, command=self.confirm_destroy,
        )
        self.btn_ok.grid(row=0, column=0, padx=(0, 6), sticky='e')

        self.btn_cancelar = ctk.CTkButton(
            actions, width=120, text=t('popup.cancel'),
            fg_color=BTN_RED, hover_color=BTN_HOVER_RED,
            corner_radius=8, height=32, command=self.destroy,
        )
        self.btn_cancelar.grid(row=0, column=1, padx=(6, 0), sticky='w')

    def confirm_destroy(self):
        if self.has_confirm:
            value = self.entry_confirm.get()
            keyword = t('popup.confirm_keyword')
            if value.upper() == keyword.upper():
                self.destroy()
                self.func()
            else:
                PopUpWindow(self, t('popup.error'), t('popup.confirm_mismatch', value=value))
        else:
            self.destroy()
            self.func()
