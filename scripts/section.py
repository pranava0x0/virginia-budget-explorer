"""Split a large budget PDF into named sections using its own bookmarks.

The 651-page executive budget document ships real PDF bookmarks (Part A/B/C/D,
then one entry per secretarial office within Part B). Level-2 bookmarks are the
natural section boundaries: level 3/4 entries under them are internal aids
(a "...Details" jump target, a same-page short caption) that restate a level-2
page rather than opening a new one. A section runs from its bookmark's page to
one page before the next level-2 bookmark (or to the end of the document).

Writes data/derived/<stem>.sections.json: [{index, part, title, start_page,
end_page, source_stem}, ...]. No text is duplicated here -- pages.json stays
the single source of truth for content; sections are just page-range labels.

    python3 scripts/section.py <stem>
"""
from __future__ import annotations

import json
import logging
import sys

import fitz

from config import DERIVED_DIR, RAW_DIR

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("section")


def sections_for(stem: str) -> list[dict]:
    pdf_path = RAW_DIR / f"{stem}.pdf"
    if not pdf_path.exists():
        raise FileNotFoundError(f"missing PDF: {pdf_path} (run scrape.py first)")
    doc = fitz.open(pdf_path)
    toc = doc.get_toc()

    parts = [(title, page) for lvl, title, page in toc if lvl == 1 and page > 0]
    headers = [(title, page) for lvl, title, page in toc if lvl == 2 and page > 0]
    if not headers:
        raise ValueError(f"{stem}: no level-2 bookmarks found; nothing to section on")

    def part_for(page: int) -> str:
        current = parts[0][0] if parts else "Document"
        for title, p in parts:
            if p <= page:
                current = title
            else:
                break
        return current

    sections = []
    for i, (title, start) in enumerate(headers):
        end = headers[i + 1][1] - 1 if i + 1 < len(headers) else doc.page_count
        sections.append({
            "index": i, "part": part_for(start), "title": title,
            "start_page": start, "end_page": end, "source_stem": stem,
        })
    return sections


def main(argv: list[str]) -> int:
    if not argv:
        log.error("usage: python3 scripts/section.py <stem>")
        return 1
    stem = argv[0]
    sections = sections_for(stem)
    DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    out = DERIVED_DIR / f"{stem}.sections.json"
    out.write_text(json.dumps(sections, indent=2), encoding="utf-8")
    log.info("✓ %s: %d sections -> %s", stem, len(sections), out.relative_to(out.parent.parent.parent))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
