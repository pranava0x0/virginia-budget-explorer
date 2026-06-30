"""Download and cache the official Virginia budget PDFs.

Idempotent: a source already present as a valid PDF is not re-downloaded
(re-runs are fast and never re-hit the server). Enforces a host allowlist so
an off-origin URL RAISES instead of silently pulling a non-authoritative file,
and validates the %PDF magic so an HTML 404 page can never masquerade as a
budget document. Writes sources/manifest.json with full provenance.

Stdlib only (urllib) -- no third-party HTTP dependency to keep the supply
chain minimal.

    python3 scripts/scrape.py            # fetch missing, verify present
    python3 scripts/scrape.py --force    # re-download everything
"""
from __future__ import annotations

import hashlib
import json
import logging
import sys
import time
from datetime import date
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import fitz  # PyMuPDF, for page_count in the manifest

from config import (
    ALLOWED_HOSTS,
    MANIFEST,
    RAW_DIR,
    REQUEST_SPACING_SECONDS,
    SOURCES,
    USER_AGENT,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("scrape")


def _check_host(url: str) -> None:
    host = urlparse(url).hostname or ""
    if host not in ALLOWED_HOSTS:
        raise ValueError(
            f"refusing off-allowlist host {host!r} for {url} "
            f"(allowed: {sorted(ALLOWED_HOSTS)})"
        )


def _is_pdf(path) -> bool:
    with open(path, "rb") as fh:
        return fh.read(5) == b"%PDF-"


def download(url: str, dest) -> int:
    _check_host(url)
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=60) as resp:
        status = resp.status
        data = resp.read()
    if not data.startswith(b"%PDF-"):
        raise ValueError(
            f"{url} did not return a PDF (got {data[:40]!r}); refusing to cache"
        )
    dest.write_bytes(data)
    return status


def main(argv: list[str]) -> int:
    force = "--force" in argv
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []
    failures = 0

    for src in SOURCES:
        dest = RAW_DIR / f"{src['stem']}.pdf"
        status = None
        if dest.exists() and _is_pdf(dest) and not force:
            log.info("cached  %s", dest.name)
        else:
            try:
                log.info("fetch   %s <- %s", dest.name, src["url"])
                status = download(src["url"], dest)
                time.sleep(REQUEST_SPACING_SECONDS)
            except Exception as exc:  # network/parse: log and continue
                failures += 1
                log.error("FAILED %s: %s", src["stem"], exc)
                continue

        digest = hashlib.sha256(dest.read_bytes()).hexdigest()
        page_count = fitz.open(dest).page_count
        manifest.append({
            "stem": src["stem"],
            "url": src["url"],
            "title": src["title"],
            "publisher": src["publisher"],
            "enactment": src["enactment"],
            "biennium": src["biennium"],
            "stage": src["stage"],
            "as_of": src["as_of"],
            "bytes": dest.stat().st_size,
            "page_count": page_count,
            "sha256": digest,
            "http_status": status,
            "captured_at": date.today().isoformat(),
        })

    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    ok = len(manifest)
    log.info("✓ %d cached · ✗ %d failed · manifest -> %s",
             ok, failures, MANIFEST.relative_to(RAW_DIR.parent.parent))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
