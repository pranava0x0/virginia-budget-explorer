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
