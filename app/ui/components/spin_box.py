import customtkinter as ctk


class SpinBox(ctk.CTkFrame):
    def __init__(self, master, step=1, func=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self.configure(fg_color='transparent', corner_radius=0)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.func = func
        self.step = step

        self.entry = ctk.CTkEntry(self, width=100, height=26, border_width=0, corner_radius=0)
        self.entry.grid(row=0, column=0, rowspan=2)
        self.entry.insert(1, 1)

        self.btn_up = ctk.CTkButton(
            self, text='▲', font=('arial', 6), width=20, height=10, corner_radius=0, command=self.increase
        )
        self.btn_up.grid(row=0, column=0, sticky='E')

        self.btn_down = ctk.CTkButton(
            self, text='▼', font=('arial', 6), width=20, height=10, corner_radius=0, command=self.decrease
        )
        self.btn_down.grid(row=1, column=0, sticky='E')

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
