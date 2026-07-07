# ArtemiS — Functional Overview

What the application does, how its main features fit together, and typical usage flows.  
For clone, build, and repository layout, see `docs/DEVELOPER.md`.

---

## What it is

**ArtemiS** is a Windows desktop application for batch printing of Brazilian postal **Aviso de Recebimento (AR)** forms and related label workflows.

It covers the full production pipeline in one tool: template design, CSV-driven variable data, multiple labels per sheet, two-sided forms, operational reporting, and printing to any Windows printer — including Zebra and other label printers registered through the standard Windows driver.

### Capabilities

- Reads semicolon-delimited CSV work-order (WO) files from configurable folders.
- Matches variable data to visual layouts stored per **client** and **product**.
- Generates PDFs with text, logos, barcodes (Code 128, Code 39), QR codes, and DataMatrix.
- Imposes **multiple labels on one sheet** — preset AR layouts or a custom label grid.
- Uses **vertical imposition depth** on *3 per sheet — vertical* and *2 per sheet — vertical* so records stay in CSV order after horizontal cutting.
- Supports **duplex (back-side)** elements — separate from imposition depth.
- Prints via selectable engines or exports merged PDFs for review.
- Provides a visual template editor, administration, selective reprint (**Remake**), and **audit / reporting** across stations.

**Goal:** standardize AR and label production, replace manual alignment with templates bound to CSV columns, validate print queues, and support partial reprints.

### Work order CSV — first four columns (required structure)

Every WO file is semicolon-delimited. The **first four columns** are fixed by convention — ArtemiS reads them for product selection, WO identification, and **Remake** search. Additional columns are free for template bindings (`Coluna_5`, `Coluna_6`, …).

| Column | Content | Used for |
|--------|---------|----------|
| **1** | `client name - product name` | **Product selection.** The first data row must use this exact pattern (client and product separated by ` - `). ArtemiS splits the string to find the registered **client / product** pair and load the correct layout. |
| **2** | Primary barcode | **Remake — AR / barcode lookup.** Scan or type the main barcode (or AR number) to find the matching row in an archived WO. |
| **3** | Client or company name | **Remake — name lookup.** Search by recipient name or company name when reprinting selected forms. |
| **4** | Work code / file ID | **Standardization.** Same work identifier on every row (e.g. batch or file code). Shown in the Remake window and used to align WO files with operator scans; keep it consistent across the batch. |

<div class="note">

**Important:** Do not reorder or repurpose these four columns. Production will not resolve the correct product if column 1 is wrong; Remake filters depend on columns 2 and 3.

</div>

---

## Printing features

### Multiple labels on one sheet

| Mode | Description |
|------|-------------|
| **3 per sheet — vertical** | Three AR slots stacked on A4; uses **depth imposition** |
| **2 per sheet — horizontal** | Two AR slots side by side |
| **2 per sheet — vertical** | Two AR slots stacked on A4; uses **depth imposition** |
| **1 per sheet — A4** | Full A4 page per record |
| **Custom** | Arbitrary sheet size, label size, margins, and grid (columns × rows) |

In **Custom** mode the administrator defines sheet preset, label dimensions (mm), grid, gaps, margins, fill order (*Row by row* / *Column by column*), and two scopes: **Label** (each slot) and **Header** (sheet-level titles, pagination, etc.).

### Vertical imposition depth (3 and 2 per sheet — vertical only)

**Depth** applies **only** to *3 per sheet — vertical* and *2 per sheet — vertical*. It is **not** duplex and **not** the Custom-mode fill order.

When several ARs share one A4 page stacked vertically, operators often cut the printed stack horizontally. Depth imposition ensures each cut pile stays in CSV order.

ArtemiS splits the file into one stream per vertical slot instead of placing records 1, 2, 3 on the same page:

- **3 vertical:** first third of records → top slot across pages; second third → middle; last third → bottom.
- **2 vertical:** first half → top; second half → bottom.

Example — nine records (1–9), **3 per sheet — vertical**:

| Page | Top | Middle | Bottom |
|------|-----|--------|--------|
| 1 | 1 | 4 | 7 |
| 2 | 2 | 5 | 8 |
| 3 | 3 | 6 | 9 |

After cutting horizontally through the stack: top pile **1–2–3**, middle **4–5–6**, bottom **7–8–9** — no re-sorting.

