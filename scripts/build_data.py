"""Build docs/data/budget.json from curated records, verified against source.

Every numeric figure and every quote here is transcribed from the cached PDFs
and then RE-CHECKED against the extracted page text before anything is written.
If a value or quote is not found on its cited page (after light unicode/space
normalization), the build RAISES -- a wrong number or a drifted quote fails
loud instead of shipping. Page citations are PDF page indices (1-based), which
the test suite recomputes independently.

    python3 scripts/build_data.py
"""
from __future__ import annotations

import json
import logging
import re
import sys
import unicodedata
from datetime import date

from config import BUDGET_JSON, MANIFEST, TEXT_DIR, canonical_area

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("build")


# --- normalization (shared with the test suite) ----------------------------
_PUNCT = {"’": "'", "‘": "'", "“": '"', "”": '"',
          "–": "-", "—": "-", "…": "...", " ": " "}


def norm(s: str) -> str:
    """NFKC + ASCII-ize smart punctuation + collapse whitespace.

    NFKC folds ligatures (staﬃng -> staffing) so PDF typography doesn't
    break a verbatim check. Whitespace is collapsed because PDF extraction
    injects newlines mid-sentence.
    """
    s = unicodedata.normalize("NFKC", s)
    for a, b in _PUNCT.items():
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def load_pages(stem: str) -> list[str]:
    return json.loads((TEXT_DIR / f"{stem}.pages.json").read_text(encoding="utf-8"))


# --- curated source records ------------------------------------------------
# FY2024-2026 biennial GENERAL FUND spending by secretarial area.
# value_str is the exact token printed on the page (verified); millions is the
# numeric value for charts. Two stages of the SAME biennium: as adopted
# (Chapter 2, 2024) and as amended (Chapter 725, 2025) -> the change-over-time.
BY_AREA = [
    # stem, page, biennium, stage, enactment, as_of, [(label_raw, value_str)]
    ("overview_2024_fy2024-2026", 9, "FY2024-2026", "As adopted",
     "Chapter 2 (2024)", "2024-05-31", "63.7", "millions", [
        ("Health & Human Resources", "20,003.1"),
        ("K-12 Education", "19,712.9"),
        ("Higher Education", "7,230.8"),
        ("Public Safety & Veterans", "5,405.3"),
        ("Finance", "2,272.7"),
        ("Debt Service", "2,072.9"),
        ("Commerce, Labor, Nat Resources & Ag.", "2,034.4"),
        ("Admin + Central Accounts", "2,667.2"),
        ("Judicial + Other", "2,349.8"),
     ]),
    ("overview_2025_ch725", 9, "FY2024-2026", "As amended",
     "Chapter 725 (2025)", "2025-05-19", "67.4", "millions", [
        ("Health & Human Resources", "20,872"),
        ("K-12 Education", "20,256"),
        ("Higher Education", "7,487"),
        ("Public Safety & Veterans", "5,450"),
        ("Finance", "3,701"),
        ("Debt Service", "2,018"),
        ("Commerce, Labor, Nat Resources & Ag.", "2,380"),
        ("Admin + Central Accounts", "2,843"),
        ("Judicial + Other", "2,468"),
     ]),
    # FY2026-2028, HB 30 as introduced (this table prints $ in BILLIONS).
    ("overview_2026_fy2026-2028", 21, "FY2026-2028", "As introduced",
     "HB 30 (2026)", "2026-01-14", "70.1", "billions", [
        ("Health and Human Resources", "24.0"),
        ("K-12 Education", "21.2"),
        ("Higher Education", "7.8"),
        ("Public Safety and Homeland Security + Veterans", "5.8"),
        ("Finance", "2.3"),
        ("Administration + Central Accounts", "2.8"),
        ("Debt Service", "2.1"),
        ("Judicial + Other", "2.2"),
        ("Commerce, Labor, Ag & Natural Sources", "1.9"),
     ]),
]

# FY2024-2026 nongeneral fund revenues by source (Chapter 2, page 8) = $104.4B.
NGF_REVENUE = ("overview_2024_fy2024-2026", 8, "FY2024-2026", "104.4", [
    ("Federal Grants & Contracts", "Federal Grants & Contracts", "45,606.7"),
    ("Educational Institutional", "Educational Institutional", "15,267.2"),
    ("NGF Taxes", "Nongeneral Fund Taxes", "14,669.2"),
    ("All Other NGF", "All Other Nongeneral Fund", "12,413.2"),
    ("Hosp $ Inst", "Hospital & Institutional", "6,742.6"),
    ("Sales", "Sales", "5,168.4"),
    ("Licenses, Rights and Privileges", "Licenses, Rights & Privileges", "2,830.5"),
    ("Lottery Proceeds Fund", "Lottery Proceeds Fund", "1,705.8"),
])

