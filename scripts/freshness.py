"""Freshness probe: detect a new budget stage or a changed source document.

The site once silently presented a superseded budget stage as current (HB 30 was
enacted while the site still called it "as introduced"). This makes that failure
loud instead. It NEVER auto-ingests — detection only; a human curates the new
document into the pipeline.

Two lanes, run against committed baselines so a fresh clone has everything it
needs to diff:

  1. Portal stage lane (primary canary). Fetch the live year/session/bill/stage
     list and diff it against the committed data/derived/portal/portal_index.json.
     A new (year, session, bill, stage) row — e.g. HB 30 gaining a "Chapter"
     stage — is the highest-signal freshness event.

  2. Source-document lane. HEAD each manifest URL and compare its Content-Length
     to the sha256-anchored `bytes` recorded in sources/manifest.json at capture.
     A size change (or a URL that now errors) means the document was re-issued.

Exit code is 0 by default (a detected change is not a failure). Under GitHub
Actions it writes `drift=true|false` to $GITHUB_OUTPUT and a Markdown report to
freshness_report.md for the workflow to open an issue. `--check` exits non-zero
on drift, for local/manual use.

    python3 scripts/freshness.py           # probe live, print a report
    python3 scripts/freshness.py --check   # exit 1 if anything changed
"""
from __future__ import annotations

import json
import logging
import os
import socket
import sys
import urllib.request
from pathlib import Path

from config import MANIFEST, USER_AGENT
from portal_api import PORTAL_BASE, PORTAL_DIR, http_get, parse_year_session_bill, _strip_ns

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("freshness")

INDEX_ENDPOINT = "Budget.Bills.1.ListOfYearSessionBill/"


def _bill_key(b: dict) -> tuple:
    return (b["year"], b["session_type"], b["house_bill"], b["senate_bill"], b["bill_type"])


def _bill_label(b: dict) -> str:
    bill = b["house_bill"] or b["senate_bill"]
    return f"{b['year']} {b['session_desc']} · {bill} · {b['bill_type']}"


def probe_portal() -> tuple[list[str], list[str]]:
    """Return (added_labels, removed_labels) vs the committed portal index."""
    baseline = json.loads((PORTAL_DIR / "portal_index.json").read_text())["bills"]
    live = parse_year_session_bill(_strip_ns(http_get(PORTAL_BASE + INDEX_ENDPOINT)))
    base_keys = {_bill_key(b): b for b in baseline}
    live_keys = {_bill_key(b): b for b in live}
    added = [_bill_label(b) for k, b in live_keys.items() if k not in base_keys]
    removed = [_bill_label(b) for k, b in base_keys.items() if k not in live_keys]
    return sorted(added), sorted(removed)


def probe_sources() -> list[str]:
    """Return a list of human-readable change notes for the six source docs."""
    notes = []
    for m in json.loads(Path(MANIFEST).read_text()):
        url, stem, want = m["url"], m["stem"], m.get("bytes")
        try:
            req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=30) as r:
                got = r.headers.get("Content-Length")
                lm = r.headers.get("Last-Modified")
            got = int(got) if got and got.isdigit() else None
            if want and got is not None and got != want:
                notes.append(f"{stem}: size changed {want:,} → {got:,} bytes"
                             + (f" (Last-Modified {lm})" if lm else ""))
        except (urllib.error.URLError, socket.timeout) as e:
            notes.append(f"{stem}: URL now errors ({type(e).__name__}: {e}) — {url}")
    return notes


def _emit_github(drift: bool, report: str) -> None:
    """Wire results to the GitHub Actions runner, if present."""
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"drift={'true' if drift else 'false'}\n")
    if os.environ.get("GITHUB_ACTIONS"):
        Path("freshness_report.md").write_text(report, encoding="utf-8")


def main() -> int:
    check = "--check" in sys.argv[1:]
    added, removed = probe_portal()
    source_notes = probe_sources()
    drift = bool(added or removed or source_notes)

    lines = ["## Budget freshness probe", ""]
    if not drift:
        lines.append("No change: the live portal stages and all six source documents "
                     "match the committed baseline.")
    else:
        if added:
            lines += ["**New budget stage(s) detected** (curate into the pipeline — do not auto-ingest):", ""]
            lines += [f"- {a}" for a in added] + [""]
        if removed:
            lines += ["**Stage(s) no longer listed** (portal changed):", ""]
            lines += [f"- {r}" for r in removed] + [""]
        if source_notes:
            lines += ["**Source document(s) changed** (re-run scripts/scrape.py to re-capture):", ""]
            lines += [f"- {n}" for n in source_notes] + [""]
    report = "\n".join(lines)
    print(report)

    _emit_github(drift, report)
    if drift:
        log.info("freshness: DRIFT (%d new, %d removed, %d source change(s))",
                 len(added), len(removed), len(source_notes))
    else:
        log.info("freshness: no change")
    return 1 if (drift and check) else 0


if __name__ == "__main__":
    sys.exit(main())
