#!/usr/bin/env python3
"""
foreclosure_notices scraper — El Paso County, TX (el_paso_tx).

Source: El Paso County Clerk "Foreclosures" search portal
  https://apps.epcountytx.gov/publicrecords/Foreclosures

Build-Mode notes (recorded during the el_paso_tx build):
  - The search form carries an invisible reCAPTCHA v3
    (api.js?render=<sitekey>). It is NOT a v2 checkbox challenge and
    passes for a real browser; a Playwright Chromium session clears it
    without a solver. Phase 0 recon (metadata-only) wrongly recorded
    "no CAPTCHA" — corrected here.
  - The form POSTs to /Foreclosures/ForeclosureSearch -> 302 ->
    GET /Foreclosures/ForeclosureSearchResults (a server-rendered
    results table).
  - The results table columns are: Instrument #, Subdivision, Lot,
    Block, Unit, Tract, Page Count, Sale Date, Document(link).
    There is NO street address in the table — the property is keyed by
    legal description. Street address / owner live inside the linked
    Notice-of-Sale document and/or come from EPCAD enrichment.

Output: data/el_paso_tx/raw/foreclosure_notices.jsonl
  Each line conforms to the MASTER_PROMPT.md §4.32 wrapped raw-record
  contract. raw_payload carries normalized, faithfully-captured fields.

This scraper does portal protocol + field normalization only. It does
NOT translate to signals — that is the translator's job (§4.32).
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "data" / "el_paso_tx" / "raw" / "foreclosure_notices.jsonl"
LOG = REPO / "data" / "el_paso_tx" / "raw" / "foreclosure_notices.scrape.log"
PORTAL = "https://apps.epcountytx.gov/publicrecords/Foreclosures"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

# Forward window: upcoming foreclosure sales from the build date onward.
SALE_DATE_FROM = "05/01/2026"
SALE_DATE_TO = "12/31/2026"


def _log(lines: list[str], msg: str) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"[{stamp}] {msg}"
    lines.append(line)
    print(line, file=sys.stderr)


def scrape() -> int:
    log: list[str] = []
    OUT.parent.mkdir(parents=True, exist_ok=True)
    _log(log, f"start url={PORTAL} window={SALE_DATE_FROM}..{SALE_DATE_TO}")

    rows_out: list[dict] = []
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=UA, viewport={"width": 1600, "height": 1000})
        page = ctx.new_page()
        page.goto(PORTAL, wait_until="domcontentloaded", timeout=45_000)
        page.wait_for_selector("input[name='SaleDateFrom']", timeout=15_000)
        page.wait_for_timeout(2500)  # let reCAPTCHA v3 init

        page.fill("input[name='SaleDateFrom']", SALE_DATE_FROM)
        page.fill("input[name='SaleDateTo']", SALE_DATE_TO)
        page.click("button:has-text('Submit'), input[type=submit]")
        page.wait_for_load_state("domcontentloaded", timeout=30_000)
        page.wait_for_timeout(4000)
        _log(log, f"submitted; results url={page.url}")

        # The results page renders a table. Extract every data row.
        # Header row carries <th>; data rows carry <td>.
        table_rows = page.locator("table tr").all()
        _log(log, f"table tr count={len(table_rows)}")

        for tr in table_rows:
            tds = tr.locator("td").all()
            if len(tds) < 8:
                continue  # header / spacer row
            cells = [td.inner_text().strip() for td in tds]
            # Column order: Instrument#, Subdivision, Lot, Block, Unit,
            # Tract, Page Count, Sale Date, Document(link)
            instrument = cells[0]
            subdivision = cells[1]
            lot, block, unit, tract = cells[2], cells[3], cells[4], cells[5]
            page_count = cells[6]
            sale_date = cells[7]
            # Document link href, if present in the last cell.
            doc_href = ""
            links = tr.locator("a").all()
            for a in links:
                href = a.get_attribute("href") or ""
                if href and "javascript" not in href.lower():
                    doc_href = href
                    break
            if doc_href and doc_href.startswith("/"):
                doc_href = "https://apps.epcountytx.gov" + doc_href

            # Normalize sale_date (mm/dd/yyyy) -> ISO + year/month ints.
            recording_year = recording_month = None
            sale_iso = ""
            try:
                d = datetime.strptime(sale_date, "%m/%d/%Y").date()
                sale_iso = d.isoformat()
                recording_year, recording_month = d.year, d.month
            except ValueError:
                pass

            # Compose a legal-description string. El Paso foreclosure rows
            # carry no street address; the legal description is the
            # property key until EPCAD enrichment attaches situs/owner.
            legal_parts = []
            if subdivision:
                legal_parts.append(subdivision)
            if lot:
                legal_parts.append(f"LOT {lot}")
            if block:
                legal_parts.append(f"BLK {block}")
            if unit:
                legal_parts.append(f"UNIT {unit}")
            if tract:
                legal_parts.append(f"TRACT {tract}")
            legal_description = " ".join(legal_parts).upper().strip()

            stable = hashlib.sha1(
                f"{instrument}|{subdivision}|{lot}|{block}|{unit}|{tract}|{sale_date}"
                .encode("utf-8")
            ).hexdigest()[:16]

            rows_out.append({
                "raw_record_id": f"elp_fcl_{stable}",
                "source_id": "foreclosure_notices",
                "source_url": doc_href or f"{PORTAL}#{stable}",
                "source_fetched_at": fetched_at,
                "parser_confidence": 90,  # legal-desc only; no street address
                "raw_payload": {
                    "instrument_number": instrument,
                    "doc_number": instrument,
                    "subdivision": subdivision,
                    "lot": lot,
                    "block": block,
                    "unit": unit,
                    "tract": tract,
                    "legal_description": legal_description,
                    "page_count": page_count,
                    "sale_date": sale_iso or sale_date,
                    "recording_year": recording_year,
                    "recording_month": recording_month,
                    "document_url": doc_href,
                },
            })

        browser.close()

    with open(OUT, "w", encoding="utf-8") as fh:
        for rec in rows_out:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    _log(log, f"parsed={len(rows_out)} wrote {OUT.relative_to(REPO)}")
    conf = (sum(1 for r in rows_out if r['raw_payload']['recording_year'])
            / len(rows_out)) if rows_out else 0.0
    _log(log, f"parser_confidence(date-parse rate)={conf:.3f}")
    _log(log, "done")
    with open(LOG, "w", encoding="utf-8") as fh:
        fh.write("\n".join(log) + "\n")
    return 0 if rows_out else 5


if __name__ == "__main__":
    raise SystemExit(scrape())
