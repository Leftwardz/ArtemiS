"""Grupos de impressão — subpastas de busca dentro da pasta central de workorders."""

from __future__ import annotations

import os
from typing import Optional

DEFAULT_PRINT_GROUP_NAME = 'PADRAO'
DEFAULT_SEARCH_FOLDER = r'C:\ArtemiS\Workorders'
LEGACY_ROOT_GROUP_NAME = 'AR'


def normalize_group_flag(group_name: str) -> str:
    if not group_name:
        return ''
    return f'\\{group_name}'


def resolve_work_search_path(search_folder: str, group_flag: str, is_remake: bool) -> str:
    if is_remake:
        return search_folder + group_flag + '\\Old'
    return search_folder + group_flag


def ensure_group_subdirectory(search_folder: str, group_name: str) -> None:
    if search_folder and group_name:
        group_path = os.path.join(search_folder, group_name)
        os.makedirs(group_path, exist_ok=True)
        os.makedirs(os.path.join(group_path, 'Old'), exist_ok=True)


def migrate_legacy_group_folder(search_folder: str) -> None:
    """Renomeia subpasta legada AR para o grupo padrão, se aplicável."""
    if not search_folder:
        return
    legacy_path = os.path.join(search_folder, LEGACY_ROOT_GROUP_NAME)
    default_path = os.path.join(search_folder, DEFAULT_PRINT_GROUP_NAME)
    if os.path.isdir(legacy_path) and not os.path.exists(default_path):
        os.rename(legacy_path, default_path)


def ensure_workorder_directories(search_folder: str, group_names: Optional[list[str]] = None) -> None:
    if not search_folder:
        return
    migrate_legacy_group_folder(search_folder)
    os.makedirs(search_folder, exist_ok=True)
    for name in group_names or []:
        if not name:
            continue
        group_path = os.path.join(search_folder, name)
        os.makedirs(group_path, exist_ok=True)
        os.makedirs(os.path.join(group_path, 'Old'), exist_ok=True)
