"""Placeholders de paginação no cabeçalho de folha (escopo sheet)."""

_SHEET_PAGE_PLACEHOLDERS = ('{pag}', '{total}', '{p}', '{t}')


def has_sheet_page_placeholders(text) -> bool:
    if not text:
        return False
    s = str(text)
    return any(ph in s for ph in _SHEET_PAGE_PLACEHOLDERS)


def apply_sheet_page_placeholders(text, group_page, group_total):
    if group_page is None or group_total is None or text is None:
        return text
    result = str(text)
    result = result.replace('{pag}', str(group_page))
    result = result.replace('{total}', str(group_total))
    result = result.replace('{p}', str(group_page))
    result = result.replace('{t}', str(group_total))
    return result
