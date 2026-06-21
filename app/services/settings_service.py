"""Persistência de config.json e troca de banco."""

import json
import os
from dataclasses import dataclass

from app import runtime
from app.models.database_manager import DataBase
from app.utils.ghostscript_paths import ghostscript_is_available

PRINT_BACKENDS = ('pdftoprinter', 'ghostscript')
PRINT_BACKEND_LABELS = {
    'pdftoprinter': 'PDFtoPrinter',
    'ghostscript': 'Ghostscript',
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

    if backend == 'ghostscript' and not ghostscript_is_available():
        return SettingsSaveResult(
            ok=False,
            error='Ghostscript não encontrado.\n'
                  'Rode scripts/fetch_ghostscript.ps1 ou inclua no build PyInstaller.',
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


def save_database_location(folder: str) -> SettingsSaveResult:
    if not os.path.exists(os.path.dirname(folder)) and os.path.dirname(folder):
        return SettingsSaveResult(ok=False, error=f'Caminho: {folder} não encontrada no sistema')

    if runtime.context.config.get('database_location') == folder:
        return SettingsSaveResult(ok=True)

    runtime.context.config['database_location'] = folder
    try:
        with open('config.json', 'w') as configfile:
            json.dump(runtime.context.config, configfile, indent=4)
        new_db = DataBase(runtime.context.config['database_location'])
        new_db.create_tables()
        runtime.set_db(new_db)
        return SettingsSaveResult(ok=True, message='Banco de Dados Salvo!')
    except Exception as e:
        return SettingsSaveResult(ok=False, error=f'Erro ao salvar o caminho\n{e}')
