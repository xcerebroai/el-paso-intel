#!/usr/bin/env python3
"""
Multi-source lead aggregator — El Paso County (el_paso_tx).

Merges every source's matched_lead output into one dashboard payload.
Idempotent: it reads the clerk_recordings base (leads.json as written by
build_clerk_pipeline.py — clerk-only) plus each additional source's
translated matched_lead file, and rewrites leads.json + the dashboard
data files. In the daily refresh, build_clerk_pipeline.py runs first
(writing the clerk-only leads.json), then this aggregator merges the rest.

One matched_lead per parcel. Signals from different sources STACK on the
same parcel. Identical (parcel_id, signal_type) signals are de-duplicated
into one entry with a count (Fix 2). Every row keeps a primary §13.2
clerk/court/foreclosure signal (§13.5.1).

Reads : data/el_paso_tx/leads.json                              (clerk base)
        data/el_paso_tx/translated/foreclosure_notices_translated.jsonl
Writes: data/el_paso_tx/leads.json   dashboard/data.json   dashboard/data.js
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LEADS = REPO / "data" / "el_paso_tx" / "leads.json"
# Idempotency (Fix 3, v5): the clerk base is read from a STABLE file that
# only build_clerk_pipeline.py writes — never from leads.json, which this
# aggregator overwrites. Re-running aggregate_leads.py therefore always
# merges foreclosure_notices onto the same clerk base exactly once.
CLERK_BASE = REPO / "data" / "el_paso_tx" / "clerk_leads_base.json"
DASH = REPO / "dashboard"
ADDITIONAL = {
    "foreclosure_notices":
        REPO / "data/el_paso_tx/translated/foreclosure_notices_translated.jsonl",
}
SIGNAL_PRIORITY = {
    "foreclosure_notice": 95, "lis_pendens": 90, "federal_tax_lien": 85,
    "state_tax_lien": 84, "judgment_lien": 80, "mechanics_lien": 70,
    "hospital_lien": 65, "code_lien": 60, "affidavit_of_heirship": 55,
    "administrator_deed": 52, "executor_deed": 50,
    "estate_titled_property": 40, "trust_titled_property": 30,
}


def dedup_signals(signals: list[dict]) -> list[dict]:
    """Collapse identical signal_type entries into one with a count
    (Fix 2 / Fix 3). Sums counts and unions source_urls / evidence_ids /
    instrument_numbers — so one parcel with N recordings of one distress
    type renders ONE chip carrying N distinct instrument numbers, and the
    cross-source merge never re-counts a signal already deduped per-source."""
    by: dict[str, dict] = {}
    for s in signals:
        st = s["signal_type"]
        m = by.get(st)
        if m is None:
            m = dict(s)
            m.setdefault("count", 1)
            m["source_urls"] = list(s.get("source_urls") or
                                    ([s["source_url"]] if s.get("source_url") else []))
            m["evidence_ids"] = list(s.get("evidence_ids") or
                                     ([s["evidence_id"]] if s.get("evidence_id") else []))
            m["instrument_numbers"] = list(s.get("instrument_numbers") or
                ([s["instrument_number"]] if s.get("instrument_number") else []))
            by[st] = m
        else:
            m["count"] = m.get("count", 1) + s.get("count", 1)
            for u in (s.get("source_urls") or []):
                if u not in m["source_urls"]:
                    m["source_urls"].append(u)
            for ev in (s.get("evidence_ids") or []):
                if ev not in m["evidence_ids"]:
                    m["evidence_ids"].append(ev)
            for ino in (s.get("instrument_numbers") or
                        ([s["instrument_number"]] if s.get("instrument_number") else [])):
                if ino not in m["instrument_numbers"]:
                    m["instrument_numbers"].append(ino)
            if (s.get("recorded_date") or "") > (m.get("recorded_date") or ""):
                m["recorded_date"] = s.get("recorded_date")
    return list(by.values())


def finalize(lead: dict) -> None:
    lead["signals"] = dedup_signals(lead["signals"])
    lead["signal_types"] = [s["signal_type"] for s in lead["signals"]]
    lead["signal_count"] = len(lead["signals"])
    prim = [s for s in lead["signals"]
            if s["source_id"] != "epcad_enrichment_derived"]
    prim.sort(key=lambda s: SIGNAL_PRIORITY.get(s["signal_type"], 0), reverse=True)
    lead["primary_signal"] = prim[0]["signal_type"] if prim else None
    dates = [s.get("sale_date") or s.get("recorded_date") or ""
             for s in lead["signals"]]
    lead["latest_event_date"] = max([d for d in dates if d], default="")
    su = []
    for s in lead["signals"]:
        for u in (s.get("source_urls") or []):
            if u and u not in su:
                su.append(u)
    lead["source_urls"] = su


def main() -> int:
    base_path = CLERK_BASE if CLERK_BASE.exists() else LEADS
    base = json.loads(base_path.read_text())
    print(f"clerk base: {base_path.name} ({len(base.get('records', []))} records)")
    records = base.get("records", [])
    by_parcel = {r["parcel_id"]: r for r in records
                 if r.get("parcel_resolution_status") == "RESOLVED"
                 and r.get("parcel_id")}
    sources_active = list(base.get("sources_active") or ["clerk_recordings"])
    added_new = stacked = 0

    for source_id, path in ADDITIONAL.items():
        if not path.exists():
            print(f"  (skip {source_id}: {path.name} not present)")
            continue
        sources_active.append(source_id) if source_id not in sources_active else None
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            lead = json.loads(line)
            pid = lead.get("parcel_id")
            host = by_parcel.get(pid) if (
                lead.get("parcel_resolution_status") == "RESOLVED" and pid) else None
            if host is not None:
                host["signals"].extend(lead["signals"])
                stacked += 1
            else:
                records.append(lead)
                if lead.get("parcel_resolution_status") == "RESOLVED" and pid:
                    by_parcel[pid] = lead
                added_new += 1

    for r in records:
        finalize(r)
    # §13.5.1 — drop any row with no primary (non-enrichment) signal
    kept = [r for r in records if r.get("primary_signal")]
    dropped = len(records) - len(kept)

    resolved = sum(1 for r in kept
                   if r.get("parcel_resolution_status") == "RESOLVED")
    review = sum(1 for r in kept
                 if r.get("parcel_resolution_status") == "REVIEW_REQUIRED")
    # ACTIONABLE: the operator has a concrete next move on the lead — a
    # property to inspect (situs address / legal description), a dated
    # foreclosure sale, or a named distressed party to skip-trace. The
    # only non-actionable bucket is REVIEW_REQUIRED (filer-vs-debtor: the
    # harness could not name a debtor, so the operator must resolve that
    # first). A clerk lead with owner + signal + source but no parcel is
    # still actionable — skip-trace research per Fix 4F.
    def _actionable(r):
        if r.get("parcel_resolution_status") == "REVIEW_REQUIRED":
            return False
        if "unidentified party" in (r.get("owner_name") or "").lower():
            return False
        has_party = bool((r.get("owner_name") or "").strip())
        has_prop = bool(r.get("property_full_address")
                        or r.get("legal_description"))
        has_sale = any(s.get("sale_date") for s in r.get("signals", []))
        return has_party or has_prop or has_sale
    actionable = sum(1 for r in kept if _actionable(r))
    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "county": "El Paso", "state": "TX",
        "build_label": "SOURCE_LIMITED",
        "build_label_reason": (
            "Multi-source build: " + " + ".join(sources_active) +
            ". court_probate, court_civil and tax_collector are deferred."),
        "sources_active": sources_active,
        "lead_total": len(kept),
        "epcad_enrichment_resolved": resolved,
        "epcad_enrichment_unresolved": len(kept) - resolved - review,
        "review_required": review,
        "actionable_leads": actionable,
        "records": kept,
    }
    LEADS.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    (DASH / "data.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    (DASH / "data.js").write_text(
        "window.LEADS = " + json.dumps(payload, ensure_ascii=False) + ";\n")

    from collections import Counter
    st = Counter()
    for r in kept:
        for t in r["signal_types"]:
            st[t] += 1
    stack = Counter(r["signal_count"] for r in kept)
    print(f"=== multi-source aggregation ===")
    print(f"sources_active:     {sources_active}")
    print(f"lead_total:         {len(kept)}  (stacked onto existing: {stacked}, "
          f"new: {added_new}, dropped no-primary: {dropped})")
    print(f"EPCAD resolved:     {resolved}")
    print(f"REVIEW_REQUIRED:    {review}  (filer-vs-debtor unresolved)")
    print(f"ACTIONABLE leads:   {actionable} / {len(kept)} "
          f"({100*actionable//max(len(kept),1)}%)")
    print(f"signal_type dist:   {dict(st.most_common())}")
    print(f"stacking dist:      {dict(sorted(stack.items()))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
