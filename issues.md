# Issues

Living audit trail. Each entry: date · area · description · root cause · status.

## Fixed

- **2026-06-30 · scraper · HTML 404 page cached as a `.pdf`.**
  An early guess at an older overview URL (`hac.virginia.gov/documents/2022/...`)
  returned a 200 with an HTML "page not found" body. A naive download would have
  saved it as a PDF and the extractor would have produced garbage.
  *Root cause:* trusting HTTP 200 instead of the file content. **code bug.**
  *Fix:* `scrape.py` validates the `%PDF-` magic and refuses to cache anything
  else; `test_manifest_hashes_match_disk` + `validate_pdf` guard re-runs. The
  bad file was deleted and the source dropped from the corpus.

- **2026-06-30 · donut chart · colored slices invisible (only the gray ring showed).**
  Slice `<circle>`s had a correct blue/teal/etc. stroke in the DOM but rendered
  off-canvas. *Root cause:* rotation was applied via the SVG `transform`
  attribute (`rotate(-90 cx cy)`) while CSS `transform-origin` defaulted to
  `50% 50%`; the browser composed both origins, rotating each arc around a point
  120px off-center and pushing it outside the viewBox. The background ring (no
  transform) was unaffected, masking the bug. **code bug.**
  *Fix:* rotate via CSS (`transform: rotate(-90deg); transform-box: fill-box`)
  and drop the attribute transform, so the origin is the circle's own center.

- **2026-06-30 · trend chart · right-edge labels overlapped in the low-value cluster.**
  Five areas between $2.0B–$3.7B stacked their two-line labels on top of each
  other; a single push-down + clamp also dragged the top labels off their dots.
  **code bug** (layout). *Fix:* two-pass de-collision — push down for overlap,
  then relax the dense cluster upward into the empty space above it — plus leader
  lines from each label to its data point.

- **2026-06-30 · tests · hash check required gitignored PDFs (Codex P1).**
  `test_manifest_hashes_match_disk` asserted every `sources/raw/*.pdf` existed,
  but those are gitignored — so the suite failed on a fresh checkout. **test bug.**
  *Fix:* skip the per-file hash check when the PDF is absent (it's a local
  integrity check; the committed `.pages.json` is the evidence the other tests use).

- **2026-06-30 · data freshness · "Data as of" showed the build date (Codex P2).**
  `build_data.py` stamped `meta.captured_at = date.today()`, and the header
  rendered it as data freshness — so rebuilding from unchanged documents advanced
  the date, making stale figures look current. **code bug** (violates the project's
  own "publication ≠ capture date / don't re-stamp on re-parse" rule).
  *Fix:* `meta.data_as_of` is now the newest source `as_of`; `meta.built_at` holds
  the build timestamp separately; the UI shows `data_as_of`.

- **2026-07-01 · quote miner · `find_quotes.py` scanned less than half the document (Codex-style self-review).**
  `mine()` only walked the 16 named Part B office sections, skipping
  `OperatingBudgetSummaryTables` (assumed to be "just tables") and every Part D
  section, then additionally truncated each scanned section to its top 8
  candidates by dollar magnitude. Auditing marker counts directly against the
  extracted page text (`"Introduced Budget Non-Technical Changes".count(...)`)
  showed 264 such zones in the document but only 117 were ever scanned — the
  appendix alone held 101 (a per-agency restatement of the same office-level
  changes at finer grain) and Part D's "Caboose" sections held 46 more, which
  turned out to be a *distinct* budget action (amendments to the current
  FY2024-2026 biennium, bundled in the same PDF, not the FY2026-2028 budget the
  rest of the document covers). **Root cause:** a title-based allowlist that
  encoded an untested assumption about which sections contain narrative
  content, plus a hard per-section cap with no way to recover what it dropped.
  *Fix:* scan every section (skip only single-page `IntroCover_*` covers) and
  let the zone-detection naturally yield zero candidates where there's nothing
  to find; drop the cap entirely and store every candidate with a
  `rank_in_section` for reviewer convenience instead of truncating. Candidate
  count went from 107 (silently capped from an unknown, unrecorded larger set)
  to 324 (the complete, auditable set). Regression test:
  `tests/test_find_quotes.py`. Also fixed `.gitignore`: `*.sections.json` was
  wrongly marked "regenerable from committed data" — it actually depends on the
  raw PDF's bookmarks (gitignored), so it needed to be committed, not ignored.

