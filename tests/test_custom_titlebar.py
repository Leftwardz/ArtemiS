from app.ui.custom_titlebar import format_geometry


def test_format_geometry():
    assert format_geometry(1200, 800, 100, 200) == '1200x800+100+200'
