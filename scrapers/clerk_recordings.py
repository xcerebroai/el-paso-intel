#!/usr/bin/env python3
"""
clerk_recordings scraper — El Paso County, TX (el_paso_tx).

Source: El Paso County Clerk Official Public Records
  https://apps.epcountytx.gov/publicrecords/OfficialPublicRecords

Portal protocol (see runs/el_paso_tx/build/clerk_recordings_portal_fingerprint.md):
  - ASP.NET form; doc type is the `Style` SELECT; date window is
    InstrumentDateFrom / InstrumentDateTo.
  - reCAPTCHA v3 (invisible) — passes for a real browser, no solver.
  - POST OfficialPublicRecordsSearch -> 302 -> OfficialPublicRecordsSearchResults.
  - Results paginate via ?page=N (20 rows/page; 500-record cap).
  - One table row per (document x party-name); grouped here by Document #.

Output: data/el_paso_tx/raw/clerk_recordings.jsonl  (MASTER_PROMPT §4.32 shape).
Scrapes only the focused PRIMARY_LEAD doc-type set for this session
(clerk_recordings_doc_type_classification.md).
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "data" / "el_paso_tx" / "raw" / "clerk_recordings.jsonl"
LOG = REPO / "data" / "el_paso_tx" / "raw" / "clerk_recordings.scrape.log"
FORM = "https://apps.epcountytx.gov/publicrecords/OfficialPublicRecords"
RESULTS = ("https://apps.epcountytx.gov/publicrecords/OfficialPublicRecords/"
           "OfficialPublicRecordsSearchResults")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

DATE_FROM = "01/01/2026"
DATE_TO = "05/17/2026"
PAGE_CAP = 25            # 500-record portal cap / 20 per page
INTER_DOCTYPE_DELAY = 15  # polite delay between doc-type searches

# (Style value, code, signal_type) — focused PRIMARY_LEAD set for this session.
SCRAPE_SET = [
    ("108", "LIP", "lis_pendens"),
    ("16",  "AOJ", "judgment_lien"),
    ("92",  "FTL", "federal_tax_lien"),
    ("166", "STL", "state_tax_lien"),
    ("117", "MEL", "mechanics_lien"),
    ("94",  "HOS", "hospital_lien"),
    ("28",  "ATL", "code_lien"),
    ("194", "AFH", "affidavit_of_heirship"),
    ("89",  "EXR", "executor_deed"),
    ("6",   "ADD", "administrator_deed"),
]

log_lines: list[str] = []


def log(msg: str) -> None:
    line = f"[{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}] {msg}"
    log_lines.append(line)
    print(line, file=sys.stderr, flush=True)


def parse_rows(page) -> list[dict]:
    """Parse the result table; return one dict per (document x name) row."""
    out = []
    for tr in page.locator("table tr").all():
        tds = tr.locator("td").all()
        if len(tds) < 10:
            continue
        c = [td.inner_text().strip() for td in tds]
        # Document#, PageCount, Date, Name, NameType, Book, Page, Type, Style, Subdivision, (Document)
        out.append({
            "instrument_number": c[0], "page_count": c[1], "date": c[2],
            "name": c[3], "name_type": c[4], "book": c[5], "page": c[6],
            "rec_type": c[7], "style": c[8], "subdivision": c[9],
        })
    return out


def scrape_doc_type(page, style_value: str, code: str, signal_type: str) -> list[dict]:
    """Search one doc type, page through all results, group by Document #."""
    page.goto(FORM, wait_until="domcontentloaded", timeout=45_000)
    page.wait_for_selector("select[name='Style']", timeout=15_000)
    page.wait_for_timeout(2500)  # let reCAPTCHA v3 init
    page.select_option("select[name='Style']", style_value)
    page.fill("input[name='InstrumentDateFrom']", DATE_FROM)
    page.fill("input[name='InstrumentDateTo']", DATE_TO)
    page.click("#submit")
    page.wait_for_load_state("domcontentloaded", timeout=30_000)
    page.wait_for_timeout(3500)

    import re
    body = page.inner_text("body")
    m = re.search(r"([\d,]+)\s+Records?\s+Found", body, re.I)
    found = int(m.group(1).replace(",", "")) if m else 0
    pages = min((found + 19) // 20, PAGE_CAP) if found else 0
    log(f"  {code}/{signal_type}: {found} records found -> {pages} pages")

    rows = parse_rows(page)
    for p in range(2, pages + 1):
        page.goto(f"{RESULTS}?page={p}", wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_timeout(900)
        rows.extend(parse_rows(page))

    # Group rows by instrument number into one record per document.
    by_doc: dict[str, dict] = {}
    for r in rows:
        inum = r["instrument_number"]
        if not inum:
            continue
        rec = by_doc.setdefault(inum, {
            "instrument_number": inum, "recording_date": r["date"],
            "doc_type_code": code, "doc_type_raw": r["style"],
            "signal_type": signal_type, "book": r["book"], "page": r["page"],
            "rec_type": r["rec_type"], "subdivision": r["subdivision"],
            "page_count": r["page_count"], "parties": [],
        })
        if r["name"]:
            rec["parties"].append({"name": r["name"], "name_type": r["name_type"]})
    log(f"  {code}: {len(rows)} rows -> {len(by_doc)} unique documents")
    return list(by_doc.values())


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    log(f"start clerk_recordings scrape window={DATE_FROM}..{DATE_TO} "
        f"doc_types={len(SCRAPE_SET)}")
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    all_records: list[dict] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=UA, viewport={"width": 1600, "height": 1000})
        page = ctx.new_page()
        for i, (style_value, code, signal_type) in enumerate(SCRAPE_SET):
            for attempt in (1, 2, 3):
                try:
                    docs = scrape_doc_type(page, style_value, code, signal_type)
                    break
                except Exception as exc:
                    log(f"  {code}: attempt {attempt} failed: {exc!r}")
                    docs = []
                    page.wait_for_timeout(4000)
            for d in docs:
                inum = d["instrument_number"]
                all_records.append({
                    "raw_record_id": f"elp_clk_{inum}",
                    "source_id": "clerk_recordings",
                    "source_url": f"{FORM}?doc={inum}",
                    "source_fetched_at": fetched_at,
                    "parser_confidence": 95,
                    "raw_payload": d,
                })
            if i < len(SCRAPE_SET) - 1:
                time.sleep(INTER_DOCTYPE_DELAY)
        browser.close()

    # Dedupe across doc types by raw_record_id (defensive).
    seen, deduped = set(), []
    for r in all_records:
        if r["raw_record_id"] not in seen:
            seen.add(r["raw_record_id"])
            deduped.append(r)

    with open(OUT, "w", encoding="utf-8") as fh:
        for r in deduped:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    log(f"wrote {len(deduped)} records -> {OUT.relative_to(REPO)}")

    # per-signal-type tally
    tally: dict[str, int] = {}
    for r in deduped:
        st = r["raw_payload"]["signal_type"]
        tally[st] = tally.get(st, 0) + 1
    log(f"signal_type tally: {tally}")
    log("done")
    with open(LOG, "w", encoding="utf-8") as fh:
        fh.write("\n".join(log_lines) + "\n")
    return 0 if deduped else 5


if __name__ == "__main__":
    raise SystemExit(main())
