"""Backend PDFtoPrinter (comportamento idêntico ao histórico do projeto).

Mantém EXATAMENTE o mesmo comando usado antes da abstração:
    PDFtoPrinter_N.exe focus="Impressão de AR" <impressora> <pdf>

Limitações conhecidas (registradas em log, não falham o job):
- Não controla cópias, duplex, orientação, bandeja nem tamanho de papel.
  O papel depende da preferência da impressora (validada à parte por
  print_service.validate_printer_paper).
"""

import subprocess

from app.utils.printing.base import PrintBackend, PrintJob, PrintResult

# Lista preservada de printer_handler.PDFTOPRINTER_EXECUTABLES.
PDFTOPRINTER_EXECUTABLES = (
    'PDFtoPrinter.exe',
    'PDFtoPrinter_2.exe',
    'PDFtoPrinter_3.exe',
    'PDFtoPrinter_4.exe',
    'PDFtoPrinter_5.exe',
)


class PdfToPrinterBackend(PrintBackend):
    name = 'pdftoprinter'
    label = 'PDFtoPrinter'
    experimental = False

    def is_available(self) -> bool:
        return True

    def print_job(self, job: PrintJob) -> PrintResult:
        from app.utils.printing.logger import get_print_logger
        log = get_print_logger()

        ignored = [p for p, used in (
            ('copies', job.copies != 1),
            ('duplex', job.duplex != 'simplex'),
            ('orientation', job.orientation != 'portrait'),
            ('tray', job.tray is not None),
        ) if used]
        if ignored:
            log.warning('PDFtoPrinter ignora parâmetros: %s', ', '.join(ignored))

        exe_index = job.slot_index if job.slot_index is not None else 0
        try:
            executable = PDFTOPRINTER_EXECUTABLES[exe_index]
        except IndexError:
            executable = PDFTOPRINTER_EXECUTABLES[0]

        command = [executable, 'focus="Impressão de AR"', job.printer, job.pdf_path]
        log.info('comando PDFtoPrinter: %s', command)
        try:
            subprocess.call(command, shell=True)
        except subprocess.CalledProcessError as exc:
            return PrintResult.failure(
                self.name,
                'Erro ao enviar arquivo para a impressora',
                detail=str(exc),
            )
        except Exception as exc:
            return PrintResult.failure(self.name, str(exc), detail=repr(exc))

        return PrintResult.success(self.name, message='Enviado via PDFtoPrinter')
