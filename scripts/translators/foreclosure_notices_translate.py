#!/usr/bin/env python3
"""
foreclosure_notices translator — El Paso County (el_paso_tx). Step 3.

Reads the OCR-extracted notices and builds matched_lead records, joining
each notice to an EPCAD parcel by STREET ADDRESS (the notice carries a
real situs address — unlike clerk_recordings' name-only join). Output
records share the leads.json matched_lead shape so Step 4 can merge them
into the existing clerk_recordings board.

Reads : data/el_paso_tx/raw/foreclosure_notices/extracted.jsonl
Writes: data/el_paso_tx/translated/foreclosure_notices_translated.jsonl

Lead origination (§13): foreclosure_notice is a §13.2 primary lead event.
EPCAD parcel data is §13.3 enrichment — it decorates, never originates.
"""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[2]
EXTRACTED = REPO / "data/el_paso_tx/raw/foreclosure_notices/extracted.jsonl"
OUT = REPO / "data/el_paso_tx/translated/foreclosure_notices_translated.jsonl"
EPCAD = "https://epcadpropertysearch.azurewebsites.net/Api/Properties/GetProperties"

# ---- entity / estate / trust classification (mirrors Fix 1/3) ----
ESTATE_HIGH = re.compile(
    r"\bESTATE\s+OF\b|\bEST\s+OF\b|\bHEIRS\s+OF\b|\bSUCCESSORS\s+OF\b"
    r"|\bDECEASED\b|\bDEC'D\b|\b\w[\w\s]*\s+ESTATE\b|\b\w[\w\s]*\s+HEIRS\b", re.I)
TRUST_PAT = re.compile(
    r"\b[\w\s]+\s+(FAMILY\s+|LIVING\s+|REVOCABLE\s+|IRREVOCABLE\s+)?TRUST\b", re.I)
ENTITY_PAT = re.compile(
    r"\b(LLC|L\.?L\.?C|INC|CORP|CORPORATION|L\.?P\.?|LLP|LTD|COMPANY|CO|"
    r"PARTNERSHIP|PARTNERS|HOLDINGS|PROPERTIES|INVESTMENTS|BANK|ASS'?N|"
    r"ASSOCIATION|ASSOCIATES|ASSOC|ENTERPRISES|GROUP|OWNER|CENTER|SERVICES|"
    r"COMMISSION|AUTHORITY|DISTRICT|FUND|MANAGEMENT|REALTY|MORTGAGE|"
    r"NATIONAL)\b"
    r"|\bCITY\s+OF\b|\bCOUNTY\s+OF\b|\bSTATE\s+OF\b|\bUNITED\s+STATES\b"
    r"|\bCREDIT\s+UNION\b", re.I)
# street-type tokens dropped before address token-overlap scoring
_ADDR_STOP = {"ST", "AVE", "DR", "PL", "CT", "RD", "LN", "LANE", "BLVD",
              "CIR", "WAY", "TER", "TRL", "PKWY", "HWY", "N", "S", "E", "W",
              "NE", "NW", "SE", "SW", "EL", "PASO", "TX"}


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


def _atokens(s: str) -> set:
    return {t for t in re.split(r"[\s,./#-]+", (s or "").upper())
            if len(t) > 1 and t not in _ADDR_STOP and not t.isdigit()}


def parse_situs(addr: str) -> dict:
    """Parse a notice 'NUM STREET CITY, TX ZIP' string into components."""
    out = {"number": "", "street": "", "city": "", "state": "TX", "zip": "",
           "full": (addr or "").strip()}
    a = re.sub(r"\s+", " ", addr or "").strip().rstrip(",")
    m = re.search(r"\b(\d{5})(?:-\d{4})?\s*$", a)
    if m:
        out["zip"] = m.group(1)
        a = a[:m.start()].strip().rstrip(",")
    a = re.sub(r",?\s*TX\s*$", "", a).strip().rstrip(",")
    m = re.match(r"^\s*(\d+[A-Z]?)\s+(.+)$", a)
    if m:
        out["number"] = m.group(1)
        rest = m.group(2)
        # split trailing CITY off the street name
        cm = re.search(r"\b(EL PASO|SOCORRO|HORIZON CITY|SAN ELIZARIO|ANTHONY"
                       r"|VINTON|CLINT|CANUTILLO|FABENS|TORNILLO)\b\s*$",
                       rest, re.I)
        if cm:
            out["city"] = cm.group(1).upper()
            out["street"] = rest[:cm.start()].strip().rstrip(",")
        else:
            out["street"] = rest.strip().rstrip(",")
    return out


