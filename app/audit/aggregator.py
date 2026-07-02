"""Aggregator: copia eventos do SQLite local para o SQLite central (rede).

- Roda em thread daemon própria; toda I/O de rede acontece aqui (fora do
  caminho de impressão).
- Flush em lote: lê linhas não sincronizadas do local, INSERT OR IGNORE no
  central (idempotente por uuid), marca como sincronizadas no local.
- Tolerante a falha de rede: se o central estiver indisponível, não marca como
  sincronizado e tenta de novo no próximo ciclo.
- Faz prune por retenção no central e remove cópias locais já sincronizadas e
  antigas (mantém o local enxuto sem perder a fonte da verdade recente).
"""

import threading
from datetime import datetime, timedelta, timezone

from app.audit import store

_LOCAL_KEEP_DAYS = 14  # mantém cópia local de itens já sincronizados por N dias


class Aggregator:
    def __init__(self, local_db_path, central_db_path, interval_seconds, retention_days):
        self._local_db_path = local_db_path
        self._central_db_path = central_db_path
        self._interval = max(15, int(interval_seconds))
        self._retention_days = max(1, int(retention_days))
        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        if self._thread is not None:
            return
        self._thread = threading.Thread(
            target=self._run, name='AuditAggregator', daemon=True,
        )
        self._thread.start()

    def stop(self, timeout=10):
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)

    def _run(self):
        # primeiro flush logo após o intervalo inicial curto
        while not self._stop_event.wait(self._interval):
            self.flush_once()

    def flush_once(self):
        """Executa um ciclo de flush+prune. Nunca levanta exceção."""
        local = None
        central = None
        try:
            local = store.connect(self._local_db_path)
        except Exception:
            return
        try:
            central = store.connect(self._central_db_path, central=True)
        except Exception:
            # rede indisponível: tenta no próximo ciclo, dados seguem locais.
            try:
                local.close()
            except Exception:
                pass
            return

        try:
            rows = store.fetch_unsynced(local, limit=500)
            while rows:
                store.insert_many(central, rows)
                central.commit()
                store.mark_synced(local, [r['id'] for r in rows])
                local.commit()
                rows = store.fetch_unsynced(local, limit=500)

            now = datetime.now(timezone.utc)
            central_cutoff = (now - timedelta(days=self._retention_days)).isoformat()
            local_cutoff = (now - timedelta(days=_LOCAL_KEEP_DAYS)).isoformat()
            store.prune_before(central, central_cutoff)
            central.commit()
            store.prune_before(local, local_cutoff, synced_only=True)
            local.commit()
        except Exception:
            # qualquer erro: aborta o ciclo silenciosamente (best-effort).
            pass
        finally:
            for conn in (central, local):
                try:
                    if conn is not None:
                        conn.close()
                except Exception:
                    pass
