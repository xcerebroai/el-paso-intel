#!/usr/bin/env python3
"""
clerk_recordings pipeline — translator + EPCAD enrichment + matched_lead
aggregation for El Paso County (el_paso_tx). Steps 4 and 5 of the
single-source clerk_recordings build.

Reads : data/el_paso_tx/raw/clerk_recordings.jsonl  (scraper output, §4.32 shape)
Writes: data/el_paso_tx/translated/clerk_recordings_translated.jsonl
        data/el_paso_tx/leads.json   (matched_lead records, dashboard payload)

Lead-origination contract (§13):
  - Every signal here is from clerk_recordings, a PRIMARY_LEAD_SOURCE.
  - EPCAD parcel data is §13.3 ENRICHMENT — it attaches, never originates.
  - estate_titled_property / trust_titled_property are STACKED signals on a
    row already originated by a clerk distress event; they never create a row.
"""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[3]
RAW = REPO / "data" / "el_paso_tx" / "raw" / "clerk_recordings.jsonl"
TRANSLATED = REPO / "data" / "el_paso_tx" / "translated" / "clerk_recordings_translated.jsonl"
LEADS = REPO / "data" / "el_paso_tx" / "leads.json"
EPCAD = "https://epcadpropertysearch.azurewebsites.net/Api/Properties/GetProperties"

# operator-readable label per signal_type
SIGNAL_LABELS = {
    "lis_pendens": "Lis Pendens", "judgment_lien": "Judgment Lien",
    "federal_tax_lien": "Federal Tax Lien", "state_tax_lien": "State Tax Lien",
    "mechanics_lien": "Mechanics Lien", "hospital_lien": "Hospital Lien",
    "code_lien": "Code / Administrative Lien",
    "affidavit_of_heirship": "Affidavit of Heirship",
    "executor_deed": "Executor's Deed", "administrator_deed": "Administrator's Deed",
    "estate_titled_property": "Estate-Titled Property",
    "trust_titled_property": "Trust-Titled Property",
}
# priority for choosing a row's primary signal (higher = stronger distress)
SIGNAL_PRIORITY = {
    "lis_pendens": 90, "federal_tax_lien": 85, "state_tax_lien": 84,
    "judgment_lien": 80, "mechanics_lien": 70, "hospital_lien": 65,
    "code_lien": 60, "affidavit_of_heirship": 55, "administrator_deed": 52,
    "executor_deed": 50, "estate_titled_property": 40, "trust_titled_property": 30,
}

# Fix 1 (v2): doc-type-aware debtor-party selection. The debtor / distressed
# party sits on a DIFFERENT name_type per document type — there is no single
# universal rule (see runs/el_paso_tx/build/data_quality_audit.md). Each value
# is an ordered preference list of name_type words; the first party whose
# name_type contains one of them (case-insensitive) is the debtor.
DEBTOR_PARTY_RULES = {
    "lis_pendens":           ["DEFENDANT"],
    "judgment_lien":         ["DEFENDANT"],
    "federal_tax_lien":      ["TAX PAYER", "GRANTEE"],
    "state_tax_lien":        ["TAX PAYER", "GRANTEE"],
    "hospital_lien":         ["GRANTEE"],   # patient debtor, NOT the hospital filer
    "code_lien":             ["GRANTEE"],   # property/business debtor, NOT the govt filer
    "mechanics_lien":        ["GRANTOR"],   # property owner, NOT the contractor filer
    "construction_lien":     ["GRANTOR"],
    "affidavit_of_heirship": ["GRANTOR"],
    "executor_deed":         ["GRANTOR"],
    "administrator_deed":    ["GRANTOR"],
    "probate_recording":     ["GRANTOR"],
}

# EPCAD match-quality guard (Fix 1 / Finding 4): the EPCAD ownerName search is
# a partial match, so it can return a parcel owned by an unrelated party that
# merely shares a common word (e.g. "EL PASO LTACH PARTNERS LP" -> a "CITY OF
# EL PASO" parcel). Tokens below are dropped before scoring name overlap.
_MATCH_STOPWORDS = {"LP", "LLC", "INC", "CORP", "CORPORATION", "LTD", "LLP",
    "CO", "THE", "OF", "AND", "COMPANY", "TR", "ET", "AL", "L.L.C", "L.P"}


def _tokens(name: str) -> set:
    """Significant uppercase tokens of a name, stopwords removed."""
    return {t for t in re.split(r"[\s,./&]+", (name or "").upper())
            if len(t) > 1 and t not in _MATCH_STOPWORDS}


ESTATE_HIGH = re.compile(
    r"\bESTATE\s+OF\b|\bEST\s+OF\b|\bHEIRS\s+OF\b|\bSUCCESSORS\s+OF\b"
    r"|\bDECEASED\b|\bDEC'D\b|\b\w[\w\s]*\s+ESTATE\b|\b\w[\w\s]*\s+HEIRS\b", re.I)
