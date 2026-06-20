from app.utils.printer_handler import print_pdf_file, set_default_printer, is_papersize_a4, is_process_running


def print_document(pdf_path, printer_name, exe_index):
    """
    Triggers physical printing of a ununified batch PDF file.
    """
    print_pdf_file(pdf_path, printer_name, exe_index)


def configure_printer_settings(printer_name, paper_size):
    """
    Validates if the target printer matches the required paper specifications.
    """
    return is_papersize_a4(printer_name, paper_size)
