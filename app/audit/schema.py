"""Esquema do banco de auditoria (idêntico no local e no central).

Usa sqlite3 puro (não o ORM de produção) para isolar 100% a auditoria do
banco compartilhado: arquivos próprios, conexões próprias, sem migração.
"""

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS audit_events (
    id           TEXT PRIMARY KEY,
    ts_utc       TEXT NOT NULL,
    ts_local     TEXT,
    pc_name      TEXT NOT NULL,
    windows_user TEXT,
    category     TEXT NOT NULL,
    action       TEXT NOT NULL,
    printer      TEXT,
    product      TEXT,
    backend      TEXT,
    paper_size   TEXT,
    copies       INTEGER,
    success      INTEGER,
    detail       TEXT,
    app_version  TEXT,
    synced       INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_audit_ts     ON audit_events (ts_utc);
CREATE INDEX IF NOT EXISTS ix_audit_user   ON audit_events (windows_user);
CREATE INDEX IF NOT EXISTS ix_audit_prn    ON audit_events (printer);
CREATE INDEX IF NOT EXISTS ix_audit_cat    ON audit_events (category);
CREATE INDEX IF NOT EXISTS ix_audit_synced ON audit_events (synced);
"""

# Colunas gravadas a partir do evento (na ordem do INSERT). `synced` é controle.
EVENT_COLUMNS = (
    'id', 'ts_utc', 'ts_local', 'pc_name', 'windows_user',
    'category', 'action', 'printer', 'product', 'backend',
    'paper_size', 'copies', 'success', 'detail', 'app_version',
)

CATEGORIES = ('print', 'config_access', 'cadastro', 'error')

DEFAULT_FLUSH_INTERVAL_SECONDS = 180
DEFAULT_RETENTION_DAYS = 180
DETAIL_MAX_CHARS = 2000
