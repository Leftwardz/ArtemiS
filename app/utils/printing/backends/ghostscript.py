"""Backend Ghostscript (mantém o comportamento atual do dispositivo mswinpr2).

Comando base preservado de printer_handler._print_via_ghostscript:
    gswin64c -dNOPAUSE -dBATCH -dQUIET -sDEVICE=mswinpr2
             -sOutputFile=%printer%<impressora> [-sPAPERSIZE=<gs>] <pdf>

Extensões opcionais (só entram quando o job pede algo diferente do default,
preservando 100% o comportamento atual quando os defaults são usados):
- cópias  -> -dNumCopies=<n>
- duplex  -> -dDuplex / -dTumble  (suportado pelo mswinpr2 via DEVMODE interno)

Paisagem: o mswinpr2 não controla dmOrientation por job (limitação do
dispositivo Ghostscript no Windows). Jobs em paisagem usam DEVMODE+GDI, o
mesmo caminho do backend Win32 DEVMODE — que o driver respeita.

Etiquetas com dimensões custom (mm) também usam DEVMODE+GDI em retrato, com
dmPaperWidth/dmPaperLength no DEVMODE do job.
"""

import os

from app.utils.subprocess_hidden import run_hidden

from app.utils.ghostscript_paths import (
    ghostscript_bin_dir,
    ghostscript_env,
    ghostscript_is_available,
    resolve_ghostscript_exe,
)
from app.utils.paper_size_map import paper_size_to_ghostscript
from app.utils.printing.base import (
    DUPLEX_LONG_EDGE,
    DUPLEX_SHORT_EDGE,
    ORIENTATION_LANDSCAPE,
    PrintBackend,
    PrintJob,
    PrintResult,
)


def uses_devmode_gdi_for_job(job: PrintJob) -> bool:
    """True when the job must use DEVMODE+GDI instead of mswinpr2."""
    if job.orientation == ORIENTATION_LANDSCAPE:
        return True
    try:
        width_mm = float(job.paper_width_mm)
        height_mm = float(job.paper_height_mm)
    except (TypeError, ValueError):
        return False
    return width_mm > 0 and height_mm > 0


def build_ghostscript_command(gs_exe: str, job: PrintJob) -> list[str]:
    """Monta a linha de comando mswinpr2 (somente retrato)."""
    output = f'%printer%{job.printer}'
    command = [
        gs_exe,
        '-dNOPAUSE', '-dBATCH', '-dQUIET',
        '-sDEVICE=mswinpr2',
        f'-sOutputFile={output}',
    ]

    gs_paper = paper_size_to_ghostscript(job.paper_size)
    if gs_paper:
        command.append(f'-sPAPERSIZE={gs_paper}')

    if job.copies and int(job.copies) > 1:
        command.append(f'-dNumCopies={int(job.copies)}')
    if job.duplex in (DUPLEX_LONG_EDGE, DUPLEX_SHORT_EDGE):
        command.append('-dDuplex')
        command.append('-dTumble' if job.duplex == DUPLEX_SHORT_EDGE else '-dTumble=false')

    command.append(job.pdf_path)
    return command


def _gdi_available() -> bool:
    try:
        import win32gui  # noqa: F401
        import win32print  # noqa: F401
        import win32ui  # noqa: F401
        from PIL import ImageWin  # noqa: F401
        return True
    except Exception:
        return False


class GhostscriptBackend(PrintBackend):
    name = 'ghostscript'
    label = 'Ghostscript'
    experimental = False

    def is_available(self) -> bool:
        try:
            return ghostscript_is_available()
        except Exception:
            return False

    def print_job(self, job: PrintJob) -> PrintResult:
        from app.utils.printing.logger import get_print_logger
        log = get_print_logger()

        if uses_devmode_gdi_for_job(job):
            return self._print_landscape(job, log)

        config = job.config
        gs_exe = resolve_ghostscript_exe(config)
        env = ghostscript_env(config)
        bin_dir = ghostscript_bin_dir()
        command = build_ghostscript_command(gs_exe, job)

        if job.tray is not None:
            log.warning('Ghostscript/mswinpr2 não controla bandeja por job; ignorando tray=%s', job.tray)

        log.info('comando Ghostscript: %s', command)
        log.info('Ghostscript cwd=%s GS_LIB=%s', bin_dir, env.get('GS_LIB'))
        try:
            result = run_hidden(
                command,
                env=env,
                capture_output=True,
                text=True,
                cwd=bin_dir,
            )
        except Exception as exc:
            return PrintResult.failure(self.name, f'Falha ao iniciar Ghostscript: {exc}', detail=repr(exc))

        if result.returncode != 0:
            detail = (result.stderr or result.stdout or '').strip()
            return PrintResult.failure(
                self.name,
                'Erro ao imprimir via Ghostscript.',
                detail=detail,
            )

        return PrintResult.success(self.name, message='Enviado via Ghostscript')

    def _print_landscape(self, job: PrintJob, log) -> PrintResult:
        if not _gdi_available():
            return PrintResult.failure(
                self.name,
                'Orientação paisagem exige pywin32 (DEVMODE+GDI). '
                'Use o motor Win32 DEVMODE nas configurações.',
            )
        log.info(
            'DEVMODE+GDI: mswinpr2 não cobre este job (paisagem ou etiqueta custom); '
            'raster GS + GDI com dmPaperWidth/dmPaperLength',
        )
        try:
            from app.utils.printing.devmode_gdi_print import print_job_via_devmode_gdi
            pages = print_job_via_devmode_gdi(job, log=log)
        except Exception as exc:
            return PrintResult.failure(
                self.name,
                f'Erro ao imprimir paisagem via DEVMODE+GDI: {exc}',
                detail=repr(exc),
            )
        return PrintResult.success(
            self.name,
            message=f'Enviado via Ghostscript (paisagem, {pages} pág.)',
        )
