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
_POPUP_MAX_W = 560
_BODY_PAD = 16
_CARD_PAD = 14


def _entry_kwargs(**extra):
    return dict(
        fg_color=THEME_BG, border_color=THEME_CARD_BORDER,
        border_width=1, corner_radius=8, height=32, **extra,
    )


def _popup_wraplength(window_width: int) -> int:
    return max(160, window_width - (_BODY_PAD + _CARD_PAD) * 2 - 8)


def _fit_popup_geometry(window: ctk.CTkToplevel, master, min_w: int, min_h: int = 0):
    window.update_idletasks()
    width = max(min_w, window.winfo_reqwidth())
    height = max(min_h, window.winfo_reqheight())
    window.geometry(calculate_center_screen_with_monitor(master, width, height, get_monitor(master)))
    window.minsize(width, height)
    window.resizable(False, False)


class PopUpWindow(ctk.CTkToplevel):
    def __init__(self, master, title, text, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iconbitmap(ICON)
        self.master = master
        self.title(title)
        self.configure(fg_color=THEME_BG)

        header = ctk.CTkFrame(self, fg_color=THEME_CARD, corner_radius=0, height=48)
        header.pack(fill='x')
        header.pack_propagate(False)
        ctk.CTkLabel(
            header, text=title, font=(FONT, 15, 'bold'), text_color='white', anchor='w',
        ).pack(side='left', padx=16, pady=10)

        body = ctk.CTkFrame(self, fg_color='transparent')
        body.pack(fill='both', expand=True, padx=_BODY_PAD, pady=(12, 12))

        card = ctk.CTkFrame(
            body, fg_color=THEME_CARD, corner_radius=12,
            border_width=1, border_color=THEME_CARD_BORDER,
        )
        card.pack(fill='x')

        self.lbl_text = ctk.CTkLabel(
            card, text=text, font=(FONT, 12), text_color='white',
            wraplength=_popup_wraplength(_POPUP_MAX_W),
            justify='left', anchor='nw',
        )
        self.lbl_text.pack(fill='x', padx=_CARD_PAD, pady=_CARD_PAD)

        self.btn_close = ctk.CTkButton(
            body, text=t('popup.close'), width=120,
            fg_color=THEME_ACCENT, hover_color=THEME_ACCENT_HOVER,
            corner_radius=8, height=32, command=self.destroy,
        )
        self.btn_close.pack(pady=(10, 0))

        self.update_idletasks()
        natural_w = min(
            _POPUP_MAX_W,
            max(_POPUP_MIN_W, self.lbl_text.winfo_reqwidth() + (_BODY_PAD + _CARD_PAD) * 2 + 8),
        )
        self.lbl_text.configure(wraplength=_popup_wraplength(natural_w))
        _fit_popup_geometry(self, master, natural_w)

        self.grab_set()


class ConfirmWindow(ctk.CTkToplevel):
    def __init__(self, master, title, text, func, has_confirm=True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iconbitmap(ICON)
        self.func = func
        self.has_confirm = has_confirm

        self.title(title)
        self.master = master
        self.configure(fg_color=THEME_BG)
        self.grab_set()

        header = ctk.CTkFrame(self, fg_color=THEME_CARD, corner_radius=0, height=48)
        header.pack(fill='x')
        header.pack_propagate(False)
        ctk.CTkLabel(
            header, text=title, font=(FONT, 15, 'bold'), text_color='white', anchor='w',
        ).pack(side='left', padx=16, pady=10)

        body = ctk.CTkFrame(self, fg_color='transparent')
        body.pack(fill='both', expand=True, padx=_BODY_PAD, pady=(12, 12))

        card = ctk.CTkFrame(
            body, fg_color=THEME_CARD, corner_radius=12,
            border_width=1, border_color=THEME_CARD_BORDER,
        )
        card.pack(fill='x')

        self.lbl_text = ctk.CTkLabel(
            card, text=text, font=(FONT, 12), text_color='white',
            wraplength=_popup_wraplength(480),
            justify='left', anchor='nw',
        )
        self.lbl_text.pack(fill='x', padx=_CARD_PAD, pady=(12, 8))

        if has_confirm:
            ctk.CTkLabel(
                card, text=t('popup.confirm_prompt'), font=(FONT, 11),
                text_color=THEME_TEXT_SECONDARY, anchor='w', justify='left',
            ).pack(fill='x', padx=_CARD_PAD, pady=(0, 4))
            self.entry_confirm = ctk.CTkEntry(card, **_entry_kwargs())
            self.entry_confirm.pack(fill='x', padx=_CARD_PAD, pady=(0, 12))

        actions = ctk.CTkFrame(body, fg_color='transparent')
        actions.pack(fill='x', pady=(10, 0))

        self.btn_ok = ctk.CTkButton(
            actions, text=t('popup.ok'), width=120,
            fg_color=THEME_ACCENT, hover_color=THEME_ACCENT_HOVER,
            corner_radius=8, height=32, command=self.confirm_destroy,
        )
        self.btn_ok.pack(side='left', expand=True, padx=(0, 6))

        self.btn_cancelar = ctk.CTkButton(
            actions, width=120, text=t('popup.cancel'),
            fg_color=BTN_RED, hover_color=BTN_HOVER_RED,
            corner_radius=8, height=32, command=self.destroy,
        )
        self.btn_cancelar.pack(side='right', expand=True, padx=(6, 0))

        self.update_idletasks()
        natural_w = min(560, max(400, self.lbl_text.winfo_reqwidth() + (_BODY_PAD + _CARD_PAD) * 2 + 8))
        self.lbl_text.configure(wraplength=_popup_wraplength(natural_w))
        _fit_popup_geometry(self, master, natural_w, min_h=170 if has_confirm else 150)

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
