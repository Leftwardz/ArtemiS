"""Mapeamento código Windows DMPAPER → nome Ghostscript -sPAPERSIZE."""

# Códigos alinhados a app/ui/constants.py PAPER_SIZE_TIP (0 = qualquer)
PAPER_SIZE_TO_GHOSTSCRIPT = {
    '1': 'letter',
    '2': 'letter',
    '3': '11x17',      # tabloid
    '4': 'ledger',
    '5': 'legal',
    '6': 'statement',
    '7': 'a5',
    '8': 'a3',
    '9': 'a4',
    '10': 'b4',
    '11': 'b5',
    '12': 'folio',
    '13': 'quarto',
    '14': '10x14',
    '15': '11x17',
    '16': 'note',
    '17': 'envelope',
    '18': 'envelope',
    '19': 'envelope',
    '20': 'envelope',
    '21': 'envelope',
}


def paper_size_to_ghostscript(paper_size):
    """Retorna nome GS ou None se 0 / desconhecido (driver usa default)."""
    if paper_size is None:
        return None
    key = str(paper_size).strip()
    if key in ('', '0'):
        return None
    return PAPER_SIZE_TO_GHOSTSCRIPT.get(key)
