"""Font catalog, ReportLab registration, and custom font import."""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

CATALOG_BUILTIN = 'fonts.json'
CATALOG_CUSTOM = 'fonts.custom.json'
WINDOWS_FONTS_DIR = Path(os.environ.get('WINDIR', r'C:\Windows')) / 'Fonts'

_config: dict = {}
_lookup: Dict[str, 'FontEntry'] = {}
_registered_names: set = set()
_catalog_cache: Optional[List['FontEntry']] = None


@dataclass
class FontEntry:
    id: str
    display_name: str
    regular_path: Path
    bold_path: Optional[Path]
    builtin: bool
    aliases: List[str] = field(default_factory=list)

    @property
    def has_bold(self) -> bool:
        return self.bold_path is not None and self.bold_path.is_file()


@dataclass
class FontImportResult:
    ok: bool
    message: str = ''
    error: str = ''


def app_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def fonts_dir() -> Path:
    return app_dir() / 'fontes'


def _is_unc_path(path: str) -> bool:
    normalized = path.replace('/', '\\')
    return normalized.startswith('\\\\')


def custom_fonts_dir() -> Path:
    explicit = (_config.get('fonts_folder') or '').strip()
    if explicit:
        return Path(explicit)
    db = (_config.get('database_location') or '').strip()
    if db and _is_unc_path(db):
        return Path(os.path.dirname(db)) / 'fontes'
    return fonts_dir() / 'custom'


def custom_catalog_path() -> Path:
    return custom_fonts_dir() / CATALOG_CUSTOM


def init_fonts(config: dict) -> None:
    """Load config and register all fonts (call once after runtime.init)."""
    global _config
    _config = dict(config or {})
    register_all_fonts()


def _load_json(path: Path) -> dict:
    if not path.is_file():
        return {'families': []}
    with open(path, encoding='utf-8') as handle:
        return json.load(handle)


def _save_custom_catalog(families: list) -> None:
    folder = custom_fonts_dir()
    folder.mkdir(parents=True, exist_ok=True)
    path = custom_catalog_path()
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump({'families': families}, handle, indent=4, ensure_ascii=False)


def _resolve_family_file(filename: str, builtin: bool) -> Path:
    root = fonts_dir() if builtin else custom_fonts_dir()
    return root / filename


def _slug_id(name: str) -> str:
    slug = re.sub(r'[^a-z0-9]+', '_', (name or '').lower()).strip('_')
    return slug or 'font'


def _add_lookup_keys(entry: FontEntry) -> None:
    keys = {entry.display_name, entry.id, *entry.aliases}
    for key in keys:
        if key:
            _lookup[key.casefold()] = entry


def load_catalog(*, force: bool = False) -> List[FontEntry]:
    global _catalog_cache
    if _catalog_cache is not None and not force:
        return list(_catalog_cache)

    _lookup.clear()
    entries: List[FontEntry] = []
    seen_ids: set = set()

    for raw in _load_json(fonts_dir() / CATALOG_BUILTIN).get('families', []):
        entry = _entry_from_raw(raw, builtin=True)
        if entry.id in seen_ids:
            continue
        seen_ids.add(entry.id)
        entries.append(entry)
        _add_lookup_keys(entry)

    for raw in _load_json(custom_catalog_path()).get('families', []):
        entry = _entry_from_raw(raw, builtin=False)
        if entry.id in seen_ids:
            continue
        seen_ids.add(entry.id)
        entries.append(entry)
        _add_lookup_keys(entry)

    _catalog_cache = entries
    return list(entries)


def _entry_from_raw(raw: dict, *, builtin: bool) -> FontEntry:
    regular_name = raw.get('regular') or ''
    bold_name = raw.get('bold')
    return FontEntry(
        id=str(raw.get('id') or _slug_id(raw.get('display_name', ''))),
        display_name=str(raw.get('display_name') or ''),
        regular_path=_resolve_family_file(regular_name, builtin),
        bold_path=_resolve_family_file(bold_name, builtin) if bold_name else None,
        builtin=builtin,
        aliases=list(raw.get('aliases') or []),
    )


def _reportlab_name_variants(entry: FontEntry) -> List[Tuple[str, Path]]:
    names: List[Tuple[str, Path]] = []
    bases = {entry.display_name, *entry.aliases}
    for base in bases:
        if not base:
            continue
        names.append((base, entry.regular_path))
        if entry.has_bold:
            names.append((f'{base}-Bold', entry.bold_path))
    return names


def register_all_fonts() -> None:
    global _catalog_cache
    _catalog_cache = None
    for entry in load_catalog(force=True):
        for name, path in _reportlab_name_variants(entry):
            if name in _registered_names:
                continue
            if not path.is_file():
                continue
            try:
                pdfmetrics.registerFont(TTFont(name, str(path)))
                _registered_names.add(name)
            except Exception:
                continue


def reload_fonts() -> None:
    register_all_fonts()


def lookup_font(font_name: str) -> Optional[FontEntry]:
    load_catalog()
    return _lookup.get((font_name or '').strip().casefold())


