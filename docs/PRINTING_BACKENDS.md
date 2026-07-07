# Printing architecture (multiple backends)

Reference document for the decoupled printing layer and a comparative report
of the available backends.

## Overview

All printing goes through a **single interface** and a **single parameter
contract**:

```
print_service.finish_print_job(...)
   └─ printer_handler.print_pdf_file(...)        # compatibility wrapper
        └─ app.utils.printing.dispatch(job, backend_name)
             └─ <PrintBackend>.print_job(PrintJob) -> PrintResult
```

### Components (`app/utils/printing/`)

| File | Role |
|---|---|
| `base.py` | `PrintJob` (parameters), `PrintResult`, `PrintBackend` (interface). |
| `registry.py` | Registers backends (protected import), availability, and `dispatch()` with logging. |
| `logger.py` | Dedicated log at `logs/print.log`. |
| `devmode.py` | Per-job DEVMODE, `DeviceCapabilities`, spooler status. |
| `pdf_raster.py` | Rasterises PDF→PNG via Ghostscript (for GDI backends). |
| `gdi_print.py` | Draws pages on a DC created with the job DEVMODE. |
| `backends/*.py` | Concrete implementations. |

### `PrintJob` contract

`pdf_path`, `printer`, `copies`, `duplex` (`simplex`/`long_edge`/`short_edge`),
`orientation` (`portrait`/`landscape`), `paper_size` (**DMPAPER** code, e.g.
`9` = A4), `tray` (DMBIN code or `None` = default tray), `slot_index`
(PDFtoPrinter only), `config`.

> **Neutral defaults**: callers currently pass `copies=1`, `simplex`,
> `portrait`, `tray=None`. With that, PDFtoPrinter and Ghostscript behave
> **exactly** as they did before the refactor.

### Guarantees

- **No permanent printer changes**: no backend uses `SetPrinter`. DEVMODE is
  applied to a temporary DC/handle (valid only for the job) — administrator
  rights are not required.
- **Resilience**: a backend that fails to import (missing dependency) is
  simply omitted from the `registry`; the app keeps working with the others.
  Backends never raise — they return `PrintResult(ok=False, ...)`.
- **No automatic fallback** (project decision): if the selected backend fails,
  the error is shown in the UI (current behaviour preserved). There is no
  retry on another backend.

### Logging (`logs/print.log`)

Each job logs: chosen backend, all parameters, command/DEVMODE applied,
printer capabilities (advanced backend), spooler status, and success/failure
with driver/GS error detail.

---

## Comparative report

| Backend | Paper/job | Duplex | Copies | Tray | Orientation | Admin? | Output | Dependency | Maturity |
|---|---|---|---|---|---|---|---|---|---|
| **PDFtoPrinter** | ❌ (uses printer preference) | ❌ | ❌ | ❌ | ❌ | No | Vector (driver) | `PDFtoPrinter*.exe` | Stable (production) |
| **Ghostscript** | ✅ (`-sPAPERSIZE`) | ⚠️ best-effort | ✅ (`-dNumCopies`) | ❌ | ✅ landscape (DEVMODE+GDI) | No | Vector (portrait) / raster (landscape) | Bundled Ghostscript + pywin32 (landscape) | Stable |
| **Win32 DEVMODE** | ✅ (`dmPaperSize`) | ✅ (`dmDuplex`) | ✅ (`dmCopies`) | ✅ (`dmDefaultSource`) | ✅ (`dmOrientation`) | No | **Rasterised** (GDI) | Ghostscript (rasterise only) + pywin32 | Experimental |
| **Win32 advanced** | ✅ | ✅ | ✅ | ✅ | ✅ | No | **Rasterised** (GDI) | same as DEVMODE | Experimental |
| **XPS Print API** | ✅ (from PDF) | ⚠️ driver default | ⚠️ driver default | ⚠️ driver default | ✅ (from PDF) | No | Vector (XPS) | Ghostscript (`xpswrite`) + `XpsPrint.dll` | Experimental |

### PDFtoPrinter (production)
- **Advantages**: simple, fast (immediate handoff to spooler), faithful vector output; parallelism via five executables (`slot_index`).
- **Limitations**: does not control paper/duplex/copies/tray per job — relies on whatever is already configured in the Windows printer preferences (which is why `validate_printer_paper` still enforces correct paper **only** for this backend).

### Ghostscript (production)
- **Advantages**: sets **paper per job** (`-sPAPERSIZE`); vector output via `mswinpr2` in portrait; copies per job; no admin required.
- **Landscape**: the `mswinpr2` device **cannot control physical printer orientation** per job (Ghostscript limitation on Windows). Landscape jobs use the same path as Win32 DEVMODE: rasterise the PDF via Ghostscript and print with `dmOrientation` via GDI.
- **Limitations**: tray is not controlled per job; duplex is *best-effort* (depends on device/driver); process blocks until GS finishes.

### Win32 DEVMODE per job (experimental)
- **Advantages**: **full** per-job control — paper, duplex, copies, tray, and orientation — built in DEVMODE and validated by `DocumentProperties`, **without admin** and **without persisting** anything on the printer.
- **Limitations**: `win32print`/GDI **does not render PDF**; pages are rasterised via Ghostscript (≈300 DPI) and drawn via GDI. Rasterised output (larger, sharpness depends on DPI). So it **still depends on Ghostscript** to rasterise.

### Win32 Print API advanced (experimental)
- **Advantages**: everything DEVMODE offers **plus** `DeviceCapabilities` queries (duplex/copies/paper/trays) with warnings when the job requests unsupported options, and **spooler status** (`EnumJobs`) for log diagnostics.
- **Limitations**: same as the DEVMODE backend (rasterised output, Ghostscript dependency for rasterisation).

### XPS Print API (experimental)
- **Advantages**: fully modern Windows pipeline; submits XPS to the spooler via `StartXpsPrintJob`; vector output; paper embedded from PDF→XPS.
- **Limitations**: finishing options (duplex/tray/copies) use the driver's **default PrintTicket** in this version (no custom PrintTicket yet) — non-applicable parameters are logged. Depends on `XpsPrint.dll` and Ghostscript (`-sDEVICE=xpswrite`). The most experimental backend.

---

## How to select the backend

Settings → **Print engine** (combo lists only backends available on the
machine). Persisted in `config.json` → `print_backend`. Optional GDI backend
DPI override: `config.json` → `win32_raster_dpi` (default 300).

## Design notes (scope)

- Printing still runs on the Tk thread (via `after`), as before. Rasterised
  backends may take longer; moving to a worker thread is a future improvement
  (out of scope for this delivery to avoid changing the current flow).
- New parameters (copies/duplex/tray) do not have UI yet: they use neutral
  defaults. The infrastructure already carries them end-to-end, ready for a
  future per-product/printer options screen.