- **2026-07-01 · quote miner · dense multi-agency pages silently merged into one zone (caught in code review of the fix above).**
  `nontechnical_zone_text()` located the Non-Technical marker with a plain
  `str.find()`, which only finds the FIRST occurrence per page. Some pages —
  especially the compact Part D Caboose Bill pages — pack 2-4 agencies onto
  one page with no "Operating Budget Summary" table between them (nothing
  resets the state machine), so all of them got concatenated into a single
  blob under the first agency's boundary. Confirmed directly: page 586 has 4
  markers; the old code returned one merged zone spanning all 4 items with no
  separator between an Energy-project item and an unrelated inland-port item.
  **Root cause:** `str.find()` returns only the first match; the zone-walker
  had no way to notice a second start marker before an end marker, so it
  never re-opened a boundary. *Fix:* rewrote the walker to enumerate every
  marker occurrence (start and end) on a page via `re.finditer`, sorted by
  position, and treat a fresh start marker as implicitly closing whatever
  zone was open — the same as an explicit end marker. Also added a self-check
  to `mine()`: it now asserts the number of start markers it actually walked
  equals an independently-computed count over the raw page text, and raises
  if they diverge — this is exactly the check that would have caught the
  *first* bug in this pair (117 of 264 zones scanned) automatically instead
  of requiring a manual audit. Candidate count went from 324 to 313 (fewer,
  because properly-bounded zones stop producing the occasional run-on
  "sentence" that used to splice two agencies' text together — a healthy
  drop, not new data loss; the 264/264 marker reconciliation confirms
  complete coverage). Regression test:
  `tests/test_find_quotes.py::TestZoneWalkerHandlesDenseMultiMarkerPages`.
  Found via an 8-angle automated code review of the PR, not manual testing —
  worth noting as a case where the fix for one bug needs its own review pass,
  not just a green test suite, before it's trustworthy.

- **2026-07-01 · frontend · new source stem broken every citation link in the UI (caught by the Codex GitHub App review, not by my own review pass).**
  Adding `executive_budget_doc_2026` to `SOURCES` and `NEXT_YEAR` never
  touched `docs/app.js`'s `DOC_SHORT` map (a hardcoded `{stem: "short label"}`
  dict used to render every citation link). Nothing enforced that the two
  stay in sync, and nothing in the test suite covers `docs/app.js` at all
  (vanilla JS, no build step, no JS test runner) — nine "Next Year" citation
  links silently rendered `undefined · p. 46` / `Open undefined at page 46`
  in production. **Root cause:** a duplicated, hand-maintained lookup table
  with zero test coverage on the JS side of the codebase. *Fix:* added the
  missing `DOC_SHORT` entry, plus `tests/test_budget.py::TestAppJs`, which
  parses `DOC_SHORT`'s keys out of `docs/app.js` and asserts every
  `source_stem` used anywhere in the shipped `budget.json` has an entry —
  this is the first test in the suite that reads JS source at all, closing a
  real gap where the Python test suite had no visibility into the frontend.
  Also generalized shipped provenance copy (`build_data.py`'s `meta.note`,
  `docs/index.html`'s meta description/footer, `docs/app.js`'s hero
  subtitle) that still said "House Appropriations Committee documents" only,
  which became inaccurate once a Department of Planning and Budget document
  was added as a source — same root cause, a claim about "every source"
  that nothing re-checked when a new source was added.
  *Lesson:* my own 8-angle review (angles A-H, run before this) missed both
  of these — none of the angles were scoped to read `docs/app.js` at all,
  since the diff under review was filtered to `scripts/`, `tests/`, and
  markdown docs. A second, independent automated reviewer (Codex) that
  reviewed the *actual* full PR diff (including `docs/`) caught what a
  self-scoped review missed. Worth remembering: scoping a review to "the
  files I changed" can silently exclude files a change has real, breaking
  effects on.

## Known limitations (not bugs)

- **Time series depth.** The over-time view currently spans one biennium at two
  enactment stages (adopted → amended). Earlier biennia (FY2022-24, FY2020-22)
  would lengthen the x-axis; see `backlog.md`. This is a coverage gap, logged
  honestly, not a silent zero.
- **FY26-28 by-area.** The HB 30 Conference Report is a policy-initiatives deck
  with no by-secretarial-area total table, so the new biennium contributes
  headline totals and quotes but not a pie slice set. Structural source gap.
- **"Virginia in Focus" FY25 by-area figures** live inside a chart image (no text
  layer), so they are deliberately not transcribed — only text-layer numbers are
  shipped, to keep every figure verifiable.
