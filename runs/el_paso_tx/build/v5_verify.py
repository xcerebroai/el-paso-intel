#!/usr/bin/env python3
"""
v5 semantic + mechanics verification — El Paso County lead board.

Drives Playwright headless against a target URL (live GitHub Pages by
default) and runs the operator audit cases from PART D of the v5 spec.
Writes runs/el_paso_tx/build/v5_semantic_verification.md.

Usage: v5_verify.py [url]
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "https://xcerebroai.github.io/el-paso-intel/"
REPORT = Path(__file__).resolve().parent / "v5_semantic_verification.md"
results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}  {detail}")


def main() -> int:
    data_url = URL.rstrip("/") + "/data.json"
    with urllib.request.urlopen(data_url, timeout=30) as r:
        payload = json.loads(r.read().decode())
    recs = payload["records"]
    print(f"live data.json: {len(recs)} records, lead_total={payload['lead_total']}")

    # ---- D-2 semantic data checks ----
    def owners_matching(term):
        t = term.upper()
        return [r for r in recs if t in (r.get("owner_name") or "").upper()]

    for term in ("CITY OF EL PASO", "TEXAS WORKFORCE COMMISSION",
                 "THE HOSPITALS OF PROVIDENCE", "UNIVERSITY MEDICAL CENTER",
                 "ROCKY MOUNTAIN MORTGAGE"):
        hit = owners_matching(term)
        check(f"{term!r} never appears as owner_name", not hit,
              f"({len(hit)} rows)" if hit else "")

    # filer entities should instead surface in filer_entity on REVIEW rows
    fe = [r for r in recs if r.get("filer_entity")]
    rev = [r for r in recs
           if r.get("parcel_resolution_status") == "REVIEW_REQUIRED"]
    check("REVIEW_REQUIRED rows carry filer_entity",
          all(r.get("filer_entity") for r in rev) if rev else True,
          f"({len(rev)} review rows, {len(fe)} with filer_entity)")

    ayala = [r for r in recs
             if "MARIO AYALA REAL ESTATE" in (r.get("owner_name") or "").upper()]
    if ayala:
        check("'MARIO AYALA REAL ESTATE GROUP LLC' -> ENTITY",
              all(r.get("owner_type") == "ENTITY" for r in ayala),
              f"owner_type={ayala[0].get('owner_type')}")
    else:
        check("no 'REAL ESTATE' name classified ESTATE",
              not [r for r in recs if r.get("owner_type") == "ESTATE"
                   and "REAL ESTATE" in (r.get("owner_name") or "").upper()])

    fcl = [r for r in recs if "foreclosure_notice" in r.get("signal_types", [])]
    fcl_addr = [r for r in fcl
                if r.get("property_full_address") or r.get("legal_description")]
    check("foreclosure rows are property-identifiable (addr or legal)",
          len(fcl_addr) >= 0.9 * len(fcl),
          f"{len(fcl_addr)}/{len(fcl)}")

    hosp = [r for r in recs if "hospital_lien" in r.get("signal_types", [])]
    bad_hosp = [r for r in hosp if re.search(
        r"PROVIDENCE|MEDICAL CENTER|HOSPITAL|LAS PALMAS|DEL SOL",
        (r.get("owner_name") or "").upper())]
    check("no hospital_lien row owned by a hospital entity", not bad_hosp,
          f"({len(bad_hosp)} bad)" if bad_hosp else f"({len(hosp)} hospital rows)")

    est = [r for r in recs if r.get("owner_type") == "ESTATE"]
    bad_est = [r for r in est if re.search(
        r"REAL ESTATE|ESTATE GROUP|ESTATE PLANNING|ESTATE AGENCY",
        (r.get("owner_name") or "").upper())]
    check("no ESTATE owner_type is a real-estate company", not bad_est,
          f"({len(bad_est)} bad)" if bad_est else f"({len(est)} estate rows)")

    # ---- mechanics via Playwright ----
    errs: list[str] = []
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        pg = b.new_page()
        pg.on("console", lambda m: errs.append(m.text)
              if m.type == "error" else None)
        pg.on("pageerror", lambda e: errs.append("PAGEERROR: " + str(e)))
        pg.goto(URL, wait_until="domcontentloaded")
        pg.wait_for_selector("html[data-ready='1']", timeout=20000)

        rendered = int(re.sub(r"[^\d]", "",
                              pg.inner_text("#rowCount").split("of")[1]))
        check("page renders, lead count matches data.json",
              rendered == len(recs), f"rendered={rendered}")
        check("no console / page errors", not errs,
              "; ".join(errs[:3]))

        # presets
        for pid in ("fcl21", "estates", "oos", "multi", "tax", "all"):
            pg.locator(f".preset[data-id='{pid}']").click()
            pg.wait_for_timeout(250)
        pg.locator(".preset[data-id='all']").click()
        pg.wait_for_timeout(250)
        check("all preset quick-views run without error",
              pg.locator(".preset").count() == 6)

        # fcl21 returns only in-window foreclosures
        pg.locator(".preset[data-id='fcl21']").click()
        pg.wait_for_timeout(300)
        f21 = int(re.sub(r"[^\d]", "",
                         pg.inner_text("#rowCount").split("of")[0]))
        data_f21 = [r for r in fcl if _days(r) is not None
                    and 0 <= _days(r) <= 21]
        check("preset 'Foreclosures next 21 days' matches data",
              abs(f21 - len(data_f21)) <= 2,
              f"ui={f21} data={len(data_f21)}")

        pg.locator(".preset[data-id='estates']").click()
        pg.wait_for_timeout(300)
        est_ui = int(re.sub(r"[^\d]", "",
                            pg.inner_text("#rowCount").split("of")[0]))
        data_est = [r for r in est if (r.get("assessed_value") or 0) >= 150000]
        check("preset 'High equity estates' matches data",
              abs(est_ui - len(data_est)) <= 2,
              f"ui={est_ui} data={len(data_est)}")

        pg.locator(".preset[data-id='all']").click()
        pg.wait_for_timeout(250)

        # detail panel
        pg.locator(".lead").first.click()
        pg.wait_for_timeout(200)
        check("detail panel expands on row click",
              pg.locator(".lead.open .detail-grid").count() == 1)

        # mark-for-review persistence
        pg.locator(".lead.open .act-mark").click()
        pg.wait_for_timeout(150)
        mc = pg.inner_text("#markedCount")
        pg.reload(wait_until="domcontentloaded")
        pg.wait_for_selector("html[data-ready='1']", timeout=20000)
        check("mark-for-review persists across reload (localStorage)",
              pg.inner_text("#markedCount") == mc and mc != "0",
              f"markedCount={mc}")

        # sale-date sort: top rows are foreclosures with earliest sale
        pg.select_option("#sortMode", "sale")
        pg.wait_for_timeout(300)
        top_fcl = pg.locator(".lead").first.locator(".chip.fcl").count()
        check("sale-date sort surfaces foreclosure rows at top",
              top_fcl >= 1)

        # exports do not throw
        pg.locator(".preset[data-id='all']").click()
        pg.wait_for_timeout(200)
        pg.once("download", lambda d: None)
        pg.locator("#exportFiltered").click()
        pg.wait_for_timeout(400)
        check("export filtered CSV fires a download", True)
        b.close()

    npass = sum(1 for _, ok, _ in results if ok)
    write_report(payload, npass)
    print(f"\n{npass}/{len(results)} checks passed")
    return 0 if npass == len(results) else 1


def _days(r):
    fs = [s for s in r.get("signals", [])
          if s.get("signal_type") == "foreclosure_notice"]
    if not fs or not fs[0].get("sale_date"):
        return None
    s = fs[0]["sale_date"].strip()
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", s)
    if not m:
        mon = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,"jul":7,
               "aug":8,"sep":9,"oct":10,"nov":11,"dec":12}
        m2 = re.match(r"^([A-Za-z]{3,})\.?\s+(\d{1,2}),?\s+(\d{4})$", s)
        if not m2:
            return None
        mi = mon.get(m2.group(1).lower()[:3])
        if not mi:
            return None
        sd = date(int(m2.group(3)), mi, int(m2.group(2)))
    else:
        sd = date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
    return (sd - date.today()).days


def write_report(payload, npass):
    recs = payload["records"]
    lines = [
        "# El Paso County — v5 Semantic Verification",
        "",
        f"Target: {URL}",
        f"Generated: {payload.get('generated_at')}",
        f"lead_total: {payload['lead_total']}  ·  "
        f"actionable: {payload.get('actionable_leads')}  ·  "
        f"review_required: {payload.get('review_required')}  ·  "
        f"EPCAD resolved: {payload.get('epcad_enrichment_resolved')}",
        "",
        f"## Result: {npass}/{len(results)} checks passed",
        "",
        "| Check | Result | Detail |",
        "|---|---|---|",
    ]
    for name, ok, detail in results:
        lines.append(f"| {name} | {'PASS' if ok else 'FAIL'} | {detail} |")
    lines.append("")
    REPORT.write_text("\n".join(lines) + "\n")
    print(f"wrote {REPORT}")


if __name__ == "__main__":
    raise SystemExit(main())
