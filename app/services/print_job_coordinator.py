from threading import Thread

from app.services.pdf_service import write_text_to_pdf


def start_pdf_generation(
    items,
    files_lines,
    orientation_list,
    is_remake,
    printer,
    on_progress,
    on_error,
    on_complete,
):
    """Inicia geração de PDF em thread separada (callbacks opcionais, sem Tkinter)."""
    thread = Thread(
        target=write_text_to_pdf,
        kwargs={
            'items': items,
            'files_lines': files_lines,
            'orientation_list': orientation_list,
            'is_remake': is_remake,
            'printer': printer,
            'on_progress': on_progress,
            'on_error': on_error,
            'on_complete': on_complete,
        },
    )
    thread.start()
