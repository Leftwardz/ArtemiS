"""Backend Win32 + DEVMODE por JOB (experimental).

Estratégia:
1. Monta um DEVMODE só para este job (papel/cópias/duplex/orientação/bandeja),
   validado via DocumentProperties — sem gravar na impressora (sem admin).
2. Como win32print/GDI não renderiza PDF, rasteriza as páginas via Ghostscript.
3. Cria um DC com o DEVMODE (CreateDC) e desenha as páginas (GDI).

Vantagens: controle real de duplex/cópias/orientação/papel/bandeja por job.
Limitação: saída rasterizada (depende do Ghostscript p/ rasterizar).
"""

from app.utils.ghostscript_paths import ghostscript_is_available
from app.utils.printing.base import PrintBackend, PrintJob, PrintResult
from app.utils.printing.devmode import build_job_devmode, describe_devmode
from app.utils.printing.gdi_print import print_images_via_gdi
from app.utils.printing.pdf_raster import DEFAULT_DPI, rasterize_pdf


class Win32DevmodeBackend(PrintBackend):
    name = 'win32_devmode'
    label = 'Win32 DEVMODE (experimental)'
    experimental = True

    def is_available(self) -> bool:
        try:
            import win32gui  # noqa: F401
            import win32print  # noqa: F401
            import win32ui  # noqa: F401
            from PIL import ImageWin  # noqa: F401
        except Exception:
            return False
        # Depende do Ghostscript apenas para rasterizar o PDF.
        try:
            return ghostscript_is_available()
        except Exception:
            return False

    def print_job(self, job: PrintJob) -> PrintResult:
        from app.utils.printing.logger import get_print_logger
        log = get_print_logger()

        dpi = DEFAULT_DPI
        if job.config:
            dpi = int(job.config.get('win32_raster_dpi', DEFAULT_DPI) or DEFAULT_DPI)

        try:
            devmode, applied = build_job_devmode(job.printer, job)
        except Exception as exc:
            return PrintResult.failure(
                self.name, f'Falha ao montar DEVMODE: {exc}', detail=repr(exc),
            )

        log.info('DEVMODE aplicado: %s', applied)
        log.debug('DEVMODE final: %s', describe_devmode(devmode))

        try:
            with rasterize_pdf(job.pdf_path, dpi=dpi, config=job.config) as raster:
                log.info('rasterizado em %d página(s) @ %d DPI', len(raster.image_paths), dpi)
                pages = print_images_via_gdi(
                    job.printer, devmode, raster.image_paths,
                    doc_title='Impressão de AR',
                )
        except Exception as exc:
            return PrintResult.failure(
                self.name, f'Erro na impressão GDI: {exc}', detail=repr(exc),
            )

        return PrintResult.success(
            self.name, message=f'Enviado via Win32 DEVMODE ({pages} pág.)',
        )
