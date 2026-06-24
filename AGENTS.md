# ArtemiS

ArtemiS is a **Windows desktop GUI application** (Python + Tkinter/CustomTkinter) for
batch-generating and printing Brazilian postal *Aviso de Recebimento* (AR) forms from
CSV work orders. See `docs/PROJECT_OVERVIEW.md` (Portuguese) for full functionality.

There is a single "service": the desktop app, entrypoint `Main.py` (`python Main.py` on
Windows). `Database.py` (SQLAlchemy/SQLite), `pdf_utils.py` (reportlab PDF rendering) and
`utils.py` (barcode/QR/DataMatrix + Windows printing) are imported by it.

## Cursor Cloud specific instructions

This repo targets Windows, but it runs on the Linux cloud VM for development via a thin
compatibility layer that does **not** modify any application source.

### Running the app (Linux)
- Use the launcher, not `Main.py` directly:
  `DISPLAY=:1 .venv/bin/python run_linux.py`
- `run_linux.py` adds `dev_stubs/` to `sys.path` (Windows-only `win32*` stubs) and no-ops
  `iconbitmap` (X11 Tk cannot load Windows `.ico` icons). It then runs `Main.py` unchanged.
- On first launch the app requires registering an admin user via the gear icon; the
  **username must be longer than 5 characters** (e.g. `admin123admin`).

### Environment facts (non-obvious)
- **Python 3.11** is required and the venv lives at `.venv`. The pinned deps (Pillow 9.4.0,
  Levenshtein, etc.) do **not** build on Python 3.12; use `python3.11`.
- Install deps from **`requirements-linux.txt`**, not `requirements.txt`. The original
  `requirements.txt` is the Windows production spec and won't install on Linux (`pywin32`
  has no Linux wheel; `scipy==1.10.1` has no 3.12 build). `requirements-linux.txt` also adds
  `PyPDF2` (imported by `pdf_utils.py` but missing from `requirements.txt`).
- **Printing is Windows-only** and unavailable here: `pywin32` is replaced by stubs in
  `dev_stubs/` and `PDFtoPrinter.exe` cannot run. The print buttons will raise if exercised;
  everything else (DB/auth, client/product management, template editor, PDF + barcode/QR/
  DataMatrix generation) works on Linux.
- **Font filenames are case-sensitive on Linux.** `pdf_utils.py` references e.g.
  `fontes/Arial.ttf`, `fontes/arialn.ttf`, `fontes/arialnb.ttf`, `fontes/Morganite-Semibold.ttf`
  whose real files differ only in case. Case-variant **symlinks** in `fontes/` fix this and
  are intentionally **not committed** (they would corrupt the font files on a Windows
  checkout). They persist in the VM snapshot; if missing, recreate from `fontes/`:
  `for r in Arial.ttf arialn.ttf arialnb.ttf Morganite-Semibold.ttf; do m=$(ls fontes | grep -ix "$r"); [ -n "$m" ] && ln -sf "$m" "fontes/$r"; done`
- `config.json` points `search_folder` at `C:\AR`; on Linux the app harmlessly creates a
  literal directory named `C:\AR` in the working directory.

### Lint / test / build
- There is **no configured linter and no test suite**. Use a syntax check:
  `.venv/bin/python -m py_compile Main.py utils.py pdf_utils.py Database.py`
- "Build" = PyInstaller (`Main.spec`); it produces a Windows `.exe` and is not used for Linux
  development.
