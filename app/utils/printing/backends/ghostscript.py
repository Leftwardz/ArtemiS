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
"""

import os
import subprocess

from app.utils.ghostscript_paths import (
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
    """True quando o job deve usar DEVMODE+GDI em vez de mswinpr2."""
    return job.orientation == ORIENTATION_LANDSCAPE


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
        command = build_ghostscript_command(gs_exe, job)

        if job.tray is not None:
            log.warning('Ghostscript/mswinpr2 não controla bandeja por job; ignorando tray=%s', job.tray)

        log.info('comando Ghostscript: %s', command)
        try:
            result = subprocess.run(
                command,
                env=env,
                capture_output=True,
                text=True,
                cwd=os.path.dirname(gs_exe) if os.path.isfile(gs_exe) else None,
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
            'paisagem: mswinpr2 não controla orientação por job; '
            'usando DEVMODE+GDI (Ghostscript rasteriza, GDI imprime)',
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
