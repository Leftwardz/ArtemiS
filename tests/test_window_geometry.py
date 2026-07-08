from app.utils.window_geometry import (
    center_over_reference,
    clamp_to_work_area,
    get_monitor,
)


def test_get_monitor_uses_both_axes(monkeypatch):
    class Monitor:
        def __init__(self, x, y, width, height):
            self.x = x
            self.y = y
            self.width = width
            self.height = height

    class FakeWidget:
        def winfo_toplevel(self):
            return self

        def update_idletasks(self):
            return None

        def winfo_rootx(self):
            return 2000

        def winfo_rooty(self):
            return 50

        def winfo_width(self):
            return 800

        def winfo_height(self):
            return 600

    monkeypatch.setattr(
        'app.utils.window_geometry.get_monitors',
        lambda: [
            Monitor(0, 0, 1920, 1080),
            Monitor(1920, 0, 1920, 1080),
        ],
    )
    assert get_monitor(FakeWidget()) == 1


def test_center_over_reference():
    x, y = center_over_reference(100, 200, 800, 600, 400, 300)
    assert x == 300
    assert y == 350


def test_clamp_to_work_area():
    x, y = clamp_to_work_area(5000, 5000, 400, 300, 1920, 0, 1920, 1080)
    assert x == 1920 + 1920 - 400
    assert y == 1080 - 300
