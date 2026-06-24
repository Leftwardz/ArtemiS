"""Linux development launcher for ArtemiS.

ArtemiS targets Windows. This launcher lets the app run on Linux for
development WITHOUT modifying any application source code. It:

  1. Adds ``dev_stubs/`` to ``sys.path`` so the Windows-only ``win32*``
     imports resolve to harmless stubs (real printing stays Windows-only).
  2. No-ops ``wm_iconbitmap`` because X11/Tk cannot load Windows ``.ico``
     window icons (purely cosmetic).
  3. Executes ``Main.py`` unchanged as ``__main__``.

Usage:
    DISPLAY=:1 .venv/bin/python run_linux.py
"""

import os
import runpy
import sys
import tkinter

HERE = os.path.dirname(os.path.abspath(__file__))

# 1. Resolve Windows-only pywin32 imports to Linux stubs.
sys.path.insert(0, os.path.join(HERE, "dev_stubs"))

# 2. X11 Tk does not support Windows .ico icons; make the call a no-op.
tkinter.Wm.wm_iconbitmap = lambda self, *args, **kwargs: None
tkinter.Wm.iconbitmap = lambda self, *args, **kwargs: None

try:
    import customtkinter

    customtkinter.CTk.iconbitmap = lambda self, *args, **kwargs: None
    if hasattr(customtkinter, "CTkToplevel"):
        customtkinter.CTkToplevel.iconbitmap = lambda self, *args, **kwargs: None
except Exception:  # pragma: no cover - customtkinter always present in dev env
    pass

# 3. Run the unmodified application entrypoint.
os.chdir(HERE)
runpy.run_path(os.path.join(HERE, "Main.py"), run_name="__main__")
