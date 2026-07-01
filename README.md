# Virginia Budget Explorer

**Live:** https://pranava0x0.github.io/virginia-budget-explorer/

A small, static dashboard for the Commonwealth of Virginia's general fund budget.
Every figure and quote is scraped from official House Appropriations Committee
documents and **verified verbatim against its source page** before it ships — the
build fails if a number or quote drifts from the document it cites.

Clean, accessible, and dependency-free: tabbed views, self-hosted Inter, inline
SVG charts (no charting library), a source + page citation on every figure, a
per-data-point validator, and an `llms.txt` so machines get the same facts. No
backend, no build step — just a `docs/` folder on GitHub Pages.

Accessibility: keyboard-navigable ARIA tabs, skip link, table captions,
AA-contrast text, visible focus, and reduced-motion support.

Every figure shows a source + page citation, and a build-time validator confirms
all 76 data points against their source page (the green "verified" banner).

## What's in it (tabbed)

- **Overview** — KPI strip, a donut of general fund spending by secretarial area
  (toggle adopted ↔ amended), and a sortable table of every area with the change,
  share, and a per-row source link.
- **Over time** — each area's general fund across three budgets: FY2024-2026 as
  adopted, as amended, and FY2026-2028 as introduced.
- **Funding** — where the money comes from (general fund + nongeneral fund).
- **Next year** — the FY2026-2028 budget (HB 30): proposed totals, the by-area
  change vs the current budget, and key deltas/changes pulled verbatim from the
  107-page committee overview and the 651-page DPB executive budget document,
  each with a page citation.
- **Quotes & sources** — policy principles (verbatim, page-cited) and the six
  official documents behind every number, with the verification status.

## Pipeline

Five scripts, run in order. Re-runs are cheap: downloads are cached and the build
is deterministic.

```bash
python3 scripts/scrape.py        # download + cache official PDFs -> sources/raw/, manifest.json
python3 scripts/extract.py       # per-page text (PyMuPDF) -> data/text/*.{txt,pages.json}
python3 scripts/build_data.py    # curated + source-verified data -> docs/data/budget.json
python3 scripts/validate.py      # per-data-point check -> docs/data/validation.json (CI gate)
python3 -m unittest discover -s tests   # lock quotes/numbers to their pages
```

### Mining quotes from a large (100s-of-pages) document

For a document too large to skim page-by-page (the DPB executive budget
document is 651 pages), two extra scripts turn its own PDF bookmarks into a
review queue instead of requiring a full manual read:

```bash
python3 scripts/section.py <stem>      # PDF bookmarks -> data/derived/<stem>.sections.json (page ranges per office/part)
python3 scripts/find_quotes.py <stem>  # regex/keyword triage per section -> data/derived/<stem>.candidate_quotes.json
```

`find_quotes.py` is deterministic (no LLM calls) and scans every section for
the "Introduced Budget Non-Technical Changes" zone, skipping only the
"Technical Changes" zone that repeats the same centrally-funded IT/rent/
insurance boilerplate in every agency — it does not skip sections by name.
(An earlier version allowlisted only the 16 named office sections and capped
each at 8 candidates; that silently missed 147 of the document's 264
Non-Technical zones — a per-agency appendix and a bundled second budget action,
the FY2024-2026 Caboose Bill — and discarded most of what it did find. See
`issues.md`.) Nothing is capped or dropped: every candidate is kept, ranked by
dollar magnitude within its section. The candidates are a shortlist for a
human (or an agent doing judgment, not transcription) to hand-pick from and
transcribe into `build_data.py`'s `QUOTES`/`NEXT_YEAR` — which re-verify
everything verbatim against the source page before it ships, same as any
other entry.

`*.sections.json` is committed (it depends on the raw PDF's bookmarks, which
aren't preserved anywhere else since `sources/raw/*.pdf` is gitignored);
`*.candidate_quotes.json` is not (cheaply regenerable from committed data,
and it's scratch triage output, not something the build or tests read).

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

- Sources: the "Overview of Virginia's Budget" reports for FY2024-2026 and
  FY2026-2028, the HB 30 Conference Report, "Virginia in Focus", and the DPB
  executive budget document — House Appropriations Committee and Department of
  Planning and Budget documents, fetched from `budget.lis.virginia.gov`,
  `hac.virginia.gov`, and `dpb.virginia.gov` (enforced by a host allowlist in
  the scraper).
- `sources/manifest.json` records each document's URL, sha256, page count, and
  capture date. "Data as of" on the site reflects the newest *source* date, not
  the build date.
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
