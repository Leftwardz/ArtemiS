"""Custom window title bar for Windows (borderless chrome with drag + window controls)."""

from __future__ import annotations

import sys
from ctypes import Structure, byref, sizeof, wintypes
from typing import Optional

import customtkinter as ctk

if sys.platform == 'win32':
    from ctypes import windll
else:
    windll = None  # type: ignore[assignment]

from app.ui.constants import (
    FONT,
    THEME_NAV_ACTIVE,
    THEME_SIDEBAR,
    THEME_TEXT_SECONDARY,
)

TITLEBAR_HEIGHT = 36
WIN_ICON_FONT = 'Segoe MDL2 Assets'
ICON_MINIMIZE = '\uE921'
ICON_MAXIMIZE = '\uE922'
ICON_RESTORE = '\uE923'
ICON_CLOSE = '\uE8BB'


class _MONITORINFO(Structure):
    _fields_ = [
        ('cbSize', wintypes.DWORD),
        ('rcMonitor', wintypes.RECT),
        ('rcWork', wintypes.RECT),
        ('dwFlags', wintypes.DWORD),
    ]


def _is_windows() -> bool:
    return sys.platform == 'win32'


def format_geometry(width: int, height: int, x: int, y: int) -> str:
    return f'{int(width)}x{int(height)}+{int(x)}+{int(y)}'


def _primary_work_area() -> tuple[int, int, int, int]:
    """Return (x, y, width, height) of the primary monitor work area."""
    if not _is_windows() or windll is None:
        return 0, 0, 1920, 1080
    rect = wintypes.RECT()
    windll.user32.SystemParametersInfoW(0x0030, 0, byref(rect), 0)
    return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top


def _monitor_work_area(window: ctk.CTk) -> tuple[int, int, int, int]:
    """Return work area for the monitor nearest to the window."""
    if not _is_windows() or windll is None:
        return 0, 0, 1920, 1080
    try:
        hwnd = _window_hwnd(window)
        monitor = windll.user32.MonitorFromWindow(hwnd, 2)  # MONITOR_DEFAULTTONEAREST
        if not monitor:
            return _primary_work_area()
        info = _MONITORINFO()
        info.cbSize = sizeof(_MONITORINFO)
        if not windll.user32.GetMonitorInfoW(monitor, byref(info)):
            return _primary_work_area()
        work = info.rcWork
        return work.left, work.top, work.right - work.left, work.bottom - work.top
    except Exception:
        return _primary_work_area()


def _window_hwnd(window: ctk.CTk) -> int:
    window.update_idletasks()
    hwnd = window.winfo_id()
    if windll is None:
        return hwnd
    parent = windll.user32.GetParent(hwnd)
    return parent or hwnd


