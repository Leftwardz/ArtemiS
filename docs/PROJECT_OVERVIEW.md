# ArtemiS — Project Overview

Functional and structural documentation for the project in its current form.  
For development guidelines and architecture decisions, see `docs/AI_CONTEXT.md` and `docs/DECISIONS.md`.

---

## What it is

**ArtemiS** is a Windows desktop application (Python) for batch printing of Brazilian postal **Aviso de Recebimento (AR)** forms and related label workflows.

The platform is designed as a single tool for the full print pipeline: template design, CSV-driven variable data, multi-label imposition on a physical sheet, two-sided AR layouts, operational reporting, and dispatch to any Windows printer — including label printers such as Zebra models registered through the standard Windows print driver.

### What the system does

- Reads semicolon-delimited CSV work-order (WO) files from configurable folders.
- Matches variable data to visual layouts stored per client and product.
- Generates dynamic PDFs with text, logos, barcodes (Code 128, Code 39), QR codes, and DataMatrix.
- Imposes **multiple labels on one sheet** using preset AR layouts or a fully custom label grid.
- Supports **two-sided AR (“depth”)** by placing selected elements on the back of the physical sheet.
- Supports **column-depth packing** so records fill down each column before moving to the next — a layout choice that simplifies guillotine cutting.
- Sends batches to Windows printers via `PDFtoPrinter.exe` (up to five parallel queues), Ghostscript, or other selectable print engines; or exports merged PDFs for review.
- Provides a visual template editor, Windows-identity-based administration, selective reprint (Remake), and **audit / reporting** across production stations.

**Goal:** standardize and speed up AR and label production, eliminating manual alignment through templates that map CSV columns to layout elements, with queue validation and partial reprint support.

### Stack

| Layer | Technology |
|--------|------------|
| UI | CustomTkinter / Tkinter |
| Persistence | SQLAlchemy + SQLite |
| PDF | ReportLab |
| Windows printing | `PDFtoPrinter.exe`, Win32 print APIs, Ghostscript |
| Distribution | PyInstaller (`Main.spec` → `.exe`) |

---

## Printing capabilities in depth

### Multiple labels on one sheet

ArtemiS is not limited to one AR per page. Products can use:

| Mode | Description |
|------|-------------|
| **3 per sheet — vertical** | Three AR slots stacked on A4 |
| **2 per sheet — horizontal** | Two AR slots side by side |
| **2 per sheet — vertical** | Two AR slots stacked |
| **1 per sheet — A4** | Full A4 page per record |
| **Custom** | Arbitrary sheet size, label size, margins, and grid (columns × rows) |

In **Custom** mode the designer defines:

- Sheet preset (A4, A3, Letter, landscape variants, or fully custom mm dimensions).
- Label width and height in millimetres.
- Grid: number of columns and rows, gaps, and top/left margins.
- **Fill order** (packing): *Row by row* or *Column by column* (see below).
- Two editing scopes: **Label** (content inside each slot) and **Header** (sheet-level elements such as group titles and page numbers).

Each CSV record occupies the next free slot on the sheet according to the chosen packing order. When a sheet is full, the next record starts a new physical page.

### Zebra and thermal label sheets

There is no separate ZPL generator. Instead, **Custom** layout mode is the generic label engine:

1. Measure the physical label (or die-cut area) in millimetres.
2. Choose a sheet preset that matches the stock loaded in the printer (or define custom mm size).
3. Set label width/height, grid, and margins to match the label positions on that stock.
4. Register the Zebra (or any) printer in **Settings → Printing** using its Windows printer name.
5. Run production as usual — ArtemiS builds a PDF and sends it through the selected print engine.

Because output is PDF → Windows spooler, any printer with a working Windows driver (including Zebra) can print the imposed grid. Label dimensions and grid spacing are under full administrator control.

### AR with depth (duplex / back side)

Some AR forms need content on **both sides** of the paper (front and back). In the template editor, each element has a **Duplex (back)** option:

- Elements without the flag are drawn on the **front** of the physical sheet.
- Elements with **Duplex (back)** are drawn on the **reverse** side, at the same position offsets.