TRUST_PAT = re.compile(
    r"\b[\w\s]+\s+(FAMILY\s+|LIVING\s+|REVOCABLE\s+|IRREVOCABLE\s+)?TRUST\b", re.I)
ENTITY_PAT = re.compile(
    r"\b(LLC|L\.?L\.?C|INC|CORP|CORPORATION|L\.?P\.?|LTD|COMPANY|CO|"
    r"PARTNERSHIP|HOLDINGS|PROPERTIES|INVESTMENTS|BANK|ASS'?N|ASSOCIATION)\b", re.I)


def classify_owner_type(name: str) -> str:
    if not name:
        return "UNKNOWN"
    if ESTATE_HIGH.search(name):
        return "ESTATE"
    if TRUST_PAT.search(name):
        return "TRUST"
    if ENTITY_PAT.search(name):
        return "ENTITY"
    return "INDIVIDUAL"


def parse_addr(addr: str) -> dict:
    """Parse 'STREET CITY, ST ZIP' (EPCAD format) into components."""
    out = {"street": "", "city": "", "state": "", "zip": "", "full": addr or ""}
    if not addr:
        return out
    a = addr.strip().rstrip(",")
    m = re.search(r"\b([A-Z]{2})\s+(\d{5})(?:-\d{4})?\s*$", a)
    if m:
        out["state"], out["zip"] = m.group(1), m.group(2)
        a = a[:m.start()].strip().rstrip(",")
    # last comma-or-space token group before state = city (best-effort)
    if "," in a:
        street, _, city = a.rpartition(",")
        out["street"], out["city"] = street.strip(), city.strip()
    else:
        out["street"] = a
    return out


_epcad_cache: dict[str, dict | None] = {}


def epcad_lookup(owner_name: str, client: httpx.Client) -> dict | None:
    """Per-row EPCAD enrichment by owner name. Returns parsed enrichment
    or None. Cached by name. Conservative: only accepts a confident hit."""
    key = (owner_name or "").strip().upper()
    if not key or len(key) < 4:
        return None
    if key in _epcad_cache:
        return _epcad_cache[key]
    result = None
    qtok = _tokens(key)
    try:
        r = client.get(EPCAD, params={"ownerName": key, "page": 1, "pageSize": 10},
                        timeout=40)
        if r.status_code == 200:
            props = (r.json() or {}).get("Properties") or []
            # Match-quality guard: score every candidate by token overlap of
            # the queried name vs the candidate parcel's owner name. Accept
            # the best candidate only if it clears the threshold — Jaccard
            # >= 0.6, OR >= 2 shared significant tokens covering >= 50% of the
            # queried name. Otherwise return None (UNRESOLVED) rather than
            # blindly trusting Properties[0].
            best, best_score = None, 0.0
            for cand in props:
                cowners = cand.get("Owners") or [{}]
                ctok = _tokens((cowners[0] or {}).get("Name") or "")
                if not qtok or not ctok:
                    continue
                inter = qtok & ctok
                jacc = len(inter) / len(qtok | ctok)
                accept = jacc >= 0.6 or (
                    len(inter) >= 2 and len(inter) / len(qtok) >= 0.5)
                if accept and jacc > best_score:
                    best, best_score = cand, jacc
            if best is not None:
                p = best
                loc = p.get("Location") or {}
                owners = p.get("Owners") or [{}]
                vals = sorted(p.get("Values") or [{}],
                              key=lambda v: v.get("Year") or 0)
                v = vals[-1] if vals else {}
                ow = owners[0]
                result = {
                    "epcad_property_id": p.get("PropertyId"),
                    "epcad_geo_id": p.get("GeoID"),
                    "legal_description": p.get("LegalDescription"),
                    "owner_name": ow.get("Name"),
                    "situs": parse_addr(loc.get("Address")),
                    "mailing": parse_addr(ow.get("MailingAddress")),
                    "assessed_value": v.get("AssessedValue"),
                    "appraised_value": v.get("AppraisedValue"),
                    "market_value": v.get("MarketValue"),
                    "no_homestead": p.get("No_Homestead"),
                    "exemptions": ow.get("Excemptions"),
                    "epcad_match_count": len(props),
                    "epcad_match_score": round(best_score, 3),
                }
    except Exception as exc:
        print(f"  epcad lookup error for {key!r}: {exc!r}", file=sys.stderr)
    _epcad_cache[key] = result
    return result


