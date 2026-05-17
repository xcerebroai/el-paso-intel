#!/usr/bin/env python3
"""Step 1 portal-fingerprint probe for clerk_recordings (El Paso OPR)."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

BUILD = Path(__file__).resolve().parent
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
URL = "https://apps.epcountytx.gov/publicrecords/OfficialPublicRecords"

posts = []
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(user_agent=UA)
    pg = ctx.new_page()
    pg.on("response", lambda r: posts.append((r.status, r.request.method, r.url))
          if (r.request.method == "POST" or "Search" in r.url) and "epcountytx" in r.url
          else None)
    pg.goto(URL, wait_until="domcontentloaded", timeout=45_000)
    pg.wait_for_timeout(2500)

    fields = pg.eval_on_selector_all(
        "input,select,textarea",
        "els=>els.map(e=>({tag:e.tagName,name:e.name||'',id:e.id||'',type:e.type||''}))")
    # doc-type catalog
    catalog = []
    doc_select_name = None
    for s in pg.locator("select").all():
        nm = s.get_attribute("name") or s.get_attribute("id") or ""
        opts = [{"value": o.get_attribute("value"),
                 "text": o.inner_text().strip()} for o in s.locator("option").all()]
        if len(opts) > 20:  # the doc-type select is the big one
            doc_select_name = nm
            catalog = opts
    (BUILD / "clerk_recordings_doc_type_catalog.json").write_text(
        json.dumps({"select_name": doc_select_name,
                    "option_count": len(catalog),
                    "options": catalog}, indent=2))

    # sample search: Abstract of Judgment (value 16), recent date window
    result = {"attempted": False}
    try:
        # fill a doc type + date range if those fields exist
        names = {f["name"] for f in fields if f["name"]}
        if doc_select_name and catalog:
            pg.select_option(f"select[name='{doc_select_name}']", "16")
        for fn in ("FileDateFrom", "FiledDateFrom", "RecordDateFrom", "DateFrom"):
            if fn in names:
                pg.fill(f"input[name='{fn}']", "04/01/2026")
                result["date_from_field"] = fn
        for fn in ("FileDateTo", "FiledDateTo", "RecordDateTo", "DateTo"):
            if fn in names:
                pg.fill(f"input[name='{fn}']", "05/17/2026")
                result["date_to_field"] = fn
        pg.click("button:has-text('Submit'), input[type=submit]")
        pg.wait_for_load_state("domcontentloaded", timeout=30_000)
        pg.wait_for_timeout(5000)
        result["attempted"] = True
        result["url_after"] = pg.url
        result["body_head"] = pg.inner_text("body")[:400].replace("\n", " ")
        th = pg.eval_on_selector_all("table th", "e=>e.map(x=>x.innerText.trim())")
        result["table_headers"] = th
        result["table_row_count"] = pg.locator("table tr").count()
        # pagination hints
        result["pagination_text"] = " | ".join(
            pg.eval_on_selector_all(
                "a,span,li",
                "e=>e.map(x=>x.innerText.trim()).filter(t=>/page|next|of \\d|\\d+ records|results/i.test(t)).slice(0,12)"))
        # first data row sample
        rows = pg.locator("table tr").all()
        for tr in rows:
            tds = tr.locator("td").all()
            if len(tds) >= 4:
                result["first_data_row"] = [td.inner_text().strip() for td in tds]
                links = [a.get_attribute("href") for a in tr.locator("a").all()]
                result["first_row_links"] = links
                break
    except Exception as e:
        result["error"] = repr(e)
    b.close()

print("=== FORM FIELDS ===")
for f in fields:
    print(" ", f)
print(f"\n=== DOC-TYPE SELECT: name={doc_select_name!r}  options={len(catalog)} ===")
print("(full catalog -> clerk_recordings_doc_type_catalog.json)")
print("\n=== SAMPLE SEARCH ===")
print(json.dumps(result, indent=1))
print("\n=== POST/Search responses ===")
for s, m, u in posts[:15]:
    print(f"  {s} {m} {u}")
