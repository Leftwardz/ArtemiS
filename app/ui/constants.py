ICON = 'img/favicon3.ico'
FONT = 'Segoe UI'
APP_NAME = 'ArtemiS'
# UI theme tokens (defaults = purple preset; overridden at startup via app.ui.theme)
THEME_SIDEBAR = '#1a1033'
THEME_BG = '#12151f'
THEME_CARD = '#1e2433'
THEME_CARD_BORDER = '#2d3548'
THEME_ACCENT = '#7c3aed'
THEME_ACCENT_HOVER = '#6d28d9'
THEME_ACCENT_SECONDARY = '#4f6ef7'
THEME_NAV_ACTIVE = '#261845'
THEME_TEXT_SECONDARY = '#8b95a5'
THEME_PROGRESS_BG = '#2d1b4e'
THEME_ICON = '#a78bfa'
THEME_NAV_TEXT_ACCENT = '#c4b5fd'
THEME_GRADIENT_HOVER = '#4338ca'
THEME_TABLE_ROW_A = '#1a1d28'
THEME_TABLE_ROW_B = '#12151f'
THEME_CANVAS_BG = '#2a3142'
THEME_ERROR_TEXT = '#f87171'
BTN_RED = '#732425'
BTN_HOVER_RED = '#4a191a'


def apply_theme_colors(**colors: str) -> None:
    """Update module-level theme tokens (call once at app startup)."""
    global THEME_SIDEBAR, THEME_BG, THEME_CARD, THEME_CARD_BORDER
    global THEME_ACCENT, THEME_ACCENT_HOVER, THEME_ACCENT_SECONDARY
    global THEME_NAV_ACTIVE, THEME_TEXT_SECONDARY, THEME_PROGRESS_BG
    global THEME_ICON, THEME_NAV_TEXT_ACCENT, THEME_GRADIENT_HOVER
    global THEME_TABLE_ROW_A, THEME_TABLE_ROW_B, THEME_CANVAS_BG, THEME_ERROR_TEXT
    global BTN_RED, BTN_HOVER_RED

    THEME_SIDEBAR = colors['sidebar']
    THEME_BG = colors['bg']
    THEME_CARD = colors['card']
    THEME_CARD_BORDER = colors['card_border']
    THEME_ACCENT = colors['accent']
    THEME_ACCENT_HOVER = colors['accent_hover']
    THEME_ACCENT_SECONDARY = colors['accent_secondary']
    THEME_NAV_ACTIVE = colors['nav_active']
    THEME_TEXT_SECONDARY = colors['text_secondary']
    THEME_PROGRESS_BG = colors['progress_bg']
    BTN_RED = colors['destructive']
    BTN_HOVER_RED = colors['destructive_hover']
    THEME_ICON = colors['icon']
    THEME_NAV_TEXT_ACCENT = colors['nav_text_accent']
    THEME_GRADIENT_HOVER = colors['gradient_hover']
    THEME_TABLE_ROW_A = colors['table_row_a']
    THEME_TABLE_ROW_B = colors['table_row_b']
    THEME_CANVAS_BG = colors['canvas_bg']
    THEME_ERROR_TEXT = colors['error_text']

DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720
SIDEBAR_WIDTH = 200

CONFIG_WIDTH = 950
CONFIG_HEIGHT = 680

LOADING_SIDEBAR_WIDTH = SIDEBAR_WIDTH

PAPER_COLOR_LIST = {
    'Branco': '#FFFFFF',
    'Verde': '#3CB371',
    'Azul': '#87CEFA',
    'Rosa': '#EE82EE',
    'Amarelo': '#FFFF00',
    'Marfim': '#eee9b4',
}

FONT_LIST = [
    'Arial',
    'Trebuchet MS',
    'Arial Narrow',
    'Times New Roman',
    'Saira Extracondensed',
    'Morganite Semibold',
    'Oswald',
    'Bahnschrift',
]


def get_font_list():
    """Font families from the dynamic catalog (falls back to FONT_LIST before init)."""
    try:
        from app.services.font_service import list_font_families
        families = list_font_families()
        if families:
            return families
    except Exception:
        pass
    return list(FONT_LIST)

# Cor no editor para itens marcados como duplex (verso)
DUPLEX_CANVAS_COLOR = '#AAAAAA'

PAPER_SIZE_TIP = """
Segue lista de papeis:
00 - (Aceita Qualquer Papel)
01 - (Letter)
02 - (Letter Small)
03 - (Tabloid)
04 - (Ledger)
05 - (Legal)
06 - (Statement)
07 - (A5)
08 - (A3)
09 - (A4)
10 - (B4)
11 - (B5)
12 - (Folio)
13 - (Quarto)
14 - (10x14 inches)
15 - (11x17 inches)
16 - (Note)
17 - (Envelope #9)
18 - (Envelope #10)
19 - (Envelope #11)
20 - (Envelope #12)
21 - (Envelope #14)
"""

FIXED_TEXT_PAGE_TIP = (
    'No cabeçalho (escopo Folha), use placeholders de paginação:\n'
    '{p} ou {pag} — página do grupo\n'
    '{t} ou {total} — total de páginas do grupo\n'
    'Ex.: Pág. {p}/{t}'
)
