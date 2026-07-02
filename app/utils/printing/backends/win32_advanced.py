"""Backend Win32 Print API avançada (experimental).

Diferença em relação ao win32_devmode:
- Consulta DeviceCapabilities antes de imprimir e LOGA o que a impressora
  suporta (duplex/cópias/papéis/bandejas), avisando quando o job pede algo
  não suportado (sem bloquear — apenas registra).
- Após enviar, lê o status dos jobs no spooler (EnumJobs) para capturar
  mensagens de erro do spooler no log.

Continua sem alterar configurações permanentes (DEVMODE por job + DC).
"""

from app.utils.ghostscript_paths import ghostscript_is_available
from app.utils.printing.base import (
    DUPLEX_SIMPLEX,
    PrintBackend,
    PrintJob,
    PrintResult,
)
from app.utils.printing.devmode import (
    build_job_devmode,
    describe_devmode,
    query_device_capabilities,
    read_recent_job_status,
)
from app.utils.printing.gdi_print import print_images_via_gdi
from app.utils.printing.pdf_raster import DEFAULT_DPI, rasterize_pdf


class Win32AdvancedBackend(PrintBackend):
    name = 'win32_advanced'
    label = 'Win32 Print API avançada (experimental)'
    experimental = True

    def is_available(self) -> bool:
        try:
            import win32gui  # noqa: F401
            import win32print  # noqa: F401
            import win32ui  # noqa: F401
            from PIL import ImageWin  # noqa: F401
        except Exception:
            return False
        try:
            return ghostscript_is_available()
        except Exception:
            return False

    def _log_capabilities(self, job, log):
        caps = query_device_capabilities(job.printer)
        log.info('capacidades da impressora: %s', caps)

        if job.duplex != DUPLEX_SIMPLEX and caps.get('duplex') is False:
            log.warning('impressora NÃO suporta duplex; o driver pode ignorar.')
        papers = caps.get('papers') or []
        try:
            paper_code = int(str(job.paper_size))
        except (TypeError, ValueError):
            paper_code = 0
        if paper_code and papers and paper_code not in papers:
            log.warning('papel %s não está na lista suportada %s.', paper_code, papers)
        if job.tray is not None:
            bins = caps.get('bins') or []
            if bins and int(job.tray) not in bins:
                log.warning('bandeja %s não está em %s.', job.tray, bins)

    def print_job(self, job: PrintJob) -> PrintResult:
        from app.utils.printing.logger import get_print_logger
        log = get_print_logger()

        dpi = DEFAULT_DPI
        if job.config:
            dpi = int(job.config.get('win32_raster_dpi', DEFAULT_DPI) or DEFAULT_DPI)

        try:
            self._log_capabilities(job, log)
        except Exception as exc:
            log.warning('falha ao consultar capacidades: %r', exc)

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
            try:
                log.error('status do spooler após falha: %s', read_recent_job_status(job.printer))
            except Exception:
                pass
            return PrintResult.failure(
                self.name, f'Erro na impressão GDI: {exc}', detail=repr(exc),
            )

        try:
            log.info('status do spooler: %s', read_recent_job_status(job.printer))
        except Exception:
            pass

        return PrintResult.success(
            self.name, message=f'Enviado via Win32 avançada ({pages} pág.)',
        )
