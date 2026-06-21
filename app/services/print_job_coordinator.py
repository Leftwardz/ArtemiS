import os
from threading import Thread

from app.services.pdf_service import write_text_to_pdf


def pdf_output_folder(search_folder: str) -> str:
    return os.path.join(search_folder, 'PDFs')


def start_pdf_generation(
    items,
    files_lines,
    orientation_list,
    search_folder,
    is_remake,
    printer,
    on_progress,
    on_error,
    on_complete,
):
    """Inicia geração de PDF em thread separada (callbacks opcionais, sem Tkinter)."""
    folder_destination = pdf_output_folder(search_folder)
    thread = Thread(
        target=write_text_to_pdf,
        kwargs={
            'items': items,
            'files_lines': files_lines,
            'orientation_list': orientation_list,
            'path': folder_destination,
            'is_remake': is_remake,
            'printer': printer,
            'on_progress': on_progress,
            'on_error': on_error,
            'on_complete': on_complete,
        },
    )
    thread.start()
    return folder_destination
