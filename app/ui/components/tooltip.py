import customtkinter as ctk


class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None

        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        if self.tooltip_window is None:
            self.hide_tooltip()

            x = self.widget.winfo_rootx() + 20
            y = self.widget.winfo_rooty() + 20

            self.tooltip_window = ctk.CTkToplevel(self.widget)
            self.tooltip_window.wm_overrideredirect(True)
            self.tooltip_window.wm_geometry(f"+{x}+{y}")
            self.tooltip_window.bind("<Leave>", self.hide_tooltip)

            label = ctk.CTkLabel(self.tooltip_window, text=self.text, padx=5, pady=5)
            label.pack()
        else:
            self.tooltip_window.deiconify()

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.withdraw()
            x = self.widget.winfo_rootx() + 20
            y = self.widget.winfo_rooty() + 20
            self.tooltip_window.wm_geometry(f"+{x}+{y}")
