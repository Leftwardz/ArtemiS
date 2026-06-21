import os
import shutil

from app.utils.document_delivery import open_path
from app.utils.printer_handler import is_papersize_a4, print_pdf_file


def validate_printer_paper(printer_name, paper_size):
    if printer_name == 'Criar PDF':
        return True
    return is_papersize_a4(printer_name, paper_size)


def get_printer_paper_error_message(paper_size, wording='configurado'):
    return (
        f'Impressora não está definida com papel {wording} no produto: {paper_size}\n'
        f'Informar Equipe de Suporte'
    )


def finish_print_job(pdf_path, files_to_move, is_remake, printer_name, exe_index=None):
    """
    Opens or prints the unified PDF and archives source work files when not in remake mode.
    """
    if printer_name == 'Criar PDF':
        open_path(pdf_path)
    else:
        print_pdf_file(os.path.abspath(pdf_path), printer_name, exe_index)

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


def print_document(pdf_path, printer_name, exe_index):
    """Triggers physical printing of a unified batch PDF file."""
    print_pdf_file(pdf_path, printer_name, exe_index)


def configure_printer_settings(printer_name, paper_size):
    """Validates if the target printer matches the required paper specifications."""
    return validate_printer_paper(printer_name, paper_size)
