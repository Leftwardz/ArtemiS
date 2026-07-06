"""Ícones e gradientes para o tema da tela principal (Pillow + CTkImage)."""

from __future__ import annotations

from typing import Optional

import customtkinter as ctk
from PIL import Image, ImageDraw


def _hex_rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip('#')
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def _horizontal_gradient(size: tuple[int, int], left: str, right: str) -> Image.Image:
    width, height = size
    start = _hex_rgb(left)
    end = _hex_rgb(right)
    img = Image.new('RGBA', (width, height))
    pixels = img.load()
    for x in range(width):
        ratio = x / max(width - 1, 1)
        r = int(start[0] + (end[0] - start[0]) * ratio)
        g = int(start[1] + (end[1] - start[1]) * ratio)
        b = int(start[2] + (end[2] - start[2]) * ratio)
        for y in range(height):
            pixels[x, y] = (r, g, b, 255)
    return img


def rounded_gradient_image(
    width: int,
    height: int,
    color_left: str,
    color_right: str,
    *,
    radius: int = 10,
) -> Image.Image:
    width = max(width, 2)
    height = max(height, 2)
    grad = _horizontal_gradient((width, height), color_left, color_right)
    mask = Image.new('L', (width, height), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, width - 1, height - 1), radius=radius, fill=255)
    grad.putalpha(mask)
    return grad


def gradient_ctk_image(
    width: int,
    height: int,
    color_left: str,
    color_right: str,
    *,
    radius: int = 10,
) -> ctk.CTkImage:
    img = rounded_gradient_image(width, height, color_left, color_right, radius=radius)
    return ctk.CTkImage(light_image=img, dark_image=img, size=(width, height))


def _stroke(draw: ImageDraw.ImageDraw, points, color: str, width: int = 2):
    draw.line(points, fill=color, width=width, joint='curve')


def _draw_printer(draw: ImageDraw.ImageDraw, size: int, color: str):
    m = size / 20
    draw.rounded_rectangle((4 * m, 8 * m, 16 * m, 17 * m), radius=2 * m, outline=color, width=max(1, int(2 * m)))
    draw.rectangle((6 * m, 4 * m, 14 * m, 9 * m), outline=color, width=max(1, int(2 * m)))
    draw.rectangle((7 * m, 12 * m, 13 * m, 15 * m), fill=color)


def _draw_gear(draw: ImageDraw.ImageDraw, size: int, color: str):
    cx, cy = size / 2, size / 2
    r = size * 0.28
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=color, width=2)
    draw.ellipse((cx - r * 0.35, cy - r * 0.35, cx + r * 0.35, cy + r * 0.35), outline=color, width=2)
    for angle in range(0, 360, 45):
        import math
        rad = math.radians(angle)
        x1 = cx + math.cos(rad) * r * 0.55
        y1 = cy + math.sin(rad) * r * 0.55
        x2 = cx + math.cos(rad) * r * 1.05
        y2 = cy + math.sin(rad) * r * 1.05
        draw.line((x1, y1, x2, y2), fill=color, width=2)


def _draw_refresh(draw: ImageDraw.ImageDraw, size: int, color: str):
    m = size / 20
    draw.arc((4 * m, 4 * m, 16 * m, 16 * m), start=45, end=300, fill=color, width=2)
    draw.polygon([(14 * m, 4 * m), (16 * m, 8 * m), (11 * m, 8 * m)], fill=color)
    draw.polygon([(6 * m, 16 * m), (4 * m, 12 * m), (9 * m, 12 * m)], fill=color)


def _draw_chart(draw: ImageDraw.ImageDraw, size: int, color: str):
    m = size / 20
    draw.line((4 * m, 16 * m, 16 * m, 16 * m), fill=color, width=2)
    draw.rectangle((5 * m, 11 * m, 8 * m, 16 * m), fill=color)
    draw.rectangle((9 * m, 8 * m, 12 * m, 16 * m), fill=color)
    draw.rectangle((13 * m, 5 * m, 16 * m, 16 * m), fill=color)


def _draw_help(draw: ImageDraw.ImageDraw, size: int, color: str):
    cx, cy = size / 2, size / 2
    r = size * 0.38
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=color, width=2)
    draw.arc((cx - r * 0.35, cy - r * 0.55, cx + r * 0.35, cy + r * 0.05), start=200, end=340, fill=color, width=2)
    draw.line((cx, cy + r * 0.12, cx, cy + r * 0.32), fill=color, width=2)
    draw.ellipse((cx - 1.5, cy + r * 0.42, cx + 1.5, cy + r * 0.48), fill=color)


