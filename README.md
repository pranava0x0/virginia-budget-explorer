# Virginia Budget Explorer

A small, static dashboard for the Commonwealth of Virginia's general fund budget.
Every figure and quote is scraped from official House Appropriations Committee
documents and **verified verbatim against its source page** before it ships — the
build fails if a number or quote drifts from the document it cites.

Modeled after the clarity of open-data budget sites (clean tables, big honest
numbers, transparent sourcing) without the weight: no backend, no charting
library, no build step. Just a `docs/` folder you can drop on GitHub Pages.

## What's in it

- **KPI strip** — biennial general fund, biggest area, areas tracked, next biennium.
- **Donut** — general fund spending by secretarial area (toggle adopted ↔ amended).
- **Table** — every area, both budget versions, with the change and share. Sortable.
- **Over-time chart** — each area's spending from adopted (May 2024) to amended (May 2025).
- **Resources** — where the FY2026 general fund comes from.
- **Quotes** — policy principles, each verbatim with a page-cited link to the PDF.
- **Sources** — the four official documents behind every number.

## Pipeline

Four scripts, run in order. Re-runs are cheap: downloads are cached and the build
is deterministic.

```bash
python3 scripts/scrape.py        # download + cache official PDFs -> sources/raw/, manifest.json
python3 scripts/extract.py       # per-page text (PyMuPDF) -> data/text/*.{txt,pages.json}
python3 scripts/build_data.py    # curated + source-verified data -> docs/data/budget.json
python3 -m unittest discover -s tests   # lock quotes/numbers to their pages
```

Then serve the static site:

```bash
python3 -m http.server 8000 --directory docs
# open http://localhost:8000
```

To add another biennium (a longer time series), append its document to `SOURCES`
in `scripts/config.py`, transcribe its by-area table into `BY_AREA` in
`scripts/build_data.py`, and re-run the four steps. The over-time chart and the
table pick up the new time point automatically.

## Data provenance

- Sources: the "Overview of Virginia's Budget" reports, the HB 30 Conference
  Report, and "Virginia in Focus" — all House Appropriations Committee staff
  documents, fetched from `budget.lis.virginia.gov` and `hac.virginia.gov`
  (enforced by a host allowlist in the scraper).
- `sources/manifest.json` records each document's URL, sha256, page count, and
  capture date.
- By-area dollars are **general fund, $ in millions**.
- **Rounding note:** the KPI and table totals are summed from the area figures,
  so they can differ by ~0.1B from a document's own rounded headline (e.g. the
  amended biennium sums to $67.5B; Chapter 725 states it as "$67.4 billion").
  The build asserts the two agree within 1.5%.

This is an independent civic tool, not an official state publication.

## Stack

Vanilla JS + hand-rolled inline SVG charts (zero front-end dependencies).
Python 3.9 + PyMuPDF for extraction (the only third-party dependency; pinned in
`requirements.txt`). No npm, no bundler, no tracker.
