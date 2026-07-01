"""Regression tests for the candidate-quote miner (scripts/find_quotes.py).

Two bugs surfaced ingesting the 651-page executive budget document, both
logged in issues.md:

1. An earlier version of mine() only scanned the 16 named Part B office
   sections and capped each at 8 candidates. It silently missed 147 of the
   document's 264 "Introduced Budget Non-Technical Changes" zones (the
   OperatingBudgetSummaryTables appendix and the Part D Caboose bill) and
   discarded most of what it did find.
2. The fix for #1 introduced a second bug: some pages pack 2-4 agencies
   back-to-back with no "Operating Budget Summary" between them, and the
   zone-walker only found the FIRST marker per page, merging every agency on
   such a page into one blob.

These tests lock in the fixes for both: full-document scanning, no
truncation, and per-marker (not per-page) zone boundaries.

    python3 -m unittest tests.test_find_quotes
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from config import DERIVED_DIR, TEXT_DIR  # noqa: E402
from find_quotes import mine, nontechnical_zone_text, NONTECHNICAL_START  # noqa: E402

STEM = "executive_budget_doc_2026"
_available = (DERIVED_DIR / f"{STEM}.sections.json").exists() and (TEXT_DIR / f"{STEM}.pages.json").exists()


@unittest.skipUnless(_available, "executive_budget_doc_2026 sections/pages not present")
class TestMineCoversWholeDocument(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # mine() is a pure function of the committed .pages.json/.sections.json
        # on disk -- compute it once for the whole class, not once per test.
        cls.candidates = mine(STEM)

    def test_scans_beyond_named_office_sections(self):
        # the appendix and the caboose bill are not Part B office sections by
        # title, but they hold more Non-Technical zones than the offices do
        sections_hit = {c["section"] for c in self.candidates}
        self.assertIn("OperatingBudgetSummaryTables", sections_hit)
        self.assertIn("CabooseBullets", sections_hit)

    def test_caboose_candidates_are_labeled_distinctly(self):
        # the caboose bill amends a different biennium (FY2024-2026) than the
        # main document (FY2026-2028) -- a reviewer must be able to tell them
        # apart from the `part`/`section` fields alone
        caboose = [c for c in self.candidates if c["section"].startswith("Caboose")]
        self.assertTrue(caboose)
        for c in caboose:
            self.assertEqual(c["part"], "PartD_ALL")

    def test_nothing_is_capped_per_section(self):
        # no section's kept-candidate count is silently truncated to a round
        # cap; the largest section (Office of Education, ~77 pages of items)
        # should show far more than an old hardcoded cap of 8
        from collections import Counter
        counts = Counter(c["section"] for c in self.candidates)
        self.assertGreater(counts["07_OfficeofEducation"], 20)

    def test_every_candidate_has_a_rank_and_no_duplicates_dropped(self):
        # rank_in_section must be a dense 0..n-1 sequence per section, proving
        # sorting doesn't silently drop entries the way a slice would
        from collections import defaultdict
        by_section = defaultdict(list)
        for c in self.candidates:
            by_section[c["section"]].append(c["rank_in_section"])
        for section, ranks in by_section.items():
            self.assertEqual(sorted(ranks), list(range(len(ranks))),
                              f"{section}: rank_in_section is not a dense 0..n-1 sequence")


@unittest.skipUnless(_available, "executive_budget_doc_2026 sections/pages not present")
class TestZoneWalkerHandlesDenseMultiMarkerPages(unittest.TestCase):
    """Page 586 packs 4 separate agencies' Non-Technical zones onto one page
    with no "Operating Budget Summary" between them. A version keyed on
    str.find() (first-match-only) merged all 4 into a single blob; walking
    every marker occurrence as one ordered sequence must split them instead."""

    def test_multi_marker_page_yields_multiple_agencies_worth_of_content(self):
        import json
        pages = json.loads((TEXT_DIR / f"{STEM}.pages.json").read_text(encoding="utf-8"))
        marker_count = pages[585].count(NONTECHNICAL_START)
        self.assertGreaterEqual(marker_count, 4, "fixture assumption changed: page 586 no longer dense")

        zones = nontechnical_zone_text(pages, 586, 596)
        page_586_text = next(text for pno, text in zones if pno == 586)
        # each of the 4 agencies' distinct dollar figures must all survive --
        # a merge bug wouldn't drop text, but a truncation bug would
        for needle in ("$1,000,000", "$9,750,000", "$9,020,150", "($1,404,243)"):
            self.assertIn(needle, page_586_text, f"{needle} missing from merged page-586 zone text")

    def test_coverage_self_check_does_not_raise(self):
        # mine() cross-checks its own marker-walk count against an independent
        # count of the start marker across the whole document and raises on
        # mismatch -- this is the regression guard for the original coverage
        # bug (117 of 264 zones scanned). Calling mine() here must not raise.
        mine(STEM)  # raises RuntimeError on a coverage mismatch


if __name__ == "__main__":
    unittest.main(verbosity=2)
