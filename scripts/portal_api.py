"""Ingest the Virginia Budget Portal web service (budget.lis.virginia.gov).

The portal exposes the Commonwealth's budget as structured XML — the same
numbers the HAC/DPB PDFs render, but machine-readable and versioned by stage.
This module fetches, caches, parses, and commits two endpoints:

  Budget.Bills.1.ListOfYearSessionBill
      Every (year, session, bill, stage) the portal knows about, back to 1996.
      scripts/freshness.py diffs this to detect a new budget stage the moment
      it publishes (e.g. HB 30 moving Introduced -> Enrolled -> Chapter).

  Budget.Bills.2.ListOfYearSessionBillNumberTypeSecretariat/{y}/{s}/{bill}/{type}
      Per-secretariat totals per fiscal year, base and amended.

⚠ FRAME: the secretariat totals are ALL FUNDS (operating + capital across GF,
federal, tuition, etc.). Every other dollar on the site is GENERAL FUND. The two
frames must never be summed or compared without the label — that is the classic
budget-site error. Each part's own `totals_year*` is authoritative; the
secretariat rows include branch-level aggregates (e.g. "Executive Department"
already contains every "Office of …" beneath it), so summing the rows
double-counts. This module stores the rows verbatim and never sums them.

Raw XML is cached AND committed under data/derived/portal/raw/ (small text — the
evidence); the parsed JSON committed alongside is what the site and the freshness
probe read. tests/test_portal.py re-parses the committed XML and asserts the JSON
matches, so the repo self-verifies offline on a fresh clone. `fetched_at` is the
one volatile field and is preserved across an --offline re-parse (never
re-stamped from unchanged bytes).

    python3 scripts/portal_api.py            # fetch live: refresh raw cache + JSON
    python3 scripts/portal_api.py --offline  # re-parse committed XML only (no network)
"""
from __future__ import annotations

import json
import logging
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from config import ALLOWED_HOSTS, DERIVED_DIR, REQUEST_SPACING_SECONDS, USER_AGENT

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("portal")

PORTAL_BASE = "https://budget.lis.virginia.gov/BudgetPortalWebService/"
PORTAL_DIR = DERIVED_DIR / "portal"
RAW_DIR = PORTAL_DIR / "raw"
PORTAL_SOURCE = "Virginia Budget Portal web service (budget.lis.virginia.gov)"

# Which enacted bill/stage to pull secretariat (all-funds) totals for. HB 30,
# 2026 Special Session I, is the FY2026-2028 biennial budget; "Chapter" is the
# enacted stage. Keep this list tiny and current — the freshness probe flags
# when a newer stage appears.
SECRETARIAT_TARGETS = [
    {"year": "2026", "session_type": "2", "bill": "HB30", "stage": "Chapter",
     "biennium": "FY2026-2028"},
]

_last_request = 0.0


def _check_host(url: str) -> None:
    """Raise on any URL outside the authoritative allowlist (same rule as
    scrape.py — an off-origin host must fail loud, not be trusted)."""
    host = urlparse(url).hostname
    if host not in ALLOWED_HOSTS:
        raise ValueError(f"refusing off-allowlist portal host: {host!r} ({url})")


def _strip_ns(xml_bytes: bytes) -> ET.Element:
    """Parse XML namespace-agnostically.

    The portal wraps everything in a default datacontract namespace and uses an
    `i:nil` prefix for null fields. The schema is undocumented and could shift,
    so we match on local tag names: drop xmlns decls, prefixed attributes, and
    element/attribute prefixes before parsing.
    """
    txt = xml_bytes.decode("utf-8", "replace")
    txt = re.sub(r'\sxmlns(:\w+)?="[^"]*"', "", txt)   # xmlns declarations
    txt = re.sub(r'\s\w+:\w+="[^"]*"', "", txt)         # prefixed attrs (i:nil)
    txt = re.sub(r"<(/?)\w+:", r"<\1", txt)              # element prefixes
    return ET.fromstring(txt)


def fetch(path: str, name: str, *, offline: bool) -> bytes:
    """Return raw XML bytes for a portal endpoint path.

    offline: read the committed raw cache only (no network) — for CI and tests.
    live: rate-limited GET (host-allowlisted, informative UA), then write the
    raw cache so re-runs and the self-verifying test never re-download.
    """
    global _last_request
    raw_path = RAW_DIR / f"{name}.xml"
    if offline:
        if not raw_path.exists():
            raise FileNotFoundError(
                f"--offline but no committed cache at {raw_path} (run without --offline once)")
        return raw_path.read_bytes()

    url = PORTAL_BASE + path
    _check_host(url)
    wait = REQUEST_SPACING_SECONDS - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    log.info("GET %s", url)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read()
    _last_request = time.monotonic()
    if not body.lstrip().startswith(b"<"):
        raise ValueError(f"portal returned non-XML for {url}: {body[:80]!r}")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(body)
    return body


def _int_or_none(text: str | None) -> int | None:
    text = (text or "").strip()
    return int(text) if text.isdigit() else None


def parse_year_session_bill(root: ET.Element) -> list[dict]:
    """[(year, session_type, session_desc, house_bill, senate_bill, bill_type)]."""
    out = []
    for row in root.iter("YearsSessionsBills"):
        out.append({
            "year": (row.findtext("SessionYear") or "").strip(),
            "session_type": (row.findtext("SessionType") or "").strip(),
            "session_desc": (row.findtext("SessionDesc") or "").strip(),
            "house_bill": (row.findtext("HouseBillNumber") or "").strip(),
            "senate_bill": (row.findtext("SenateBillNumber") or "").strip(),
            "bill_type": (row.findtext("BillType") or "").strip(),
        })
    return out


