"""Tema escuro Azure (ttk) — arquivos em theme/ + azure.tcl na raiz do app."""
import os
import sys


def app_dir() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def apply_azure_dark_theme(tk_root) -> None:
    """Aplica tema escuro Azure em widgets ttk (Treeview, Scrollbar, etc.)."""
    azure_tcl = os.path.join(app_dir(), 'azure.tcl')
    if not os.path.isfile(azure_tcl):
        return
    try:
        tk_root.tk.call('source', azure_tcl)
        tk_root.tk.call('set_theme', 'dark')
    except Exception:
        pass
