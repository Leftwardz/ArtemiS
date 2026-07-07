from dataclasses import dataclass
from typing import List, Optional

from app.i18n import PDF_MODE_SENTINEL, t
from app.services.layout_service import get_product_paper_size
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
    layout_configs: Optional[list] = None


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
            error_title=t('common.error'),
            error_message=t('remake.empty_list'),
        )

    product_obj = db.search_product(client, product)
    if product_obj is None:
        return RemakeJobResult(
            ok=False,
            error_title=t('common.error'),
            error_message=t('work.product_missing', client=client, product=product),
        )

    paper_size = get_product_paper_size(product_obj)
    if printer != PDF_MODE_SENTINEL:
        if not validate_printer_paper(printer, paper_size):
            return RemakeJobResult(
                ok=False,
                error_title=t('common.error'),
                error_message=get_printer_paper_error_message(
                    paper_size,
                    wording_key='printer_paper.wording_registered',
                ),
            )

    items = [db.consult_drawings_from_product(client, product)]
    orientations = [product_obj.orientation]
    layout_configs = [getattr(product_obj, 'layout_config', None)]
    return RemakeJobResult(
        ok=True,
        lines=[lines],
        items=items,
        orientations=orientations,
        layout_configs=layout_configs,
    )
