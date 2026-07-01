# Backlog

- **Ingest the FY2024-2026 Caboose Bill amendments** (medium). The executive
  budget document bundles a second, distinct budget action after Part D:
  "2026 Introduced Caboose Bill - 2024-2026 Biennium" amendments to the
  *current* biennium's second year, not the FY2026-2028 budget the rest of the
  document covers. `scripts/find_quotes.py` now scans it (see
  `data/derived/executive_budget_doc_2026.candidate_quotes.json`, sections
  `CabooseBullets` / `CabooseOperatingBudgetSummaryTables`, 31 candidates) but
  none have been curated into `build_data.py` yet — they'd need their own
  `NEXT_YEAR`-style list (or a `biennium` field added to `next_year_changes`)
  since mixing them into the FY2026-2028 list as-is would mislabel them.
- **Curate more of the 313-candidate pool** (medium). Only 9 of 313 deterministically-mined
  candidates from the executive budget document have been hand-picked into
  `NEXT_YEAR` so far. The full, uncapped set is in
  `data/derived/executive_budget_doc_2026.candidate_quotes.json` (regenerate
  with `scripts/find_quotes.py executive_budget_doc_2026`), ranked by dollar
  magnitude within each of its 18 sections.
- **Extend the time series further back** (high). The over-time chart now spans
  FY2024-26 (adopted + amended) and FY2026-28 (introduced). Pull the 2022 and 2020
  session overviews (FY2022-24, FY2020-22) and add their by-area tables to `BY_AREA`
  for a 5+ point series per area.
- **Per-area detail drill-down** (medium). Click an area → its top spending items
  (captured on the overview pages 9–10 / 22–26) and the relevant quotes.
- **Deep-link tabs + per-figure "verified" tick** (low). Hash-route the tabs and
  badge each citation with its `validation.json` status (the aggregate banner
  already shows it).
- **OCR the image-only figures in "Virginia in Focus"** (low). The FY25 by-area /
  fund-source chart values are in a raster; a gated, additive OCR pass could
  recover them — only if each recovered number stays page-verifiable.
- **Print / share view** (low). A clean print stylesheet and per-section deep links.

## Done

- Ingest the 651-page DPB executive budget document (`dpb.virginia.gov/budget/buddoc26`):
  `scripts/section.py` splits it into per-office sections via its own PDF
  bookmarks, `scripts/find_quotes.py` mines candidate policy changes
  deterministically per section, and 9 hand-picked, page-verified deltas were
  added to the Next Year tab across Judicial, Executive Offices, Agriculture,
  Education, HHR, Natural Resources, Public Safety, Transportation, and Central
  Appropriations.
- Multi-biennium by-area time series (FY2024-26 adopted/amended + FY2026-28 introduced).
- Fund-source breakdown surfaced (general fund + nongeneral fund) in the Funding tab.
- Next Year tab: FY2026-28 deltas + verbatim, page-cited change items.
- Citation on every data point; per-data-point validator + verified banner.
- Tabbed, responsive (mobile/tablet/desktop) layout.
