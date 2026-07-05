import tkinter
from tkinter import ttk

from app.ui.constants import THEME_TABLE_ROW_A, THEME_TABLE_ROW_B
from app.ui.ttk_theme import (
    ARTEMIS_SCROLLBAR_H_STYLE,
    ARTEMIS_SCROLLBAR_V_STYLE,
    ARTEMIS_TREEVIEW_STYLE,
    apply_artemis_ttk_theme,
)


class Table(ttk.Treeview):
    def __init__(self, master, cols_names, *args, **kwargs):
        toplevel = master.winfo_toplevel()
        apply_artemis_ttk_theme(toplevel)
        kwargs.setdefault('style', ARTEMIS_TREEVIEW_STYLE)
        super().__init__(master, *args, **kwargs)

        self.configure(columns=cols_names)
        self.tag_configure('odd', background=THEME_TABLE_ROW_A)
        self.tag_configure('even', background=THEME_TABLE_ROW_B)

        for i, col_name in enumerate(cols_names, start=1):
            self.heading(f"#{i}", text=col_name)
            self.column(f"#{i}", width=100, anchor=tkinter.CENTER)

        scroll_y = ttk.Scrollbar(
            self, orient='vertical', command=self.yview, style=ARTEMIS_SCROLLBAR_V_STYLE,
        )
        scroll_y.pack(side='right', fill='y')

        scroll_x = ttk.Scrollbar(
            self, orient='horizontal', command=self.xview, style=ARTEMIS_SCROLLBAR_H_STYLE,
        )
        scroll_x.pack(side='bottom', fill='x')

        self.configure(yscrollcommand=scroll_y.set)
        self.configure(xscrollcommand=scroll_x.set)

    def id_exists(self, item_id):
        return self.exists(str(item_id))

    def add_item(self, values, item_id=None):
        values = tuple(values)
        uid = str(item_id if item_id is not None else values[0])
        if self.id_exists(uid):
            return False
        tag = 'odd' if len(self.get_children()) % 2 else 'even'
        self.insert('', 'end', iid=uid, values=values, tags=(tag,))
        return True

    def remove_selected_items(self):
        for item in self.selection():
            self.delete(item)

    def remove_all(self):
        for item in self.get_children():
            self.delete(item)

    def get_selected_items(self):
        items = []
        for item in self.selection():
            values = self.item(item, 'values')
            items.append(values)

        return items

    def get_items(self):
        items = []
        for item in self.get_children():
            values = self.item(item, 'values')
            items.append(values)

        return items