_epcad_cache: dict[str, dict | None] = {}


def epcad_by_address(situs: dict, debtor_names: list, client: httpx.Client) -> dict | None:
    """EPCAD lookup by street number + name, with a token-overlap match
    guard. Among candidates clearing the guard, prefer the one whose owner
    name overlaps the notice debtor names."""
    num, street = situs.get("number", ""), situs.get("street", "")
    if not num or not street:
        return None
    key = f"{num}|{street}".upper()
    if key in _epcad_cache:
        return _epcad_cache[key]
    result = None
    qtok = _atokens(street)
    dtok = set()
    for d in debtor_names or []:
        dtok |= {t for t in re.split(r"[\s,.]+", d.upper()) if len(t) > 1}
    # EPCAD's streetNumber param breaks the query — search by streetName
    # alone, then match the street number client-side. streetName is
    # suffix-sensitive ("AIKEN LN" -> 0) and page-capped, so try the
    # street with and without its trailing type word and paginate.
    _SFX = {"DR", "LN", "LANE", "ST", "AVE", "RD", "PL", "CT", "BLVD", "CIR",
            "WAY", "DRIVE", "STREET", "AVENUE", "ROAD", "COURT", "PLACE",
            "LOOP", "TRL", "PASS", "PKWY"}
    variants = [street]
    parts = street.rsplit(" ", 1)
    if len(parts) == 2 and parts[1].upper().strip(".") in _SFX:
        variants.append(parts[0])
    props: list = []
    try:
        for v in variants:
            acc = []
            for page in range(1, 9):           # up to ~400 properties / street
                r = client.get(EPCAD, params={"streetName": v, "page": page,
                                              "pageSize": 50}, timeout=40)
                if r.status_code != 200:
                    break
                batch = (r.json() or {}).get("Properties") or []
                acc.extend(batch)
                if len(batch) < 50:
                    break
            if acc:
                props = acc
                break
        if props:
            best, best_score = None, 0.0
            for cand in props:
                loc = cand.get("Location") or {}
                caddr = (loc.get("Address") or "").strip().upper()
                # require an exact street-number prefix match
                if not re.match(rf"^{re.escape(num)}\s", caddr):
                    continue
                ctok = _atokens(caddr)
                if not qtok or not ctok:
                    continue
                inter = qtok & ctok
                jacc = len(inter) / len(qtok | ctok)
                accept = jacc >= 0.6 or (
                    len(inter) >= 2 and len(inter) / len(qtok) >= 0.5)
                if not accept:
                    continue
                # tie-break: owner-name overlap with the notice debtor
                owners = cand.get("Owners") or [{}]
                otok = {t for t in re.split(r"[\s,.]+",
                        (owners[0] or {}).get("Name", "").upper()) if len(t) > 1}
                score = jacc + (0.5 if (dtok & otok) else 0.0)
                if score > best_score:
                    best, best_score = cand, score
            if best is not None:
                loc = best.get("Location") or {}
                owners = best.get("Owners") or [{}]
                vals = sorted(best.get("Values") or [{}],
                              key=lambda v: v.get("Year") or 0)
                v = vals[-1] if vals else {}
                ow = owners[0]
                result = {
                    "geo_id": best.get("GeoID"),
                    "property_id": best.get("PropertyId"),
                    "owner_name": ow.get("Name"),
                    "situs": loc.get("Address") or "",
                    "mailing": ow.get("MailingAddress") or "",
                    "assessed_value": v.get("AssessedValue"),
                    "appraised_value": v.get("AppraisedValue"),
                    "no_homestead": best.get("No_Homestead"),
                }
    except Exception as exc:
        print(f"  epcad error {key!r}: {exc!r}", file=sys.stderr)
    _epcad_cache[key] = result
    return result


