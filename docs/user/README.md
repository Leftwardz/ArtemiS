# ArtemiS user manuals

End-user documentation (not developer docs). Sources are Markdown with screenshots; PDFs are generated for distribution.

## Guides

| Audience | Source | Output PDF |
|----------|--------|------------|
| Production operators | `en/production-user-guide.md` | `output/ArtemiS_Production_User_Guide_EN.pdf` |
| Administrators / IT | `en/administrator-guide.md` | `output/ArtemiS_Administrator_Guide_EN.pdf` |

## Build (Linux dev VM or CI)

```bash
# 1. Capture UI screenshots (English UI, requires DISPLAY)
DISPLAY=:1 .venv/bin/python scripts/capture_user_manual_screenshots.py

# 2. Build PDFs from Markdown + images
.venv/bin/python scripts/build_user_manuals.py
```

PDFs are written to `docs/user/output/`. Screenshots live in `docs/user/assets/en/`.

## Build (Windows)

Same Python scripts work on Windows. Use a visible desktop session for screenshots. Chrome or Edge (Chromium) must be on `PATH` for PDF export; the build script tries common install locations automatically.

## Updating after UI changes

1. Edit the Markdown in `docs/user/en/`.
2. Re-run the screenshot script if labels or layout changed.
3. Re-run the PDF build script.
4. Ship the new PDFs with the next release (or place them on the shared install folder).

## Notes

- Manuals are intentionally **non-technical** — no code, file paths for developers, or architecture.
- Screenshots use demo data (`DEMO` client) so real customer names never appear in docs.
- For other languages, add `docs/user/<locale>/` and extend `build_user_manuals.py`.
