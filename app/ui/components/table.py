import tkinter
from tkinter import ttk


class Table(ttk.Treeview):
    def __init__(self, master, cols_names, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        try:
            self.tk.call("source", "azure.tcl")
            self.tk.call("set_theme", "dark")
        except Exception:
            pass

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
        for item in self.get_children():
            values = self.item(item, "values")
            if values[0] == str(item_id):
                return True

        return False

    def add_item(self, values):
        values = tuple(values)
        if not self.id_exists(values[0]):
            self.insert("", "end", values=values)

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
