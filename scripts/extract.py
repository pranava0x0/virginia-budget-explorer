"""Extract per-page text from each cached budget PDF.

Writes two artifacts per document into data/text/:
  - <stem>.txt        human-readable, with "--- PAGE N ---" markers
  - <stem>.pages.json list[str] of page text, index 0 == page 1

Per-page granularity is what lets every displayed quote carry a real page
citation. PyMuPDF (fitz) reads the text layer directly -- these documents are
digitally produced, so no OCR is needed. If a page yields no text we log it so
an extraction failure can never masquerade as an empty page.
"""
from __future__ import annotations

import json
import logging
import sys

import fitz  # PyMuPDF

from config import RAW_DIR, TEXT_DIR, SOURCES

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("extract")


def extract_one(stem: str) -> dict:
    pdf_path = RAW_DIR / f"{stem}.pdf"
    if not pdf_path.exists():
        raise FileNotFoundError(f"missing PDF: {pdf_path} (run scrape.py first)")

    doc = fitz.open(pdf_path)
    pages: list[str] = []
    empty_pages: list[int] = []
    for i in range(doc.page_count):
        text = doc[i].get_text("text")
        if not text.strip():
            empty_pages.append(i + 1)
        pages.append(text)

    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    # Human-readable paged dump
    marked = "".join(
        f"\n--- PAGE {i + 1} ---\n{t}" for i, t in enumerate(pages)
    )
    (TEXT_DIR / f"{stem}.txt").write_text(marked, encoding="utf-8")
    # Machine-readable page array for precise citation lookups
    (TEXT_DIR / f"{stem}.pages.json").write_text(
        json.dumps(pages, ensure_ascii=False), encoding="utf-8"
    )

    if empty_pages:
        log.warning("%s: %d empty pages (no text layer): %s",
                    stem, len(empty_pages), empty_pages[:20])
    log.info("%s: %d pages -> data/text/%s.{txt,pages.json}",
             stem, doc.page_count, stem)
    return {"stem": stem, "pages": doc.page_count, "empty_pages": empty_pages}


def main() -> int:
    results = [extract_one(s["stem"]) for s in SOURCES]
    total = sum(r["pages"] for r in results)
    empty = sum(len(r["empty_pages"]) for r in results)
    log.info("✓ extracted %d docs · %d pages · %d empty pages",
             len(results), total, empty)
    return 0


if __name__ == "__main__":
    sys.exit(main())
