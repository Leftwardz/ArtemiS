"""Carregamento de traduções a partir de arquivos JSON."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

PDF_MODE_SENTINEL = 'Criar PDF'

if getattr(sys, 'frozen', False):
    _MODULE_DIR = Path(sys._MEIPASS) / 'app' / 'i18n'
else:
    _MODULE_DIR = Path(__file__).resolve().parent

_BUILTIN_LOCALES_DIR = _MODULE_DIR / 'locales'


class I18n:
    def __init__(self):
        self._language = 'pt'
        self._catalog: dict[str, Any] = {}
        self._locales: dict[str, dict[str, Any]] = {}
        self._locales_folder: str = ''

    def init(self, config: dict | None = None) -> None:
        config = config or {}
        self._locales_folder = (config.get('locales_folder') or '').strip()
        self._discover_locales()
        language = (config.get('language') or 'pt').strip()
        self.set_language(language if language in self._locales else 'pt')

    def _discover_locales(self) -> None:
        self._locales.clear()
        for folder in self._locale_search_dirs():
            if not folder.is_dir():
                continue
            for path in sorted(folder.glob('*.json')):
                try:
                    data = json.loads(path.read_text(encoding='utf-8'))
                except (OSError, json.JSONDecodeError):
                    continue
                code = (data.get('meta') or {}).get('code') or path.stem
                self._locales[code] = data

    def _locale_search_dirs(self) -> list[Path]:
        dirs: list[Path] = [_BUILTIN_LOCALES_DIR]
        cwd_locales = Path.cwd() / 'locales'
        if cwd_locales != _BUILTIN_LOCALES_DIR:
            dirs.append(cwd_locales)
        if self._locales_folder:
            custom = Path(self._locales_folder)
            if custom not in dirs:
                dirs.append(custom)
        return dirs

    def reload_locales(self, locales_folder: str | None = None) -> None:
        if locales_folder is not None:
            self._locales_folder = (locales_folder or '').strip()
        current = self._language
        self._discover_locales()
        if current not in self._locales:
            current = 'pt' if 'pt' in self._locales else next(iter(self._locales), 'pt')
        self.set_language(current)

    def set_language(self, code: str) -> None:
        if code not in self._locales:
            code = 'pt' if 'pt' in self._locales else next(iter(self._locales), 'pt')
        self._language = code
        self._catalog = self._locales.get(code, {})

    @property
    def language(self) -> str:
        return self._language

    def available_languages(self) -> list[tuple[str, str]]:
        """Lista (código, nome nativo) ordenada por nome."""
        items: list[tuple[str, str]] = []
        for code, data in self._locales.items():
            meta = data.get('meta') or {}
            label = meta.get('native_name') or meta.get('name') or code
            items.append((code, label))
        return sorted(items, key=lambda item: item[1].lower())

    def language_label(self, code: str | None = None) -> str:
        code = code or self._language
        data = self._locales.get(code, {})
        meta = data.get('meta') or {}
        return meta.get('native_name') or meta.get('name') or code

    def locales_folder(self) -> str:
        return self._locales_folder

    def default_user_locales_dir(self) -> Path:
        return Path.cwd() / 'locales'

    def t(self, key: str, **kwargs) -> str:
        node: Any = self._catalog
        for part in key.split('.'):
            if isinstance(node, dict):
                node = node.get(part)
            else:
                node = None
                break
        if node is None:
            return key
        text = str(node)
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, ValueError):
                return text
        return text

    def pdf_mode_label(self) -> str:
        return self.t('main.create_pdf')

    def is_pdf_mode_label(self, label: str) -> bool:
        return label == PDF_MODE_SENTINEL or label == self.pdf_mode_label()

    def resolve_printer_selection(self, combo_label: str) -> str:
        if self.is_pdf_mode_label(combo_label):
            return PDF_MODE_SENTINEL
        return combo_label

    def paper_color_label(self, db_color: str) -> str:
        key = f'paper.{db_color}'
        translated = self.t(key)
        return translated if translated != key else db_color


_instance = I18n()


def get_i18n() -> I18n:
    return _instance


def init_i18n(config: dict | None = None) -> None:
    _instance.init(config)


def t(key: str, **kwargs) -> str:
    return _instance.t(key, **kwargs)


def set_language(code: str) -> None:
    _instance.set_language(code)


def get_language() -> str:
    return _instance.language


def available_languages() -> list[tuple[str, str]]:
    return _instance.available_languages()


def reload_locales(locales_folder: str | None = None) -> None:
    _instance.reload_locales(locales_folder)


def pdf_mode_label() -> str:
    return _instance.pdf_mode_label()


def is_pdf_mode_label(label: str) -> bool:
    return _instance.is_pdf_mode_label(label)


def resolve_printer_selection(label: str) -> str:
    return _instance.resolve_printer_selection(label)


def paper_color_label(db_color: str) -> str:
    return _instance.paper_color_label(db_color)
