# ArtemiS

ArtemiS is a **Windows desktop GUI application** (Python + CustomTkinter/Tkinter) for
batch-generating and printing Brazilian postal *Aviso de Recebimento* (AR) forms from
CSV work orders. See `docs/PROJECT_OVERVIEW.md` (Portuguese) for full functionality.

Entry point: `Main.py` → `app.bootstrap.main()`. Application code lives under `app/`
(models, services, ui, utils). See `docs/AI_CONTEXT.md` for architecture and refactor status.

### Windows setup (after clone)
- `pip install -r requirements.txt` — Ghostscript já vem em `vendor/ghostscript/` (sem script extra).
- Build: `.\scripts\build.ps1` (ou `pyinstaller Main.spec`) → pasta `dist/` completa.
- Verificar: `.\scripts\verify_dist.ps1` — depois copie **`dist/` inteira** para os PCs.
- No PC destino: `.\scripts\test_ghostscript_dist.ps1` na pasta com `Main.exe`.
- Use `config.dist.json` como modelo de `config.json` na primeira instalação (caminhos relativos).

## Cursor Cloud specific instructions

This repo targets Windows, but it runs on the Linux cloud VM for development via a thin
compatibility layer that does **not** modify any application source.

### Running the app (Linux)
- Use the launcher, not `Main.py` directly:
  `DISPLAY=:1 .venv/bin/python run_linux.py`
- `run_linux.py` adds `dev_stubs/` to `sys.path` (Windows-only `win32*` stubs) and no-ops
  `iconbitmap` (X11 Tk cannot load Windows `.ico` icons). It then runs `Main.py` unchanged.
- Config access uses Windows identity stubs; on Linux the dev stubs treat the current user
  as a local administrator so the gear icon (⚙) opens settings without AD/COM.

### Environment facts (non-obvious)
- **Python 3.10+** is required (tested on **3.11**, **3.12**, and **3.14**); the venv lives at `.venv`.
- Install deps from **`requirements-linux.txt`**, not `requirements.txt`. The Windows
  `requirements.txt` includes `pywin32` (no Linux wheel; stubs in `dev_stubs/`).
- Smoke test (Linux): `./scripts/smoke_test_env.sh python3.14`
- **Printing is Windows-only** and unavailable here: `pywin32` is replaced by stubs in
  `dev_stubs/` and `PDFtoPrinter.exe` cannot run. Printer enumeration returns empty; print
  actions raise if exercised. Everything else (DB, client/product management, template
  editor, PDF + barcode/QR/DataMatrix generation) works on Linux.
- **Font filenames are case-sensitive on Linux.** `app/services/pdf_service.py` references
  e.g. `fontes/Arial.ttf`, `fontes/arialn.ttf`, `fontes/arialnb.ttf`, `fontes/Morganite-Semibold.ttf`
  whose real files differ only in case. Case-variant **symlinks** in `fontes/` fix this and
  are intentionally **not committed** (they would corrupt the font files on a Windows
  checkout). They persist in the VM snapshot; if missing, recreate from `fontes/`:
  `for r in Arial.ttf arialn.ttf arialnb.ttf Morganite-Semibold.ttf; do m=$(ls fontes | grep -ix "$r"); [ -n "$m" ] && ln -sf "$m" "fontes/$r"; done`
- `config.json` points `search_folder` at `C:\AR`; on Linux the app harmlessly creates a
  literal directory named `C:\AR` in the working directory.

### Lint / test / build
- There is **no configured linter and no test suite**. Use a syntax check:
  `.venv/bin/python -m py_compile Main.py app/bootstrap.py`
- "Build" = PyInstaller (`Main.spec`); it produces a Windows `.exe` and is not used for Linux
  development.
