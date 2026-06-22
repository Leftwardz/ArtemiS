"""Persistência de config.json e troca de banco."""

import json
import os
import sqlite3
import stat
from dataclasses import dataclass

from app import runtime
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
            return SettingsSaveResult(ok=False, error=f'Pasta não encontrada: {parent}')

    if runtime.context.config.get('audit_central_location', '') == path:
        return SettingsSaveResult(ok=True)

    runtime.context.config['audit_central_location'] = path
    try:
        with open('config.json', 'w') as configfile:
            json.dump(runtime.context.config, configfile, indent=4)
        return SettingsSaveResult(
            ok=True,
            message='Local do banco de logs salvo!\nReinicie o ArtemiS para aplicar à agregação.',
        )
    except Exception as e:
        return SettingsSaveResult(ok=False, error=f'Erro ao salvar o caminho\n{e}')


def get_print_backend():
    backend = runtime.context.config.get('print_backend', 'pdftoprinter')
    if backend not in PRINT_BACKENDS:
        return 'pdftoprinter'
    return backend


def get_print_backend_label():
    return PRINT_BACKEND_LABELS.get(get_print_backend(), 'PDFtoPrinter')


def save_print_backend(backend: str) -> SettingsSaveResult:
    if backend not in PRINT_BACKENDS:
        return SettingsSaveResult(ok=False, error='Motor de impressão inválido.')

    from app.utils.printing.registry import get_backend
    backend_obj = get_backend(backend)
    if backend_obj is None or not backend_obj.is_available():
        hint = ''
        if backend in ('ghostscript', 'win32_devmode', 'win32_advanced', 'xps'):
            hint = ('\nEste motor depende do Ghostscript empacotado.\n'
                    'Rode scripts/fetch_ghostscript.ps1 ou inclua no build PyInstaller.')
        label = PRINT_BACKEND_LABELS.get(backend, backend)
        return SettingsSaveResult(
            ok=False,
            error=f'Motor de impressão "{label}" não está disponível nesta máquina.{hint}',
        )

    if runtime.context.config.get('print_backend') == backend:
        return SettingsSaveResult(ok=True)

    runtime.context.config['print_backend'] = backend
    try:
        with open('config.json', 'w') as configfile:
            json.dump(runtime.context.config, configfile, indent=4)
        label = PRINT_BACKEND_LABELS[backend]
        return SettingsSaveResult(ok=True, message=f'Motor de impressão: {label}')
    except Exception as e:
        return SettingsSaveResult(ok=False, error=f'Erro ao salvar configuração\n{e}')


def save_search_folder(folder: str) -> SettingsSaveResult:
    if not os.path.exists(folder):
        return SettingsSaveResult(ok=False, error=f'Caminho: {folder} não encontrada no sistema')

    if runtime.context.config.get('search_folder') == folder:
        return SettingsSaveResult(ok=True)

    runtime.context.config['search_folder'] = folder
    try:
        with open('config.json', 'w') as configfile:
            json.dump(runtime.context.config, configfile, indent=4)
        return SettingsSaveResult(ok=True, message='Caminho Salvo!')
    except Exception as e:
        return SettingsSaveResult(ok=False, error=f'Erro ao salvar o caminho\n{e}')


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
            return (
                'Não é possível gravar no banco neste local (somente leitura).\n\n'
                'Verifique se:\n'
                '• o arquivo .db não está marcado como "Somente leitura";\n'
                '• a pasta/compartilhamento de rede permite escrita para o seu usuário;\n'
                '• o caminho não aponta para uma pasta protegida (ex.: Arquivos de Programas).\n\n'
                f'Detalhe técnico: {e}'
            )
        return f'Erro ao validar gravação no banco:\n{e}'
    except Exception as e:
        return f'Erro ao acessar o banco no destino:\n{e}'


def save_database_location(folder: str) -> SettingsSaveResult:
    folder = os.path.abspath(folder) if folder else folder
    if not os.path.exists(os.path.dirname(folder)) and os.path.dirname(folder):
        return SettingsSaveResult(ok=False, error=f'Caminho: {folder} não encontrada no sistema')

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
        return SettingsSaveResult(ok=True, message='Banco de Dados Salvo!')
    except Exception as e:
        runtime.context.config['database_location'] = previous_location
        return SettingsSaveResult(ok=False, error=f'Erro ao salvar o caminho\n{e}')
