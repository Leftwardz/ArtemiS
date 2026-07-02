"""Registro de backends, disponibilidade e dispatch com logging.

- O import de cada backend é protegido: um backend que falhe ao importar
  (dependência ausente, etc.) é apenas ignorado — o app NUNCA quebra por isso.
- dispatch() registra backend escolhido, parâmetros, sucesso/falha e detalhes
  de erro do driver/spooler, e devolve sempre um PrintResult.
"""

from app.utils.printing.base import PrintBackend, PrintJob, PrintResult
from app.utils.printing.logger import get_print_logger

# Ordem de exibição na UI. (name, dotted_path, ClassName)
_BACKEND_SPECS = (
    ('pdftoprinter', 'app.utils.printing.backends.pdftoprinter', 'PdfToPrinterBackend'),
    ('ghostscript', 'app.utils.printing.backends.ghostscript', 'GhostscriptBackend'),
    ('win32_devmode', 'app.utils.printing.backends.win32_devmode', 'Win32DevmodeBackend'),
    ('win32_advanced', 'app.utils.printing.backends.win32_advanced', 'Win32AdvancedBackend'),
    ('xps', 'app.utils.printing.backends.xps', 'XpsBackend'),
)

_registry = None


def _build_registry():
    import importlib

    registry = {}
    log = get_print_logger()
    for name, module_path, class_name in _BACKEND_SPECS:
        try:
            module = importlib.import_module(module_path)
            backend_cls = getattr(module, class_name)
            instance = backend_cls()
            registry[name] = instance
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
    for name, _module_path, _class_name in _BACKEND_SPECS:
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
