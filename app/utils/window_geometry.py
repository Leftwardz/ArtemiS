"""Window placement helpers (multi-monitor aware on Windows)."""

from __future__ import annotations

import sys
from ctypes import Structure, byref, sizeof, wintypes

from screeninfo import get_monitors

if sys.platform == 'win32':
    from ctypes import windll
else:
    windll = None  # type: ignore[assignment]


class _MONITORINFO(Structure):
    _fields_ = [
        ('cbSize', wintypes.DWORD),
        ('rcMonitor', wintypes.RECT),
        ('rcWork', wintypes.RECT),
        ('dwFlags', wintypes.DWORD),
    ]


def _toplevel_hwnd(widget) -> int | None:
    if windll is None:
        return None
    try:
        top = widget.winfo_toplevel()
        top.update_idletasks()
        hwnd = top.winfo_id()
        parent = windll.user32.GetParent(hwnd)
        return parent or hwnd
    except Exception:
        return None


def _monitor_work_area_from_hwnd(hwnd: int) -> tuple[int, int, int, int] | None:
    if windll is None:
        return None
    try:
        monitor = windll.user32.MonitorFromWindow(hwnd, 2)  # MONITOR_DEFAULTTONEAREST
        if not monitor:
            return None
        info = _MONITORINFO()
        info.cbSize = sizeof(_MONITORINFO)
        if not windll.user32.GetMonitorInfoW(monitor, byref(info)):
            return None
        work = info.rcWork
        return work.left, work.top, work.right - work.left, work.bottom - work.top
    except Exception:
        return None


def get_monitor(master) -> int:
    """
    Return the index of the monitor containing the center of ``master``'s toplevel.
    """
    try:
        ref = master.winfo_toplevel()
        ref.update_idletasks()
        widget_x = ref.winfo_rootx() + ref.winfo_width() / 2
        widget_y = ref.winfo_rooty() + ref.winfo_height() / 2
    except Exception:
        return -1

    monitors = get_monitors()
    for index, monitor in enumerate(monitors):
        if (
            monitor.x <= widget_x < monitor.x + monitor.width
            and monitor.y <= widget_y < monitor.y + monitor.height
        ):
            return index
    return -1


def get_monitor_work_area_for_widget(widget) -> tuple[int, int, int, int]:
    """Return ``(x, y, width, height)`` work area for the monitor nearest to ``widget``."""
    hwnd = _toplevel_hwnd(widget)
    if hwnd is not None:
        area = _monitor_work_area_from_hwnd(hwnd)
        if area is not None:
            return area

    monitors = get_monitors()
    index = get_monitor(widget)
    if 0 <= index < len(monitors):
        monitor = monitors[index]
        return monitor.x, monitor.y, monitor.width, monitor.height

    if monitors:
        monitor = monitors[0]
        return monitor.x, monitor.y, monitor.width, monitor.height
    return 0, 0, 1920, 1080


def clamp_to_work_area(
    x: float,
    y: float,
    width: int,
    height: int,
    work_x: int,
    work_y: int,
    work_w: int,
    work_h: int,
) -> tuple[int, int]:
    clamped_x = max(work_x, min(int(x), work_x + max(work_w - width, 0)))
    clamped_y = max(work_y, min(int(y), work_y + max(work_h - height, 0)))
    return clamped_x, clamped_y


def center_over_reference(
    ref_x: int,
    ref_y: int,
    ref_w: int,
    ref_h: int,
    width: int,
    height: int,
    move_x: int = 0,
    move_y: int = 0,
) -> tuple[float, float]:
    x = ref_x + (ref_w - width) / 2 + move_x
    y = ref_y + (ref_h - height) / 2 + move_y
    return x, y


def center_window_on_widget(master, width: int, height: int, move_x=0, move_y=0) -> str:
    """Center a window over the reference widget's toplevel (same monitor as the app)."""
    ref = master.winfo_toplevel()
    ref.update_idletasks()
    ref_x = ref.winfo_rootx()
    ref_y = ref.winfo_rooty()
    ref_w = max(ref.winfo_width(), 1)
    ref_h = max(ref.winfo_height(), 1)
    x, y = center_over_reference(ref_x, ref_y, ref_w, ref_h, width, height, move_x, move_y)
    work_x, work_y, work_w, work_h = get_monitor_work_area_for_widget(ref)
    x, y = clamp_to_work_area(x, y, width, height, work_x, work_y, work_w, work_h)
    return '%dx%d+%d+%d' % (width, height, x, y)


def maximize_window_on_widget(window, master) -> str:
    """Maximize ``window`` on the monitor where ``master`` is shown."""
    ref = master.winfo_toplevel()
    work_x, work_y, work_w, work_h = get_monitor_work_area_for_widget(ref)
    geometry = '%dx%d+%d+%d' % (work_w, work_h, work_x, work_y)
    window.geometry(geometry)
    return geometry


def calculate_center_screen_with_monitor(master, width: int, height: int, monitor_index: int, move_x=0, move_y=0):
    """
    Calculate geometry to center a window over ``master``'s toplevel.

    ``monitor_index`` is kept for backward compatibility; placement follows the
    parent window so dialogs stay on the same monitor as the application.
    """
    del monitor_index  # legacy callers still pass get_monitor(master)
    return center_window_on_widget(master, width, height, move_x, move_y)


def calculate_center_screen(width: int, height: int, window, move_x=0, move_y=0):
    """Center on the monitor nearest to ``window`` (used by the main app at startup)."""
    return center_window_on_widget(window, width, height, move_x, move_y)
