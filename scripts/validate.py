"""Per-data-point validator for the shipped dashboard.

Walks every figure and quote in docs/data/budget.json, re-checks it against the
extracted source page (normalized verbatim match), and emits:

  - a printed PASS/FAIL line per data point, with an evidence snippet
  - docs/data/validation.json  (consumed by the site to show a "verified"
    badge + the exact source link for each point)

Exit code is non-zero if any point fails, so this doubles as a CI gate. This is
the granular complement to tests/test_budget.py: where the tests assert in bulk,
this enumerates and reports every single point so verification is auditable.

    python3 scripts/validate.py
"""
from __future__ import annotations

import json
import sys
from datetime import date

from config import BUDGET_JSON, TEXT_DIR
from build_data import norm  # shared normalizer

_pages: dict[str, list[str]] = {}


def pages(stem: str) -> list[str]:
    if stem not in _pages:
        _pages[stem] = json.loads((TEXT_DIR / f"{stem}.pages.json").read_text())
    return _pages[stem]


def evidence(stem: str, page: int, needle: str) -> tuple[bool, str]:
    """Return (found, snippet). Snippet is a window of normalized page text
    around the match, so a human (or the UI) can see the value in context."""
    pg = pages(stem)
    if not (1 <= page <= len(pg)):
        return False, f"(no page {page} in {stem})"
    text = norm(pg[page - 1])
    n = norm(needle)
    idx = text.find(n)
    if idx < 0:
        return False, ""
    start = max(0, idx - 45)
    end = min(len(text), idx + len(n) + 45)
    return True, ("…" if start else "") + text[start:end] + ("…" if end < len(text) else "")


def points(data: dict):
    """Flatten every verifiable data point into (id, type, label, value, stem, page)."""
    for r in data["by_area"]:
        yield (f"area:{r['area']}:{r['stage']}", "by_area",
               f"{r['area']} ({r['stage']})", r["value_str"], r["source_stem"], r["page"])
    for r in data["ngf_revenue"]:
        yield (f"ngf:{r['source']}", "ngf_revenue", r["source"], r["value_str"], r["source_stem"], r["page"])
    for r in data["gf_resources_fy2026"]:
        yield (f"gfres:{r['label']}", "gf_resources", r["label"], r["value_str"], r["source_stem"], r["page"])
    for r in data["gf_top10_fy2026"]:
        yield (f"gftop:{r['label']}", "gf_top10", r["label"], r["value_str"], r["source_stem"], r["page"])
    for r in data["totals"]:
        yield (f"total:{r['biennium']}:{r['kind']}", "total",
               f"{r['biennium']} {r['kind']}", r["value_str"], r["source_stem"], r["page"])
    for i, q in enumerate(data["quotes"]):
        yield (f"quote:{i}", "quote", q["topic"], q["text"], q["source_stem"], q["page"])
    for i, c in enumerate(data.get("next_year_changes", [])):
        yield (f"change:{i}", "next_year_change", c["headline"], c["text"], c["source_stem"], c["page"])


def main() -> int:
    data = json.loads(BUDGET_JSON.read_text())
    url_for = {s["stem"]: s["url"] for s in data["sources"]}
    title_for = {s["stem"]: s["title"] for s in data["sources"]}

    results, failed = [], 0
    for pid, ptype, label, value, stem, page in points(data):
        ok, snippet = evidence(stem, page, value)
        if not ok:
            failed += 1
        mark = "✓" if ok else "✗ FAIL"
        print(f"{mark}  [{ptype}] {label}  ·  {stem} p{page}")
        if not ok:
            print(f"        value not found: {value[:80]!r}")
        results.append({
            "id": pid, "type": ptype, "label": label,
            "value": value if ptype not in ("quote", "next_year_change") else None,
            "source_stem": stem, "doc_title": title_for.get(stem),
            "page": page, "url": f"{url_for.get(stem, '')}#page={page}",
            "ok": ok, "evidence": snippet,
        })

    report = {
        "validated_on": date.today().isoformat(),
        "data_as_of": data["meta"].get("data_as_of"),
        "total": len(results),
        "passed": len(results) - failed,
        "failed": failed,
        "all_passed": failed == 0,
        "points": results,
    }
    out = BUDGET_JSON.parent / "validation.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n{'✓ ALL PASSED' if failed == 0 else '✗ ' + str(failed) + ' FAILED'} · "
          f"{report['passed']}/{report['total']} points verified · wrote {out.name}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
