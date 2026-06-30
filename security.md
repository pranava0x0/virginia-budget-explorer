# Security notes

## Supply-chain advisory sweep

- **Swept:** 2026-06-30 against the advisory index
  (`https://pranava0x0.github.io/vibe-coding-security/llms-ctx.txt`).
- **Result:** clean for this project's dependencies.
  - `PyMuPDF` (only third-party Python dep) — not listed in any advisory.
  - No npm dependencies (the front end is dependency-free, hand-rolled SVG).
  - Noted but **not used here:** `echarts-for-react` is in an active npm worm
    (Shai-Hulud / Mini Shai-Hulud); avoided by hand-rolling charts.
- **Re-sweep** if a dependency is added/upgraded, a CDN asset or GitHub Action is
  introduced, or this cache is older than 7 days.

## Hardening in place

- **Source-host allowlist** — `scrape.py` raises on any URL outside
  `budget.lis.virginia.gov` / `hac.virginia.gov`; covered by a test.
- **Content validation** — downloads must start with `%PDF-` or they are refused
  (an HTML 404 cannot masquerade as a budget document).
- **Pinned dependency** — `requirements.txt` pins `PyMuPDF==1.26.5` (exact, not a
  range). Install with `pip install -r requirements.txt` (or it is already
  present system-wide).
- **No secrets** — the pipeline reads only public documents; nothing to commit.
- **No machine-local paths** in committed data — sources are stored as public URLs
  in `sources/manifest.json`.
- **Self-hosted fonts** — Inter woff2 files are committed under `docs/fonts` and
  served same-origin; no third-party font/CDN request at runtime (also avoids the
  privacy concern of an external font host).
