import os
import subprocess

import pywintypes
import psutil
import win32print

from app.utils.file_parser import FileUtils
from app.utils.ghostscript_paths import ghostscript_env, resolve_ghostscript_exe
from app.utils.paper_size_map import paper_size_to_ghostscript

PDFTOPRINTER_EXECUTABLES = (
    'PDFtoPrinter.exe',
    'PDFtoPrinter_2.exe',
    'PDFtoPrinter_3.exe',
    'PDFtoPrinter_4.exe',
    'PDFtoPrinter_5.exe',
)


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


def _print_via_pdftoprinter(pdf_path, printer_name, exe_index):
    if exe_index is None:
        exe_index = 0
    executable = PDFTOPRINTER_EXECUTABLES[exe_index]
    command = [executable, 'focus="Impressão de AR"', printer_name, pdf_path]
    try:
        subprocess.call(command, shell=True)
    except subprocess.CalledProcessError as exc:
        raise Exception('Erro ao enviar arquivo para a impressora') from exc


def _print_via_ghostscript(pdf_path, printer_name, paper_size, config=None):
    gs_exe = resolve_ghostscript_exe(config)
    env = ghostscript_env(config)
    output = f'%printer%{printer_name}'

    command = [
        gs_exe,
        '-dNOPAUSE', '-dBATCH', '-dQUIET',
        '-sDEVICE=mswinpr2',
        f'-sOutputFile={output}',
    ]
    gs_paper = paper_size_to_ghostscript(paper_size)
    if gs_paper:
        command.append(f'-sPAPERSIZE={gs_paper}')
    command.append(pdf_path)

    result = subprocess.run(
        command,
        env=env,
        capture_output=True,
        text=True,
        cwd=os.path.dirname(gs_exe) if os.path.isfile(gs_exe) else None,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or '').strip()
        raise Exception(f'Erro ao imprimir via Ghostscript.\n{detail}')


def print_pdf_file(pdf_path, printer_name, exe_index=0, paper_size='9', backend='pdftoprinter', config=None):
    pdf_path = os.path.abspath(pdf_path)
    if backend == 'ghostscript':
        _print_via_ghostscript(pdf_path, printer_name, paper_size, config)
    else:
        _print_via_pdftoprinter(pdf_path, printer_name, exe_index)