# FY2026 General Fund snapshot (Virginia in Focus, page 17).
GF_RESOURCES_FY26 = ("virginia_in_focus_2026", 17, [
    ("Personal Income", "21,714.2"),
    ("Sales Tax", "4,987.4"),
    ("Other Taxes", "2,633.3"),
    ("Corporate Income", "2,025.5"),
    ("Transfers", "1,572.2"),
    ("Carryforward", "1,404.7"),
])
GF_TOP10_FY26 = ("virginia_in_focus_2026", 17, [
    ("K-12", "9,508.7"),
    ("Medicaid", "7,649.3"),
    ("Higher Ed Institutions", "2,025.5"),
    ("Debt Redemption", "993.0"),
    ("Personal Property Tax Relief", "950.0"),
    ("State Correction Facilities", "907.6"),
    ("Higher Ed Student Aid", "854.8"),
    ("Health Services", "703.9"),
    ("Sheriffs & Regional Jails", "634.2"),
    ("Salary Increases", "561.2"),
])

# Headline biennium totals (stated in the documents). value_str is verified.
TOTALS = [
    ("overview_2024_fy2024-2026", 8, "FY2024-2026", "As adopted",
     "Chapter 2 (2024)", "GF spending", "$63.7 billion", "2024-05-31"),
    ("overview_2025_ch725", 9, "FY2024-2026", "As amended",
     "Chapter 725 (2025)", "GF spending", "$67.4 billion", "2025-05-19"),
    # FY2026-2028 figures from the contemporaneous introduced-budget overview
    # (the conference report restates the introduced total slightly differently;
    # use the primary January source to avoid shipping two "introduced" numbers).
    ("overview_2026_fy2026-2028", 20, "FY2026-2028", "As introduced",
     "HB 30 (2026)", "GF spending", "$70.1 billion", "2026-01-14"),
    ("overview_2026_fy2026-2028", 17, "FY2026-2028", "As introduced",
     "HB 30 (2026)", "GF resources", "$71.9 billion", "2026-01-14"),
]

# Key quotes & policy principles. Each is verified verbatim on its cited page.
QUOTES = [
    ("overview_2024_fy2024-2026", 8, "Spending priorities",
     "Spending in the areas of K-12 and Health and Human Resources represents 62% of the state's total biennial operational budget.",
     "Just two areas drive nearly two-thirds of operating spending."),
    ("overview_2024_fy2024-2026", 8, "General Fund spending",
     "Chapter 2 includes general fund spending totaling $63.7 billion over the biennium with $31.8 billion in FY 2025 and $32.0 billion in FY 2026 in operating expenditures.",
     "The enacted FY2024-2026 general fund operating budget."),
    ("overview_2025_ch725", 9, "Health & Human Resources",
     "Children's Services Act (CSA) Forecast. Adds $37.0 million in FY 2025 and $63.3 million in FY 2026 for estimated caseload and cost increases in CSA.",
     "Caseload-driven forecasts push HHR spending up in the amended budget."),
    ("virginia_in_focus_2026", 17, "Where the money goes",
     "51.1% of general fund appropriations are for K-12 and Medicaid",
     "K-12 and Medicaid alone are over half the general fund."),
    ("virginia_in_focus_2026", 17, "Concentration of spending",
     "The top 10 general fund appropriations total $24.4 billion, or 72.3% of the general fund budget",
     "Ten line items account for nearly three-quarters of the general fund."),
    ("virginia_in_focus_2026", 17, "Where the money comes from",
     "The personal income tax provides about 63% of General Fund revenues",
     "The general fund leans heavily on a single revenue source."),
    ("conf_report_hb30_2026", 5, "Data centers",
     "Conference Report includes Part 3 language - applicable for this biennium only - establishing a rate of $0.011/kWh of all electricity consumed at each data center per month",
     "A first-of-its-kind energy consumption fee targeting data centers."),
    ("conf_report_hb30_2026", 5, "Data centers",
     "Annual revenue collections are capped at $600 million per year",
     "The new data-center fee is capped, with overages refunded pro-rata."),
    ("conf_report_hb30_2026", 6, "Tax relief",
     "Reflects revenue reduction of $51.0 million in the first year and $120.0 million in the second year to reflect increasing the standard deduction",
     "A standard-deduction increase trades revenue for household tax relief."),
    ("virginia_in_focus_2026", 12, "Economy",
     "Unemployment has been rising in Virginia and its regions since the beginning of 2025 with statewide unemployment reaching 3.5% in September from 3% in January 2025.",
     "A softening labor market is the backdrop to the next budget."),
]

