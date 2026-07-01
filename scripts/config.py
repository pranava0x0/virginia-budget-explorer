"""Single source of truth for the VA Budget dashboard pipeline.

Holds paths, the canonical list of source documents to scrape, the host
allowlist, and the canonical secretarial-area names. Everything downstream
(scrape, extract, build, tests) imports from here.
"""
from __future__ import annotations

from pathlib import Path

# --- Paths -----------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "sources" / "raw"
TEXT_DIR = ROOT / "data" / "text"
DERIVED_DIR = ROOT / "data" / "derived"
DOCS_DIR = ROOT / "docs"
MANIFEST = ROOT / "sources" / "manifest.json"
BUDGET_JSON = DOCS_DIR / "data" / "budget.json"

# --- Network ethics --------------------------------------------------------
USER_AGENT = "VABudgetDashboard/0.1 (civic budget research; pranava.raparla@gmail.com)"
REQUEST_SPACING_SECONDS = 2.0  # >= 1.5s between requests to one host
# Authoritative origins only. The scraper RAISES on any off-allowlist host.
ALLOWED_HOSTS = {
    "budget.lis.virginia.gov",
    "hac.virginia.gov",
    "dpb.virginia.gov",
}

# --- Source documents ------------------------------------------------------
# Each entry is one official PDF. `stem` is the local filename (no extension).
# `biennium` / `as_of` describe what the document reports; `session` is the GA
# session that produced it. These power provenance + the multi-year axis.
SOURCES = [
    {
        "stem": "overview_2024_fy2024-2026",
        "url": "https://budget.lis.virginia.gov/sessionreport/2024/2/2434/",
        "title": "An Overview of Virginia's Biennial Budget FY 2024-2026",
        "publisher": "House Appropriations Committee Staff",
        "session": "2024 Special Session I",
        "enactment": "Chapter 2, 2024 Special Session I",
        "biennium": "FY2024-2026",
        "stage": "as adopted",
        "as_of": "2024-05-31",
    },
    {
        "stem": "overview_2025_ch725",
        "url": "https://budget.lis.virginia.gov/sessionreport/2025/1/2467/",
        "title": "Overview of Virginia's Budget for FY 2024-2026 (Chapter 725)",
        "publisher": "House Appropriations Committee Staff",
        "session": "2025 Session",
        "enactment": "Chapter 725, 2025 Acts of Assembly",
        "biennium": "FY2024-2026",
        "stage": "amended",
        "as_of": "2025-05-19",
    },
    {
        "stem": "overview_2026_fy2026-2028",
        "url": "https://hac.virginia.gov/wp-content/uploads/2026/01/2026-Summary-Document-1-8-2026.pdf",
        "title": "An Overview of Virginia's Biennial Budget for FY 2026-2028 (HB 30, as introduced)",
        "publisher": "House Appropriations Committee Staff",
        "session": "2026 Session",
        "enactment": "HB 30, as introduced",
        "biennium": "FY2026-2028",
        "stage": "as introduced",
        "as_of": "2026-01-14",
    },
    {
        "stem": "conf_report_hb30_2026",
        "url": "https://hac.virginia.gov/wp-content/uploads/2026/06/Conference-Report-Summary-Presentation.pdf",
        "title": "HB 30 Conference Report (FY 2026-2028 Biennial Budget)",
        "publisher": "House Appropriations Committee Staff",
        "session": "2026 Session",
        "enactment": "HB 30 Conference Report",
        "biennium": "FY2026-2028",
        "stage": "conference report",
        "as_of": "2026-06-22",
    },
    {
        "stem": "virginia_in_focus_2026",
        "url": "https://hac.virginia.gov/wp-content/uploads/2026/01/Virginia-In-Focus-PRINT.pdf",
        "title": "Virginia in Focus: Budget and Outcomes for Core Government Areas",
        "publisher": "House Appropriations Committee Staff",
        "session": "2026 Session",
        "enactment": "n/a",
        "biennium": "FY2024-2026",
        "stage": "reference",
        "as_of": "2026-01-15",
    },
    {
        "stem": "executive_budget_doc_2026",
        "url": "https://dpb.virginia.gov/budget/buddoc26/BudgetDocument.pdf",
        "title": "The 2026 Executive Budget Document: Commonwealth of Virginia 2026-2028 Biennial Budget and Amendments to the 2025 Appropriation Act",
        "publisher": "Virginia Department of Planning and Budget",
        "session": "2026 Session",
        "enactment": "HB 30, as introduced",
        "biennium": "FY2026-2028",
        "stage": "as introduced",
        "as_of": "2025-12-17",
    },
]

# --- Canonical secretarial areas ------------------------------------------
# The overviews print slightly varied labels for the same area across years.
# Map every observed variant -> a single canonical name so the time series
# lines up. Keep the raw label alongside the canonical one when storing data.
AREA_CANONICAL = {
    "health & human resources": "Health & Human Resources",
    "health and human resources": "Health & Human Resources",
    "k-12 education": "K-12 Education",
    "k-12 direct aid": "K-12 Education",
    "higher education": "Higher Education",
    "public safety & veterans": "Public Safety & Veterans",
    "public safety and veterans": "Public Safety & Veterans",
    "public safety and homeland security + veterans": "Public Safety & Veterans",
    "public safety": "Public Safety & Veterans",
    "finance": "Finance",
    "debt service": "Debt Service",
    "commerce, labor, nat resources & ag.": "Commerce, Labor, Natural Resources & Agriculture",
    "commerce, labor, natural resources & agriculture": "Commerce, Labor, Natural Resources & Agriculture",
    "commerce, labor, ag & natural sources": "Commerce, Labor, Natural Resources & Agriculture",
    "commerce & trade": "Commerce, Labor, Natural Resources & Agriculture",
    "admin + central accounts": "Administration & Central Accounts",
    "administration + central accounts": "Administration & Central Accounts",
    "administration & central accounts": "Administration & Central Accounts",
    "administration": "Administration & Central Accounts",
    "judicial + other": "Judicial & Other",
    "judicial & other": "Judicial & Other",
    "judicial": "Judicial & Other",
}


def canonical_area(label: str) -> str | None:
    """Return the canonical area name for a printed label, or None if unknown.

    Returns None (rather than guessing) so an unmapped label fails loud at
    ingest instead of silently splitting one area across two series.
    """
    return AREA_CANONICAL.get(label.strip().lower().rstrip(":"))
