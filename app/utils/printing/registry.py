"""Registro de backends, disponibilidade e dispatch com logging.

- O import de cada backend é protegido: um backend que falhe ao importar
  (dependência ausente, etc.) é apenas ignorado — o app NUNCA quebra por isso.
- dispatch() registra backend escolhido, parâmetros, sucesso/falha e detalhes
  de erro do driver/spooler, e devolve sempre um PrintResult.
"""

from app.utils.printing.base import PrintBackend, PrintJob, PrintResult
from app.utils.printing.logger import get_print_logger

# Imports estáticos: PyInstaller não rastreia importlib.import_module em runtime.
_BACKEND_CLASSES: dict[str, type] = {}
try:
    from app.utils.printing.backends.pdftoprinter import PdfToPrinterBackend
    _BACKEND_CLASSES['pdftoprinter'] = PdfToPrinterBackend
except Exception:
    pass
try:
    from app.utils.printing.backends.ghostscript import GhostscriptBackend
    _BACKEND_CLASSES['ghostscript'] = GhostscriptBackend
except Exception:
    pass
try:
    from app.utils.printing.backends.win32_devmode import Win32DevmodeBackend
    _BACKEND_CLASSES['win32_devmode'] = Win32DevmodeBackend
except Exception:
    pass
try:
    from app.utils.printing.backends.win32_advanced import Win32AdvancedBackend
    _BACKEND_CLASSES['win32_advanced'] = Win32AdvancedBackend
except Exception:
    pass
try:
    from app.utils.printing.backends.xps import XpsBackend
    _BACKEND_CLASSES['xps'] = XpsBackend
except Exception:
    pass

# Ordem de exibição na UI.
_BACKEND_ORDER = (
    'pdftoprinter',
    'ghostscript',
    'win32_devmode',
    'win32_advanced',
    'xps',
)
_BACKEND_SPECS = tuple(
    (name, cls.__module__, cls.__name__)
    for name in _BACKEND_ORDER
    if (cls := _BACKEND_CLASSES.get(name)) is not None
)

_registry = None


def _build_registry():
    registry = {}
    log = get_print_logger()
    for name in _BACKEND_ORDER:
        backend_cls = _BACKEND_CLASSES.get(name)
        if backend_cls is None:
            continue
        try:
            registry[name] = backend_cls()
        except Exception as exc:  # pragma: no cover - depende do ambiente
            log.warning('backend %s indisponível para carregar: %r', name, exc)
    return registry


def _get_registry():
    global _registry
    if _registry is None:
        _registry = _build_registry()
    return _registry


def get_backend(name) -> PrintBackend:
    """Retorna a instância do backend ou None."""
    return _get_registry().get(name)


def list_backends():
    """Lista [(name, label, available, experimental)] na ordem de exibição."""
    registry = _get_registry()
    items = []
    for name in _BACKEND_ORDER:
        backend = registry.get(name)
        if backend is None:
            continue
        try:
            available = backend.is_available()
        except Exception:
            available = False
        items.append((name, backend.label, available, backend.experimental))
    return items


def available_backends():
    """Apenas os nomes de backends disponíveis nesta máquina."""
    return [name for name, _label, available, _exp in list_backends() if available]


def dispatch(job: PrintJob, backend_name: str) -> PrintResult:
    """Executa o job no backend escolhido, com logging detalhado.

    Não levanta exceção: sempre retorna PrintResult. (O chamador decide se
    propaga o erro para a UI.)
    """
    log = get_print_logger()
    log.info('=== JOB backend=%s params=%s', backend_name, job.as_log_dict())

    backend = get_backend(backend_name)
    if backend is None:
        msg = f'Backend de impressão desconhecido/indisponível: {backend_name}'
        log.error(msg)
        return PrintResult.failure(backend_name, msg)

    try:
        if not backend.is_available():
            msg = f'Backend {backend_name} não está disponível nesta máquina.'
            if backend_name in ('ghostscript', 'win32_devmode', 'win32_advanced', 'xps'):
                from app.utils.ghostscript_paths import describe_ghostscript_paths
                log.error('Ghostscript paths: %s', describe_ghostscript_paths())
            log.error(msg)
            return PrintResult.failure(backend_name, msg)
    except Exception as exc:
        msg = f'Falha ao verificar disponibilidade de {backend_name}: {exc}'
        log.error(msg)
        return PrintResult.failure(backend_name, msg, detail=repr(exc))

    try:
        result = backend.print_job(job)
    except Exception as exc:  # rede de segurança: backend nunca deveria levantar
        log.exception('exceção inesperada no backend %s', backend_name)
        return PrintResult.failure(backend_name, f'Erro inesperado: {exc}', detail=repr(exc))

    if result.ok:
        log.info('RESULT ok backend=%s msg=%s', result.backend, result.message)
    else:
        log.error('RESULT fail backend=%s error=%s detail=%s',
                  result.backend, result.error, result.detail)
    return result
