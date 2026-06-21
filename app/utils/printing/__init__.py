"""Camada de impressão desacoplada (múltiplos backends).

Ponto de entrada estável para o resto do app:

    from app.utils.printing import PrintJob, dispatch, available_backends

Cada backend implementa a mesma interface (PrintBackend) e recebe os mesmos
parâmetros (PrintJob). Backends indisponíveis no sistema são ignorados sem
quebrar a aplicação.
"""

from app.utils.printing.base import PrintBackend, PrintJob, PrintResult
from app.utils.printing.registry import (
    available_backends,
    dispatch,
    get_backend,
    list_backends,
)

__all__ = [
    'PrintBackend',
    'PrintJob',
    'PrintResult',
    'available_backends',
    'dispatch',
    'get_backend',
    'list_backends',
]
