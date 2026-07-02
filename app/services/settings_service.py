"""Persistência de config.json e troca de banco."""

import json
import os
import sqlite3
import stat
from dataclasses import dataclass

from app import runtime
from app.i18n import get_i18n, reload_locales, set_language, t
from app.models.database_manager import DataBase

PRINT_BACKENDS = (
    'pdftoprinter',
    'ghostscript',
    'win32_devmode',
    'win32_advanced',
    'xps',
)
PRINT_BACKEND_LABELS = {
    'pdftoprinter': 'PDFtoPrinter',
    'ghostscript': 'Ghostscript',
    'win32_devmode': 'Win32 DEVMODE (experimental)',
    'win32_advanced': 'Win32 Print API avançada (experimental)',
    'xps': 'XPS Print API (experimental)',
}


@dataclass
class SettingsSaveResult:
    ok: bool
    message: str = ''
    error: str = ''


def get_search_folder():
    return runtime.context.config.get('search_folder', '')


def get_database_location():
    return runtime.context.config.get('database_location', '')


def get_audit_central_location():
    return runtime.context.config.get('audit_central_location', '')


def save_audit_central_location(path: str) -> SettingsSaveResult:
    """Salva o caminho do banco CENTRAL de logs (vazio = mesma pasta do Database)."""
    path = (path or '').strip()

    if path:
        parent = os.path.dirname(os.path.abspath(path))
        if parent and not os.path.exists(parent):
            return SettingsSaveResult(ok=False, error=t('settings.audit_folder_missing', path=parent))

    if runtime.context.config.get('audit_central_location', '') == path:
        return SettingsSaveResult(ok=True)

    runtime.context.config['audit_central_location'] = path
    try:
        with open('config.json', 'w') as configfile:
            json.dump(runtime.context.config, configfile, indent=4)
        return SettingsSaveResult(
            ok=True,
            message=t('settings.audit_saved'),
        )
    except Exception as e:
        return SettingsSaveResult(ok=False, error=t('settings.audit_save_error', error=e))


def get_print_backend():
    backend = runtime.context.config.get('print_backend', 'pdftoprinter')
    if backend not in PRINT_BACKENDS:
        return 'pdftoprinter'
    return backend


def get_print_backend_label():
    return PRINT_BACKEND_LABELS.get(get_print_backend(), 'PDFtoPrinter')


def save_print_backend(backend: str) -> SettingsSaveResult:
    if backend not in PRINT_BACKENDS:
        return SettingsSaveResult(ok=False, error=t('settings.invalid_backend'))

    from app.utils.printing.registry import get_backend
    backend_obj = get_backend(backend)
    if backend_obj is None or not backend_obj.is_available():
        hint = ''
        if backend in ('ghostscript', 'win32_devmode', 'win32_advanced', 'xps'):
            hint = t('settings.backend_hint')
        label = PRINT_BACKEND_LABELS.get(backend, backend)
        return SettingsSaveResult(
            ok=False,
            error=t('settings.backend_unavailable', label=label, hint=hint),
        )

    if runtime.context.config.get('print_backend') == backend:
        return SettingsSaveResult(ok=True)

    runtime.context.config['print_backend'] = backend
    try:
        with open('config.json', 'w') as configfile:
            json.dump(runtime.context.config, configfile, indent=4)
        label = PRINT_BACKEND_LABELS[backend]
        return SettingsSaveResult(ok=True, message=t('settings.backend_saved', label=label))
    except Exception as e:
        return SettingsSaveResult(ok=False, error=t('settings.save_error', error=e))


def save_search_folder(folder: str) -> SettingsSaveResult:
    if not os.path.exists(folder):
        return SettingsSaveResult(ok=False, error=t('settings.path_not_found', path=folder))

    if runtime.context.config.get('search_folder') == folder:
        return SettingsSaveResult(ok=True)

    runtime.context.config['search_folder'] = folder
    try:
        with open('config.json', 'w') as configfile:
            json.dump(runtime.context.config, configfile, indent=4)
        return SettingsSaveResult(ok=True, message=t('settings.path_saved'))
    except Exception as e:
        return SettingsSaveResult(ok=False, error=t('settings.path_save_error', error=e))


