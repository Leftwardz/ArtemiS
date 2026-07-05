"""Build user-manual PDFs from Markdown sources and screenshots."""

from __future__ import annotations

import html
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown
from markdown.extensions.tables import TableExtension

ROOT = Path(__file__).resolve().parents[1]
USER_DOCS = ROOT / 'docs' / 'user'
OUTPUT_DIR = USER_DOCS / 'output'
TEMPLATE_CSS = USER_DOCS / 'templates' / 'manual.css'

GUIDES = [
    {
        'source': USER_DOCS / 'en' / 'production-user-guide.md',
        'pdf': OUTPUT_DIR / 'ArtemiS_Production_User_Guide_EN.pdf',
        'doc_id': 'production-en',
    },
    {
        'source': USER_DOCS / 'en' / 'administrator-guide.md',
        'pdf': OUTPUT_DIR / 'ArtemiS_Administrator_Guide_EN.pdf',
        'doc_id': 'admin-en',
    },
]


def _parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    meta: dict[str, str] = {}
    if not text.startswith('---'):
        return meta, text
    end = text.find('\n---', 3)
    if end == -1:
        return meta, text
    block = text[3:end].strip()
    body = text[end + 4 :].lstrip('\n')
    for line in block.splitlines():
        if ':' in line:
            key, value = line.split(':', 1)
            meta[key.strip()] = value.strip()
    return meta, body


def _enhance_markdown_html(html_text: str, source_path: Path) -> str:
    html_text = re.sub(
        r'<p><div class="(note|warning|tip)">',
        r'<div class="\1"><p>',
        html_text,
    )
    html_text = re.sub(
        r'</div>\s*</p>',
        '</p></div>',
        html_text,
    )

    def _abs_img_src(src: str) -> str:
        resolved = (source_path.parent / src).resolve()
        return resolved.as_uri() if resolved.is_file() else src

    def _figure_block(match: re.Match[str]) -> str:
        alt = html.escape(match.group(1))
        src = _abs_img_src(match.group(2))
        caption = html.escape(match.group(3).strip())
        return (
            f'<figure><img src="{html.escape(src, quote=True)}" alt="{alt}"/>'
            f'<figcaption>{caption}</figcaption></figure>'
        )

    # Markdown wraps image + italic caption in one paragraph.
    html_text = re.sub(
        r'<p><img alt="([^"]*)" src="([^"]+)" />\s*<em>(.*?)</em></p>',
        _figure_block,
        html_text,
        flags=re.DOTALL,
    )

    def _resolve_img(match: re.Match[str]) -> str:
        alt = match.group(1)
        src = _abs_img_src(match.group(2))
        return f'<img alt="{alt}" src="{html.escape(src, quote=True)}"/>'

    html_text = re.sub(
        r'<img alt="([^"]*)" src="([^"]+)" />',
        _resolve_img,
        html_text,
    )
    return html_text


def _wrap_html(meta: dict[str, str], body_html: str, source_path: Path) -> str:
    title = html.escape(meta.get('title', source_path.stem))
    subtitle = html.escape(meta.get('subtitle', ''))
    audience = html.escape(meta.get('audience', ''))
    version = html.escape(meta.get('version', ''))
    meta_line = ' · '.join(x for x in (audience, f'v{version}' if version else '') if x)
    css_uri = TEMPLATE_CSS.resolve().as_uri()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>{title}</title>
  <link rel="stylesheet" href="{css_uri}"/>
</head>
<body>
  <header class="doc-header">
    <h1>{title}</h1>
    <p class="subtitle">{subtitle}</p>
    <p class="meta">{meta_line}</p>
  </header>
  <main>
    {body_html}
  </main>
  <footer class="doc-footer">ArtemiS — {title}</footer>
</body>
</html>
"""


def _find_chrome() -> list[str]:
    candidates = [
        '/usr/bin/google-chrome-stable',
        '/opt/google/chrome/google-chrome',
        'google-chrome-stable',
        'google-chrome',
        'chromium',
        'chromium-browser',
        'microsoft-edge',
    ]
    for name in candidates:
        path = shutil.which(name) or (name if Path(name).is_file() else None)
        if path:
            return [path]
    return []


def _html_to_pdf(html_path: Path, pdf_path: Path) -> None:
    chrome = _find_chrome()
    if not chrome:
        raise RuntimeError('No Chromium-based browser found for PDF export.')
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    user_data = Path(tempfile.gettempdir()) / 'artemis-chrome-profile'
    user_data.mkdir(parents=True, exist_ok=True)
    cmd = [
        *chrome,
        '--headless=new',
        '--disable-gpu',
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-software-rasterizer',
        '--run-all-compositor-stages-before-draw',
        '--virtual-time-budget=15000',
        f'--user-data-dir={user_data}',
        f'--print-to-pdf={pdf_path}',
        '--no-pdf-header-footer',
        html_path.resolve().as_uri(),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if result.returncode != 0 or not pdf_path.is_file():
        raise RuntimeError(
            f'PDF export failed (exit {result.returncode}): {result.stderr.strip()}'
        )


BUILD_DIR = OUTPUT_DIR / '.build'


def build_guide(guide: dict) -> Path:
    source: Path = guide['source']
    pdf: Path = guide['pdf']
    raw = source.read_text(encoding='utf-8')
    meta, md_body = _parse_front_matter(raw)
    body_html = markdown.markdown(
        md_body,
        extensions=[TableExtension(), 'fenced_code', 'sane_lists'],
    )
    body_html = _enhance_markdown_html(body_html, source)
    full_html = _wrap_html(meta, body_html, source)

    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    html_path = BUILD_DIR / f"{guide['doc_id']}.html"
    html_path.write_text(full_html, encoding='utf-8')
    _html_to_pdf(html_path, pdf)
    print(f'Built {pdf.relative_to(ROOT)}')
    return pdf


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    built = []
    for guide in GUIDES:
        if not guide['source'].is_file():
            print(f'Missing source: {guide["source"]}', file=sys.stderr)
            return 1
        built.append(build_guide(guide))
    print(f'\n{len(built)} PDF(s) in {OUTPUT_DIR.relative_to(ROOT)}/')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
