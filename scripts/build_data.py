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

from config import BUDGET_JSON, DOCS_DIR, MANIFEST, TEXT_DIR, canonical_area

LLMS_TXT = DOCS_DIR / "llms.txt"

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
# Each entry: (stem, page, area, headline, verbatim_excerpt). The text is
# verified on its page; `headline` is our short framing of the change. The
# first batch is transcribed from the HAC committee overview (a 107-page
# summary); the second batch is mined from the primary ~700-page DPB executive
# budget document itself -- see scripts/section.py + scripts/find_quotes.py,
# whose candidates were hand-picked and verified here.
_OVERVIEW = "overview_2026_fy2026-2028"
_EXEC_DOC = "executive_budget_doc_2026"
NEXT_YEAR = [
    (_OVERVIEW, 20, "Overall", "$2.5B more than the current budget",
     "Measured against Chapter 725 operating expenses, this represents an increase of $2.5 billion over the biennium"),
    (_OVERVIEW, 22, "Overall", "$4.7B in net new spending",
     "HB 30, as introduced, includes a new amendments totaling a net of $4.7 billion of funding increases over the biennium"),
    (_OVERVIEW, 21, "Overall", "K-12 and HHS still dominate",
     "continue to dominate total spending with 65% of spending directed to these areas of government"),
    (_OVERVIEW, 24, "K-12 Education", "School construction grants nearly to $519M",
     "increasing the total grants available for the biennium from $360.0 million to $519.0 million"),
    (_OVERVIEW, 23, "Health & Human Resources", "Children's health insurance funded",
     "Includes spending of $29.6 million in FY 2027 and $55.2 million in FY 2028 for the children's health insurance programs (FAMIS and M-CHIP)"),
    (_OVERVIEW, 23, "Health & Human Resources", "DD Waiver rate increases",
     "to increase rates for certain DD Waiver services that were included in a rate study of services required pursuant to the Permanent Injunction"),
    (_OVERVIEW, 21, "Commerce, Labor, Natural Resources & Agriculture", "$144.1M for water quality",
     "$144.1 million for the Water Quality Improvement Fund and Agriculture Cost-Share program"),
    (_OVERVIEW, 21, "Commerce, Labor, Natural Resources & Agriculture", "$35M for biotech at UVA",
     "$35.0 million for the Institute for Biotechnology at UVA"),
    (_OVERVIEW, 25, "Commerce, Labor, Natural Resources & Agriculture", "$43.5M for local stormwater",
     "Proposes $43.5 million GF in FY 2027 for deposit in the Stormwater Local Assistance Fund"),
    (_OVERVIEW, 26, "Public Safety & Veterans", "More for inmate medical care",
     "Proposes an additional $28.9 million GF in FY 2027 and $30.8 million GF in FY 2028 to reflect increased estimated costs of providing medical care to inmates"),
    (_OVERVIEW, 26, "Public Safety & Veterans", "New Cardinal Disaster Relief Fund",
     "Proposes the establishment of the Cardinal Disaster Relief Fund with the Department of Emergency Management"),
    (_EXEC_DOC, 46, "Judicial", "Expand judicial video conferencing infrastructure",
     "Provides positions and funding to support the implementation and long-term maintenance of courtroom video conferencing technology infrastructure across the Commonwealth."),
    (_EXEC_DOC, 63, "Executive Offices", "New staff for the Children's Ombudsman",
     "Provides funding and two positions for a data analyst and a deputy director for the Office of the Children's Ombudsman."),
    (_EXEC_DOC, 91, "Commerce, Labor, Natural Resources & Agriculture", "Expanded hemp enforcement",
     "Appropriates nongeneral funds to expand the department’s hemp enforcement activities. It is anticipated that the department will hire additional inspector and compliance positions, implement a product sampling program, and work more closely with local law enforcement to investigate and prosecute violations of Virginia law."),
    (_EXEC_DOC, 118, "K-12 Education", "$299M more for school construction grants",
     "In total, $299.0 million of additional state support is provided for grants to local school boards to support the construction, expansion, or modernization of public school buildings."),
    (_EXEC_DOC, 216, "Health & Human Resources", "Ends automatic inflation for Medicaid providers",
     "Eliminates the automatic inflation adjustments that would have been provided for hospitals, freestanding psychiatric facilities, disproportionate share hospitals payments, graduate medical education payments, nursing facilities, and any other provider rates for fiscal years 2027 and 2028."),
    (_EXEC_DOC, 255, "Commerce, Labor, Natural Resources & Agriculture", "Hampton Roads nutrient removal funding",
     "Provides funding to complete support for the Hampton Roads Sanitation District Boat Harbor Treatment Plant project through the Enhanced Nutrient Removal Certainty program."),
    (_EXEC_DOC, 279, "Public Safety & Veterans", "More support for State Police operations",
     "Provides additional general fund support to cover increased personnel and equipment costs."),
    (_EXEC_DOC, 299, "Transportation", "Port Authority terminal expansion",
     "Provides additional nongeneral fund appropriation to continue efforts required to keep facilities operating at optimum efficiency especially during construction elsewhere on the port terminals."),
    (_EXEC_DOC, 317, "Administration & Central Accounts", "New 2026 capital construction pool",
     "Provides funding for the construction or acquisition of capital projects at agencies and institutions of higher education. Funding for 15 projects is pooled together centrally and subject to the capital pool process in Section 2.2-1515 et. seq, Code of Virginia."),
]


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
    for stem, page, area, headline, text in NEXT_YEAR:
        assert_on_page(stem, page, text, "next-year change"); checks += 1
        next_year.append({"area": area, "headline": headline, "text": text,
                          "source_stem": stem, "page": page,
                          "doc_title": manifest[stem]["title"]})

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


