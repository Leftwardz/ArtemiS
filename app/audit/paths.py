"""Resolução dos caminhos dos bancos de auditoria (local e central).

- LOCAL: sempre em disco local do PC (%LOCALAPPDATA%\\ArtemiS\\audit). É a
  fonte da verdade até o flush; nunca depende de rede.
- CENTRAL: store derivado na rede (para a visão global). Por padrão fica na
  mesma pasta do banco de produção; pode ser sobrescrito em config.json
  (audit_central_location).
"""

import os


def _local_dir():
    base = os.environ.get('LOCALAPPDATA') or os.path.expanduser('~')
    path = os.path.join(base, 'ArtemiS', 'audit')
    os.makedirs(path, exist_ok=True)
    return path


def local_audit_db_path():
    return os.path.join(_local_dir(), 'audit_local.db')


def local_audit_jsonl_path():
    """Fallback de último recurso quando nem o SQLite local grava."""
    return os.path.join(_local_dir(), 'audit_fallback.jsonl')


def central_audit_db_path(config=None):
    config = config or {}
    override = (config.get('audit_central_location') or '').strip()
    if override:
        return override

    db_location = config.get('database_location', 'database.db')
    folder = os.path.dirname(os.path.abspath(db_location))
    return os.path.join(folder, 'artemis_audit_central.db')
