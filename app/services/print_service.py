import os
import shutil
from threading import Thread

from app.utils.document_delivery import open_path
from app.utils.printer_handler import is_papersize_a4, print_pdf_file
from app.utils.temp_pdf import remove_temp_pdf, write_temp_pdf


def _delayed_remove_temp_pdf(path: str, delay_seconds: float = 60):
    import time
    time.sleep(delay_seconds)
    remove_temp_pdf(path)


def validate_printer_paper(printer_name, paper_size):
    if printer_name == 'Criar PDF':
        return True
    return is_papersize_a4(printer_name, paper_size)


def get_printer_paper_error_message(paper_size, wording='configurado'):
    return (
        f'Impressora não está definida com papel {wording} no produto: {paper_size}\n'
        f'Informar Equipe de Suporte'
    )


def finish_print_job(pdf_data, files_to_move, is_remake, printer_name, exe_index=None):
    """
    Imprime ou abre o PDF unificado e arquiva os CSVs de origem.
    pdf_data: bytes do PDF gerado em memória; grava temp efêmero só para PDFtoPrinter/visualizador.
    """
    temp_path = write_temp_pdf(pdf_data)
    defer_remove = False
    try:
        if printer_name == 'Criar PDF':
            open_path(temp_path)
            defer_remove = True
        else:
            print_pdf_file(os.path.abspath(temp_path), printer_name, exe_index)

        for file in files_to_move:
            try:
                filename = os.path.basename(file)
                directory = os.path.dirname(file)
                old_path = os.path.join(directory, 'Old')

                path_to_verify = os.path.join(old_path, filename)
                if os.path.exists(path_to_verify) and not is_remake:
                    os.remove(path_to_verify)
                if not is_remake:
                    shutil.move(file, old_path)
            except shutil.Error:
                pass
    except Exception:
        remove_temp_pdf(temp_path)
        raise
    else:
        if defer_remove:
            Thread(target=_delayed_remove_temp_pdf, args=(temp_path,), daemon=True).start()
        else:
            remove_temp_pdf(temp_path)


def print_document(pdf_path, printer_name, exe_index):
    """Triggers physical printing of a unified batch PDF file."""
    print_pdf_file(pdf_path, printer_name, exe_index)


def configure_printer_settings(printer_name, paper_size):
    """Validates if the target printer matches the required paper specifications."""
    return validate_printer_paper(printer_name, paper_size)