*2 per sheet — horizontal* and *1 per sheet — A4* do **not** use this algorithm.

### Zebra and thermal labels

There is no ZPL export. **Custom** mode defines label size and grid in millimetres; output is PDF → Windows spooler. Register the Zebra printer in Settings and match grid dimensions to the physical stock.

### Duplex (back side)

Elements marked **Duplex (back)** in the template editor print on the reverse at the same offsets. Unmarked elements print on the front.

Requirements: do not mix duplex and non-duplex products in one queue; use Ghostscript or Win32 DEVMODE (PDFtoPrinter cannot set duplex per job).

### Custom layout — fill order

| Packing | Behaviour |
|---------|-----------|
| **Row by row** | Left → right, then next row |
| **Column by column** | Top → bottom per column, then next column |

Independent of vertical depth on preset AR modes.

**Sheet headers:** Header-scope segments can group records; placeholders `{p}` / `{t}` show page number and total within the group.

### Print engines (operational)

Selected in **Settings → Printing**. Technical detail: `docs/PRINTING_BACKENDS.md`.

| Engine | When to use |
|--------|-------------|
| **PDFtoPrinter** | Standard portrait AR, no duplex. Most tested; fast vector output. Relies on printer preferences already set in Windows. |
| **Ghostscript** | Duplex, landscape, or paper size per job. Recommended for those cases. |
| **Win32 DEVMODE / advanced** | Full per-job control (experimental; rasterised output). |
| **XPS Print API** | Experimental. |

No automatic fallback between engines.

---

## Application areas

### Production

Main operator screen: choose printer or **Create PDF**, pick a **print group**, scan or type WO codes, build a queue, and run **Start**.

- Validates client/product and blocks mixed paper colour or size in one queue.
- Shows product paper colour (Green, Blue, Pink, Yellow, Ivory, White).
- Generates and prints in the background with progress for up to five printers.

### Template designer

Visual editor for layouts: lines, rectangles, text, counters, segments, barcodes, images.

- Bind fields to CSV columns; preview with a sample CSV file; generate test PDF.
- Undo, keyboard nudge, duplicate (segments excepted).
- Import/export products as JSON.

### Remake

Reprint selected lines from a WO already in `Old/`: filter by line range, RankInJob, AR number, or recipient name; print only the chosen records.

### Settings and administration

Windows identity for access (no ArtemiS password). Manage clients, products, printers, print groups, paths, print engine, and who may open Settings.

### Audit and reports

Each PC logs locally; events aggregate to an optional central database. **Audit / logs** in Settings filters by date, user, printer, and category (`print`, configuration changes, errors).

---

## Usage flows

### Administrator — setup and design

1. Open ⚙ **Settings** (Windows admin or granted user).
2. Set WO search folder and database path.
3. Register printers, print groups, clients, and products.
4. Design layout: orientation, paper colour, CSV column bindings.
5. Use **Duplex (back)** only for real two-sided forms.
6. Vertical presets (3 or 2 per sheet) apply depth automatically.
7. Pick print engine (PDFtoPrinter for standard portrait AR).
8. Test PDF, then save.

### Operator — production

1. Select printer and print group.
2. Scan WO; confirm paper colour.
3. Add WOs to queue; click **Start**.
4. CSV archived to `Old/`; PDFs under `{search_folder}/PDFs/` when applicable.

### Operator — remake

1. Enable **Remake**; scan archived WO.
2. Select lines to reprint; **Start**.

---

## Glossary

| Term | Meaning |
|------|---------|
| **AR** | Aviso de Recebimento (Brazilian postal receipt notice) |
| **WO** | Work order — batch CSV file |
| **Client / Product** | Pair identifying layout and print rules |
| **Print group** | Subfolder under the WO search path |
| **Custom layout** | User-defined sheet/label grid (mm) |
| **Depth** | Imposition on 3/2 vertical presets for ordered piles after horizontal cutting |
| **Duplex (back)** | Content on the reverse side of the sheet |
| **Packing** | Custom-mode fill order (row vs column) |
| **Label / Header scope** | Per-slot vs sheet-level template content |
| **Old/** | Archive folder for processed WOs |
| **Remake** | Partial reprint from `Old/` |
| **Audit** | Local-first logs with optional central reporting |
