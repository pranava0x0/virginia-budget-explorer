# Security notes

## Supply-chain advisory sweep

- **Swept:** 2026-07-05 against the advisory index
  (`https://pranava0x0.github.io/vibe-coding-security/llms-ctx.txt`) — re-swept
  because CI workflows were added (a GitHub Action is a re-sweep trigger).
- **Result:** clean for this project's dependencies and the two actions used.
  - `PyMuPDF` (only third-party Python dep) — not listed in any advisory.
  - No npm dependencies (the front end is dependency-free, hand-rolled SVG).
  - `actions/checkout`, `actions/setup-python` — pinned to full commit SHAs
    (below), not moving tags. The **Cordyceps** CI/CD-misconfiguration advisory
    (2026-06-24) and the `aquasecurity/trivy-action` tag-force-push incident are
    why: our workflows avoid `pull_request_target`, take no untrusted shell
    inputs, and grant least-privilege `permissions:` per job.
  - Noted but **not used here:** `echarts-for-react` is in an active npm worm
    (Shai-Hulud / Mini Shai-Hulud); avoided by hand-rolling charts. The
    `claude-code-action` [bot] trust-bypass advisory does not apply (not used).
- **Re-sweep** if a dependency is added/upgraded, a CDN asset or GitHub Action is
  introduced, or this cache is older than 7 days.

### Pinned GitHub Actions (re-pin with `gh api repos/<owner>/<repo>/commits/<tag> --jq .sha`)

- `actions/checkout` → `9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0` (v7.0.0)
- `actions/setup-python` → `ece7cb06caefa5fff74198d8649806c4678c61a1` (v6.3.0)

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
