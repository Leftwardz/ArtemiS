"""Acesso sqlite3 puro aos bancos de auditoria (local e central).

Cada conexão é criada e usada por UMA thread (sqlite3 não compartilha conexão
entre threads). Pragmas escolhidos por contexto:
- local:   WAL + busy_timeout curto (disco local, escritor único = worker).
- central: DELETE (WAL é inseguro em SMB) + busy_timeout alto (rede, vários PCs).
"""

import sqlite3

from app.audit.schema import EVENT_COLUMNS, SCHEMA_SQL

_INSERT_SQL = (
    f"INSERT OR IGNORE INTO audit_events ({', '.join(EVENT_COLUMNS)}) "
    f"VALUES ({', '.join('?' for _ in EVENT_COLUMNS)})"
)


def connect(path, central=False):
    conn = sqlite3.connect(path, timeout=30 if central else 5)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    try:
        cur.execute('PRAGMA journal_mode=DELETE' if central else 'PRAGMA journal_mode=WAL')
        cur.execute(f'PRAGMA busy_timeout={30000 if central else 5000}')
        cur.execute('PRAGMA synchronous=NORMAL')
    except sqlite3.Error:
        pass
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn


def _row_values(event):
    return tuple(event.get(col) for col in EVENT_COLUMNS)


def insert_event(conn, event):
    conn.execute(_INSERT_SQL, _row_values(event))


def insert_many(conn, events):
    conn.executemany(_INSERT_SQL, [_row_values(e) for e in events])


def fetch_unsynced(conn, limit=500):
    cur = conn.execute(
        'SELECT * FROM audit_events WHERE synced = 0 ORDER BY ts_utc LIMIT ?',
        (limit,),
    )
    return [dict(row) for row in cur.fetchall()]


def mark_synced(conn, ids):
    if not ids:
        return
    placeholders = ', '.join('?' for _ in ids)
    conn.execute(
        f'UPDATE audit_events SET synced = 1 WHERE id IN ({placeholders})',
        tuple(ids),
    )


def prune_before(conn, before_iso_utc, synced_only=False):
    if synced_only:
        conn.execute(
            'DELETE FROM audit_events WHERE synced = 1 AND ts_utc < ?',
            (before_iso_utc,),
        )
    else:
        conn.execute('DELETE FROM audit_events WHERE ts_utc < ?', (before_iso_utc,))


def query_events(conn, *, ts_from=None, ts_to=None, local_from=None, local_to=None,
                 user=None, printer=None, product=None, category=None,
                 success=None, limit=500):
    """Consulta para a tela de auditoria (filtros opcionais)."""
    clauses = []
    params = []
    if ts_from:
        clauses.append('ts_utc >= ?')
        params.append(ts_from)
    if ts_to:
        clauses.append('ts_utc <= ?')
        params.append(ts_to)
    if local_from:
        clauses.append('ts_local >= ?')
        params.append(local_from)
    if local_to:
        clauses.append('ts_local <= ?')
        params.append(local_to)
    if user:
        clauses.append('windows_user LIKE ?')
        params.append(f'%{user}%')
    if printer:
        clauses.append('printer LIKE ?')
        params.append(f'%{printer}%')
    if product:
        clauses.append('product LIKE ?')
        params.append(f'%{product}%')
    if category:
        clauses.append('category = ?')
        params.append(category)
    if success is not None:
        clauses.append('success = ?')
        params.append(1 if success else 0)

    where = (' WHERE ' + ' AND '.join(clauses)) if clauses else ''
    sql = (
        'SELECT ts_local, ts_utc, pc_name, windows_user, category, action, '
        'printer, product, backend, paper_size, copies, success, detail '
        f'FROM audit_events{where} ORDER BY ts_utc DESC LIMIT ?'
    )
    params.append(int(limit))
    cur = conn.execute(sql, tuple(params))
    return [dict(row) for row in cur.fetchall()]
