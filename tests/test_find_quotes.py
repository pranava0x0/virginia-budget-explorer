"""Regression tests for the candidate-quote miner (scripts/find_quotes.py).

An earlier version of mine() only scanned the 16 named Part B office
sections and dropped every candidate beyond a per-section cap. It silently
missed 147 of the document's 264 "Introduced Budget Non-Technical Changes"
zones (the OperatingBudgetSummaryTables appendix and the Part D Caboose bill)
and discarded candidates from the ones it did scan. These tests lock in both
fixes: full-document scanning and no truncation.

    python3 -m unittest tests.test_find_quotes
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from config import DERIVED_DIR, TEXT_DIR  # noqa: E402
from find_quotes import mine  # noqa: E402

STEM = "executive_budget_doc_2026"
_available = (DERIVED_DIR / f"{STEM}.sections.json").exists() and (TEXT_DIR / f"{STEM}.pages.json").exists()


@unittest.skipUnless(_available, "executive_budget_doc_2026 sections/pages not present")
class TestMineCoversWholeDocument(unittest.TestCase):
    def setUp(self):
        self.candidates = mine(STEM)

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
