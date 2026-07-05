"""Impressoras virtuais do Windows que exigem interação (ex.: diálogo Salvar como)."""

_INTERACTIVE_MARKERS = (
    'microsoft print to pdf',
    'microsoft xps document writer',
    'onenote',
    'fax',
)


def is_interactive_virtual_printer(printer_name: str) -> bool:
    """True quando o driver costuma abrir um diálogo modal do Windows ao imprimir."""
    name = (printer_name or '').strip().casefold()
    if not name:
        return False
    return any(marker in name for marker in _INTERACTIVE_MARKERS)
