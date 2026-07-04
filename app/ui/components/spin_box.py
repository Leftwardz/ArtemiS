import customtkinter as ctk

from app.ui.constants import (
    THEME_ACCENT,
    THEME_ACCENT_HOVER,
    THEME_BG,
    THEME_CARD_BORDER,
)


class SpinBox(ctk.CTkFrame):
    def __init__(self, master, step=1, func=None, entry_width=100, entry_height=26,
                 btn_width=20, btn_height=10, *args, **kwargs):
        super().__init__(
            master, fg_color=THEME_BG, corner_radius=8,
            border_width=1, border_color=THEME_CARD_BORDER, *args, **kwargs,
        )

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.func = func
        self.step = step

        self.entry = ctk.CTkEntry(
            self, width=entry_width, height=entry_height,
            border_width=0, corner_radius=6, fg_color=THEME_BG,
        )
        self.entry.grid(row=0, column=0, rowspan=2, padx=(4, 0), pady=2, sticky='ew')

        btn_font = ('Segoe UI', 7 if entry_height >= 30 else 6)
        self.btn_up = ctk.CTkButton(
            self, text='▲', font=btn_font, width=btn_width, height=btn_height,
            corner_radius=4, fg_color=THEME_ACCENT, hover_color=THEME_ACCENT_HOVER,
            border_width=0, command=self.increase,
        )
        self.btn_up.grid(row=0, column=1, padx=(2, 4), pady=(3, 1), sticky='e')

        self.btn_down = ctk.CTkButton(
            self, text='▼', font=btn_font, width=btn_width, height=btn_height,
            corner_radius=4, fg_color=THEME_ACCENT, hover_color=THEME_ACCENT_HOVER,
            border_width=0, command=self.decrease,
        )
        self.btn_down.grid(row=1, column=1, padx=(2, 4), pady=(1, 3), sticky='e')

    def increase(self):
        try:
            if type(self.step) == float:
                value = round(float(self.entry.get()) + float(self.step), 1)
            else:
                value = int(self.entry.get()) + self.step
            self.entry.delete(0, 'end')
            self.entry.insert(0, str(value))
            if self.func:
                self.func()
        except ValueError:
            return

    def decrease(self):
        try:
            if type(self.step) == float:
                value = round(float(self.entry.get()) - float(self.step), 1)
            else:
                value = int(self.entry.get()) - self.step
            if value < 0:
                value = 0
            self.entry.delete(0, 'end')
            self.entry.insert(0, str(value))
            if self.func:
                self.func()
        except ValueError:
            return

    def set(self, value):
        self.entry.delete(0, 'end')
        self.entry.insert(0, str(value))

    def get(self):
        return self.entry.get()
