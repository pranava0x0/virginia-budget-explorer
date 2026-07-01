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

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("find_quotes")

NONTECHNICAL_START = "Introduced Budget Non-Technical Changes"
ZONE_END_MARKERS = ("Operating Budget Summary", "Introduced Budget Technical Changes")

DOLLAR_RE = re.compile(r"\(?\$[\d,]+(?:\.\d+)?\)?")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def load(stem: str):
    pages = json.loads((TEXT_DIR / f"{stem}.pages.json").read_text(encoding="utf-8"))
    sections = json.loads((DERIVED_DIR / f"{stem}.sections.json").read_text(encoding="utf-8"))
    return pages, sections


def nontechnical_zone_text(pages: list[str], start_page: int, end_page: int) -> list[tuple[int, str]]:
    """Yield (page_number, text) for the stretches inside a Non-Technical zone.

    State carries across pages within the section since a department's
    non-technical items can spill onto the next page before the following
    department's "Operating Budget Summary" resets the state.
    """
    in_zone = False
    out = []
    for pno in range(start_page, end_page + 1):
        text = pages[pno - 1]
        idx = text.find(NONTECHNICAL_START)
        if idx == -1:
            if in_zone:
                # check this page doesn't itself close the zone before we emit it
                end_idx = min((text.find(m) for m in ZONE_END_MARKERS if m in text), default=None)
                if end_idx is not None:
                    out.append((pno, text[:end_idx]))
                    in_zone = False
                else:
                    out.append((pno, text))
            continue
        zone = text[idx + len(NONTECHNICAL_START):]
        end_idx = min((zone.find(m) for m in ZONE_END_MARKERS if m in zone), default=None)
        if end_idx is not None:
            out.append((pno, zone[:end_idx]))
            in_zone = False
        else:
            out.append((pno, zone))
            in_zone = True
    return out


def candidate_sentences(page_text: str) -> list[str]:
    sentences = SENTENCE_RE.split(re.sub(r"\s+", " ", page_text).strip())
    return [s.strip() for s in sentences if DOLLAR_RE.search(s) and 30 <= len(s) <= 400]


def mine(stem: str) -> list[dict]:
    pages, sections = load(stem)
    candidates = []
    zones_hit = 0  # sections that actually contained a Non-Technical marker
    for sec in sections:
        if sec["title"].startswith("IntroCover_"):
            continue  # single-page cover, never has content
        zone_pages = nontechnical_zone_text(pages, sec["start_page"], sec["end_page"])
        if zone_pages:
            zones_hit += 1
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

    log.info("%s: %d sections scanned (%d with a Non-Technical zone) · %d candidates found "
              "(nothing capped or dropped)", stem, len(sections), zones_hit, len(candidates))
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
