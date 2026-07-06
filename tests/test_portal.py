"""Self-verification for the committed Virginia Budget Portal data.

The portal's derived JSON (data/derived/portal/*.json) is generated from raw XML
that is ALSO committed (data/derived/portal/raw/*.xml). These tests re-parse the
committed XML and assert the JSON matches — so a portal-schema change or a
hand-edit can't silently alter the shipped numbers, and the repo self-verifies
offline on a fresh clone (no network). This is the portal lane of the project's
verbatim-verification discipline.

    python3 -m unittest discover -s tests
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from config import ALLOWED_HOSTS  # noqa: E402
from portal_api import (  # noqa: E402
    PORTAL_DIR, RAW_DIR, _check_host, _strip_ns,
    parse_secretariat, parse_year_session_bill,
)

INDEX = json.loads((PORTAL_DIR / "portal_index.json").read_text())
SECRETARIAT = json.loads((PORTAL_DIR / "secretariat_2026_2_HB30_Chapter.json").read_text())


class TestPortalSelfVerifies(unittest.TestCase):
    def test_index_json_matches_committed_xml(self):
        reparsed = parse_year_session_bill(_strip_ns((RAW_DIR / "bills_list.xml").read_bytes()))
        self.assertEqual(INDEX["bills"], reparsed,
                         "portal_index.json is stale vs its raw XML — re-run scripts/portal_api.py")
        self.assertEqual(INDEX["count"], len(reparsed))

    def test_secretariat_json_matches_committed_xml(self):
        reparsed = parse_secretariat(_strip_ns((RAW_DIR / "secretariat_2026_2_HB30_Chapter.xml").read_bytes()))
        for k in ("budget_year1", "budget_year2", "parts"):
            self.assertEqual(SECRETARIAT[k], reparsed[k],
                             f"secretariat JSON field {k!r} drifted from raw XML — re-run scripts/portal_api.py")


class TestPortalProvenance(unittest.TestCase):
    def test_endpoints_allowlisted(self):
        for rec in (INDEX, SECRETARIAT):
            host = urlparse(rec["endpoint"]).hostname
            self.assertIn(host, ALLOWED_HOSTS, f"off-allowlist portal endpoint: {host}")

    def test_check_host_rejects_off_allowlist(self):
        with self.assertRaises(ValueError):
            _check_host("https://evil.example.com/BudgetPortalWebService/x")
        _check_host("https://budget.lis.virginia.gov/BudgetPortalWebService/x")  # no raise


class TestPortalInvariants(unittest.TestCase):
    def test_enacted_hb30_stage_present(self):
        # The FY2026-2028 budget is enacted: HB 30, 2026 Special Session I exists
        # as a "Chapter" bill. This is the evidence behind the site's "enacted"
        # framing; if the portal ever drops it, this fails loudly.
        chapters = [b for b in INDEX["bills"]
                    if b["year"] == "2026" and b["session_type"] == "2"
                    and b["house_bill"] == "HB30" and b["bill_type"] == "Chapter"]
        self.assertTrue(chapters, "HB30 2026 Special Session I 'Chapter' not in portal index")

    def test_index_count_floor(self):
        # sessions back to 1996 across many bills/stages — a truncated fetch
        # (e.g. a partial response saved as complete) would fall under this.
        self.assertGreaterEqual(len(INDEX["bills"]), 100)

    def test_secretariat_frame_is_labeled_all_funds(self):
        self.assertEqual(SECRETARIAT["frame"], "all funds")
        self.assertIn("not be summed", SECRETARIAT["note"])
        self.assertNotIn("general fund", SECRETARIAT["note"].split("NOT general fund")[-1].lower(),
                         "note must not imply these are general-fund figures")

    def test_operating_part_totals_positive(self):
        part1 = next((p for p in SECRETARIAT["parts"] if p["part"] == "1"), None)
        self.assertIsNotNone(part1, "Part 1 (Operating Expenses) missing")
        self.assertGreater(part1["totals_year1"], 0)
        self.assertGreater(part1["totals_year2"], 0)
        # sanity: all-funds operating is ~$100B/yr, far above the ~$35B/yr GF —
        # a strong guard against accidentally storing the wrong frame here.
        self.assertGreater(part1["totals_year1"], 50_000_000_000)


class TestPortalParsing(unittest.TestCase):
    def test_int_or_none_handles_sign_and_absence(self):
        from portal_api import _int_or_none
        self.assertEqual(_int_or_none("102491360895"), 102491360895)
        self.assertEqual(_int_or_none("-5000"), -5000)   # str.isdigit() would have dropped this
        self.assertEqual(_int_or_none("  42 "), 42)
        self.assertIsNone(_int_or_none(""))
        self.assertIsNone(_int_or_none(None))
        self.assertIsNone(_int_or_none("N/A"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
