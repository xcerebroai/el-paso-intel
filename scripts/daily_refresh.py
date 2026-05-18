#!/usr/bin/env python3
"""
daily_refresh.py — El Paso County (el_paso_tx) refresh orchestration.

Runs the active source scrapers, the translator + EPCAD enrichment
pipeline, and regenerates the dashboard payloads. Invoked daily by
.github/workflows/daily-refresh.yml and runnable locally.

Modular by design: each source is a pair of callables registered in
SOURCES. Adding a source later (tax_collector, court_probate,
court_civil, foreclosure_notices) is a one-line change here once that
source's scraper + pipeline exist.

Current scope: clerk_recordings only (other 3 sources deferred).

On any scraper/pipeline failure this script raises (subprocess
check=True) so the CI job fails WITHOUT committing a partial refresh.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PY = sys.executable
LEADS = REPO / "data" / "el_paso_tx" / "leads.json"
DASH = REPO / "dashboard"


def _run(script_relpath: str) -> None:
    """Run a repo script with the current interpreter; raise on failure."""
    script = REPO / script_relpath
    print(f"[daily_refresh] running {script_relpath}", flush=True)
    subprocess.run([PY, str(script)], check=True, cwd=str(REPO))


# ---- per-source steps -------------------------------------------------

def run_clerk_recordings_scraper() -> None:
    """Scrape El Paso County Clerk Official Public Records -> raw jsonl."""
    _run("scrapers/clerk_recordings.py")


def run_clerk_recordings_pipeline() -> None:
    """Translator + per-row EPCAD enrichment + matched_lead aggregation
    for clerk_recordings -> data/el_paso_tx/leads.json."""
    _run("runs/el_paso_tx/build/build_clerk_pipeline.py")


def run_foreclosure_notices_scraper() -> None:
    """Scrape the County Clerk Foreclosures portal -> notice PDFs."""
    _run("scripts/scrapers/foreclosure_notices.py")


def run_foreclosure_notices_ocr() -> None:
    """OCR the notice PDFs + field extraction -> extracted.jsonl."""
    _run("scripts/translators/foreclosure_notices_ocr.py")


def run_foreclosure_notices_translate() -> None:
    """EPCAD address-join + matched_lead build for foreclosure_notices."""
    _run("scripts/translators/foreclosure_notices_translate.py")


# Source registry. Each entry: source_id -> ordered list of callables.
# clerk_recordings runs first (it writes the clerk-only leads.json that
# the aggregator then merges every other source into).
SOURCES = {
    "clerk_recordings": [run_clerk_recordings_scraper,
                         run_clerk_recordings_pipeline],
    "foreclosure_notices": [run_foreclosure_notices_scraper,
                            run_foreclosure_notices_ocr,
                            run_foreclosure_notices_translate],
    # "tax_collector":   [...],   # deferred
    # "court_probate":   [...],   # deferred
    # "court_civil":     [...],   # deferred
}


def regenerate_dashboard_data() -> None:
    """Regenerate dashboard/data.json and dashboard/data.js from leads.json.
    (Multi-source aggregation will replace this step's input once more
    sources are registered; for one source leads.json IS the aggregate.)"""
    if not LEADS.exists():
        raise SystemExit("leads.json missing — pipeline did not produce output")
    payload = json.loads(LEADS.read_text())
    shutil.copy(LEADS, DASH / "data.json")
    (DASH / "data.js").write_text(
        "window.LEADS = " + json.dumps(payload, ensure_ascii=False) + ";\n")
    print(f"[daily_refresh] dashboard data regenerated "
          f"(lead_total={payload.get('lead_total')})", flush=True)


def main() -> int:
    print(f"[daily_refresh] start — sources: {list(SOURCES)}", flush=True)
    # clerk_recordings must run first — build_clerk_pipeline.py writes the
    # clerk-only leads.json that scripts/aggregate_leads.py then merges
    # every other source into.
    for source_id, steps in SOURCES.items():
        print(f"[daily_refresh] === {source_id} ===", flush=True)
        for step in steps:
            step()
    # multi-source merge -> leads.json + dashboard/data.json + data.js
    _run("scripts/aggregate_leads.py")
    print("[daily_refresh] complete", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