def resolve_reportlab_font(font_name: str, font_style: str) -> str:
    style = (font_style or 'normal').strip().lower()
    entry = lookup_font(font_name)
    if entry is None:
        base = (font_name or 'Arial').strip().capitalize()
        return f'{base}-Bold' if style == 'bold' else base
    if style == 'bold' and entry.has_bold:
        return f'{entry.display_name}-Bold'
    return entry.display_name


def list_font_families() -> List[str]:
    return sorted({entry.display_name for entry in load_catalog()})


def family_has_bold(display_name: str) -> bool:
    entry = lookup_font(display_name)
    return bool(entry and entry.has_bold)


def list_catalog_rows() -> List[dict]:
    rows = []
    for entry in load_catalog():
        rows.append({
            'id': entry.id,
            'display_name': entry.display_name,
            'regular': entry.regular_path.name,
            'bold': entry.bold_path.name if entry.bold_path else '',
            'builtin': entry.builtin,
            'has_bold': entry.has_bold,
        })
    return rows


def validate_fonts_folder(path: str) -> FontImportResult:
    folder = (path or '').strip()
    if not folder:
        return FontImportResult(ok=True)
    if not os.path.isdir(folder):
        return FontImportResult(ok=False, error=f'Pasta não encontrada: {folder}')
    test_file = os.path.join(folder, '._artemis_font_write_test')
    try:
        with open(test_file, 'w', encoding='utf-8') as handle:
            handle.write('ok')
        os.remove(test_file)
        return FontImportResult(ok=True)
    except OSError as exc:
        return FontImportResult(ok=False, error=str(exc))


def _unique_filename(folder: Path, basename: str) -> str:
    candidate = basename
    stem = Path(basename).stem
    suffix = Path(basename).suffix
    counter = 1
    while (folder / candidate).exists():
        candidate = f'{stem}_{counter}{suffix}'
        counter += 1
    return candidate


def _copy_ttf(source: Union[str, Path], dest_dir: Path, prefix: str) -> Path:
    source_path = Path(source)
    if source_path.suffix.lower() != '.ttf':
        raise ValueError('Apenas arquivos .ttf são suportados.')
    if not source_path.is_file():
        raise FileNotFoundError(f'Arquivo não encontrado: {source_path}')
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_name = _unique_filename(dest_dir, f'{prefix}_{source_path.name}')
    dest_path = dest_dir / dest_name
    shutil.copy2(source_path, dest_path)
    return dest_path


def _load_custom_families() -> list:
    return list(_load_json(custom_catalog_path()).get('families', []))


def import_font(
    regular_path: str,
    display_name: str,
    bold_path: Optional[str] = None,
) -> FontImportResult:
    display_name = (display_name or '').strip()
    if not display_name:
        return FontImportResult(ok=False, error='Nome de exibição obrigatório.')

    families = _load_custom_families()
    font_id = _slug_id(display_name)
    if any(f.get('id') == font_id for f in families):
        suffix = 2
        while any(f.get('id') == f'{font_id}_{suffix}' for f in families):
            suffix += 1
        font_id = f'{font_id}_{suffix}'

    dest_dir = custom_fonts_dir()
    try:
        regular_dest = _copy_ttf(regular_path, dest_dir, font_id)
        bold_dest = _copy_ttf(bold_path, dest_dir, f'{font_id}_bold') if bold_path else None
    except (ValueError, FileNotFoundError) as exc:
        return FontImportResult(ok=False, error=str(exc))
    except OSError as exc:
        return FontImportResult(ok=False, error=str(exc))

    families.append({
        'id': font_id,
        'display_name': display_name,
        'regular': regular_dest.name,
        'bold': bold_dest.name if bold_dest else None,
        'aliases': [display_name.casefold()],
        'builtin': False,
    })
    try:
        _save_custom_catalog(families)
    except OSError as exc:
        return FontImportResult(ok=False, error=str(exc))

    reload_fonts()
    return FontImportResult(ok=True, message=display_name)


def remove_custom_font(font_id: str, *, delete_files: bool = True) -> FontImportResult:
    families = _load_custom_families()
    target = None
    remaining = []
    for family in families:
        if family.get('id') == font_id:
            target = family
        else:
            remaining.append(family)
    if target is None:
        return FontImportResult(ok=False, error='Fonte customizada não encontrada.')

    if delete_files:
        folder = custom_fonts_dir()
        for key in ('regular', 'bold'):
            filename = target.get(key)
            if filename:
                path = folder / filename
                if path.is_file():
                    try:
                        path.unlink()
                    except OSError:
                        pass

    try:
        _save_custom_catalog(remaining)
    except OSError as exc:
        return FontImportResult(ok=False, error=str(exc))

    reload_fonts()
    return FontImportResult(ok=True, message=target.get('display_name', font_id))


