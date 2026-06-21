import win32print
import pywintypes
import psutil
import subprocess
import os
from app.utils.file_parser import FileUtils


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
        # Obter um identificador de impressora
        PRINTER_DEFAULTS = {"DesiredAccess": win32print.PRINTER_ACCESS_USE}
        printer_handle = win32print.OpenPrinter(printer_name, PRINTER_DEFAULTS)

        try:
            try:
                # Isso irá falhar com um erro, mas retornará o tamanho necessário
                printer_info = win32print.GetPrinter(printer_handle, 2)
            except pywintypes.error as e:
                if e.winerror == 122:  # ERROR_INSUFFICIENT_BUFFER
                    needed_size = e.args[2]
                    printer_info = win32print.GetPrinter(printer_handle, 2, needed_size)
                else:
                    raise

            if int(paper_size) == 0:
                return True
            else:
                if printer_info['pDevMode'].PaperSize == int(paper_size):
                    return True
                else:
                    return False

        finally:
            # Garantir que o identificador da impressora seja fechado
            win32print.ClosePrinter(printer_handle)

    except Exception as e:
        path = 'Errors_Logs.txt'
        FileUtils.write_log_file(path, e)
        return False


def print_pdf_file(pdf_path, printer_name, exe_index):
    executables = [
        'PDFtoPrinter.exe',
        'PDFtoPrinter_2.exe',
        'PDFtoPrinter_3.exe',
        'PDFtoPrinter_4.exe',
        'PDFtoPrinter_5.exe',
    ]

    command = [executables[exe_index], 'focus="Impressão de AR"', printer_name, pdf_path]

    try:
        subprocess.call(command, shell=True)
    except subprocess.CalledProcessError:
        raise Exception('Erro ao enviar arquivo para a impressora')
