"""Backend Ghostscript (mantém o comportamento atual do dispositivo mswinpr2).

Comando base preservado de printer_handler._print_via_ghostscript:
    gswin64c -dNOPAUSE -dBATCH -dQUIET -sDEVICE=mswinpr2
             -sOutputFile=%printer%<impressora> [-sPAPERSIZE=<gs>] <pdf>

Extensões opcionais (só entram quando o job pede algo diferente do default,
preservando 100% o comportamento atual quando os defaults são usados):
- cópias  -> -dNumCopies=<n>
- duplex  -> -dDuplex / -dTumble  (suportado pelo mswinpr2 via DEVMODE interno)
Nenhuma dessas opções altera a configuração permanente da impressora; valem
apenas para o processo do Ghostscript (ou seja, só para o JOB).
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
    PrintBackend,
    PrintJob,
    PrintResult,
)


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

        config = job.config
        gs_exe = resolve_ghostscript_exe(config)
        env = ghostscript_env(config)
        output = f'%printer%{job.printer}'

        # Comando base idêntico ao histórico.
        command = [
            gs_exe,
            '-dNOPAUSE', '-dBATCH', '-dQUIET',
            '-sDEVICE=mswinpr2',
            f'-sOutputFile={output}',
        ]

        gs_paper = paper_size_to_ghostscript(job.paper_size)
        if gs_paper:
            command.append(f'-sPAPERSIZE={gs_paper}')

        # Extensões opcionais — só anexadas quando diferem do default.
        if job.copies and int(job.copies) > 1:
            command.append(f'-dNumCopies={int(job.copies)}')
        if job.duplex in (DUPLEX_LONG_EDGE, DUPLEX_SHORT_EDGE):
            command.append('-dDuplex')
            command.append('-dTumble' if job.duplex == DUPLEX_SHORT_EDGE else '-dTumble=false')

        command.append(job.pdf_path)

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
