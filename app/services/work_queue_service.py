import os
from dataclasses import dataclass
from typing import List, Optional

from app.services.production_service import (
    WorkValidationError,
    find_work_in_directory,
    get_product_from_file,
    get_work_product_info,
    is_empty_file,
    normalize_group_flag,
    resolve_work_search_path,
    validate_queue_consistency,
)


@dataclass
class WorkSearchResult:
    status: str
    work: str = ''
    full_path: str = ''
    defined_paper_size: Optional[str] = None
    defined_color: Optional[str] = None
    show_color: bool = False
    open_remake: bool = False
    error: Optional[WorkValidationError] = None
    search_folder: str = ''


def search_work_for_queue(
    work: str,
    search_folder: str,
    group_name: str,
    is_remake: bool,
    skip_remake_screen: bool,
    queued_paths: List[str],
    defined_paper_size,
    defined_color,
    db,
) -> WorkSearchResult:
    work = work.upper()
    if not work:
        return WorkSearchResult(status='empty')

    group_flag = normalize_group_flag(group_name)
    path = resolve_work_search_path(search_folder, group_flag, is_remake)

    if not os.path.exists(path):
        return WorkSearchResult(
            status='path_missing',
            error=WorkValidationError('Erro', f'Caminho "{path}" não existe!'),
        )

    full_path = find_work_in_directory(path, work)
    if full_path is None:
        return WorkSearchResult(status='not_found', work=work, search_folder=search_folder)

    if full_path in queued_paths:
        return WorkSearchResult(status='duplicate', work=work)

    if is_empty_file(full_path):
        return WorkSearchResult(status='empty_file', work=work)

    work_info = get_work_product_info(full_path, db)
    if work_info is None:
        client, product = get_product_from_file(full_path)
        return WorkSearchResult(
            status='product_missing',
            work=work,
            error=WorkValidationError(
                'Erro',
                f'Cliente: "{client}" e Produto: "{product}" não existem no banco',
            ),
        )

    consistency = validate_queue_consistency(
        work_info.paper_size,
        work_info.color,
        defined_paper_size,
        defined_color,
    )
    if not consistency.ok:
        return WorkSearchResult(status='inconsistent', work=work, error=consistency.error)

    return WorkSearchResult(
        status='ok',
        work=work,
        full_path=full_path,
        defined_paper_size=consistency.defined_paper_size,
        defined_color=consistency.defined_color,
        show_color=consistency.show_color,
        open_remake=is_remake and not skip_remake_screen,
    )