def pick_distressed_party(parties: list[dict], signal_type: str) -> str:
    """Pick the debtor / distressed party using the doc-type-aware rule table
    (Fix 1, v2). The debtor's name_type varies by document type: e.g. for a
    hospital_lien the debtor is the GRANTEE (patient) while the GRANTOR is the
    hospital filer; for a mechanics_lien the debtor is the GRANTOR (owner)."""
    if not parties:
        return ""
    rule = DEBTOR_PARTY_RULES.get(signal_type)
    if rule:
        for want in rule:
            for party in parties:
                if want in (party.get("name_type") or "").upper():
                    return party.get("name", "")
        # rule produced no party match — fall through to the default ranking
    else:
        print(f"[warn] no debtor-party rule for signal_type={signal_type!r}; "
              f"using default ranking", file=sys.stderr)
    def rank(party):
        nt = (party.get("name_type") or "").upper()
        if "DEFENDANT" in nt:
            return 0
        if "GRANTOR" in nt:
            return 1
        if "PLAINTIFF" in nt:
            return 3
        return 2
    return sorted(parties, key=rank)[0].get("name", "")


def main() -> int:
    if not RAW.exists():
        print(f"raw file not found: {RAW}", file=sys.stderr)
        return 3
    raw_records = [json.loads(l) for l in RAW.read_text().splitlines() if l.strip()]
    print(f"loaded {len(raw_records)} raw clerk_recordings records", file=sys.stderr)

    TRANSLATED.parent.mkdir(parents=True, exist_ok=True)
    LEADS.parent.mkdir(parents=True, exist_ok=True)

    signals: list[dict] = []          # translator output
    translated_out: list[dict] = []
    t0 = time.time()

    with httpx.Client(headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
                      follow_redirects=True) as client:
        for i, raw in enumerate(raw_records):
            p = raw.get("raw_payload", {})
            inum = p.get("instrument_number", "")
            signal_type = p.get("signal_type", "lien")
            parties = p.get("parties", []) or []
            distressed = pick_distressed_party(parties, signal_type)

            enrich = epcad_lookup(distressed, client) if distressed else None

            sig = {
                "signal_id": f"clk_{inum}",
                "raw_record_id": raw.get("raw_record_id"),
                "source_id": "clerk_recordings",
                "source_url": raw.get("source_url"),
                "signal_type": signal_type,
                "signal_label": SIGNAL_LABELS.get(signal_type, signal_type),
                "signal_confidence": "HIGH",
                "instrument_number": inum,
                "recorded_date": p.get("recording_date"),
                "doc_type_raw": p.get("doc_type_raw"),
                "book": p.get("book"), "page": p.get("page"),
                "distressed_party": distressed,
                "all_parties": parties,
                "evidence_id": f"ev_clk_{inum}",
                "enrichment": enrich,
            }
            signals.append(sig)
            translated_out.append(sig)
            if (i + 1) % 50 == 0:
                print(f"  translated {i+1}/{len(raw_records)} "
                      f"({time.time()-t0:.0f}s)", file=sys.stderr)

    with open(TRANSLATED, "w", encoding="utf-8") as fh:
        for s in translated_out:
            fh.write(json.dumps(s, ensure_ascii=False) + "\n")

    # ---- Step 5: aggregate signals into matched_lead rows (one per parcel) ----
    leads: dict[str, dict] = {}
    unresolved_seq = 0
    for s in signals:
        e = s.get("enrichment")
        if e and e.get("epcad_geo_id"):
            key = f"PARCEL::{e['epcad_geo_id']}"
            resolution = "RESOLVED"
        else:
            unresolved_seq += 1
            key = f"UNRESOLVED::{s['distressed_party']}::{s['instrument_number']}"
            resolution = "UNRESOLVED"

        lead = leads.get(key)
        if lead is None:
            owner_name = (e or {}).get("owner_name") or s["distressed_party"]
            owner_type = classify_owner_type(owner_name)
            situs = (e or {}).get("situs") or {}
            mailing = (e or {}).get("mailing") or {}
            absentee = bool(situs.get("full") and mailing.get("full")
                            and situs.get("full") != mailing.get("full"))
            oos = bool(mailing.get("state") and mailing.get("state") != "TX")
            lead = {
                "lead_id": key.replace("::", "_").replace(" ", "_")[:80],
                "parcel_resolution_status": resolution,
                "parcel_id": (e or {}).get("epcad_geo_id", ""),
                "owner_name": owner_name,
                "owner_type": owner_type,
                "property_full_address": situs.get("full", ""),
                "property_street": situs.get("street", ""),
                "property_city": situs.get("city", ""),
                "property_state": situs.get("state", ""),
                "property_zip": situs.get("zip", ""),
                "mailing_full_address": mailing.get("full", ""),
                "mailing_city": mailing.get("city", ""),
                "mailing_state": mailing.get("state", ""),
                "assessed_value": (e or {}).get("assessed_value"),
                "appraised_value": (e or {}).get("appraised_value"),
                "homestead": (None if not e else
                              ("NO_HOMESTEAD" if e.get("no_homestead") else "HOMESTEAD")),
                "absentee_owner_flag": absentee,
                "out_of_state_owner_flag": oos,
                "legal_description": (e or {}).get("legal_description", ""),
                "signals": [],
                "signal_types": [],
                "source_urls": [],
            }
            leads[key] = lead

        lead["signals"].append({
            "signal_type": s["signal_type"], "signal_label": s["signal_label"],
            "signal_confidence": s["signal_confidence"],
            "source_id": s["source_id"], "source_url": s["source_url"],
            "instrument_number": s["instrument_number"],
            "recorded_date": s["recorded_date"], "doc_type_raw": s["doc_type_raw"],
            "evidence_id": s["evidence_id"],
        })
        if s["source_url"] not in lead["source_urls"]:
            lead["source_urls"].append(s["source_url"])

    # estate/trust STACKED signals (derived from EPCAD owner_name) + finalize
    for lead in leads.values():
        ot = lead["owner_type"]
        if ot == "ESTATE":
            lead["signals"].append({
                "signal_type": "estate_titled_property",
                "signal_label": "Estate-Titled Property",
                "signal_confidence": "HIGH", "source_id": "epcad_enrichment_derived",
                "source_url": "", "instrument_number": "",
                "recorded_date": "", "doc_type_raw": "",
                "evidence_id": f"ev_estate_{lead['lead_id']}"})
        elif ot == "TRUST":
            lead["signals"].append({
                "signal_type": "trust_titled_property",
                "signal_label": "Trust-Titled Property",
                "signal_confidence": "MEDIUM", "source_id": "epcad_enrichment_derived",
                "source_url": "", "instrument_number": "",
                "recorded_date": "", "doc_type_raw": "",
                "evidence_id": f"ev_trust_{lead['lead_id']}"})
        types = []
        for sg in lead["signals"]:
            if sg["signal_type"] not in types:
                types.append(sg["signal_type"])
        lead["signal_types"] = types
        lead["signal_count"] = len(lead["signals"])
        # primary signal = highest-priority PRIMARY signal (§13.5.1: every row
        # must carry a primary clerk signal — the estate/trust ones never count)
        primaries = [sg for sg in lead["signals"]
                     if sg["source_id"] == "clerk_recordings"]
        primaries.sort(key=lambda sg: SIGNAL_PRIORITY.get(sg["signal_type"], 0),
                       reverse=True)
        lead["primary_signal"] = primaries[0]["signal_type"] if primaries else None
        lead["latest_event_date"] = max(
            (sg["recorded_date"] for sg in lead["signals"] if sg["recorded_date"]),
            default="")

    # §13.5.1 guard — drop any row without a primary clerk-sourced signal
    rows = [l for l in leads.values() if l["primary_signal"]]
    dropped = len(leads) - len(rows)
    if dropped:
        print(f"§13.5.1 guard: dropped {dropped} rows with no primary signal",
              file=sys.stderr)

    resolved = sum(1 for l in rows if l["parcel_resolution_status"] == "RESOLVED")
    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "county": "El Paso", "state": "TX",
        "build_label": "SOURCE_LIMITED",
        "build_label_reason": ("Single-source build: clerk_recordings only. "
                               "tax_collector, court_probate, court_civil and "
                               "foreclosure_notices are deferred to later "
                               "sessions."),
        "sources_active": ["clerk_recordings"],
        "lead_total": len(rows),
        "epcad_enrichment_resolved": resolved,
        "epcad_enrichment_unresolved": len(rows) - resolved,
        "records": rows,
    }
    with open(LEADS, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)

    # report
    st_dist: dict[str, int] = {}
    for l in rows:
        for t in l["signal_types"]:
            st_dist[t] = st_dist.get(t, 0) + 1
    stack = {"1": 0, "2": 0, "3+": 0}
    for l in rows:
        n = l["signal_count"]
        stack["1" if n == 1 else "2" if n == 2 else "3+"] += 1
    ot_dist: dict[str, int] = {}
    for l in rows:
        ot_dist[l["owner_type"]] = ot_dist.get(l["owner_type"], 0) + 1
    print(f"\n=== clerk_recordings pipeline summary ===")
    print(f"raw records:        {len(raw_records)}")
    print(f"matched_leads:      {len(rows)}")
    print(f"EPCAD resolved:     {resolved} / {len(rows)}  "
          f"({100*resolved//max(len(rows),1)}%)")
    print(f"signal_type dist:   {st_dist}")
    print(f"stacking dist:      {stack}")
    print(f"owner_type dist:    {ot_dist}")
    print(f"wrote {LEADS.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