At PDF generation time, ArtemiS renders the front, turns the page, renders back-side elements, and turns again before the next sheet. This gives a true two-sided document without maintaining two separate products.

**Requirements for duplex jobs:**

- The product must use the same duplex setting consistently across a batch (no mixing duplex and non-duplex products in one queue).
- The selected print engine must support per-job duplex (Ghostscript or Win32 DEVMODE). PDFtoPrinter does not control duplex per job and will block duplex batches.

In the editor, back-side elements are shown with a distinct style so the designer can verify front/back alignment on screen.

### Column depth — packing order for easier cutting

When several labels share one sheet, **fill order** determines which slot receives the next CSV record. This is configured in Custom mode under **Order**:

| Packing | Behaviour | Typical use |
|---------|-----------|-------------|
| **Row by row** (`sequential`) | Fills left → right along a row, then moves to the next row | Reading order matches visual rows |
| **Column by column** (`column_depth`) | Fills top → bottom in the first column, then the next column | **Guillotine / strip cutting** |

**Why column depth helps cutting**

With *Column by column*, records 1, 2, 3… stack vertically in column 1 before record 4 moves to the top of column 2. After printing:

1. Cut the sheet **vertically** between columns (guillotine).
2. Each resulting strip already has its records in top-to-bottom order — no need to re-sort pieces after cutting.

Example on a 3×3 grid with four records:

```
Row by row:          Column by column:
[1][2][3]            [1][4][7]
[4][5][6]            [2][5][8]
[7][8][9]            [3][6][9]
```

For hand cutting or stack cutting by column, *Column by column* keeps each strip internally consistent.

**Sheet headers and grouping**

In Custom mode, elements in **Header** scope can define grouping keys (via segment columns). Records that share the same header values stay on the same sheet group, with optional `{p}` / `{t}` placeholders for page number and total pages within the group.

Optional cut guides (`show_cut_guides` in layout config) can draw dashed rectangles around each slot on the PDF to assist trimming (currently stored in layout JSON; exposed through the layout model).

---

## Functional modules

### 1. Production — main screen (`App`)

File: `app/ui/main_app.py`

- Windows printer selection or **Create PDF** mode.
- Filter by **print group** (registered subfolders of the WO search path).
- WO entry by typing or barcode scanner.
- Queue validation: client/product must exist; all WOs in a queue must share paper colour and size.
- Visual indicator of product paper colour (Green, Blue, Pink, Yellow, Ivory, White).
- Background-thread PDF generation and printing with responsive UI.
- Progress panel (`LoadingBarFrame`) for up to five simultaneous printers.

Services: `work_queue_service`, `production_service`, `print_job_coordinator`, `pdf_service`, `print_service`.

### 2. Template designer (`EditWindow`)

File: `app/ui/designer_window.py`

- Canvas with orientation presets or custom sheet grid.
- Tools: select, line, rectangle, fixed text, counter, segment, barcode, image (BLOB in database).
- Properties panel: coordinates, fonts, rotation (0°/90°/180°/270°), CSV column binding, default values, duplex flag.
- Shortcuts: `Delete`, arrow keys, `Ctrl+Z` (undo, 10 levels), `Ctrl+C` (duplicate — segments excluded; see limitations).
- CSV file preview with per-line data binding and test PDF (`temp/text.pdf`).
- JSON import/export of products (geometry + Base64 images).

Services: `designer_service`, `pdf_service`; adapter `designer_canvas_adapter`.

### 3. Remake — selective reprint (`RemakeWindow`)

File: `app/ui/remake_window.py`

- Enabled with **Enable Remake** when scanning a WO already archived under `Old/`.
- Filters by line range, RankInJob, AR number, or recipient name.
- Builds a partial queue and generates PDF for selected records only.

Service: `remake_service`.

### 4. Settings and administration (`ConfigWindow`)

File: `app/ui/config_window.py`

- Access via Windows identity (no separate ArtemiS password).
- Local and domain administrators always allowed; other users/groups granted in configuration.
- AD and local machine user/group search.
- CRUD for clients and products; duplicate; layout import/export.
- Global paths: WO search folder and SQLite file (`config.json`).
- Printer registration, print engine selection, and print groups for the production screen.
- **Audit / logs** — query centralised production and configuration events (see Reports below).

