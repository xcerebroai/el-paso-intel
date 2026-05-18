#!/usr/bin/env python3
"""
foreclosure_notices scraper — El Paso County, TX (el_paso_tx). Path B.

Source: El Paso County Clerk Foreclosures portal
  https://apps.epcountytx.gov/publicrecords/Foreclosures

Approach (v3 — session recycling):
  GetDocumentURL is gated by reCAPTCHA v3 and a per-session score ceiling:
  after ~9 document fetches a session's score is exhausted and
  GetDocumentURL returns `false` (the v1 popup approach and the v2
  direct-POST approach both hit the same ~9 wall). The fix is to recycle
  the whole browser session every RECYCLE_EVERY documents — a fresh
  context + fresh search re-establishes a fresh reCAPTCHA score.

  Flow: search -> page results, collecting each row's foreclosureID (the
  `id` of its View Document anchor) -> per document, POST
  /Foreclosures/GetDocumentURL/ {"foreclosureID":id} -> load the returned
  InCaptureWeb viewer URL -> the viewer fetches the notice PDF from
  /Document/Display, captured via a route handler.

Output:
  data/el_paso_tx/raw/foreclosure_notices/pdfs/fcl_NNNN.pdf
  data/el_paso_tx/raw/foreclosure_notices/listing.jsonl
  data/el_paso_tx/raw/foreclosure_notices/scrape.log

Usage: foreclosure_notices.py [max_records]
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
ROOT = "https://apps.epcountytx.gov/publicrecords/Foreclosures"
RESULTS = ROOT + "/ForeclosureSearchResults"
GETDOCURL = ROOT + "/GetDocumentURL/"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

DATE_FROM = "05/18/2026"
DATE_TO = "09/30/2026"
PAGE_CAP = 25
RECYCLE_EVERY = 8        # fetch this many docs per session, then recycle
FETCH_DELAY = 1.5

MAX_RECORDS = int(sys.argv[1]) if len(sys.argv) > 1 else 100000

_captured: list[bytes] = []
_log: list[str] = []


def log(msg: str) -> None:
    line = f"[{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}] {msg}"
    _log.append(line)
    print(line, file=sys.stderr, flush=True)


def handle_display(route):
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


def open_session(pw):
    """Fresh browser context with a freshly-scored reCAPTCHA session:
    load the portal and submit the search."""
    browser = pw.chromium.launch(headless=True)
    ctx = browser.new_context(user_agent=UA,
                              viewport={"width": 1600, "height": 1000})
    ctx.route("**/Document/Display", handle_display)
    pg = ctx.new_page()
    pg.goto(ROOT, wait_until="domcontentloaded", timeout=45_000)
    pg.wait_for_selector("input[name='SaleDateFrom']", timeout=15_000)
    pg.wait_for_timeout(2800)  # let reCAPTCHA v3 init
    pg.fill("input[name='SaleDateFrom']", DATE_FROM)
    pg.fill("input[name='SaleDateTo']", DATE_TO)
    pg.click("button:has-text('Submit'), input[type=submit]")
    pg.wait_for_load_state("domcontentloaded", timeout=30_000)
    pg.wait_for_timeout(3500)
    return browser, ctx, pg


def collect_ids(pg) -> list[dict]:
    """Page the results table, capturing each row's foreclosureID."""
    m = re.search(r"([\d,]+)\s+Records?\s+Found", pg.inner_text("body"), re.I)
    total = int(m.group(1).replace(",", "")) if m else 0
    pages = min((total + 19) // 20, PAGE_CAP) if total else 0
    log(f"{total} records found -> {pages} pages")
    rows = []
    for pageno in range(1, pages + 1):
        if pageno > 1:
            pg.goto(f"{RESULTS}?page={pageno}",
                    wait_until="domcontentloaded", timeout=30_000)
            pg.wait_for_timeout(900)
        n = pg.locator("table tr").count()
        for ri in range(1, n):
            tr = pg.locator("table tr").nth(ri)
            tds = [td.inner_text().strip() for td in tr.locator("td").all()]
            if len(tds) < 8:
                continue
            a = tr.locator("a[id]").first
            fid = a.get_attribute("id") if a.count() else None
            if fid:
                rows.append({"foreclosure_id": fid, "page": pageno,
                             "page_count": tds[6], "sale_date": tds[7]})
    return rows, total


def fetch_one(ctx, view, fid: str) -> bool:
    """POST GetDocumentURL for one foreclosureID and load the viewer so the
    notice PDF is captured. Returns True if a PDF was captured."""
    before = len(_captured)
    try:
        r = ctx.request.post(
            GETDOCURL,
            data=json.dumps({"foreclosureID": fid}),
            headers={"content-type": "application/json;charset=UTF-8",
                     "Referer": RESULTS},
            timeout=30_000)
        if r.status != 200:
            raise RuntimeError(f"GetDocumentURL HTTP {r.status}")
        index_url = r.json()
        if not isinstance(index_url, str) or "http" not in index_url:
            raise RuntimeError(f"GetDocumentURL denied (body={index_url!r})")
        view.goto(index_url, wait_until="domcontentloaded", timeout=30_000)
        for _ in range(30):  # up to ~15s for the Display PDF
            if len(_captured) > before:
                return True
            view.wait_for_timeout(500)
    except Exception as exc:
        log(f"  fid={fid}: {exc!r}")
    return len(_captured) > before


def _flush(listing: list[dict]) -> None:
    LISTING.parent.mkdir(parents=True, exist_ok=True)
    with open(LISTING, "w", encoding="utf-8") as fh:
        for r in listing:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(LOG, "w", encoding="utf-8") as fh:
        fh.write("\n".join(_log) + "\n")


def main() -> int:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    log(f"start foreclosure_notices scrape window={DATE_FROM}..{DATE_TO} "
        f"max_records={MAX_RECORDS} recycle_every={RECYCLE_EVERY}")
    listing: list[dict] = []
    seq = 0
    consecutive_misses = 0

    with sync_playwright() as pw:
        browser, ctx, pg = open_session(pw)
        rows, total = collect_ids(pg)
        log(f"collected {len(rows)} document ids")
        view = ctx.new_page()
        in_session = 0   # docs fetched on the current session

        idx = 0
        while idx < len(rows) and seq < MAX_RECORDS:
            if in_session >= RECYCLE_EVERY:
                log(f"  recycling session after {in_session} docs "
                    f"({seq} total)")
                browser.close()
                browser, ctx, pg = open_session(pw)
                view = ctx.new_page()
                in_session = 0

            row = rows[idx]
            ok = fetch_one(ctx, view, row["foreclosure_id"])
            in_session += 1
            idx += 1

            if ok:
                seq += 1
                consecutive_misses = 0
                fn = f"fcl_{seq:04d}.pdf"
                (PDF_DIR / fn).write_bytes(_captured[-1])
                listing.append({
                    "row_index": seq, "foreclosure_id": row["foreclosure_id"],
                    "page": row["page"], "sale_date": row["sale_date"],
                    "page_count": row["page_count"],
                    "listing_url": (RESULTS + (f"?page={row['page']}"
                                               if row["page"] > 1 else "")),
                    "pdf_path": f"data/el_paso_tx/raw/foreclosure_notices/pdfs/{fn}",
                    "pdf_filename": fn,
                    "fetched_at": datetime.now(timezone.utc).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"),
                })
                if seq % 10 == 0:
                    log(f"  {seq} PDFs downloaded")
            else:
                consecutive_misses += 1
                log(f"  fid={row['foreclosure_id']}: no PDF "
                    f"(consecutive miss {consecutive_misses})")
                if consecutive_misses == 2:
                    # two misses in a row — force a session recycle early
                    in_session = RECYCLE_EVERY
                if consecutive_misses >= 8:
                    log("ABORT: 8 consecutive misses even with session recycling")
                    browser.close()
                    _flush(listing)
                    return 4
            time.sleep(FETCH_DELAY)
        browser.close()

    _flush(listing)
    log(f"done: {len(listing)} PDFs from {total} listed records")
    return 0 if listing else 5


if __name__ == "__main__":
    raise SystemExit(main())
