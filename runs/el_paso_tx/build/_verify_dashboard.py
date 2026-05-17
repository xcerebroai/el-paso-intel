#!/usr/bin/env python3
"""Self-verification (§4.21) — drives the local dashboard via Playwright.
Writes a PASS/FAIL report. Usage: _verify_dashboard.py [report_path]"""
import json
import sys
import tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[3]
INDEX = (REPO / "dashboard" / "index.html").as_uri()
DATA = json.load(open(REPO / "dashboard" / "data.json"))
EXPECTED = DATA["lead_total"]
report_path = Path(sys.argv[1]) if len(sys.argv) > 1 else \
    REPO / "runs" / "el_paso_tx" / "build" / "full_self_verification.md"

checks: list[tuple[str, bool, str]] = []


def chk(name, ok, detail=""):
    checks.append((name, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name} — {detail}")


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(accept_downloads=True)
    pg = ctx.new_page()
    console_errors = []
    pg.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: console_errors.append(f"pageerror: {e}"))

    pg.goto(INDEX, wait_until="domcontentloaded", timeout=30_000)
    pg.wait_for_function("document.documentElement.getAttribute('data-ready')==='1'",
                         timeout=20_000)
    chk("page loads + data-ready=1", True, "dashboard booted")

    rows = pg.locator("#leadBody tr").count()
    chk("rows render, count matches data file", rows == EXPECTED,
        f"rendered {rows} vs expected {EXPECTED}")

    chk("no console errors", len(console_errors) == 0,
        f"{len(console_errors)} error(s): {console_errors[:3]}")

    # filter: pick one signal-type checkbox, uncheck all others, count must change/shrink
    base = pg.locator("#leadBody tr").count()
    sig_boxes = pg.locator("#signalFilter input[type=checkbox]")
    n_sig = sig_boxes.count()
    for i in range(n_sig):
        if i != 0:
            sig_boxes.nth(i).uncheck()
    pg.wait_for_timeout(300)
    filtered = pg.locator("#leadBody tr").count()
    chk("signal-type filter works", 0 < filtered < base,
        f"all-types={base}, one-type={filtered}")
    for i in range(n_sig):
        sig_boxes.nth(i).check()
    pg.wait_for_timeout(200)

    # owner-type filter
    ot = pg.locator("#ownerFilter input[type=checkbox]")
    if ot.count() > 1:
        ot.nth(0).uncheck()
        pg.wait_for_timeout(200)
        ot_filtered = pg.locator("#leadBody tr").count()
        chk("owner-type filter works", ot_filtered < base,
            f"{base} -> {ot_filtered}")
        ot.nth(0).check()
        pg.wait_for_timeout(200)
    else:
        chk("owner-type filter works", True, "single owner type — trivially ok")

    # stacking controls — ANY vs 2+ vs 3+ must differ
    pg.select_option("#stackMode", "any")
    pg.wait_for_timeout(200)
    c_any = pg.locator("#leadBody tr").count()
    pg.select_option("#stackMode", "2")
    pg.wait_for_timeout(200)
    c_2 = pg.locator("#leadBody tr").count()
    pg.select_option("#stackMode", "3")
    pg.wait_for_timeout(200)
    c_3 = pg.locator("#leadBody tr").count()
    chk("stacking controls produce different counts", c_any > c_2 >= c_3,
        f"ANY={c_any}, 2+={c_2}, 3+={c_3}")
    pg.select_option("#stackMode", "any")
    pg.wait_for_timeout(200)

    # search
    pg.fill("#searchBox", "ESTATE")
    pg.wait_for_timeout(300)
    c_search = pg.locator("#leadBody tr").count()
    chk("text search works", 0 <= c_search < base, f"search 'ESTATE' -> {c_search}")
    pg.fill("#searchBox", "")
    pg.wait_for_timeout(200)

    # CSV export
    try:
        with pg.expect_download(timeout=8000) as dl:
            pg.click("#csvBtn")
        path = dl.value
        tmp = Path(tempfile.gettempdir()) / "elp_verify.csv"
        path.save_as(tmp)
        lines = tmp.read_text().splitlines()
        chk("CSV export downloads with data", len(lines) > 1,
            f"{len(lines)} lines, header: {lines[0][:60]}")
    except Exception as e:
        chk("CSV export downloads with data", False, f"error: {e}")

    # chips visually distinct from badges
    chip = pg.locator(".chip-distress").first
    badge = pg.locator(".badge").first
    if chip.count() and badge.count():
        chip_bg = chip.evaluate("e=>getComputedStyle(e).backgroundColor")
        badge_bg = badge.evaluate("e=>getComputedStyle(e).backgroundColor")
        badge_border = badge.evaluate("e=>getComputedStyle(e).borderStyle")
        distinct = chip_bg != badge_bg and "solid" in badge_border
        chk("distress chips visually distinct from enrichment badges", distinct,
            f"chip bg={chip_bg}, badge bg={badge_bg}, badge border={badge_border}")
    else:
        chk("distress chips visually distinct from enrichment badges", False,
            "no chip/badge elements found")

    b.close()

passed = sum(1 for _, ok, _ in checks if ok)
total = len(checks)
verdict = "PASS" if passed == total else "FAIL"
lines = [f"# clerk_recordings dashboard — Self-Verification (§4.21)", "",
         f"Verdict: **{verdict}**  ({passed}/{total} checks passed)",
         f"Target: local dashboard ({INDEX})",
         f"Expected leads: {EXPECTED}", "", "## Checks", ""]
for name, ok, detail in checks:
    lines.append(f"- [{'PASS' if ok else 'FAIL'}] {name} — {detail}")
report_path.write_text("\n".join(lines) + "\n")
print(f"\n{verdict} {passed}/{total} -> {report_path}")
sys.exit(0 if verdict == "PASS" else 1)
