import os
import tkinter
from tkinter import ttk

import customtkinter as ctk

from app.ui.constants import FONT

WORK_QUEUE_WIDTH = 370
_LIST_BG = '#2b2b2b'
_LIST_FG = '#DCE4EE'
_LIST_SELECT_BG = '#1F538D'
_LIST_BORDER = '#565b5e'
_LIST_FONT_SIZE = 10
_SCROLLBAR_STYLE = 'WorkQueue.Vertical.TScrollbar'


class WorkQueueList(ctk.CTkFrame):
    """Lista de WOs na fila de produção — altura fixa, seleção múltipla, path como identificador."""

    def __init__(self, master, width=WORK_QUEUE_WIDTH, height=122, visible_rows=6, **kwargs):
        super().__init__(
            master,
            width=width,
            height=height,
            corner_radius=0,
            border_width=2,
            fg_color=_LIST_BG,
            **kwargs,
        )
        self.grid_propagate(False)
        self.pack_propagate(False)

        self._entries: list[tuple[str, str]] = []

        inner = tkinter.Frame(self, bg=_LIST_BG)
        inner.pack(fill='both', expand=True)

        self._configure_scrollbar_style()

        scrollbar = ttk.Scrollbar(inner, orient='vertical', style=_SCROLLBAR_STYLE)
        scrollbar.pack(side='right', fill='y')

        self.listbox = tkinter.Listbox(
            inner,
            width=48,
            height=visible_rows,
            activestyle='none',
            selectmode=tkinter.EXTENDED,
            exportselection=False,
            yscrollcommand=scrollbar.set,
            bg=_LIST_BG,
            fg=_LIST_FG,
            selectbackground=_LIST_SELECT_BG,
            selectforeground='white',
            highlightthickness=0,
            borderwidth=0,
            font=(FONT, _LIST_FONT_SIZE),
        )
        self.listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.listbox.yview)

    def _configure_scrollbar_style(self):
        style = ttk.Style(self)
        style.configure(
            _SCROLLBAR_STYLE,
            background=_LIST_BORDER,
            troughcolor=_LIST_BG,
            bordercolor=_LIST_BG,
            darkcolor=_LIST_BG,
            lightcolor=_LIST_BG,
            arrowcolor=_LIST_FG,
            relief='flat',
            gripcount=0,
        )
        style.map(
            _SCROLLBAR_STYLE,
            background=[('active', _LIST_SELECT_BG), ('!active', _LIST_BORDER)],
            arrowcolor=[('active', 'white'), ('!active', _LIST_FG)],
        )

    def _display_line(self, work: str, path: str) -> str:
        return f'{work}  ·  {os.path.basename(path)}'

    def _refresh(self):
        self.listbox.delete(0, tkinter.END)
        for work, path in self._entries:
            self.listbox.insert(tkinter.END, self._display_line(work, path))

    def add(self, work: str, path: str) -> bool:
        if any(existing_path == path for _, existing_path in self._entries):
            return False
        self._entries.append((work, path))
        self.listbox.insert(tkinter.END, self._display_line(work, path))
        return True

    def remove_selected(self):
        indices = list(self.listbox.curselection())
        if not indices:
            return
        for index in reversed(indices):
            del self._entries[index]
        self._refresh()

    def clear_all(self):
        self._entries.clear()
        self.listbox.delete(0, tkinter.END)

    def get_paths(self) -> list[str]:
        return [path for _, path in self._entries]

    def has_selection(self) -> bool:
        return bool(self.listbox.curselection())
