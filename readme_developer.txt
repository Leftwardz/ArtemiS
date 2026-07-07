ArtemiS — Developer Guide
=========================

Plain-text copy of docs/DEVELOPER.md (same content; .md remains the source in
the docs/ folder).

How to clone, build, and work on the codebase. For product features and
operator flows, see readme.txt.


FIRST-TIME SETUP (WINDOWS)
--------------------------

The dist/ build output is NOT in Git. Each developer generates it locally.

1. Install dependencies

     pip install -r requirements.txt

   Ghostscript ships under vendor/ghostscript/. If missing, scripts/build.ps1
   can run scripts/fetch_ghostscript.ps1.

2. Local configuration

   Copy config.dist.json to config.json:

     database_location — SQLite path (default database.db).
     search_folder     — WO root (e.g. C:\AR).

3. Build

     .\scripts\build.ps1

   Runs PyInstaller (Main.spec), verifies output, produces dist/.

   Or manually: pyinstaller Main.spec then .\scripts\verify_dist.ps1.

4. Deploy

   Copy the entire dist/ folder to production PCs. Run
   .\scripts\test_ghostscript_dist.ps1 on the target machine to confirm
   Ghostscript.

5. Run from source (dev only)

     python Main.py

   Production stations should use dist/Main.exe.


LINUX (CURSOR CLOUD / CI)
-------------------------

See AGENTS.md: Python 3.11, requirements-linux.txt, run_linux.py. Printing is
stubbed; PDF and UI development work without Windows.


STACK
-----

  UI           CustomTkinter / Tkinter
  Persistence  SQLAlchemy + SQLite
  PDF          ReportLab
  Printing     PDFtoPrinter.exe, Ghostscript, Win32 APIs (app/utils/printing/)
  Packaging    PyInstaller (Main.spec)


REPOSITORY LAYOUT
-----------------

  ArtemiS/
  ├── Main.py                 Entry → app.bootstrap.main()
  ├── config.dist.json        Template for config.json
  ├── Main.spec               PyInstaller spec
  ├── requirements.txt        Windows production deps
  ├── requirements-linux.txt  Linux dev deps
  ├── scripts/                build.ps1, verify_dist.ps1, …
  ├── vendor/ghostscript/     Bundled Ghostscript (copied into dist/)
  ├── fontes/                 Fonts for canvas and PDF
  ├── PDFtoPrinter*.exe       Print helpers (×5 for parallelism)
  └── app/
      ├── bootstrap.py        Config, DB, audit, main window
      ├── runtime.py          ApplicationContext
      ├── audit/              Local-first audit + central aggregation
      ├── models/             schema, SheetLayout, DataBase
      ├── services/           pdf, print, production, designer, …
      ├── ui/                 main_app, designer_window, config_window, …
      └── utils/              CSV, barcodes, printing backends, …

Layers
  app/ui        Windows and operator interaction
  app/services  Business logic, PDF/print orchestration
  app/models    SQLAlchemy schema and layout models
  app/utils     CSV, barcodes, print backends
  app/audit     Event logging
  app/runtime   Shared ApplicationContext

app/bootstrap.py loads config.json, opens the database, starts audit workers,
and launches the UI.


KEY MODULES (CODE MAP)
-----------------------

  Production         app/ui/main_app.py
                     app/services/production_service.py
                     app/services/work_queue_service.py
  PDF generation     app/services/pdf_service.py
                     app/utils/barcode_generator.py
  Printing           app/services/print_service.py
                     app/utils/printing/
  Designer           app/ui/designer_window.py
                     app/services/designer_service.py
  Remake             app/ui/remake_window.py
                     app/services/remake_service.py
  Admin / settings   app/ui/config_window.py
                     app/services/admin_service.py
                     app/services/settings_service.py
  Custom grid        app/models/sheet_layout.py
                     app/services/layout_service.py
                     app/services/sheet_grouping.py
  Auth (settings)    app/utils/windows_auth.py

Further reading: docs/PRINTING_BACKENDS.md (print engines).


NETWORK DEPLOYMENT
------------------

  App / dist/        Each production PC — local process; printing is local
  config.json        Each PC — often points database_location to UNC
  database.db        Shared network folder — layouts, clients, products, access
  search_folder      Network or local — WO CSV batches
  temp/              Local per PC — not shared
  Audit central DB   Network (audit_central_location) — optional aggregated logs

Settings access: Windows identity on the PC; allow list in shared SQLite
(config_access). Production does not require Settings access.

IT recommendations: stable UNC + backup for database.db; prefer domain groups
for access; avoid concurrent layout edits from many PCs (SQLite on network
shares).


KNOWN LIMITATIONS (DEVELOPMENT)
-------------------------------

  Segment duplicate   Ctrl+C does not duplicate Segment blocks
  Missing CSV column  Omitted silently in PDF — no UI warning
  Legacy users table  Unused; auth is Windows + config_access
  PDFtoPrinter        No per-job duplex, landscape, paper, copies, or tray
  Duplex / landscape  Require Ghostscript or Win32 DEVMODE; mixed queues rejected
  Print thread        Jobs run on Tk thread; raster backends may block UI


BUILD AND VERIFY SCRIPTS
------------------------

  scripts/build.ps1                  PyInstaller build + verify + GS smoke test
  scripts/verify_dist.ps1            Check dist/ completeness before deploy
  scripts/test_ghostscript_dist.ps1  Validate Ghostscript beside Main.exe
  scripts/fetch_ghostscript.ps1      Download Ghostscript into vendor/ if missing


WHAT NOT TO COMMIT
------------------

See .gitignore: dist/, config.json, database.db, audit databases, logs/,
temp/, .venv/, local WO folders.
