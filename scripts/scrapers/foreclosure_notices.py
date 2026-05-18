#!/usr/bin/env python3
"""
foreclosure_notices scraper — El Paso County, TX (el_paso_tx). Path B.

Source: El Paso County Clerk Foreclosures portal
  https://apps.epcountytx.gov/publicrecords/Foreclosures

Recon (runs/el_paso_tx/recon/foreclosure_notices_v2_recon.md):
  - Search by sale-date window -> server-rendered results, ?page=N
    pagination, 20 rows/page, reCAPTCHA v3 (passes for a real browser).
  - The listing row exposes only sale_date + page_count reliably; the
    instrument # is a masked placeholder.
  - "View Document" is JS-wired: click -> POST GetDocumentURL -> opens an
    InCaptureWeb viewer popup -> the notice PDF is served at
    /incaptureweb/Document/Display (application/pdf), captured here via
    Playwright route interception.
  - The PDFs are scanned images — OCR (the separate translator) extracts
    the address / debtor / DoT number / sale date / lender.

Output:
  data/el_paso_tx/raw/foreclosure_notices/pdfs/fcl_NNNN.pdf  (raw notices)
  data/el_paso_tx/raw/foreclosure_notices/listing.jsonl       (row metadata)
  data/el_paso_tx/raw/foreclosure_notices/scrape.log

Usage: foreclosure_notices.py [max_records]   (max_records for test runs)
"""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[2]
BASE = REPO / "data" / "el_paso_tx" / "raw" / "foreclosure_notices"
PDF_DIR = BASE / "pdfs"
LISTING = BASE / "listing.jsonl"
LOG = BASE / "scrape.log"
FORM = "https://apps.epcountytx.gov/publicrecords/Foreclosures"
RESULTS = ("https://apps.epcountytx.gov/publicrecords/Foreclosures/"
           "ForeclosureSearchResults")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

# Forward window of upcoming Texas first-Tuesday foreclosure sales.
DATE_FROM = "05/18/2026"
DATE_TO = "09/30/2026"
PAGE_CAP = 25            # 500-record portal cap / 20 per page
FETCH_DELAY = 2.5        # polite delay between document fetches (recon rule)

MAX_RECORDS = int(sys.argv[1]) if len(sys.argv) > 1 else 100000

_captured: list[bytes] = []   # PDF bodies captured by the route handler
_log: list[str] = []


def log(msg: str) -> None:
    line = f"[{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}] {msg}"
    _log.append(line)
    print(line, file=sys.stderr, flush=True)


def handle_display(route):
    """Intercept the InCaptureWeb /Document/Display request and keep the
    PDF body. Chromium routes PDF responses to its internal viewer, so the
    body is not readable post-hoc — it must be fetched at the route."""
    try:
        resp = route.fetch()
        body = resp.body()
        if body[:4] == b"%PDF":
            _captured.append(body)
        route.fulfill(response=resp)
    except Exception as exc:
        log(f"  route fetch error: {exc!r}")
        try:
            route.continue_()
        except Exception:
            pass