Services: `admin_service`, `settings_service`, `app/utils/windows_auth.py`, `app/audit/`.

### 5. Reports and audit (`AuditWindow`)

Module: `app/audit/` — UI in `app/ui/config_window.py` (AuditWindow)

Operational reporting without a separate reporting server:

- Every PC writes events to a **local** audit database (`%LOCALAPPDATA%\ArtemiS\audit`).
- A background aggregator copies unsynced events to a **central** SQLite file on the network (`audit_central_location` in `config.json`).
- Administrators open **Audit / logs** in Settings to filter by date, user, printer, file, and category.

| Category | Examples |
|----------|----------|
| `print` | Job sent, Create PDF, success/failure |
| `cadastro` | Client/product/printer/access changes |
| `config_access` | Settings opened (granted/denied) |
| `error` | Production errors with detail |

Logging is best-effort and never blocks printing. See `docs/AUDIT_LOG.md` for architecture detail.

---

## Usage flows

### Administrator — setup and design

1. Open ArtemiS; click ⚙ **Settings** (requires Windows admin or entry in access list).
2. Set WO search folder (e.g. `C:\AR`) and SQLite database path.
3. Optionally grant other users/groups under **Manage access**.
4. Register clients and products.
5. Open the editor: paper type, orientation (preset or Custom grid), and physical paper colour.
6. Draw the layout; bind elements to CSV columns (e.g. `Column_2` → address). Mark back-side elements with **Duplex (back)** when needed.
7. For custom grids, set label size, columns×rows, and packing order (*Column by column* if cutting by column).
8. Generate a test PDF, verify alignment, and save.

### Operator — production

1. Select printer and print group.
2. Scan or type WO code; system locates CSV in the group subfolder.
3. First line identifies client/product and loads the layout.
4. Check indicated paper colour; load matching stock.
5. Add WOs to queue; system blocks mixed paper colour or size.
6. Click **Start**: PDFs generated in `temp/`, merged under `{search_folder}/PDFs/`.
7. Print via selected engine or open PDF if **Create PDF** is selected.
8. Processed CSV moved to `Old/` under the batch folder.

### Operator — remake

1. Enable **Enable Remake**.
2. Scan WO; file loaded from `Old/`.
3. Filter defective lines in the Remake window.
4. Add to queue and click **Start**.
5. Only selected pages reprint; original CSV stays in `Old/`.

---

## Repository structure

```
ArtemiS/
├── Main.py / main.py       # Entry point → app.bootstrap.main()
├── config.json             # database_location, search_folder, audit_*, print_backend
├── database.db             # SQLite (clients, products, drawings, printers, access, …)
├── Main.spec               # PyInstaller
├── azure.tcl               # Azure theme (Treeviews)
├── requirements.txt
├── PDFtoPrinter.exe        # + _2 … _5 for parallel printing
├── fontes/                 # TTF/OTF (canvas and PDF)
├── theme/                  # Theme assets
├── img/                    # Icons
├── temp/                   # Barcodes and intermediate PDFs
└── app/
    ├── bootstrap.py        # Init: config, database, audit, App
    ├── runtime.py          # ApplicationContext (config + db)
    ├── audit/              # Local-first audit and central aggregation
    ├── models/
    │   ├── schema.py
    │   ├── sheet_layout.py # Custom grid / packing model
    │   └── database_manager.py
    ├── utils/
    │   ├── file_parser.py
    │   ├── barcode_generator.py
    │   ├── printing/       # Pluggable print backends
    │   └── …
    ├── services/
    │   ├── pdf_service.py
    │   ├── print_service.py
    │   ├── production_service.py
    │   ├── layout_service.py
    │   ├── sheet_grouping.py
    │   └── …
    └── ui/
        ├── main_app.py
        ├── designer_window.py
        ├── config_window.py
        └── remake_window.py
```

### Layers

