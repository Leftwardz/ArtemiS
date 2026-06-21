import os

import pywintypes
import psutil
import win32print

from app.utils.file_parser import FileUtils
from app.utils.printing.backends.pdftoprinter import PDFTOPRINTER_EXECUTABLES  # noqa: F401  (compat)


def enumerate_installed_printers():
    """Lista nomes de impressoras instaladas no Windows (local + conexões de rede)."""
    flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    names = []
    try:
        for item in win32print.EnumPrinters(flags, None, 1):
            name = item[2]
            if name and name not in names:
                names.append(name)
    except Exception:
        pass
    return sorted(names, key=str.lower)


def printer_is_available(printer_name):
    """True se o Windows consegue abrir a impressora pelo nome."""
    if not (printer_name or '').strip():
        return False
    try:
        handle = win32print.OpenPrinter(
            printer_name, {"DesiredAccess": win32print.PRINTER_ACCESS_USE},
        )
        win32print.ClosePrinter(handle)
        return True
    except Exception:
        return False


def set_default_printer(printer):
    win32print.SetDefaultPrinter(printer)


def is_process_running(process_name):
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] == process_name:
            return True
    return False


def is_papersize_a4(printer_name, paper_size=9):
    try:
        PRINTER_DEFAULTS = {"DesiredAccess": win32print.PRINTER_ACCESS_USE}
        printer_handle = win32print.OpenPrinter(printer_name, PRINTER_DEFAULTS)

        try:
            try:
                printer_info = win32print.GetPrinter(printer_handle, 2)
            except pywintypes.error as e:
                if e.winerror == 122:
                    needed_size = e.args[2]
                    printer_info = win32print.GetPrinter(printer_handle, 2, needed_size)
                else:
                    raise

            if int(paper_size) == 0:
                return True
            return printer_info['pDevMode'].PaperSize == int(paper_size)

        finally:
            win32print.ClosePrinter(printer_handle)

    except Exception as e:
        path = 'Errors_Logs.txt'
        FileUtils.write_log_file(path, e)
        return False


def print_pdf_file(
    pdf_path,
    printer_name,
    exe_index=0,
    paper_size='9',
    backend='pdftoprinter',
    config=None,
    copies=1,
    duplex='simplex',
    orientation='portrait',
    tray=None,
):
    """Despacha a impressão para o backend escolhido (camada app.utils.printing).

    Assinatura mantida por compatibilidade; novos parâmetros (copies, duplex,
    orientation, tray) têm defaults neutros que preservam o comportamento atual.
    Levanta Exception em caso de falha (preserva o tratamento de erro da UI).
    """
    from app.utils.printing import PrintJob, dispatch

    job = PrintJob(
        pdf_path=os.path.abspath(pdf_path),
        printer=printer_name,
        copies=copies,
        duplex=duplex,
        orientation=orientation,
        paper_size=str(paper_size),
        tray=tray,
        slot_index=exe_index,
        config=config,
    )
    result = dispatch(job, backend)
    if not result.ok:
        message = result.error or 'Falha na impressão.'
        if result.detail:
            message = f'{message}\n{result.detail}'
        raise Exception(message)