# Key deltas/changes in the NEXT biennium (FY2026-2028, HB 30 as introduced).
# Each entry: (page, area, headline, verbatim_excerpt). The text is verified on
# its page; `headline` is our short framing of the change.
NEXT_YEAR = [
    (20, "Overall", "$2.5B more than the current budget",
     "Measured against Chapter 725 operating expenses, this represents an increase of $2.5 billion over the biennium"),
    (22, "Overall", "$4.7B in net new spending",
     "HB 30, as introduced, includes a new amendments totaling a net of $4.7 billion of funding increases over the biennium"),
    (21, "Overall", "K-12 and HHS still dominate",
     "continue to dominate total spending with 65% of spending directed to these areas of government"),
    (24, "K-12 Education", "School construction grants nearly to $519M",
     "increasing the total grants available for the biennium from $360.0 million to $519.0 million"),
    (23, "Health & Human Resources", "Children's health insurance funded",
     "Includes spending of $29.6 million in FY 2027 and $55.2 million in FY 2028 for the children's health insurance programs (FAMIS and M-CHIP)"),
    (23, "Health & Human Resources", "DD Waiver rate increases",
     "to increase rates for certain DD Waiver services that were included in a rate study of services required pursuant to the Permanent Injunction"),
    (21, "Commerce, Labor, Natural Resources & Agriculture", "$144.1M for water quality",
     "$144.1 million for the Water Quality Improvement Fund and Agriculture Cost-Share program"),
    (21, "Commerce, Labor, Natural Resources & Agriculture", "$35M for biotech at UVA",
     "$35.0 million for the Institute for Biotechnology at UVA"),
    (25, "Commerce, Labor, Natural Resources & Agriculture", "$43.5M for local stormwater",
     "Proposes $43.5 million GF in FY 2027 for deposit in the Stormwater Local Assistance Fund"),
    (26, "Public Safety & Veterans", "More for inmate medical care",
     "Proposes an additional $28.9 million GF in FY 2027 and $30.8 million GF in FY 2028 to reflect increased estimated costs of providing medical care to inmates"),
    (26, "Public Safety & Veterans", "New Cardinal Disaster Relief Fund",
     "Proposes the establishment of the Cardinal Disaster Relief Fund with the Department of Emergency Management"),
]
NEXT_YEAR_STEM = "overview_2026_fy2026-2028"


# --- verification helpers --------------------------------------------------
class VerifyError(RuntimeError):
    pass


def assert_on_page(stem: str, page: int, needle: str, kind: str) -> None:
    pages = load_pages(stem)
    if not (1 <= page <= len(pages)):
        raise VerifyError(f"{kind}: {stem} has no page {page}")
    if norm(needle) not in norm(pages[page - 1]):
        raise VerifyError(
            f"{kind} NOT FOUND on {stem} p{page}: {needle[:70]!r}")


def recompute_quote_page(stem: str, needle: str) -> int | None:
    pages = load_pages(stem)
    n = norm(needle)
    for i, p in enumerate(pages):
        if n in norm(p):
            return i + 1
    return None