class CustomTitleBar:
    """Top chrome with drag-to-move and minimize / maximize / close."""

    def __init__(self, window: ctk.CTk, title: str, *, row: int = 0, columnspan: int = 2):
        self.window = window
        self._title = title
        self._drag_x = 0
        self._drag_y = 0
        self._maximized = False
        self._restore_geometry: Optional[str] = None
        self._enabled = _is_windows()

        self.frame = ctk.CTkFrame(
            window,
            height=TITLEBAR_HEIGHT,
            corner_radius=0,
            fg_color=THEME_SIDEBAR,
            border_width=0,
        )
        self.frame.grid(row=row, column=0, columnspan=columnspan, sticky='ew')
        self.frame.grid_propagate(False)
        self.frame.grid_columnconfigure(0, weight=1)

        if not self._enabled:
            self.frame.grid_remove()
            return

        window.overrideredirect(True)
        window.after(10, self._ensure_taskbar_icon)
        window.after(20, self._apply_border)

        drag = ctk.CTkFrame(self.frame, fg_color='transparent', corner_radius=0)
        drag.grid(row=0, column=0, sticky='nsew', padx=(12, 0))
        drag.bind('<ButtonPress-1>', self._start_move)
        drag.bind('<B1-Motion>', self._do_move)
        drag.bind('<Double-Button-1>', lambda _e: self.toggle_maximize())

        self.lbl_title = ctk.CTkLabel(
            drag,
            text=title,
            font=(FONT, 12),
            text_color=THEME_TEXT_SECONDARY,
            anchor='w',
        )
        self.lbl_title.pack(side='left', fill='x', expand=True)
        self.lbl_title.bind('<ButtonPress-1>', self._start_move)
        self.lbl_title.bind('<B1-Motion>', self._do_move)
        self.lbl_title.bind('<Double-Button-1>', lambda _e: self.toggle_maximize())

        controls = ctk.CTkFrame(self.frame, fg_color='transparent')
        controls.grid(row=0, column=1, sticky='e')

        self.btn_min = self._control_button(controls, ICON_MINIMIZE, self.minimize)
        self.btn_max = self._control_button(controls, ICON_MAXIMIZE, self.toggle_maximize)
        self.btn_close = self._control_button(controls, ICON_CLOSE, self.close)
        self.btn_min.pack(side='left')
        self.btn_max.pack(side='left')
        self.btn_close.pack(side='left')

    def _ensure_taskbar_icon(self):
        try:
            hwnd = _window_hwnd(self.window)
            gwl_exstyle = -20
            ws_ex_appwindow = 0x00040000
            ws_ex_toolwindow = 0x00000080
            style = windll.user32.GetWindowLongW(hwnd, gwl_exstyle)
            style = (style & ~ws_ex_toolwindow) | ws_ex_appwindow
            windll.user32.SetWindowLongW(hwnd, gwl_exstyle, style)
            self.window.withdraw()
            self.window.after(10, self.window.deiconify)
        except Exception:
            pass

    def _apply_border(self):
        try:
            hwnd = _window_hwnd(self.window)
            windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 34, byref(wintypes.INT(1)), 4,
            )
        except Exception:
            pass

    def _control_button(self, parent, text, command):
        return ctk.CTkButton(
            parent,
            text=text,
            width=44,
            height=TITLEBAR_HEIGHT,
            corner_radius=0,
            fg_color='transparent',
            hover_color=THEME_NAV_ACTIVE,
            text_color=THEME_TEXT_SECONDARY,
            font=(WIN_ICON_FONT, 10),
            command=command,
        )

    def set_title(self, title: str) -> None:
        self._title = title
        if self._enabled:
            self.lbl_title.configure(text=title)

    def _start_move(self, event):
        if self._maximized:
            return
        self._drag_x = event.x_root - self.window.winfo_x()
        self._drag_y = event.y_root - self.window.winfo_y()

    def _do_move(self, event):
        if self._maximized:
            return
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
        self.window.geometry(f'+{x}+{y}')

    def minimize(self):
        if not self._enabled:
            return
        windll.user32.ShowWindow(_window_hwnd(self.window), 6)

    def toggle_maximize(self):
        if not self._enabled:
            return
        if self._maximized:
            self.restore()
        else:
            self.maximize()

    def maximize(self):
        if not self._enabled or self._maximized:
            return
        self._restore_geometry = self.window.geometry()
        x, y, w, h = _monitor_work_area(self.window)
        self.window.geometry(format_geometry(w, h, x, y))
        self._maximized = True
        self.btn_max.configure(text=ICON_RESTORE)

    def restore(self):
        if not self._enabled or not self._maximized:
            return
        if self._restore_geometry:
            self.window.geometry(self._restore_geometry)
        self._maximized = False
        self.btn_max.configure(text=ICON_MAXIMIZE)

    def close(self):
        self.window.destroy()


def attach_custom_titlebar(window: ctk.CTk, title: str, *, row: int = 0, columnspan: int = 2) -> CustomTitleBar:
    return CustomTitleBar(window, title, row=row, columnspan=columnspan)
