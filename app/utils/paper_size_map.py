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

# Dimensões em pontos (largura x altura) para -sPAPERSIZE em paisagem.
# O PDF customizado já sai com a geometria correta; basta informar o tamanho
# físico da folha sem rotacionar o conteúdo via setpagedevice.
GHOSTSCRIPT_LANDSCAPE_PAPERSIZE = {
    'letter': '792x612',
    '11x17': '1224x792',
    'ledger': '792x1224',
    'legal': '1008x612',
    'statement': '612x396',
    'a5': '595x420',
    'a3': '1191x842',
    'a4': '842x595',
    'b4': '1032x729',
    'b5': '729x516',
    'folio': '936x612',
    'quarto': '720x576',
    '10x14': '1008x720',
    'note': '792x612',
}


def paper_size_to_ghostscript(paper_size):
    """Retorna nome GS ou None se 0 / desconhecido (driver usa default)."""
    if paper_size is None:
        return None
    key = str(paper_size).strip()
    if key in ('', '0'):
        return None
    return PAPER_SIZE_TO_GHOSTSCRIPT.get(key)


def paper_size_to_ghostscript_landscape(paper_size):
    """Retorna -sPAPERSIZE em pontos (WxH) para paisagem, ou None."""
    gs_name = paper_size_to_ghostscript(paper_size)
    if not gs_name:
        return None
    return GHOSTSCRIPT_LANDSCAPE_PAPERSIZE.get(gs_name)