def parse_secretariat(root: ET.Element) -> dict:
    """Parse the per-secretariat all-funds totals. Rows are stored verbatim and
    NOT summed (they include branch aggregates); each part's totals_year* is the
    authoritative figure."""
    parts = []
    for pt in root.iter("Parts"):
        secs = []
        sl = pt.find("SecretariatList")
        for s in (sl.findall("SecretariatDesc") if sl is not None else []):
            secs.append({
                "name": (s.findtext("Secretariat") or "").strip(),
                "short": (s.findtext("SecretariatShortName") or "").strip(),
                "fy1": _int_or_none(s.findtext("SecretariatFY1")),
                "fy2": _int_or_none(s.findtext("SecretariatFY2")),
                "amended_fy1": _int_or_none(s.findtext("SecretariatAmendedFY1")),
                "amended_fy2": _int_or_none(s.findtext("SecretariatAmendedFY2")),
            })
        parts.append({
            "part": (pt.findtext("Part") or "").strip(),
            "description": (pt.findtext("PartDescription") or "").strip(),
            "totals_year1": _int_or_none(pt.findtext("TotalsYear1")),
            "totals_year2": _int_or_none(pt.findtext("TotalsYear2")),
            "amended_totals_year1": _int_or_none(pt.findtext("AmendedTotalsYear1")),
            "amended_totals_year2": _int_or_none(pt.findtext("AmendedTotalsYear2")),
            "secretariats": secs,
        })
    return {
        "budget_year1": _int_or_none(root.findtext("BudgetYear1")),
        "budget_year2": _int_or_none(root.findtext("BudgetYear2")),
        "parts": parts,
    }


def _prior_fetched_at(path: Path) -> str | None:
    """The committed JSON's fetched_at, so an --offline re-parse from unchanged
    bytes preserves provenance instead of re-stamping it to today."""
    if path.exists():
        try:
            return json.loads(path.read_text()).get("fetched_at")
        except (json.JSONDecodeError, OSError):
            return None
    return None


def build(offline: bool = False) -> list[Path]:
    PORTAL_DIR.mkdir(parents=True, exist_ok=True)
    written = []

    # 1. Year / session / bill / stage index — the freshness canary.
    idx_json = PORTAL_DIR / "portal_index.json"
    path = "Budget.Bills.1.ListOfYearSessionBill/"
    bills = parse_year_session_bill(_strip_ns(fetch(path, "bills_list", offline=offline)))
    if not bills:
        raise ValueError("portal index parsed to zero bills — refusing to write")
    idx = {
        "endpoint": PORTAL_BASE + path,
        "source": PORTAL_SOURCE,
        "fetched_at": _prior_fetched_at(idx_json) if offline else date.today().isoformat(),
        "count": len(bills),
        "bills": bills,
    }
    idx_json.write_text(json.dumps(idx, indent=2, ensure_ascii=False), encoding="utf-8")
    written.append(idx_json)
    log.info("portal index: %d (year, session, bill, stage) rows", len(bills))

    # 2. Per-secretariat all-funds totals for the enacted budget(s).
    for t in SECRETARIAT_TARGETS:
        name = f"secretariat_{t['year']}_{t['session_type']}_{t['bill']}_{t['stage']}"
        sub = f"Budget.Bills.2.ListOfYearSessionBillNumberTypeSecretariat/{t['year']}/{t['session_type']}/{t['bill']}/{t['stage']}/"
        parsed = parse_secretariat(_strip_ns(fetch(sub, name, offline=offline)))
        out_json = PORTAL_DIR / f"{name}.json"
        rec = {
            "endpoint": PORTAL_BASE + sub,
            "source": PORTAL_SOURCE,
            "fetched_at": _prior_fetched_at(out_json) if offline else date.today().isoformat(),
            "biennium": t["biennium"],
            "bill": t["bill"], "bill_stage": t["stage"],
            "session_year": t["year"], "session_type": t["session_type"],
            "frame": "all funds",
            "note": ("All-funds totals (NOT general fund). Each part's totals_year* "
                     "is authoritative; secretariat rows include branch aggregates "
                     "(e.g. Executive Department contains every Office beneath it) "
                     "and must not be summed."),
            **parsed,
        }
        out_json.write_text(json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8")
        written.append(out_json)
        op = next((p for p in parsed["parts"] if p["part"] == "1"), None)
        if op:
            log.info("%s %s: operating all-funds FY%s $%.1fB / FY%s $%.1fB",
                     t["bill"], t["stage"], parsed["budget_year1"],
                     (op["totals_year1"] or 0) / 1e9, parsed["budget_year2"],
                     (op["totals_year2"] or 0) / 1e9)
    return written


def main() -> int:
    offline = "--offline" in sys.argv[1:]
    written = build(offline=offline)
    log.info("✓ wrote %d portal file(s)%s", len(written), " (offline re-parse)" if offline else "")
    for p in written:
        log.info("  %s", p.relative_to(DERIVED_DIR.parent.parent))
    return 0


if __name__ == "__main__":
    sys.exit(main())
