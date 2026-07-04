import tkinter

import customtkinter as ctk

from app.ui.constants import (
    FONT,
    THEME_ACCENT,
    THEME_BG,
    THEME_CARD,
    THEME_CARD_BORDER,
    THEME_TEXT_SECONDARY,
)


class ListBox(ctk.CTkScrollableFrame):
    def __init__(self, master, items, child=False, on_select=None, **kwargs):
        if 'fg_color' not in kwargs:
            kwargs['fg_color'] = THEME_BG
        if 'border_width' not in kwargs:
            kwargs['border_width'] = 1
            kwargs['border_color'] = THEME_CARD_BORDER
        kwargs.setdefault('corner_radius', 8)
        super().__init__(master, **kwargs)
        self.radio_list = {}
        self.radio_var = tkinter.StringVar()
        self.master = master
        self.child = child
        self.on_select = on_select

        self.grid_columnconfigure(0, weight=1)

        for item in items:
            self.radio_list[item] = ctk.CTkRadioButton(
                self,
                text=item,
                variable=self.radio_var,
                value=item,
                radiobutton_width=0,
                command=self.focus,
                font=(FONT, 13),
                width=50,
                fg_color=THEME_ACCENT,
                hover_color=THEME_ACCENT,
                text_color='white',
                border_color=THEME_CARD_BORDER,
            )
            self.radio_list[item].grid(column=0, sticky='w', padx=6, pady=2)

        if items:
            self.radio_var.set(items[0])

    def focus(self):
        selected = self.radio_var.get()
        for name, item in self.radio_list.items():
            if name != selected:
                item.configure(font=(FONT, 13), text_color='white')
            else:
                item.configure(font=(FONT, 13, 'bold'), text_color='#c4b5fd')

        if self.on_select is not None:
            self.on_select(self.child)
        elif hasattr(self.master, 'refresh'):
            self.master.refresh(self.child)
