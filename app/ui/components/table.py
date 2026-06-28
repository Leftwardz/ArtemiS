import tkinter
from tkinter import ttk


class Table(ttk.Treeview):
    def __init__(self, master, cols_names, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self.configure(columns=cols_names)

        for i, col_name in enumerate(cols_names, start=1):
            self.heading(f"#{i}", text=col_name)
            self.column(f"#{i}", width=100, anchor=tkinter.CENTER)

        scroll_y = ttk.Scrollbar(self, orient="vertical", command=self.yview)
        scroll_y.pack(side="right", fill="y")

        scroll_x = ttk.Scrollbar(self, orient="horizontal", command=self.xview)
        scroll_x.pack(side="bottom", fill="x")

        self.configure(yscrollcommand=scroll_y.set)
        self.configure(xscrollcommand=scroll_x.set)

    def id_exists(self, item_id):
        return self.exists(str(item_id))

    def add_item(self, values, item_id=None):
        values = tuple(values)
        uid = str(item_id if item_id is not None else values[0])
        if self.id_exists(uid):
            return False
        self.insert("", "end", iid=uid, values=values)
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
            values = self.item(item, "values")
            items.append(values)

        return items

    def get_items(self):
        items = []
        for item in self.get_children():
            values = self.item(item, "values")
            items.append(values)

        return items
