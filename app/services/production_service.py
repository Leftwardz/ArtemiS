import os
from dataclasses import dataclass
from typing import List, Optional, Tuple

from app.utils.file_parser import FileUtils


@dataclass
class WorkProductInfo:
    client: str
    product: str
    color: str
    paper_size: str


@dataclass
class WorkValidationError:
    title: str
    message: str


@dataclass
class QueueConsistencyResult:
    ok: bool
    error: Optional[WorkValidationError] = None
    defined_paper_size: Optional[str] = None
    defined_color: Optional[str] = None
    show_color: bool = False


def normalize_group_flag(group_name: str) -> str:
    if group_name == 'AR':
        return ''
    return f'\\{group_name}'


def resolve_work_search_path(search_folder: str, group_flag: str, is_remake: bool) -> str:
    if is_remake:
        return search_folder + group_flag + '\\Old'
    return search_folder + group_flag


def ensure_output_directories(search_folder: str):
    old_path = os.path.join(search_folder, 'Old')

    if not os.path.exists(old_path):
        os.mkdir(old_path)


def is_empty_file(path: str) -> bool:
    return os.path.getsize(path) == 0


def get_product_from_file(path: str) -> Tuple[str, str]:
    file = FileUtils(path)
    client = file.get_first_line_column(0).split('-')[0].strip()
    product = file.get_first_line_column(0).split('-')[1].strip()
    return client, product


def find_work_in_directory(search_path: str, work_code: str) -> Optional[str]:
    work_upper = work_code.upper()
    with os.scandir(search_path) as files:
        for file in files:
            if file.is_file() and work_upper in file.name.upper():
                return os.path.join(search_path, file.name)
    return None


def get_work_product_info(path: str, db) -> Optional[WorkProductInfo]:
    client, product = get_product_from_file(path)
    if not db.product_exists(client, product):
        return None

    product_obj = db.search_product(client, product)
    return WorkProductInfo(
        client=client,
        product=product,
        color=product_obj.paper_color,
        paper_size=product_obj.paper_size,
    )


def validate_queue_consistency(
    paper_size: str,
    color: str,
    defined_paper_size: Optional[str],
    defined_color: Optional[str],
) -> QueueConsistencyResult:
    if defined_paper_size is None:
        new_paper_size = paper_size
    elif paper_size != defined_paper_size:
        return QueueConsistencyResult(
            ok=False,
            error=WorkValidationError(
                'Erro',
                f'Work com Tamanho de Papel diferente dos que estão na lista - Tamanho: {paper_size}',
            ),
        )
    else:
        new_paper_size = defined_paper_size

    if defined_color is None:
        return QueueConsistencyResult(
            ok=True,
            defined_paper_size=new_paper_size,
            defined_color=color,
            show_color=True,
        )

    if color != defined_color:
        return QueueConsistencyResult(
            ok=False,
            error=WorkValidationError(
                'Erro',
                f'Work com papel diferente das works da lista - Cor: {color}',
            ),
        )

    return QueueConsistencyResult(
        ok=True,
        defined_paper_size=new_paper_size,
        defined_color=defined_color,
        show_color=False,
    )


def load_worklist_file_lines(works_paths: List[str]) -> list:
    files_lines = []

    for work_path in works_paths:
        file = FileUtils(work_path)
        lines = file.return_filelines()
        lines.append(work_path)
        files_lines.append(lines)

    return files_lines


def parse_client_product_from_work_lines(file_lines) -> Tuple[str, str]:
    """Extrai cliente e produto da primeira linha de um CSV de work."""
    if not file_lines:
        raise ValueError('Arquivo de work sem linhas')

    first_row = file_lines[0]
    if len(first_row) < 2 or not first_row[1]:
        raise ValueError('Formato de linha inválido no CSV')

    header_cell = first_row[1][0]
    if '-' not in header_cell:
        raise ValueError(f'Identificador cliente-produto inválido: {header_cell!r}')

    client, product = header_cell.split('-', 1)
    return client.strip(), product.strip()


def get_drawings_and_orientations(files_lines, db):
    all_items = []
    orientations = []
    layout_configs = []

    for file in files_lines:
        client, product = parse_client_product_from_work_lines(file)

        items = db.consult_drawings_from_product(client, product)
        all_items.append(items)

        product_obj = db.search_product(client, product)
        orientations.append(product_obj.orientation)
        layout_configs.append(getattr(product_obj, 'layout_config', None))

    return all_items, orientations, layout_configs


def get_paper_size_from_path(path: str, db) -> Optional[str]:
    client, product = get_product_from_file(path)
    product_obj = db.search_product(client, product)
    if product_obj:
        return product_obj.paper_size
    return None


def build_remake_file_lines(file_utils: FileUtils, filepath: str, position_list: List[int]):
    if not position_list:
        return None

    lines_to_remake = sorted(file_utils.search_by_rangelist(position_list))
    lines_to_remake.append(filepath)
    return lines_to_remake


def validate_duplex_batch(items_list, backend: str) -> Optional[str]:
    """Retorna chave i18n se o lote ou backend for incompatível com duplex."""
    from app.services.pdf_service import product_requires_duplex

    flags = [product_requires_duplex(items) for items in items_list]
    if any(flags) and not all(flags):
        return 'duplex.mixed_batch'
    if any(flags) and backend == 'pdftoprinter':
        return 'duplex.pdftoprinter_unsupported'
    return None
