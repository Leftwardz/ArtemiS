import os
import shutil
import traceback
from threading import Thread

from app import audit, runtime
from app.services.settings_service import get_print_backend
from app.utils.document_delivery import open_path
from app.utils.printing.base import DUPLEX_LONG_EDGE, DUPLEX_SIMPLEX, ORIENTATION_LANDSCAPE, ORIENTATION_PORTRAIT
from app.utils.printer_handler import is_papersize_a4, print_pdf_file
from app.utils.temp_pdf import remove_temp_pdf, write_temp_pdf


def _delayed_remove_temp_pdf(path: str, delay_seconds: float = 60):
    import time
    time.sleep(delay_seconds)
    remove_temp_pdf(path)


def validate_printer_paper(printer_name, paper_size):
    if printer_name == 'Criar PDF':
        return True
    # Apenas o PDFtoPrinter depende da preferência de papel já configurada na
    # impressora. Os demais backends (Ghostscript, Win32 DEVMODE, Win32 avançada
    # e XPS) definem o papel por JOB, então não precisam dessa validação.
    if get_print_backend() != 'pdftoprinter':
        return True
    return is_papersize_a4(printer_name, paper_size)


def get_printer_paper_error_message(paper_size, wording='configurado'):
    return (
        f'Impressora não está definida com papel {wording} no produto: {paper_size}\n'
        f'Informar Equipe de Suporte'
    )


def finish_print_job(pdf_data, files_to_move, is_remake, printer_name, exe_index=None, paper_size='9',
                   requires_duplex=False, orientation=ORIENTATION_PORTRAIT):
    """
    Imprime ou abre o PDF unificado e arquiva os CSVs de origem.
    pdf_data: bytes do PDF gerado em memória; grava temp efêmero só para impressão/visualizador.
    """
    temp_path = write_temp_pdf(pdf_data)
    defer_remove = False
    product_hint = (
        '; '.join(os.path.basename(f) for f in files_to_move)
        if files_to_move else None
    )
    backend = get_print_backend()
    try:
        if printer_name == 'Criar PDF':
            open_path(temp_path)
            defer_remove = True
            audit.log_print(
                printer='Criar PDF', success=True, action='create_pdf',
                product=product_hint,
            )
        else:
            if requires_duplex and backend == 'pdftoprinter':
                raise Exception(
                    'PDFtoPrinter não suporta impressão duplex por job. '
                    'Use Ghostscript ou Win32 DEVMODE nas configurações.'
                )
            if orientation == ORIENTATION_LANDSCAPE and backend == 'pdftoprinter':
                raise Exception(
                    'PDFtoPrinter não suporta orientação paisagem por job. '
                    'Use Ghostscript ou Win32 DEVMODE nas configurações.'
                )
            duplex_mode = DUPLEX_LONG_EDGE if requires_duplex else DUPLEX_SIMPLEX
            print_pdf_file(
                os.path.abspath(temp_path),
                printer_name,
                exe_index=exe_index,
                paper_size=paper_size,
                backend=backend,
                config=runtime.context.config,
                duplex=duplex_mode,
                orientation=orientation or ORIENTATION_PORTRAIT,
            )
            audit.log_print(
                printer=printer_name, success=True, backend=backend,
                paper_size=paper_size, product=product_hint,
            )

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
        if printer_name != 'Criar PDF':
            audit.log_print(
                printer=printer_name, success=False, backend=backend,
                paper_size=paper_size, product=product_hint,
                detail=traceback.format_exc(),
            )
        remove_temp_pdf(temp_path)
        raise
    else:
        if defer_remove:
            Thread(target=_delayed_remove_temp_pdf, args=(temp_path,), daemon=True).start()
        else:
            remove_temp_pdf(temp_path)


def print_document(pdf_path, printer_name, exe_index, paper_size='9'):
    """Triggers physical printing of a unified batch PDF file."""
    print_pdf_file(
        pdf_path,
        printer_name,
        exe_index=exe_index,
        paper_size=paper_size,
        backend=get_print_backend(),
        config=runtime.context.config,
    )


def configure_printer_settings(printer_name, paper_size):
    """Validates if the target printer matches the required paper specifications."""
    return validate_printer_paper(printer_name, paper_size)