def _parse_mail(addr: str) -> dict:
    m = re.search(r"\b([A-Z]{2})\s+(\d{5})(?:-\d{4})?\s*$", (addr or "").upper())
    out = {"full": addr or "", "city": "", "state": ""}
    if m:
        out["state"] = m.group(1)
    return out




def main() -> int:
    if not EXTRACTED.exists():
        print(f"extracted.jsonl not found: {EXTRACTED}", file=sys.stderr)
        return 3
    notices = [json.loads(l) for l in EXTRACTED.read_text().splitlines() if l.strip()]
    print(f"loaded {len(notices)} extracted notices", file=sys.stderr)
    OUT.parent.mkdir(parents=True, exist_ok=True)

    leads = []
    enriched = 0
    addr_n = debtor_n = doc_n = lender_n = 0
    t0 = time.time()
    with httpx.Client(headers={"User-Agent": "Mozilla/5.0",
                               "Accept": "application/json"},
                      follow_redirects=True) as client:
        for i, n in enumerate(notices):
            # --- listing-page base: always present, the reliable lead core ---
            sub = n.get("listing_subdivision", "")
            lot, blk = n.get("listing_lot", ""), n.get("listing_block", "")
            unit, tract = n.get("listing_unit", ""), n.get("listing_tract", "")
            legal_parts = []
            if sub:
                legal_parts.append(sub)
            if lot:
                legal_parts.append(f"LOT {lot}")
            if blk:
                legal_parts.append(f"BLK {blk}")
            if unit:
                legal_parts.append(f"UNIT {unit}")
            if tract:
                legal_parts.append(f"TRACT {tract}")
            legal_description = " ".join(legal_parts).strip()
            sale_date = n.get("sale_date") or n.get("listing_sale_date") or ""
            instrument = (n.get("listing_instrument_number")
                          or n.get("dot_document_number")
                          or n.get("pdf_filename", ""))

            # --- PDF-extracted (bonus) ---
            pdf_address = n.get("common_street_address", "")
            debtors = n.get("debtor_names") or []
            doc_num = n.get("dot_document_number", "")
            lender = n.get("lender_beneficiary", "")
            if pdf_address:
                addr_n += 1
            if debtors:
                debtor_n += 1
            if doc_num:
                doc_n += 1
            if lender:
                lender_n += 1

            # --- EPCAD enrichment: OPTIONAL bonus, never gates the lead ---
            e = None
            if pdf_address:
                e = epcad_by_address(parse_situs(pdf_address), debtors, client)
            if e and e.get("geo_id"):
                enriched += 1
                epcad_status = "ENRICHED"
                owner = e["owner_name"] or (debtors[0] if debtors else "")
                mail = _parse_mail(e["mailing"])
                lead = {
                    "lead_id": f"PARCEL_{e['geo_id']}",
                    "parcel_resolution_status": "RESOLVED",
                    "epcad_enrichment_status": "ENRICHED",
                    "parcel_id": e["geo_id"],
                    "owner_name": owner,
                    "property_full_address": e["situs"] or pdf_address,
                    "mailing_full_address": e["mailing"],
                    "mailing_city": "", "mailing_state": mail["state"],
                    "assessed_value": e.get("assessed_value"),
                    "appraised_value": e.get("appraised_value"),
                    "homestead": ("NO_HOMESTEAD" if e.get("no_homestead")
                                  else "HOMESTEAD"),
                    "absentee_owner_flag": bool(e["mailing"] and e["situs"]
                                                and e["mailing"] != e["situs"]),
                    "out_of_state_owner_flag": bool(mail["state"]
                                                    and mail["state"] != "TX"),
                }
            else:
                # No EPCAD match — the lead is STILL complete. The
                # foreclosure_notice originates it; listing + PDF data
                # resolve it. parcel_resolution_status is RESOLVED.
                epcad_status = "UNENRICHED"
                owner = debtors[0] if debtors else ""
                lead = {
                    "lead_id": f"FCL_{instrument}_{i}",
                    "parcel_resolution_status": "RESOLVED",
                    "epcad_enrichment_status": "UNENRICHED",
                    "parcel_id": "",
                    "owner_name": owner,
                    "property_full_address": pdf_address,
                    "mailing_full_address": "",
                    "mailing_city": "", "mailing_state": "",
                    "assessed_value": None, "appraised_value": None,
                    "homestead": None, "absentee_owner_flag": False,
                    "out_of_state_owner_flag": False,
                }
            su = parse_situs(pdf_address)
            lead["owner_type"] = classify_owner_type(owner) if owner else "UNKNOWN"
            lead["property_street"] = su["street"]
            lead["property_city"] = su["city"]
            lead["property_state"] = "TX"
            lead["property_zip"] = su["zip"]
            lead["legal_description"] = legal_description

            sig = {
                "signal_type": "foreclosure_notice",
                "signal_label": "Foreclosure Notice",
                "canonical_doc_type": "foreclosure_notice",
                "signal_confidence": "HIGH",
                "source_id": "foreclosure_notices",
                "source_url": "https://apps.epcountytx.gov/publicrecords/Foreclosures",
                "sale_date": sale_date,
                "dot_document_number": doc_num,
                "lender_beneficiary": lender,
                "mortgage_servicer": n.get("mortgage_servicer", ""),
                "debtor_names": debtors,
                "subdivision": sub, "lot": lot, "block": blk, "unit": unit,
                "recorded_date": n.get("listing_sale_date", ""),
                "instrument_number": instrument,
                "evidence_id": f"ev_fcl_{n.get('pdf_filename', '')}",
                "source_urls": ["https://apps.epcountytx.gov/publicrecords/Foreclosures"],
                "evidence_ids": [instrument],
                "count": 1,
            }
            lead["signals"] = [sig]
            lead["signal_types"] = ["foreclosure_notice"]
            lead["source_urls"] = list(sig["source_urls"])
            lead["signal_count"] = 1
            lead["primary_signal"] = "foreclosure_notice"
            lead["latest_event_date"] = sale_date
            # estate/trust stacked signal (detected on the owner — EPCAD
            # owner name when enriched, else the PDF debtor name)
            ot = lead["owner_type"]
            if ot in ("ESTATE", "TRUST"):
                lead["signals"].append({
                    "signal_type": ("estate_titled_property" if ot == "ESTATE"
                                    else "trust_titled_property"),
                    "signal_label": ("Estate-Titled Property" if ot == "ESTATE"
                                     else "Trust-Titled Property"),
                    "signal_confidence": "HIGH" if ot == "ESTATE" else "MEDIUM",
                    "source_id": "epcad_enrichment_derived", "count": 1,
                    "source_urls": [], "evidence_ids": [],
                    "sale_date": "", "recorded_date": "", "instrument_number": "",
                })
                lead["signal_types"].append(lead["signals"][-1]["signal_type"])
                lead["signal_count"] = 2
            leads.append(lead)
            if (i + 1) % 50 == 0:
                print(f"  translated {i+1}/{len(notices)} ({time.time()-t0:.0f}s)",
                      file=sys.stderr)

    with open(OUT, "w", encoding="utf-8") as fh:
        for l in leads:
            fh.write(json.dumps(l, ensure_ascii=False) + "\n")

    n = len(leads)
    print(f"\n=== foreclosure_notices translator (v2) ===")
    print(f"matched_leads:        {n}  (every notice emits a lead — no UNRESOLVED)")
    print(f"EPCAD enrichment:     ENRICHED {enriched} / UNENRICHED {n-enriched} "
          f"({100*enriched//max(n,1)}% enriched — bonus context, not required)")
    print(f"PDF address extracted:{addr_n}/{n}")
    print(f"debtor names:         {debtor_n}/{n}")
    print(f"DoT document number:  {doc_n}/{n}")
    print(f"lender:               {lender_n}/{n}")
    print(f"wrote {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
