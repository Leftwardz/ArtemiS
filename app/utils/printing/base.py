"""Contrato único de impressão: PrintJob, PrintResult e PrintBackend.

Todos os backends recebem exatamente os mesmos parâmetros (PrintJob) e
retornam o mesmo resultado (PrintResult). Nenhum backend deve alterar
configurações permanentes da impressora; mudanças valem só para o JOB.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

# Duplex (DMDUP_*): valores estáveis do Windows, independem do pywin32.
DUPLEX_SIMPLEX = 'simplex'
DUPLEX_LONG_EDGE = 'long_edge'    # virar pela borda longa (retrato) -> DMDUP_VERTICAL (2)
DUPLEX_SHORT_EDGE = 'short_edge'  # virar pela borda curta -> DMDUP_HORIZONTAL (3)

DUPLEX_TO_DMDUP = {
    DUPLEX_SIMPLEX: 1,
    DUPLEX_LONG_EDGE: 2,
    DUPLEX_SHORT_EDGE: 3,
}

ORIENTATION_PORTRAIT = 'portrait'
ORIENTATION_LANDSCAPE = 'landscape'

ORIENTATION_TO_DMORIENT = {
    ORIENTATION_PORTRAIT: 1,
    ORIENTATION_LANDSCAPE: 2,
}


@dataclass
class PrintJob:
    """Parâmetros de um job de impressão, idênticos para todos os backends.

    Observações importantes do projeto:
    - ``paper_size`` usa o MESMO código DMPAPER do Windows que o resto do app
      (ex.: ``'9'`` = A4). Confirmado por ``printer_handler.is_papersize_a4``.
    - ``orientation`` é a orientação física da impressora (portrait/landscape),
      NÃO a orientação do layout da etiqueta (``product.orientation``). O PDF já
      é gerado com a geometria correta, então o default é ``portrait``.
    - ``slot_index`` só é usado pelo backend PDFtoPrinter (escolhe qual dos N
      executáveis paralelos rodar). Demais backends ignoram.
    """

    pdf_path: str
    printer: str
    copies: int = 1
    duplex: str = DUPLEX_SIMPLEX
    orientation: str = ORIENTATION_PORTRAIT
    paper_size: str = '9'
    tray: Optional[int] = None          # None = bandeja default do driver
    slot_index: Optional[int] = None    # usado só pelo PDFtoPrinter
    config: Optional[dict] = field(default=None)

    def as_log_dict(self) -> dict:
        return {
            'printer': self.printer,
            'copies': self.copies,
            'duplex': self.duplex,
            'orientation': self.orientation,
            'paper_size': self.paper_size,
            'tray': self.tray if self.tray is not None else 'auto',
            'slot_index': self.slot_index,
            'pdf_path': self.pdf_path,
        }


@dataclass
class PrintResult:
    ok: bool
    backend: str
    message: str = ''
    error: str = ''
    detail: str = ''   # stderr/stdout do GS, erro de driver/spooler, etc.

    @classmethod
    def success(cls, backend: str, message: str = '', detail: str = '') -> 'PrintResult':
        return cls(ok=True, backend=backend, message=message, detail=detail)

    @classmethod
    def failure(cls, backend: str, error: str, detail: str = '') -> 'PrintResult':
        return cls(ok=False, backend=backend, error=error, detail=detail)


class PrintBackend(ABC):
    """Interface comum a todos os backends de impressão."""

    #: identificador estável usado em config.json (ex.: 'pdftoprinter')
    name: str = ''
    #: rótulo exibido na UI (ex.: 'PDFtoPrinter')
    label: str = ''
    #: True quando ainda em validação/comparação
    experimental: bool = False

    def is_available(self) -> bool:
        """Se o backend pode rodar nesta máquina. Nunca deve levantar exceção."""
        return True

    @abstractmethod
    def print_job(self, job: PrintJob) -> PrintResult:
        """Imprime o job. NÃO deve levantar exceção: captura tudo em PrintResult."""
        raise NotImplementedError