# --- build -----------------------------------------------------------------
def build() -> dict:
    manifest = {m["stem"]: m for m in json.loads(MANIFEST.read_text())}
    checks = 0

    # by-area, with sum gate against the stated total
    by_area = []
    for stem, page, biennium, stage, enactment, as_of, total_str, unit, rows in BY_AREA:
        total_b = float(total_str)
        scale = 1000.0 if unit == "billions" else 1.0  # normalize everything to $M
        running = 0.0
        for label_raw, value_str in rows:
            assert_on_page(stem, page, value_str, "area value"); checks += 1
            canon = canonical_area(label_raw)
            if canon is None:
                raise VerifyError(f"unmapped area label: {label_raw!r}")
            millions = float(value_str.replace(",", "")) * scale
            running += millions
            by_area.append({
                "area": canon, "label_raw": label_raw,
                "millions": millions, "value_str": value_str,
                "biennium": biennium, "stage": stage, "enactment": enactment,
                "as_of": as_of, "source_stem": stem, "page": page,
            })
        # gate: parsed rows must sum to the document's own stated total (<=1.5%)
        diff = abs(running / 1000.0 - total_b) / total_b
        if diff > 0.015:
            raise VerifyError(
                f"{stem} area rows sum {running/1000:.1f}B != stated {total_b}B "
                f"({diff:.1%})")
        log.info("by-area %s %s: sum %.1fB vs stated %.1fB ✓",
                 biennium, stage, running / 1000, total_b)

    # nongeneral fund revenue
    stem, page, biennium, total_str, ngf_rows = NGF_REVENUE
    ngf = []
    for label_raw, display, value_str in ngf_rows:
        assert_on_page(stem, page, value_str, "ngf value"); checks += 1
        ngf.append({"source": display, "label_raw": label_raw,
                    "millions": float(value_str.replace(",", "")),
                    "value_str": value_str, "biennium": biennium,
                    "source_stem": stem, "page": page})

    # FY2026 GF resources + top-10 appropriations
    def simple(spec):
        stem, page, rows = spec
        out = []
        for label, value_str in rows:
            assert_on_page(stem, page, value_str, "gf value")
            out.append({"label": label, "millions": float(value_str.replace(",", "")),
                        "value_str": value_str, "source_stem": stem, "page": page})
        return out
    gf_resources = simple(GF_RESOURCES_FY26); checks += len(gf_resources)
    gf_top10 = simple(GF_TOP10_FY26); checks += len(gf_top10)

    # headline totals
    totals = []
    for stem, page, biennium, stage, enactment, kind, value_str, as_of in TOTALS:
        assert_on_page(stem, page, value_str, "total"); checks += 1
        totals.append({"biennium": biennium, "stage": stage, "enactment": enactment,
                       "kind": kind, "value_str": value_str,
                       "billions": float(value_str.replace("$", "").split()[0]),
                       "as_of": as_of, "source_stem": stem, "page": page})

    # quotes, with independent page recompute
    quotes = []
    for stem, page, topic, text, principle in QUOTES:
        assert_on_page(stem, page, text, "quote"); checks += 1
        rp = recompute_quote_page(stem, text)
        if rp != page:
            raise VerifyError(f"quote page mismatch on {stem}: stored {page}, found {rp}")
        quotes.append({"text": text, "topic": topic, "principle": principle,
                       "source_stem": stem, "page": page,
                       "doc_title": manifest[stem]["title"],
                       "as_of": manifest[stem]["as_of"]})

    # next-year (FY2026-2028) key changes, verbatim-verified on their page
    next_year = []
    for page, area, headline, text in NEXT_YEAR:
        assert_on_page(NEXT_YEAR_STEM, page, text, "next-year change"); checks += 1
        next_year.append({"area": area, "headline": headline, "text": text,
                          "source_stem": NEXT_YEAR_STEM, "page": page,
                          "doc_title": manifest[NEXT_YEAR_STEM]["title"]})

    # display order: areas descending by amended (Ch.725) spending
    amended = {r["area"]: r["millions"] for r in by_area if r["stage"] == "As amended"}
    area_order = sorted(amended, key=amended.get, reverse=True)

    # "Data as of" must reflect the newest SOURCE date, not the build date --
    # rebuilding from unchanged documents must not advance the freshness stamp.
    data_as_of = max(m["as_of"] for m in manifest.values())

    data = {
        "meta": {
            "title": "Virginia Budget Explorer",
            "subtitle": "Where Virginia's money comes from and where it goes",
            "data_as_of": data_as_of,
            "built_at": date.today().isoformat(),
            "checks_passed": checks,
            "note": ("Figures transcribed from official House Appropriations "
                     "Committee documents and verified verbatim against the "
                     "source page. By-area dollars are General Fund."),
        },
        "areas": area_order,
        "by_area": by_area,
        "ngf_revenue": ngf,
        "gf_resources_fy2026": gf_resources,
        "gf_top10_fy2026": gf_top10,
        "totals": totals,
        "quotes": quotes,
        "next_year_changes": next_year,
        "sources": list(manifest.values()),
    }
    return data, checks


def main() -> int:
    data, checks = build()
    BUDGET_JSON.parent.mkdir(parents=True, exist_ok=True)
    BUDGET_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("✓ wrote %s · %d source-checks passed · %d areas · %d quotes",
             BUDGET_JSON.relative_to(BUDGET_JSON.parent.parent.parent),
             checks, len(data["areas"]), len(data["quotes"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
