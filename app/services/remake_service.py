from dataclasses import dataclass
from typing import List, Optional

from app.services.print_service import get_printer_paper_error_message, validate_printer_paper
from app.services.production_service import build_remake_file_lines
from app.utils.file_parser import FileUtils


@dataclass
class RemakeJobResult:
    ok: bool
    error_title: str = ''
    error_message: str = ''
    lines: Optional[list] = None
    items: Optional[list] = None
    orientations: Optional[list] = None


def prepare_remake_job(
    db,
    client: str,
    product: str,
    file_utils: FileUtils,
    filepath: str,
    position_list: List[int],
    printer: str,
) -> RemakeJobResult:
    lines = build_remake_file_lines(file_utils, filepath, position_list)
    if not lines:
        return RemakeJobResult(
            ok=False,
            error_title='Erro!',
            error_message='Lista não pode estar vazia!',
        )

    product_obj = db.search_product(client, product)
    if printer != 'Criar PDF':
        if not validate_printer_paper(printer, product_obj.paper_size):
            return RemakeJobResult(
                ok=False,
                error_title='Erro',
                error_message=get_printer_paper_error_message(
                    product_obj.paper_size,
                    wording='cadastrado',
                ),
            )

    items = [db.consult_drawings_from_product(client, product)]
    orientations = [product_obj.orientation]
    return RemakeJobResult(
        ok=True,
        lines=[lines],
        items=items,
        orientations=orientations,
    )
