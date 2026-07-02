"""AuditLogger assíncrono: fila + worker thread + fallback JSONL.

Garantias (best-effort):
- A chamada pública apenas enfileira (O(1)) e NUNCA bloqueia/levanta exceção,
  então o caminho de impressão jamais é afetado.
- O worker (único escritor do SQLite local) grava fora da thread da UI.
- Se o SQLite local falhar, cai para JSONL local; se isso falhar, descarta e
  apenas incrementa um contador interno.
"""

import json
import queue
import threading

from app.audit import store

_STOP = object()


class AuditLogger:
    def __init__(self, local_db_path, jsonl_path, max_queue=10000):
        self._local_db_path = local_db_path
        self._jsonl_path = jsonl_path
        self._queue = queue.Queue(maxsize=max_queue)
        self._thread = None
        self.dropped = 0

    def start(self):
        if self._thread is not None:
            return
        self._thread = threading.Thread(
            target=self._run, name='AuditLogger', daemon=True,
        )
        self._thread.start()

    def enqueue(self, event):
        try:
            self._queue.put_nowait(event)
        except queue.Full:
            self.dropped += 1

    def stop(self, timeout=5):
        if self._thread is None:
            return
        try:
            self._queue.put_nowait(_STOP)
        except queue.Full:
            # Fila cheia: força drenagem mínima sinalizando via put bloqueante curto.
            try:
                self._queue.put(_STOP, timeout=1)
            except Exception:
                return
        self._thread.join(timeout=timeout)

    def _run(self):
        conn = None
        try:
            conn = store.connect(self._local_db_path)
        except Exception:
            conn = None

        while True:
            item = self._queue.get()
            if item is _STOP:
                break
            self._write(conn, item)

        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass

    def _write(self, conn, event):
        try:
            if conn is None:
                raise RuntimeError('sem conexão local')
            store.insert_event(conn, event)
            conn.commit()
        except Exception:
            self._fallback(event)

    def _fallback(self, event):
        try:
            with open(self._jsonl_path, 'a', encoding='utf-8') as fh:
                fh.write(json.dumps(event, ensure_ascii=False) + '\n')
        except Exception:
            self.dropped += 1
