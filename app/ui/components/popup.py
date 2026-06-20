import customtkinter as ctk

from app.ui.constants import BTN_HOVER_RED, BTN_RED, ICON
from app.utils.window_geometry import calculate_center_screen_with_monitor, get_monitor


class PopUpWindow(ctk.CTkToplevel):
    def __init__(self, master, title, text, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iconbitmap(ICON)
        self.master = master

        self.title(title)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.frame = ctk.CTkScrollableFrame(self, fg_color='transparent', height=10)

        self.lbl_text = ctk.CTkLabel(self.frame, text=text, font=('Arial', 12, 'bold'))
        self.lbl_text.pack(padx=20, pady=10)
        self.lbl_text.update_idletasks()

        self.btn_close = ctk.CTkButton(
            self.frame,
            text='Fechar',
            fg_color=BTN_RED,
            hover_color=BTN_HOVER_RED,
            command=self.destroy,
        )
        self.btn_close.pack(padx=20, pady=10)

        window_width = max(200, self.lbl_text.winfo_reqwidth() + 80)
        frame_height = max(50, self.lbl_text.winfo_reqheight())
        window_height = max(100, frame_height - 100)

        self.geometry(calculate_center_screen_with_monitor(master, window_width, window_height, get_monitor(master)))
        self.minsize(window_width, window_height)
        self.maxsize(window_width, window_height)
        self.resizable(False, False)

        self.frame.pack(fill='both')
        self.grab_set()


class ConfirmWindow(ctk.CTkToplevel):
    def __init__(self, master, title, text, func, has_confirm=True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iconbitmap(ICON)
        height = 170 if has_confirm else 110

        self.geometry(calculate_center_screen_with_monitor(master, 550, height, get_monitor(master)))
        self.minsize(550, height)
        self.maxsize(550, height)
        self.func = func
        self.has_confirm = has_confirm

        self.resizable(False, False)
        self.title(title)
        self.master = master
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        lbl_text = ctk.CTkLabel(self, text=text, font=('Arial', 13, 'bold'))
        lbl_text.grid(row=0, column=0, columnspan=2, pady=5, padx=10)

        if has_confirm:
            lbl_text = ctk.CTkLabel(self, text='Digite "Confirmo" abaixo para validar', font=('Arial', 10, 'bold'))
            lbl_text.grid(row=1, column=0, columnspan=2, pady=5, padx=10)

            self.entry_confirm = ctk.CTkEntry(self)
            self.entry_confirm.grid(row=2, column=0, columnspan=2, pady=5, padx=10)

        self.btn_ok = ctk.CTkButton(self, text="OK", width=120, command=self.confirm_destroy)
        self.btn_ok.grid(row=6, column=0, pady=10, padx=20)

        self.btn_cancelar = ctk.CTkButton(
            self,
            width=120,
            text="Cancelar",
            fg_color=BTN_RED,
            hover_color=BTN_HOVER_RED,
            command=self.destroy,
        )
        self.btn_cancelar.grid(row=6, column=1, pady=10, padx=20)

    def confirm_destroy(self):
        if self.has_confirm:
            value = self.entry_confirm.get()
            if value.upper() == 'CONFIRMO':
                self.destroy()
                self.func()
            else:
                PopUpWindow(self, 'Erro', f'O valor digitado "{value}" não confere')
        else:
            self.destroy()
            self.func()