| Layer | Responsibility |
|--------|----------------|
| `app/ui` | Windows, visual components, operator interaction |
| `app/services` | Business rules, production/PDF/print orchestration |
| `app/models` | SQLAlchemy schema, `SheetLayout`, `DataBase` |
| `app/utils` | CSV, barcodes, printing backends, window geometry |
| `app/audit` | Operational logging and central report query |
| `app/runtime` | Shared application state (`ApplicationContext`) |

Bootstrap (`app/bootstrap.py`) loads `config.json`, opens `DataBase`, starts audit workers, registers context in `runtime.context`, and runs the UI loop.

---

## Network deployment (shared SQLite)

### Operational model

| Component | Where it runs | Notes |
|-----------|---------------|-------|
| **Executable / Python app** | Local on each production PC | One process per station; UI, PDF, and printing are local |
| **`config.json`** | Local per PC (or standard image) | Points to paths; `database_location` often UNC (e.g. `\\server\ArtemiS\database.db`) |
| **`database.db` (SQLite)** | Shared network folder | All PCs read/write the **same file** for layouts, clients, products, print groups, `config_access` |
| **WO folders (`search_folder`)** | Network or local | Batch CSVs; path may differ per site |
| **`temp/`** | Local per PC | Intermediate PDFs and barcodes — not shared |
| **Audit central DB** | Network path (`audit_central_location`) | Aggregated logs for reporting; local audit DB always on each PC |

**Identity and printing are local; layout catalogue and configuration rules are centralised in shared SQLite.**

### Windows auth × shared database

No logical conflict between Windows auth (2026-06) and shared SQLite. Layers are separate:

1. **Who may open ⚙ Settings** — decided **on the PC** via Windows session (`app/utils/windows_auth.py`).
2. **Who is on the allow list** — read from **shared SQLite** (`config_access`), same as clients/products.

**Production screen** (Start, queue, print) does not use Windows auth — operators work normally.

### Recommendations for IT

1. Point `database_location` to a stable UNC path with backup.
2. Manage access with **domain groups** (e.g. `COMPANY\ArtemiS-Config`).
3. Keep production PCs **domain-joined** when possible.
4. Restrict Settings access; day-to-day operators do not need `config_access`.
5. Point `audit_central_location` to a network path for cross-station reporting.

---

## Known limitations

### Segment duplication in the editor

In `app/ui/designer_window.py`, `Ctrl+C` does not duplicate **Segment** blocks — the action is intentionally ignored. Identical segments must be recreated via the properties panel.

### Missing CSV column

In `app/services/pdf_service.py`, if a layout references a column that does not exist in the CSV, the corresponding field is omitted from the PDF with no UI error. Inconsistent layouts may produce silently incomplete documents.

### Configuration access

Settings use the **logged-in Windows identity** on the station. Local (`Administrators`) and domain (`Domain Admins`) administrators always have access. Others may be granted in **Manage access** (`config_access` table). Legacy `users` table (SHA-256 login) remains in the database but is unused.

### Print engine constraints

- **PDFtoPrinter**: no per-job duplex, paper size, or orientation control — printer defaults must be correct.
- **Duplex layouts**: require Ghostscript or Win32 DEVMODE backend.
- **Mixed duplex products** in one queue are rejected.

---

## Glossary

| Term | Meaning |
|------|---------|
| **AR** | Aviso de Recebimento (Brazilian postal receipt notice) |
| **WO** | Work order — batch CSV file |
| **Client / Product** | Pair identifying layout and print rules in the database |
| **Print group** | WO search subfolder under `search_folder` |
| **Custom layout** | User-defined sheet and label grid (mm), including Zebra/thermal stock |
| **Packing / column depth** | Fill order: row-by-row vs column-by-column for cutting workflow |
| **Duplex (back)** | Element drawn on the reverse side of the physical sheet |
| **Label scope** | Template content repeated in each grid slot |
| **Header scope** | Sheet-level content (titles, group pagination) |
| **Old/** | Subfolder where processed WOs are archived |
| **Remake** | Partial reprint of selected lines from an archived WO |
| **Audit / reports** | Local-first event log with optional central aggregation for querying |
