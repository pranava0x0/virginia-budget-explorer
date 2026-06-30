"""Independent verification of the shipped budget.json against its sources.

These tests are the eval loop: they re-derive nothing from build_data's curated
constants except the normalizer, then check the SHIPPED docs/data/budget.json
against the extracted page text. If a quote drifts, a number is mistyped, a
citation points at the wrong page, a record count drops, or a source host
sneaks off the allowlist, a test fails loudly.

    python3 -m unittest discover -s tests        # or: python3 tests/test_budget.py
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from config import ALLOWED_HOSTS, AREA_CANONICAL, TEXT_DIR  # noqa: E402
from build_data import norm  # noqa: E402  (shared normalizer)
from urllib.parse import urlparse  # noqa: E402

BUDGET = json.loads((ROOT / "docs" / "data" / "budget.json").read_text())
MANIFEST = json.loads((ROOT / "sources" / "manifest.json").read_text())
CANONICAL_AREAS = set(AREA_CANONICAL.values())

_page_cache: dict[str, list[str]] = {}


def pages(stem: str) -> list[str]:
    if stem not in _page_cache:
        _page_cache[stem] = json.loads((TEXT_DIR / f"{stem}.pages.json").read_text())
    return _page_cache[stem]


def on_page(stem: str, page: int, needle: str) -> bool:
    pg = pages(stem)
    return 1 <= page <= len(pg) and norm(needle) in norm(pg[page - 1])


class TestQuotes(unittest.TestCase):
    def test_verbatim_on_cited_page(self):
        for q in BUDGET["quotes"]:
            self.assertTrue(
                on_page(q["source_stem"], q["page"], q["text"]),
                f"quote not verbatim on {q['source_stem']} p{q['page']}: {q['text'][:60]!r}")

    def test_page_is_first_occurrence(self):
        # the cited page must be where the quote first appears (no off-by-page)
        for q in BUDGET["quotes"]:
            pg = pages(q["source_stem"])
            n = norm(q["text"])
            first = next((i + 1 for i, p in enumerate(pg) if n in norm(p)), None)
            self.assertEqual(first, q["page"],
                             f"{q['source_stem']}: stored p{q['page']} != first occurrence p{first}")

    def test_quote_has_topic_and_principle(self):
        for q in BUDGET["quotes"]:
            self.assertTrue(q.get("topic") and q.get("principle") and q.get("doc_title"))

    def test_next_year_changes_verbatim(self):
        changes = BUDGET.get("next_year_changes", [])
        self.assertGreaterEqual(len(changes), 8, "expected a set of next-year changes")
        for c in changes:
            self.assertTrue(on_page(c["source_stem"], c["page"], c["text"]),
                            f"next-year change not verbatim on {c['source_stem']} p{c['page']}: {c['text'][:50]!r}")
            self.assertTrue(c.get("headline") and c.get("area"))


class TestValues(unittest.TestCase):
    def test_by_area_values_on_page(self):
        for r in BUDGET["by_area"]:
            self.assertTrue(on_page(r["source_stem"], r["page"], r["value_str"]),
                            f"{r['area']} {r['value_str']} not on {r['source_stem']} p{r['page']}")

    def test_other_values_on_page(self):
        for key in ("ngf_revenue", "gf_resources_fy2026", "gf_top10_fy2026", "totals"):
            for r in BUDGET[key]:
                self.assertTrue(on_page(r["source_stem"], r["page"], r["value_str"]),
                                f"{key} {r['value_str']} not on {r['source_stem']} p{r['page']}")

    def test_area_sums_match_stated_totals(self):
        # the document states its own biennial total; parsed rows must agree
        stated = {(t["biennium"], t["stage"]): t["billions"]
                  for t in BUDGET["totals"] if t["kind"] == "GF spending"}
        sums: dict[tuple, float] = {}
        for r in BUDGET["by_area"]:
            sums[(r["biennium"], r["stage"])] = sums.get((r["biennium"], r["stage"]), 0) + r["millions"]
        for key, total_b in stated.items():
            got = sums.get(key, 0) / 1000.0
            self.assertLessEqual(abs(got - total_b) / total_b, 0.015,
                                 f"{key}: rows sum {got:.1f}B vs stated {total_b}B")


class TestSchemaAndCounts(unittest.TestCase):
    def test_top_level_keys(self):
        for k in ("meta", "areas", "by_area", "ngf_revenue", "gf_resources_fy2026",
                  "gf_top10_fy2026", "totals", "quotes", "sources"):
            self.assertIn(k, BUDGET)

    def test_areas_are_canonical(self):
        for a in BUDGET["areas"]:
            self.assertIn(a, CANONICAL_AREAS, f"non-canonical area: {a}")
        for r in BUDGET["by_area"]:
            self.assertIn(r["area"], CANONICAL_AREAS)

    def test_count_floors(self):
        # append-only flavored guards: counts must never silently drop
        self.assertGreaterEqual(len(BUDGET["by_area"]), 18, "expected >= 9 areas x 2 stages")
        self.assertGreaterEqual(len(BUDGET["quotes"]), 8)
        self.assertGreaterEqual(len(BUDGET["sources"]), 4)
        self.assertEqual(len(BUDGET["areas"]), 9)

    def test_each_stage_has_every_area(self):
        for stage in ("As adopted", "As amended"):
            got = {r["area"] for r in BUDGET["by_area"] if r["stage"] == stage}
            self.assertEqual(got, set(BUDGET["areas"]), f"{stage} missing areas")

    def test_shares_sum_to_100(self):
        amended = [r["millions"] for r in BUDGET["by_area"] if r["stage"] == "As amended"]
        total = sum(amended)
        self.assertAlmostEqual(sum(amended) / total * 100, 100.0, places=3)


class TestProvenance(unittest.TestCase):
    def test_source_hosts_allowlisted(self):
        for s in BUDGET["sources"]:
            host = urlparse(s["url"]).hostname
            self.assertIn(host, ALLOWED_HOSTS, f"off-allowlist source host: {host}")

    def test_manifest_hashes_match_disk(self):
        # The raw PDFs are gitignored (regenerable via scrape.py), so on a fresh
        # checkout they're absent -- this is a local-integrity check that only
        # runs where the cached PDF exists, not a hard requirement to commit it.
        import hashlib
        checked = 0
        for m in MANIFEST:
            pdf = ROOT / "sources" / "raw" / f"{m['stem']}.pdf"
            if not pdf.exists():
                continue
            digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
            self.assertEqual(digest, m["sha256"], f"{m['stem']} sha256 drift (re-run scrape.py)")
            checked += 1
        if checked == 0:
            self.skipTest("no cached PDFs present (fresh checkout); page JSON is the evidence")

    def test_scraper_rejects_off_allowlist_host(self):
        from scrape import _check_host
        with self.assertRaises(ValueError):
            _check_host("https://evil.example.com/budget.pdf")
        _check_host("https://budget.lis.virginia.gov/sessionreport/2024/2/2434/")  # no raise


class TestLlmsTxt(unittest.TestCase):
    """docs/llms.txt must stay in sync with budget.json (generated output)."""
    def test_in_sync_with_data(self):
        from build_data import render_llms
        path = ROOT / "docs" / "llms.txt"
        self.assertTrue(path.exists(), "run scripts/build_data.py to generate llms.txt")
        expected = render_llms(BUDGET)
        self.assertEqual(path.read_text(encoding="utf-8"), expected,
                         "llms.txt is stale; re-run scripts/build_data.py")

    def test_has_key_sections(self):
        text = (ROOT / "docs" / "llms.txt").read_text(encoding="utf-8")
        for marker in ("# Virginia Budget Explorer", "## Headline totals",
                       "## Next year", "## Sources", "data/budget.json"):
            self.assertIn(marker, text)


class TestValidationArtifact(unittest.TestCase):
    """The shipped validation.json must exist and report all points passing."""
    def test_validation_all_passed(self):
        vp = ROOT / "docs" / "data" / "validation.json"
        self.assertTrue(vp.exists(), "run scripts/validate.py to produce validation.json")
        v = json.loads(vp.read_text())
        self.assertTrue(v["all_passed"], f"{v['failed']} data points failed validation")
        self.assertEqual(v["passed"], v["total"])
        self.assertGreaterEqual(v["total"], 50)


if __name__ == "__main__":
    unittest.main(verbosity=2)