def _clear_readonly_attribute(path: str) -> None:
    """Remove o atributo somente-leitura de um arquivo .db existente (best-effort)."""
    if os.path.isfile(path):
        try:
            os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
        except OSError:
            pass


def _check_database_writable(path: str) -> str:
    """Tenta escrever de fato no banco do destino.

    Retorna string vazia se for gravável, ou uma mensagem de erro amigável
    explicando por que não é. Cobre os casos comuns: arquivo com atributo
    somente-leitura, diretório/local sem permissão de escrita e share de rede
    montado como leitura.
    """
    _clear_readonly_attribute(path)
    try:
        conn = sqlite3.connect(path, timeout=5)
        try:
            conn.execute('CREATE TABLE IF NOT EXISTS _artemis_write_test (x INTEGER)')
            conn.execute('DROP TABLE IF EXISTS _artemis_write_test')
            conn.commit()
        finally:
            conn.close()
        return ''
    except sqlite3.OperationalError as e:
        msg = str(e).lower()
        if 'readonly' in msg or 'read-only' in msg or 'unable to open' in msg:
            return t('settings.db_readonly_detail', error=e)
        return t('settings.db_validate_error', error=e)
    except Exception as e:
        return t('settings.db_access_error', error=e)


def save_database_location(folder: str) -> SettingsSaveResult:
    folder = os.path.abspath(folder) if folder else folder
    if not os.path.exists(os.path.dirname(folder)) and os.path.dirname(folder):
        return SettingsSaveResult(ok=False, error=t('settings.path_not_found', path=folder))

    if runtime.context.config.get('database_location') == folder:
        return SettingsSaveResult(ok=True)

    writable_error = _check_database_writable(folder)
    if writable_error:
        return SettingsSaveResult(ok=False, error=writable_error)

    previous_location = runtime.context.config.get('database_location')
    runtime.context.config['database_location'] = folder
    try:
        with open('config.json', 'w') as configfile:
            json.dump(runtime.context.config, configfile, indent=4)
        new_db = DataBase(runtime.context.config['database_location'])
        new_db.create_tables()
        runtime.set_db(new_db)
        return SettingsSaveResult(ok=True, message=t('settings.db_saved'))
    except Exception as e:
        runtime.context.config['database_location'] = previous_location
        return SettingsSaveResult(ok=False, error=t('settings.db_save_error', error=e))


def get_language() -> str:
    return runtime.context.config.get('language', 'pt') or 'pt'


def get_locales_folder() -> str:
    return runtime.context.config.get('locales_folder', '') or ''


def save_language(code: str) -> SettingsSaveResult:
    code = (code or '').strip()
    reload_locales(get_locales_folder())
    available = {c for c, _ in get_i18n().available_languages()}
    if code not in available:
        return SettingsSaveResult(ok=False, error=t('settings.save_error', error='Invalid language'))

    if runtime.context.config.get('language') == code:
        set_language(code)
        return SettingsSaveResult(ok=True)

    runtime.context.config['language'] = code
    try:
        with open('config.json', 'w') as configfile:
            json.dump(runtime.context.config, configfile, indent=4)
        set_language(code)
        return SettingsSaveResult(ok=True, message=t('config.language_saved'))
    except Exception as e:
        return SettingsSaveResult(ok=False, error=t('settings.save_error', error=e))


def save_locales_folder(folder: str) -> SettingsSaveResult:
    folder = (folder or '').strip()
    if folder and not os.path.isdir(folder):
        return SettingsSaveResult(ok=False, error=t('settings.path_not_found', path=folder))

    if runtime.context.config.get('locales_folder', '') == folder:
        reload_locales(folder)
        return SettingsSaveResult(ok=True)

    runtime.context.config['locales_folder'] = folder
    try:
        with open('config.json', 'w') as configfile:
            json.dump(runtime.context.config, configfile, indent=4)
        reload_locales(folder)
        return SettingsSaveResult(ok=True, message=t('config.locales_folder_saved'))
    except Exception as e:
        return SettingsSaveResult(ok=False, error=t('settings.save_error', error=e))
