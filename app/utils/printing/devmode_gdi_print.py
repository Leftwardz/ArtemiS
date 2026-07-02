"""Impressão por job via DEVMODE + rasterização Ghostscript + GDI.

Caminho compartilhado pelos backends Win32 DEVMODE e Ghostscript (paisagem).
O dispositivo mswinpr2 não controla orientação física da impressora por job;
o DEVMODE (dmOrientation) sim.
"""

from app.utils.printing.devmode import build_job_devmode, describe_devmode
from app.utils.printing.gdi_print import print_images_via_gdi
from app.utils.printing.pdf_raster import DEFAULT_DPI, rasterize_pdf


def resolve_raster_dpi(config) -> int:
    if not config:
        return DEFAULT_DPI
    return int(config.get('win32_raster_dpi', DEFAULT_DPI) or DEFAULT_DPI)


def print_job_via_devmode_gdi(job, log=None):
    """Rasteriza o PDF e imprime com DEVMODE do job. Retorna nº de páginas."""
    dpi = resolve_raster_dpi(job.config)
    devmode, applied = build_job_devmode(job.printer, job)
    if log:
        log.info('DEVMODE aplicado: %s', applied)
        log.debug('DEVMODE final: %s', describe_devmode(devmode))

    with rasterize_pdf(job.pdf_path, dpi=dpi, config=job.config) as raster:
        if log:
            log.info('rasterizado em %d página(s) @ %d DPI', len(raster.image_paths), dpi)
        return print_images_via_gdi(
            job.printer,
            devmode,
            raster.image_paths,
            doc_title='Impressão de AR',
        )
