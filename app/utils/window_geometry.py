from screeninfo import get_monitors


def get_monitor(master):
    """
    Get the index of the monitor where the widget is located.
    :param master: The widget for which to determine the monitor.
    :return: Index of the monitor (0 for the first monitor, 1 for the second, and so on).
    """
    try:
        widget_x = master.winfo_rootx() + master.winfo_width() / 2
    except Exception:
        widget_x = 0

    monitors = get_monitors()

    for index, monitor in enumerate(monitors):
        if monitor.x <= widget_x < monitor.x + monitor.width:
            return index

    return -1


def calculate_center_screen_with_monitor(master, width: int, height: int, monitor_index: int, move_x=0, move_y=0):
    """
    Calculate the geometry to center the app on a specific monitor based on the position of the master widget.
    :param master: The widget to use as a reference for positioning.
    :param width: The width of the app.
    :param height: The height of the app.
    :param monitor_index: Index of the target monitor (0 for the first monitor, 1 for the second, and so on).
    :param move_x: Optional x-axis offset.
    :param move_y: Optional y-axis offset.
    :return: The geometry string to center the app on the specified monitor.
    """
    monitors = get_monitors()

    if 0 <= monitor_index < len(monitors):
        target_monitor = monitors[monitor_index]
        x = target_monitor.x + (target_monitor.width / 2) - (width / 2) + move_x
        y = target_monitor.y + (target_monitor.height / 2) - (height / 2) + move_y
    else:
        # Default to centering on the primary monitor if the specified monitor index is invalid
        primary_monitor = monitors[0]
        x = primary_monitor.x + (primary_monitor.width / 2) - (width / 2) + move_x
        y = primary_monitor.y + (primary_monitor.height / 2) - (height / 2) + move_y

    return "%dx%d+%d+%d" % (width, height, x, y)


def calculate_center_screen(width: int, height: int, window, move_x=0, move_y=0):
    """
    Receive the width and height from the app, and center in the screen
    :param width: width from the app
    :param height: height from the app
    :param window: customtkinter CTk, Frame or TopLevel object
    :return: return the geometry to center the app to the screen
    """
    try:
        screen_width, screen_height = window.winfo_screenwidth(), window.winfo_screenheight()
    except Exception:
        screen_width, screen_height = 1920, 1080
    x, y = (screen_width / 2) - (width / 2), (screen_height / 2) - (height / 2)
    return "%dx%d+%d+%d" % (width, height, x + move_x, y + move_y)
