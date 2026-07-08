from app.ui.custom_titlebar import (
    _window_minsize,
    compute_resized_geometry,
    format_geometry,
    parse_geometry,
)


def test_parse_geometry():
    assert parse_geometry('1200x800+100+200') == (1200, 800, 100, 200)


def test_format_geometry():
    assert format_geometry(1200, 800, 100, 200) == '1200x800+100+200'


def test_resize_east_increases_width():
    w, h, x, y = compute_resized_geometry(800, 600, 50, 50, 40, 0, 'e', 400, 300)
    assert (w, h, x, y) == (840, 600, 50, 50)


def test_resize_west_moves_left_edge():
    w, h, x, y = compute_resized_geometry(800, 600, 50, 50, 30, 0, 'w', 400, 300)
    assert (w, h, x, y) == (770, 600, 80, 50)


def test_resize_west_respects_min_width():
    w, h, x, y = compute_resized_geometry(800, 600, 50, 50, 500, 0, 'w', 400, 300)
    assert w == 400
    assert x == 450


def test_resize_south_increases_height():
    w, h, x, y = compute_resized_geometry(800, 600, 50, 50, 0, 25, 's', 400, 300)
    assert (w, h, x, y) == (800, 625, 50, 50)


def test_resize_north_respects_min_height():
    w, h, x, y = compute_resized_geometry(800, 600, 50, 50, 0, 400, 'n', 400, 300)
    assert h == 300
    assert y == 350


def test_resize_corner():
    w, h, x, y = compute_resized_geometry(800, 600, 50, 50, 20, 10, 'se', 400, 300)
    assert (w, h, x, y) == (820, 610, 50, 50)


class _FakeWindow:
    _min_width = 1280
    _min_height = 720


def test_window_minsize_reads_ctk_attributes():
    assert _window_minsize(_FakeWindow()) == (1280, 720)