def list_windows_fonts() -> List[Tuple[str, str]]:
    """Return (registry label, ttf filename) for installed Windows fonts."""
    if sys.platform != 'win32':
        return []
    try:
        import winreg
    except ImportError:
        return []

    results: List[Tuple[str, str]] = []
    key_path = r'SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts'
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            index = 0
            while True:
                try:
                    label, value, _ = winreg.EnumValue(key, index)
                except OSError:
                    break
                index += 1
                filename = str(value)
                if filename.lower().endswith('.ttf'):
                    results.append((str(label), filename))
    except OSError:
        return []

    results.sort(key=lambda item: item[0].casefold())
    return results


def import_windows_font(
    registry_label: str,
    filename: str,
    display_name: str,
    bold_filename: Optional[str] = None,
) -> FontImportResult:
    regular_source = WINDOWS_FONTS_DIR / filename
    bold_source = WINDOWS_FONTS_DIR / bold_filename if bold_filename else None
    if not regular_source.is_file():
        return FontImportResult(
            ok=False,
            error=f'Arquivo de fonte não encontrado em {WINDOWS_FONTS_DIR}: {filename}',
        )
    if bold_source and not bold_source.is_file():
        return FontImportResult(
            ok=False,
            error=f'Arquivo bold não encontrado: {bold_filename}',
        )
    return import_font(
        str(regular_source),
        display_name or windows_display_name(registry_label),
        str(bold_source) if bold_source else None,
    )


def windows_display_name(registry_label: str) -> str:
    name = re.sub(r'\s*\(TrueType\)\s*$', '', registry_label or '', flags=re.IGNORECASE)
    name = re.sub(r'\s*\(OpenType\)\s*$', '', name, flags=re.IGNORECASE)
    return name.strip() or registry_label


def suggest_windows_bold_match(
    items: List[Tuple[str, str]],
    registry_label: str,
    filename: str,
) -> Optional[Tuple[str, str]]:
    """Guess the matching bold face for a Windows regular font."""
    base = windows_display_name(registry_label).casefold()
    stem = Path(filename).stem.lower()

    exact: Optional[Tuple[str, str]] = None
    fallback: Optional[Tuple[str, str]] = None
    for label, fn in items:
        if label == registry_label and fn == filename:
            continue
        display = windows_display_name(label).casefold()
        fn_stem = Path(fn).stem.lower()
        if display == f'{base} bold':
            return label, fn
        if display.startswith(f'{base} ') and 'bold' in display:
            exact = exact or (label, fn)
        elif stem and (
            fn_stem.endswith('bd')
            or fn_stem.endswith('bold')
            or ('bold' in fn_stem and stem[:4] in fn_stem)
        ):
            fallback = fallback or (label, fn)
    return exact or fallback


def _delete_font_file(folder: Path, filename: Optional[str]) -> None:
    if not filename:
        return
    path = folder / filename
    if path.is_file():
        try:
            path.unlink()
        except OSError:
            pass


def update_custom_font(
    font_id: str,
    *,
    display_name: Optional[str] = None,
    regular_path: Optional[str] = None,
    bold_path: Optional[str] = None,
    remove_bold: bool = False,
) -> FontImportResult:
    families = _load_custom_families()
    target = None
    for family in families:
        if family.get('id') == font_id:
            target = family
            break
    if target is None:
        return FontImportResult(ok=False, error='Fonte customizada não encontrada.')

    new_display = (display_name if display_name is not None else target.get('display_name', '')).strip()
    if not new_display:
        return FontImportResult(ok=False, error='Nome de exibição obrigatório.')

    folder = custom_fonts_dir()
    target['display_name'] = new_display

    try:
        if regular_path:
            new_regular = _copy_ttf(regular_path, folder, font_id)
            _delete_font_file(folder, target.get('regular'))
            target['regular'] = new_regular.name

        if remove_bold:
            _delete_font_file(folder, target.get('bold'))
            target['bold'] = None
        elif bold_path:
            new_bold = _copy_ttf(bold_path, folder, f'{font_id}_bold')
            _delete_font_file(folder, target.get('bold'))
            target['bold'] = new_bold.name
    except (ValueError, FileNotFoundError) as exc:
        return FontImportResult(ok=False, error=str(exc))
    except OSError as exc:
        return FontImportResult(ok=False, error=str(exc))

    try:
        _save_custom_catalog(families)
    except OSError as exc:
        return FontImportResult(ok=False, error=str(exc))

    reload_fonts()
    return FontImportResult(ok=True, message=new_display)


def get_canvas_font(widget, font_name: str, size: int, font_style: str):
    """Return a Tk font object or tuple for canvas preview."""
    import tkinter
    import tkinter.font as tkfont

    style = (font_style or 'normal').strip().lower()
    entry = lookup_font(font_name)
    if entry is None:
        weight = 'bold' if style == 'bold' else 'normal'
        return (font_name, size, weight)

    path = entry.bold_path if style == 'bold' and entry.has_bold else entry.regular_path
    if path.is_file():
        try:
            font_obj = tkfont.Font(root=widget, file=str(path), size=size)
            if style == 'bold' and not entry.has_bold:
                font_obj.configure(weight='bold')
            return font_obj
        except tkinter.TclError:
            pass

    weight = 'bold' if style == 'bold' else 'normal'
    return (entry.display_name, size, weight)
