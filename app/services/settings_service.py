"""Persistência de config.json e troca de banco."""

import json
import os
from dataclasses import dataclass

from Database import DataBase
from app import runtime


@dataclass
class SettingsSaveResult:
    ok: bool
    message: str = ''
    error: str = ''


def get_search_folder():
    return runtime.config.get('search_folder', '')


def get_database_location():
    return runtime.config.get('database_location', '')


def save_search_folder(folder: str) -> SettingsSaveResult:
    if not os.path.exists(folder):
        return SettingsSaveResult(ok=False, error=f'Caminho: {folder} não encontrada no sistema')

    if runtime.config.get('search_folder') == folder:
        return SettingsSaveResult(ok=True)

    runtime.config['search_folder'] = folder
    try:
        with open('config.json', 'w') as configfile:
            json.dump(runtime.config, configfile, indent=4)
        return SettingsSaveResult(ok=True, message='Caminho Salvo!')
    except Exception as e:
        return SettingsSaveResult(ok=False, error=f'Erro ao salvar o caminho\n{e}')


def save_database_location(folder: str) -> SettingsSaveResult:
    if not os.path.exists(os.path.dirname(folder)) and os.path.dirname(folder):
        return SettingsSaveResult(ok=False, error=f'Caminho: {folder} não encontrada no sistema')

    if runtime.config.get('database_location') == folder:
        return SettingsSaveResult(ok=True)

    runtime.config['database_location'] = folder
    try:
        with open('config.json', 'w') as configfile:
            json.dump(runtime.config, configfile, indent=4)
        new_db = DataBase(runtime.config['database_location'])
        new_db.create_tables()
        runtime.set_db(new_db)
        return SettingsSaveResult(ok=True, message='Banco de Dados Salvo!')
    except Exception as e:
        return SettingsSaveResult(ok=False, error=f'Erro ao salvar o caminho\n{e}')
