"""Impressão GDI: desenha páginas rasterizadas em um DC com DEVMODE por job.

Usado pelos backends win32_devmode e win32_advanced. O DC é criado com o
DEVMODE do job (CreateDC), de forma que duplex/cópias/papel/orientação/bandeja
valem só para este job e o driver cuida da reprodução de cópias.
"""

import win32con
import win32gui
import win32ui
from PIL import Image, ImageWin


def print_images_via_gdi(printer_name, devmode, image_paths, doc_title):
    """Imprime as imagens (uma por página) via GDI. Retorna nº de páginas.

    Levanta exceção em caso de erro (o backend converte em PrintResult).
    """
    hdc = win32gui.CreateDC('WINSPOOL', printer_name, devmode)
    dc = win32ui.CreateDCFromHandle(hdc)
    started_doc = False
    try:
        printable_w = dc.GetDeviceCaps(win32con.HORZRES)
        printable_h = dc.GetDeviceCaps(win32con.VERTRES)

        dc.StartDoc(doc_title)
        started_doc = True

        pages = 0
        for path in image_paths:
            with Image.open(path) as img:
                img.load()
                iw, ih = img.size
                scale = min(printable_w / iw, printable_h / ih)
                tw = max(1, int(iw * scale))
                th = max(1, int(ih * scale))
                x = (printable_w - tw) // 2
                y = (printable_h - th) // 2

                dc.StartPage()
                dib = ImageWin.Dib(img)
                dib.draw(dc.GetHandleOutput(), (x, y, x + tw, y + th))
                dc.EndPage()
                pages += 1

        dc.EndDoc()
        started_doc = False
        return pages
    except Exception:
        if started_doc:
            try:
                dc.AbortDoc()
            except Exception:
                pass
        raise
    finally:
        try:
            dc.DeleteDC()
        except Exception:
            pass
