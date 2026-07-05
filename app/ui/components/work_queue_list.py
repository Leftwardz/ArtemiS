import os
import tkinter
from tkinter import ttk

import customtkinter as ctk

from app.ui.constants import (
    FONT,
    THEME_ACCENT,
    THEME_BG,
    THEME_CARD_BORDER,
    THEME_TEXT_SECONDARY,
)

WORK_QUEUE_WIDTH = 370
_LIST_FONT_SIZE = 10
_SCROLLBAR_STYLE = 'WorkQueue.Vertical.TScrollbar'


def _list_colors():
    return {
        'bg': THEME_BG,
        'fg': THEME_TEXT_SECONDARY,
        'select_bg': THEME_ACCENT,
        'border': THEME_CARD_BORDER,
    }


class WorkQueueList(ctk.CTkFrame):
    """Lista de WOs na fila de produção — altura fixa, seleção múltipla, path como identificador."""

    def __init__(self, master, width=WORK_QUEUE_WIDTH, height=100, visible_rows=5, **kwargs):
        colors = _list_colors()
        super().__init__(
            master,
            width=width,
            height=height,
            corner_radius=8,
            border_width=1,
            fg_color=colors['bg'],
            border_color=colors['border'],
            **kwargs,
        )
        self.grid_propagate(False)
        self.pack_propagate(False)
        self._colors = colors

        self._entries: list[tuple[str, str]] = []

        inner = tkinter.Frame(self, bg=colors['bg'])
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
            bg=colors['bg'],
            fg=colors['fg'],
            selectbackground=colors['select_bg'],
            selectforeground='white',
            highlightthickness=0,
            borderwidth=0,
            font=(FONT, _LIST_FONT_SIZE),
        )
        self.listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.listbox.yview)

    def _configure_scrollbar_style(self):
        colors = self._colors
        style = ttk.Style(self)
        style.configure(
            _SCROLLBAR_STYLE,
            background=colors['border'],
            troughcolor=colors['bg'],
            bordercolor=colors['bg'],
            darkcolor=colors['bg'],
            lightcolor=colors['bg'],
            arrowcolor=colors['fg'],
            relief='flat',
            gripcount=0,
        )
        style.map(
            _SCROLLBAR_STYLE,
            background=[('active', colors['select_bg']), ('!active', colors['border'])],
            arrowcolor=[('active', 'white'), ('!active', colors['fg'])],
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