def render_llms(data: dict) -> str:
    """Render an llms.txt (llmstxt.org) summary from the built data dict.

    Pure function of `data` so the test suite can regenerate and diff it -- the
    file must always be in sync with budget.json (generated output commits with
    its source).
    """
    url = {s["stem"]: s["url"] for s in data["sources"]}
    src = lambda stem, page: f"{url[stem]}#page={page}"
    L = []
    L.append("# Virginia Budget Explorer")
    L.append("")
    L.append(f"> Source-verified explorer of the Commonwealth of Virginia's general "
             f"fund budget. Every figure is transcribed from official Virginia House "
             f"Appropriations Committee documents and verified verbatim against its "
             f"source page. By-area dollars are general fund. Data as of "
             f"{data['meta'].get('data_as_of')}.")
    L.append("")
    L.append("## Headline totals")
    for t in data["totals"]:
        L.append(f"- {t['biennium']} ({t['stage']}) {t['kind']}: {t['value_str']} "
                 f"— [{t['enactment']}, p. {t['page']}]({src(t['source_stem'], t['page'])})")
    L.append("")
    L.append("## General fund spending by secretarial area (FY2024-2026, amended)")
    amended = [r for r in data["by_area"] if r["stage"] == "As amended"]
    for r in sorted(amended, key=lambda r: -r["millions"]):
        L.append(f"- {r['area']}: ${r['millions']/1000:.1f}B "
                 f"— [p. {r['page']}]({src(r['source_stem'], r['page'])})")
    L.append("")
    L.append("## Next year (FY2026-2028, HB 30) — key changes")
    for c in data.get("next_year_changes", []):
        L.append(f"- [{c['area']}] {c['headline']}: \"{c['text']}\" "
                 f"([p. {c['page']}]({src(c['source_stem'], c['page'])}))")
    L.append("")
    L.append("## Policy quotes")
    for q in data["quotes"]:
        L.append(f"- [{q['topic']}] \"{q['text']}\" — {q['doc_title']}, "
                 f"[p. {q['page']}]({src(q['source_stem'], q['page'])})")
    L.append("")
    L.append("## Sources")
    for s in data["sources"]:
        L.append(f"- [{s['title']}]({s['url']}) — {s['publisher']}, {s['page_count']} pp, as of {s['as_of']}")
    L.append("")
    L.append("## Data")
    L.append("- [Machine-readable dataset](data/budget.json)")
    L.append("- [Per-data-point verification report](data/validation.json) "
             f"— {data['meta'].get('checks_passed')} figures and quotes checked against source")
    L.append("")
    return "\n".join(L)


def main() -> int:
    data, checks = build()
    BUDGET_JSON.parent.mkdir(parents=True, exist_ok=True)
    BUDGET_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    LLMS_TXT.write_text(render_llms(data), encoding="utf-8")
    log.info("✓ wrote %s · %d source-checks passed · %d areas · %d quotes",
             BUDGET_JSON.relative_to(BUDGET_JSON.parent.parent.parent),
             checks, len(data["areas"]), len(data["quotes"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
