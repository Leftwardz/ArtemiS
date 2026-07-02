"""Módulo de auditoria do ArtemiS (local-first, agregação central, best-effort).

API pública:
    init_audit(config)        # inicia worker + aggregator (chamar no bootstrap)
    shutdown_audit()          # drena fila, flush final e encerra threads
    log_print(...)            # evento de impressão (sucesso/falha)
    log_cadastro(...)         # alteração de cadastro (cliente/produto/layout/impressora/acesso)
    log_error(...)            # erro do sistema
    query_events(...)         # consulta o banco central (tela de auditoria)

Princípios:
- Nada aqui pode quebrar o app nem atrasar a impressão. Toda função pública é
  blindada por try/except e a gravação é assíncrona.
- Não toca no banco de produção: usa arquivos e conexões próprios.
"""

import atexit
import os
import socket
import uuid
from datetime import datetime, timezone

from app.audit import paths, store
from app.audit.aggregator import Aggregator
from app.audit.logger import AuditLogger
from app.audit.schema import (
    CATEGORIES,
    DEFAULT_FLUSH_INTERVAL_SECONDS,
    DEFAULT_RETENTION_DAYS,
    DETAIL_MAX_CHARS,
)

_state = {
    'enabled': False,
    'logger': None,
    'aggregator': None,
    'pc_name': None,
    'user': None,
    'app_version': None,
    'config': None,
}


def _safe_pc_name():
    return os.environ.get('COMPUTERNAME') or socket.gethostname() or 'desconhecido'


def _safe_user():
    try:
        from app.utils import windows_auth
        return windows_auth.get_current_principal()
    except Exception:
        return os.environ.get('USERNAME', '')


def init_audit(config=None):
    """Inicializa a auditoria. Seguro chamar mais de uma vez."""
    if _state['enabled']:
        return
    try:
        config = config or {}
        if config.get('audit_enabled') is False:
            return

        _state['config'] = config
        _state['pc_name'] = _safe_pc_name()
        _state['user'] = _safe_user()
        _state['app_version'] = config.get('app_version')

        logger = AuditLogger(
            paths.local_audit_db_path(),
            paths.local_audit_jsonl_path(),
        )
        logger.start()

        aggregator = Aggregator(
            paths.local_audit_db_path(),
            paths.central_audit_db_path(config),
            int(config.get('audit_flush_interval_seconds', DEFAULT_FLUSH_INTERVAL_SECONDS)),
            int(config.get('audit_retention_days', DEFAULT_RETENTION_DAYS)),
        )
        # empurra o que ficou da sessão anterior antes de iniciar o ciclo
        aggregator.flush_once()
        aggregator.start()

        _state['logger'] = logger
        _state['aggregator'] = aggregator
        _state['enabled'] = True
        atexit.register(shutdown_audit)
    except Exception:
        # Nunca propaga: auditoria indisponível não pode impedir o app.
        _state['enabled'] = False


def shutdown_audit():
    if not _state['enabled']:
        return
    _state['enabled'] = False
    logger = _state.get('logger')
    aggregator = _state.get('aggregator')
    try:
        if logger is not None:
            logger.stop()           # drena a fila para o SQLite local
        if aggregator is not None:
            aggregator.flush_once()  # flush final local -> central
            aggregator.stop()
    except Exception:
        pass


def _truncate(text):
    if text is None:
        return None
    text = str(text)
    return text if len(text) <= DETAIL_MAX_CHARS else text[:DETAIL_MAX_CHARS] + '…'


def _emit(category, action, **fields):
    logger = _state.get('logger')
    if not _state['enabled'] or logger is None:
        return
    try:
        now = datetime.now(timezone.utc)
        event = {
            'id': uuid.uuid4().hex,
            'ts_utc': now.isoformat(),
            'ts_local': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'pc_name': _state['pc_name'],
            'windows_user': _state['user'],
            'category': category,
            'action': action,
            'printer': fields.get('printer'),
            'product': fields.get('product'),
            'backend': fields.get('backend'),
            'paper_size': (str(fields['paper_size']) if fields.get('paper_size') is not None else None),
            'copies': fields.get('copies'),
            'success': fields.get('success'),
            'detail': _truncate(fields.get('detail')),
            'app_version': _state.get('app_version'),
        }
        logger.enqueue(event)
    except Exception:
        pass


def log_print(printer, success, backend=None, paper_size=None, copies=None,
              product=None, detail=None, action=None):
    if action is None:
        action = 'print_success' if success else 'print_failure'
    _emit(
        'print', action,
        printer=printer, backend=backend, paper_size=paper_size,
        copies=copies, product=product,
        success=1 if success else 0, detail=detail,
    )


def log_cadastro(action, detail=None, printer=None):
    _emit('cadastro', action, detail=detail, printer=printer)


def log_error(detail, action='error', printer=None):
    _emit('error', action, success=0, detail=detail, printer=printer)


def query_events(**filters):
    """Consulta o banco central para a tela de auditoria. Retorna lista (pode
    ser vazia). Nunca levanta exceção."""
    conn = None
    try:
        central_path = paths.central_audit_db_path(_state.get('config') or {})
        conn = store.connect(central_path, central=True)
        return store.query_events(conn, **filters)
    except Exception:
        return []
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


__all__ = [
    'CATEGORIES',
    'init_audit', 'shutdown_audit',
    'log_print', 'log_cadastro', 'log_error',
    'query_events',
]
