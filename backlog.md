# Backlog

- **Extend the time series further back** (high). The over-time chart now spans
  FY2024-26 (adopted + amended) and FY2026-28 (introduced). Pull the 2022 and 2020
  session overviews (FY2022-24, FY2020-22) and add their by-area tables to `BY_AREA`
  for a 5+ point series per area.
- **Ingest the full ~700-page executive budget** (medium). The Next Year tab is
  built from the 107-page committee overview of HB 30. Adding the DPB executive
  budget document (`dpb.virginia.gov/budget/buddoc26`) would let the deltas be
  mined from the primary bill — needs `dpb.virginia.gov` on the host allowlist and
  a deterministic delta scan with per-item page verification.
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

- Multi-biennium by-area time series (FY2024-26 adopted/amended + FY2026-28 introduced).
- Fund-source breakdown surfaced (general fund + nongeneral fund) in the Funding tab.
- Next Year tab: FY2026-28 deltas + verbatim, page-cited change items.
- Citation on every data point; per-data-point validator + verified banner.
- Tabbed, responsive (mobile/tablet/desktop) layout.
