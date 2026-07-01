"""Deterministic candidate-quote miner for a large, page-sectioned budget PDF.

No LLM tokens spent here -- this is regex/keyword triage over text already on
disk (data/text/<stem>.pages.json), scoped by data/derived/<stem>.sections.json.
It surfaces CANDIDATES for a human (or an agent doing judgment, not
transcription) to review and hand-pick into build_data.py's curated lists,
which re-verify everything verbatim before it ships.

Most subsections in this document repeat a fixed template: an "Operating
Budget Summary" table, then "Operating Budget Changes" split into "Introduced
Budget Technical Changes" (routine, centrally-funded pass-throughs -- IT
costs, rent, insurance premiums, retirement rate ticks -- near-identical
across every agency) and "Introduced Budget Non-Technical Changes" (the
actual policy changes). Only the latter zone is worth mining: the technical
zone is high-volume, low-signal boilerplate that would drown out real
candidates.

Every section is scanned -- there is no per-title allowlist. An earlier
version only scanned the 16 named Part B office sections and skipped
"OperatingBudgetSummaryTables" on the assumption it was pure tables; it
turned out to hold 101 of the document's 264 Non-Technical zones (a
per-agency appendix restating the same changes at finer grain), and Part D's
"Caboose" sections -- a genuinely distinct budget action amending the
*current* FY2024-2026 biennium, bundled in the same PDF -- held another 46.
Scanning every section and letting the zone-detection naturally yield zero
candidates where there's nothing to find is more robust than guessing which
sections matter by title.

A second bug surfaced in review of that fix: some pages (the compact "Caboose
Bill" pages especially) pack 2-4 agencies onto one page with no "Operating
Budget Summary" table between them, so a page can contain several
Non-Technical zones back to back. The original zone-walker only located the
FIRST marker per page via `str.find`, silently merging every agency on such a
page into one blob. `_page_events` below finds every marker occurrence (start
and end) and walks them as a single ordered sequence, so a fresh start marker
implicitly closes whatever zone was open, exactly like an explicit end marker
would. `mine()` also cross-checks its own output against an independent count
of start markers in the raw text -- the previous bug (scanning 117 of 264
zones) would have been caught immediately by this check instead of requiring
a manual audit.

Nothing is dropped: every dollar-bearing candidate sentence found is written
out, ranked by dollar magnitude within its section for a reviewer's
convenience, never truncated. `part`/`section` on each candidate carries
enough provenance (e.g. "PartD_ALL / CabooseBullets") that a reviewer can
immediately tell a caboose-bill item apart from a main-budget one.

    python3 scripts/find_quotes.py <stem>
"""
from __future__ import annotations

import json
import logging
import re
import sys

from config import DERIVED_DIR, TEXT_DIR
from build_data import norm

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("find_quotes")

NONTECHNICAL_START = "Introduced Budget Non-Technical Changes"
ZONE_END_MARKERS = ("Operating Budget Summary", "Introduced Budget Technical Changes")
_ALL_MARKERS = [(NONTECHNICAL_START, "start")] + [(m, "end") for m in ZONE_END_MARKERS]

DOLLAR_RE = re.compile(r"\(?\$[\d,]+(?:\.\d+)?\)?")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def load(stem: str) -> tuple[list[str], list[dict]]:
    pages = json.loads((TEXT_DIR / f"{stem}.pages.json").read_text(encoding="utf-8"))
    sections = json.loads((DERIVED_DIR / f"{stem}.sections.json").read_text(encoding="utf-8"))
    return pages, sections


def _page_events(text: str) -> list[tuple[int, int, str]]:
    """Every marker occurrence on a page as (start_offset, end_offset, kind), in order."""
    events = []
    for marker, kind in _ALL_MARKERS:
        for m in re.finditer(re.escape(marker), text):
            events.append((m.start(), m.end(), kind))
    events.sort(key=lambda e: e[0])
    return events


def nontechnical_zone_text(pages: list[str], start_page: int, end_page: int) -> list[tuple[int, str]]:
    """Yield (page_number, text) for the stretches inside a Non-Technical zone.

    Walks every start/end marker on a page as one ordered sequence, so a page
    packing several agencies back-to-back (no "Operating Budget Summary"
    between them) still splits at each boundary -- a fresh start marker closes
    whatever zone was open, the same as an explicit end marker would. State
    (in_zone, i.e. whether we're still inside a zone opened on a prior page
    with no end marker in between) carries across pages within the section.
    """
    in_zone = False
    out = []
    for pno in range(start_page, end_page + 1):
        text = pages[pno - 1]
        segments = []
        cursor = 0
        for ev_start, ev_end, kind in _page_events(text):
            if in_zone and ev_start > cursor:
                segments.append(text[cursor:ev_start])
            in_zone = kind == "start"
            cursor = ev_end
        if in_zone and cursor < len(text):
            segments.append(text[cursor:])
        if segments:
            out.append((pno, "\n".join(segments)))
    return out


def candidate_sentences(page_text: str) -> list[str]:
    sentences = SENTENCE_RE.split(norm(page_text))
    return [s.strip() for s in sentences if DOLLAR_RE.search(s) and 30 <= len(s) <= 400]


def mine(stem: str) -> list[dict]:
    pages, sections = load(stem)
    candidates = []
    zones_hit = 0  # sections that actually contained a Non-Technical marker
    start_markers_walked = 0
    for sec in sections:
        if sec["title"].startswith("IntroCover_"):
            continue  # single-page cover, never has content
        zone_pages = nontechnical_zone_text(pages, sec["start_page"], sec["end_page"])
        if zone_pages:
            zones_hit += 1
        start_markers_walked += sum(
            pages[p - 1].count(NONTECHNICAL_START) for p in range(sec["start_page"], sec["end_page"] + 1)
        )
        sec_candidates = []
        for pno, text in zone_pages:
            for sent in candidate_sentences(text):
                amounts = DOLLAR_RE.findall(sent)
                magnitude = max((float(a.strip("()$").replace(",", "")) for a in amounts), default=0)
                sec_candidates.append({
                    "part": sec["part"], "section": sec["title"], "page": pno, "text": sent,
                    "amounts": amounts, "magnitude": magnitude,
                })
        sec_candidates.sort(key=lambda c: -c["magnitude"])
        for rank, c in enumerate(sec_candidates):
            c["rank_in_section"] = rank
        candidates.extend(sec_candidates)

    # Self-check: an independent count of the start marker across every scanned
    # page must match what the zone-walker actually walked through. This is
    # exactly the discrepancy (117 of 264 zones scanned) that the original
    # coverage bug required a manual audit to catch -- asserting it here means
    # a future regression fails the pipeline instead of shipping silently.
    total_markers = sum(p.count(NONTECHNICAL_START) for p in pages)
    if start_markers_walked != total_markers:
        raise RuntimeError(
            f"{stem}: coverage check failed -- walked {start_markers_walked} "
            f"Non-Technical markers across sections but the document has "
            f"{total_markers}; a page range or section boundary is dropping zones")

    log.info("%s: %d sections scanned (%d with a Non-Technical zone) · %d/%d markers "
              "accounted for · %d candidates found (nothing capped or dropped)",
              stem, len(sections), zones_hit, start_markers_walked, total_markers, len(candidates))
    return candidates


def main(argv: list[str]) -> int:
    if not argv:
        log.error("usage: python3 scripts/find_quotes.py <stem>")
        return 1
    stem = argv[0]
    candidates = mine(stem)
    out = DERIVED_DIR / f"{stem}.candidate_quotes.json"
    out.write_text(json.dumps(candidates, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("-> %s", out.relative_to(out.parent.parent.parent))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