def main() -> int:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    log(f"start foreclosure_notices scrape window={DATE_FROM}..{DATE_TO} "
        f"max_records={MAX_RECORDS}")
    listing: list[dict] = []
    seq = 0
    consecutive_misses = 0

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=UA, accept_downloads=True,
                                  viewport={"width": 1600, "height": 1000})
        ctx.route("**/Document/Display", handle_display)
        pg = ctx.new_page()

        pg.goto(FORM, wait_until="domcontentloaded", timeout=45_000)
        pg.wait_for_selector("input[name='SaleDateFrom']", timeout=15_000)
        pg.wait_for_timeout(2800)  # let reCAPTCHA v3 init
        pg.fill("input[name='SaleDateFrom']", DATE_FROM)
        pg.fill("input[name='SaleDateTo']", DATE_TO)
        pg.click("button:has-text('Submit'), input[type=submit]")
        pg.wait_for_load_state("domcontentloaded", timeout=30_000)
        pg.wait_for_timeout(4000)

        m = re.search(r"([\d,]+)\s+Records?\s+Found", pg.inner_text("body"), re.I)
        total = int(m.group(1).replace(",", "")) if m else 0
        pages = min((total + 19) // 20, PAGE_CAP) if total else 0
        log(f"{total} records found -> {pages} pages")

        for pageno in range(1, pages + 1):
            if seq >= MAX_RECORDS:
                break
            if pageno > 1:
                pg.goto(f"{RESULTS}?page={pageno}",
                        wait_until="domcontentloaded", timeout=30_000)
                pg.wait_for_timeout(1200)
            row_count = pg.locator("table tr").count()
            for ri in range(1, row_count):
                if seq >= MAX_RECORDS:
                    break
                tr = pg.locator("table tr").nth(ri)
                tds = [td.inner_text().strip() for td in tr.locator("td").all()]
                if len(tds) < 8:
                    continue
                page_count, sale_date = tds[6], tds[7]
                before = len(_captured)
                # Proactive cooldown — the GetDocumentURL flow is gated by
                # reCAPTCHA v3; hammering it degrades the score. Pause every
                # 8 documents to let the score recover.
                if seq and seq % 8 == 0:
                    log(f"  cooldown 30s after {seq} docs")
                    time.sleep(30)
                # Up to 3 attempts per row with a 45s backoff between —
                # recovers from transient reCAPTCHA/rate degradation.
                for attempt in (1, 2, 3):
                    try:
                        with ctx.expect_page(timeout=20_000) as npinfo:
                            tr.locator("a:has-text('View'), button:has-text('View')"
                                       ).first.click()
                        np = npinfo.value
                        try:
                            np.wait_for_load_state("domcontentloaded", timeout=20_000)
                        except Exception:
                            pass
                        for _ in range(24):  # up to ~12s for the Display PDF
                            if len(_captured) > before:
                                break
                            np.wait_for_timeout(500)
                        try:
                            np.close()
                        except Exception:
                            pass
                    except Exception as exc:
                        log(f"  p{pageno} r{ri} attempt {attempt}: viewer error {exc!r}")
                    if len(_captured) > before:
                        break
                    if attempt < 3:
                        log(f"  p{pageno} r{ri}: backoff 45s before retry")
                        time.sleep(45)

                if len(_captured) > before:
                    seq += 1
                    consecutive_misses = 0
                    fn = f"fcl_{seq:04d}.pdf"
                    (PDF_DIR / fn).write_bytes(_captured[-1])
                    listing.append({
                        "row_index": seq, "page": pageno,
                        "sale_date": sale_date, "page_count": page_count,
                        "listing_url": RESULTS + (f"?page={pageno}" if pageno > 1 else ""),
                        "pdf_path": f"data/el_paso_tx/raw/foreclosure_notices/pdfs/{fn}",
                        "pdf_filename": fn,
                        "fetched_at": datetime.now(timezone.utc).strftime(
                            "%Y-%m-%dT%H:%M:%SZ"),
                    })
                    if seq % 10 == 0:
                        log(f"  {seq} PDFs downloaded")
                else:
                    consecutive_misses += 1
                    log(f"  p{pageno} r{ri}: no PDF captured "
                        f"(consecutive miss {consecutive_misses})")
                    if consecutive_misses >= 6:
                        log("ABORT: 6 consecutive document-fetch misses "
                            "(possible reCAPTCHA degradation / portal block)")
                        browser.close()
                        _flush(listing)
                        return 4
                time.sleep(FETCH_DELAY)
        browser.close()

    _flush(listing)
    log(f"done: {len(listing)} listing rows + {seq} PDFs")
    return 0 if listing else 5


def _flush(listing: list[dict]) -> None:
    LISTING.parent.mkdir(parents=True, exist_ok=True)
    with open(LISTING, "w", encoding="utf-8") as fh:
        for r in listing:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(LOG, "w", encoding="utf-8") as fh:
        fh.write("\n".join(_log) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