def _draw_barcode(draw: ImageDraw.ImageDraw, size: int, color: str):
    m = size / 20
    x = 4 * m
    while x < 16 * m:
        w = 1.2 * m if int(x / m) % 2 == 0 else 0.8 * m
        draw.rectangle((x, 5 * m, x + w, 15 * m), fill=color)
        x += w + 0.8 * m


def _draw_palette(draw: ImageDraw.ImageDraw, size: int, color: str):
    cx, cy = size / 2, size / 2
    r = size * 0.34
    draw.pieslice((cx - r, cy - r, cx + r, cy + r), start=0, end=120, fill=color)
    draw.pieslice((cx - r, cy - r, cx + r, cy + r), start=120, end=240, fill=color)
    draw.pieslice((cx - r, cy - r, cx + r, cy + r), start=240, end=360, fill=color)
    draw.ellipse((cx - r * 0.28, cy - r * 0.28, cx + r * 0.28, cy + r * 0.28), fill='#1e2433')


_ICON_DRAWERS = {
    'production': _draw_printer,
    'printing': _draw_printer,
    'settings': _draw_gear,
    'remake': _draw_refresh,
    'reports': _draw_chart,
    'help': _draw_help,
    'queue': _draw_barcode,
    'status': _draw_palette,
}


def draw_icon(name: str, size: int = 20, color: str = '#e8ecf4') -> Image.Image:
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    drawer = _ICON_DRAWERS.get(name)
    if drawer:
        drawer(draw, size, color)
    return img


class IconCache:
    def __init__(self):
        self._cache: dict[tuple, ctk.CTkImage] = {}

    def get(self, name: str, size: int = 20, color: str = '#e8ecf4') -> ctk.CTkImage:
        key = (name, size, color)
        if key not in self._cache:
            img = draw_icon(name, size=size, color=color)
            self._cache[key] = ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
        return self._cache[key]


class GradientButton(ctk.CTkButton):
    """Botão com fundo em gradiente (CTk não suporta gradiente nativo)."""

    def __init__(
        self,
        master,
        color_left: str,
        color_right: str,
        hover_left: Optional[str] = None,
        hover_right: Optional[str] = None,
        corner_radius: int = 10,
        min_height: int = 48,
        **kwargs,
    ):
        self._color_left = color_left
        self._color_right = color_right
        self._hover_left = hover_left or color_left
        self._hover_right = hover_right or color_right
        self._corner_radius = corner_radius
        self._min_height = min_height
        self._hovering = False
        self._disabled = False
        kwargs.setdefault('compound', 'center')
        self._gradient_image = gradient_ctk_image(200, min_height, color_left, color_right, radius=corner_radius)

        super().__init__(
            master,
            image=self._gradient_image,
            fg_color='#1e2433',
            hover_color='#1e2433',
            border_width=0,
            height=min_height,
            **kwargs,
        )
        self.bind('<Enter>', self._on_enter, add='+')
        self.bind('<Leave>', self._on_leave, add='+')
        self.bind('<Configure>', self._on_configure, add='+')

    def _on_configure(self, event=None):
        if event is not None and event.widget is not self:
            return
        width = max(self.winfo_width(), 80)
        height = max(self.winfo_height(), self._min_height)
        if self._disabled:
            left, right = '#3f3f46', '#52525b'
        elif self._hovering:
            left, right = self._hover_left, self._hover_right
        else:
            left, right = self._color_left, self._color_right
        self._gradient_image = gradient_ctk_image(
            width, height, left, right, radius=self._corner_radius,
        )
        super().configure(image=self._gradient_image)

    def _on_enter(self, _event=None):
        if str(self.cget('state')) == 'disabled':
            return
        self._hovering = True
        self._on_configure()

    def _on_leave(self, _event=None):
        self._hovering = False
        self._on_configure()

    def configure(self, cnf=None, **kwargs):
        if kwargs.get('state') == 'disabled':
            self._disabled = True
        elif kwargs.get('state') == 'normal':
            self._disabled = False
        result = super().configure(cnf, **kwargs)
        self._on_configure()
        return result

    config = configure
