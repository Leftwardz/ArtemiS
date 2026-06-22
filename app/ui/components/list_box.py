import tkinter

import customtkinter as ctk

from app.ui.constants import FONT


class ListBox(ctk.CTkScrollableFrame):
    def __init__(self, master, items, child=False, on_select=None, **kwargs):
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
                font=(FONT, 14),
                width=50,
            )
            self.radio_list[item].grid(column=0, pady=2)

    def focus(self):
        for item in self.radio_list.values():
            if item != self.radio_var.get():
                item.configure(font=(FONT, 14), text_color="white")
        self.radio_list[self.radio_var.get()].configure(font=(FONT, 14, "bold"), text_color="green")

        if self.on_select is not None:
            self.on_select(self.child)
        elif hasattr(self.master, 'refresh'):
            self.master.refresh(self.child)
