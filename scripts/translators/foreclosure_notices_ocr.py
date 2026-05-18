#!/usr/bin/env python3
"""
foreclosure_notices OCR + field extraction — El Paso County (el_paso_tx).

Step 3 of the foreclosure_notices Path-B build. The notice PDFs pulled by
scripts/scrapers/foreclosure_notices.py are SCANNED IMAGES, so each is
rendered (pymupdf) and OCR'd (Tesseract), then fields are pulled by
per-layout regex. Two notice layouts are handled:
  A — "NOTICE OF [SUBSTITUTE] TRUSTEE'S SALE"  (address at page top)
  B — "APPOINTMENT OF SUBSTITUTE TRUSTEE and NOTICE OF TRUSTEE'S SALE"
      ("Property To Be Sold" + "Commonly known as:")

Reads : data/el_paso_tx/raw/foreclosure_notices/pdfs/*.pdf
        data/el_paso_tx/raw/foreclosure_notices/listing.jsonl
Writes: data/el_paso_tx/raw/foreclosure_notices/ocr/<pdf>.txt   (debug)
        data/el_paso_tx/raw/foreclosure_notices/extracted.jsonl
"""
from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path

import fitz  # pymupdf
import pytesseract
from PIL import Image

REPO = Path(__file__).resolve().parents[2]
BASE = REPO / "data" / "el_paso_tx" / "raw" / "foreclosure_notices"
PDF_DIR = BASE / "pdfs"
OCR_DIR = BASE / "ocr"
LISTING = BASE / "listing.jsonl"
EXTRACTED = BASE / "extracted.jsonl"

FIELDS = ["common_street_address", "debtor_names", "dot_document_number",
          "sale_date", "lender_beneficiary", "legal_description"]
# legal_description is layout-B only; not counted against completeness.
REQUIRED = ["common_street_address", "debtor_names", "dot_document_number",
            "sale_date", "lender_beneficiary"]


def ocr_pdf(path: Path) -> str:
    """OCR a notice PDF. Page 1 is the clerk cover sheet — OCR page 2+."""
    doc = fitz.open(path)
    out = []
    start = 1 if doc.page_count > 1 else 0
    for pi in range(start, doc.page_count):
        pix = doc[pi].get_pixmap(dpi=300)
        out.append(pytesseract.image_to_string(
            Image.open(io.BytesIO(pix.tobytes("png")))))
    doc.close()
    return "\n".join(out)


def _clean_names(blob: str) -> list[str]:
    """Split a grantor/debtor blob into individual names, dropping the
    marital/capacity descriptors that trail Texas notice party lists."""
    blob = re.split(r",?\s+(?:A SINGLE|AN UNMARRIED|HUSBAND AND WIFE|"
                    r"A MARRIED|AS COMMUNITY|JOINED|EACH AS|A/K/A|AKA)\b",
                    blob, maxsplit=1)[0]
    blob = blob.replace(" AND ", "|").replace(", AND ", "|").replace("&", "|")
    names = []
    for n in blob.split("|"):
        n = re.sub(r"\s+", " ", n).strip(" ,.")
        # reject OCR fragments that are actually a form LABEL, not a name
        # (layout C stacks labels apart from values in the OCR stream)
        if ":" in n:
            continue
        if re.search(r"\b(MORTGAGEE|MORTGAGOR|TRUSTEE|GRANTEE|GRANTOR|"
                     r"BENEFICIARY|SERVICER|ORIGINAL|CURRENT|LENDER|"
                     r"INFORMATION|PROPERTY|ADDRESS|RECORDING)\b", n, re.I):
            continue
        if 3 <= len(n) <= 70 and re.search(r"[A-Za-z]", n):
            names.append(n)
    return names


CITY_RE = (r"EL\s+PASO|SOCORRO|HORIZON\s+CITY|SAN\s+ELIZARIO|ANTHONY|VINTON"
           r"|CLINT|CANUTILLO|FABENS|TORNILLO|WESTWAY")


def extract_fields(text: str, listing_sale_date: str = "") -> dict:
    """Layout-tolerant extraction over a notice's OCR text. Shape-based
    where a field has a recognisable shape (address, document number) —
    robust across all notice layouts (A/B/C/D); label-anchored otherwise."""
    t = re.sub(r"[ \t]+", " ", text)
    rec = {f: ("" if f != "debtor_names" else []) for f in FIELDS}

    # --- sale_date: "Date: ..." not preceded by "trust"/"record" (those
    # are the Deed-of-Trust / recording date). Layout C/D bury the sale
    # date in a label/value-split block, so fall back to the listing
    # row's sale_date — always present and authoritative. ---
    for m in re.finditer(r"\b(?:Date of Sale|Sale Date|Date):\s*"
                         r"([A-Z][a-z]+\s+\d{1,2},?\s+20\d\d"
                         r"|\d{1,2}/\d{1,2}/20\d\d)", t):
        pre = t[max(0, m.start() - 16):m.start()].lower()
        if "trust" in pre or "record" in pre:
            continue
        rec["sale_date"] = m.group(1).strip()
        break
    if not rec["sale_date"] and listing_sale_date:
        rec["sale_date"] = listing_sale_date.strip()

    # --- dot_document_number: a year-prefixed 11-digit recording number
    # ("CLERK'S FILE NO. 20150036831", "Instrument 20240049385",
    # "Instrument No: 20050050228"). Prefer one near a recording keyword. ---
    best = None
    for m in re.finditer(r"\b((?:19|20)\d{9})\b", t):
        pre = t[max(0, m.start() - 45):m.start()].lower()
        if any(k in pre for k in ("file no", "instrument", "recorded",
                                  "recording", "clerk")):
            best = m.group(1)
            break
    if not best:
        anynum = re.search(r"\b((?:19|20)\d{9})\b", t)
        best = anynum.group(1) if anynum else ""
    rec["dot_document_number"] = best

    # --- debtor_names: layout B "Grantor(s):", layout A "executed by" ---
    m = re.search(r"Grantor\(s\):\s*(.+?)(?:\n\s*\n|Original Trustee|"
                  r"Original Mortgagee|Current Mortgagee)", t, re.I | re.S)
    if not m:
        m = re.search(r"executed by\s+(.+?),?\s+securing", t, re.I | re.S)
    if not m:
        m = re.search(r"Texas,?\s+with\s+(.+?),?\s+grantor", t, re.I | re.S)
    if m:
        rec["debtor_names"] = _clean_names(m.group(1))

    # --- common_street_address: shape-based — "<NUM> <STREET>, <CITY> TX
    # <ZIP>" with CITY restricted to El Paso County municipalities (so
    # trustee/servicer addresses elsewhere never match). Take the first
    # match that is NOT a sale venue (the Coliseum / Courthouse), and
    # strip any trailing barcode digit-run that bled into the street name
    # (layout A prints a barcode beside the address). ---
    flat = re.sub(r"\s+", " ", text)
    venues = ("4100 E PAISANO", "4100 E. PAISANO", "500 E SAN ANTONIO",
              "500 EAST SAN ANTONIO", "500 E. SAN ANTONIO")
    for am in re.finditer(
            rf"\b(\d{{2,6}})\s+([A-Z0-9][A-Z0-9 .'#/-]{{2,45}}?),?\s+"
            rf"((?:{CITY_RE}))\b,?\s*(?:TX|TEXAS)\b,?\s*(\d{{5}})", flat, re.I):
        num, street = am.group(1), am.group(2)
        street = re.sub(r"\s*\b\d{5,}\b\s*", " ", street).strip(" ,.")
        if not street:
            continue
        cand = re.sub(r"\s+", " ",
                      f"{num} {street}, {am.group(3)} TX {am.group(4)}"
                      ).upper().strip(" ,.")
        if any(v in cand for v in venues):
            continue
        rec["common_street_address"] = cand
        break

    # --- lender_beneficiary ---
    m = re.search(r"([A-Z][A-Za-z0-9 ,./&'-]{3,70}?)\s+is the current mortgagee",
                  t)
    if not m:
        m = re.search(r"Current Mortgagee:\s*(.+?)(?:\n|Mortgage Servicer)",
                      t, re.I)
    if not m:
        m = re.search(r"([A-Z][A-Za-z0-9 ,./&'-]{3,70}?),?\s+as Mortgage "
                      r"Servicer", t)
    if m:
        rec["lender_beneficiary"] = re.sub(r"\s+", " ", m.group(1)).strip(" ,.")

    # --- legal_description (layout B) ---
    m = re.search(r"Property To Be Sold\.?\s*(.+?)(?:Commonly known as:|"
                  r"\n\s*3\.\s*Instrument)", t, re.I | re.S)
    if m:
        rec["legal_description"] = re.sub(r"\s+", " ", m.group(1)).strip(" ,.")

    missing = [f for f in REQUIRED
               if not rec[f] or (f == "debtor_names" and not rec["debtor_names"])]
    rec["missing_fields"] = missing
    rec["extraction_complete"] = not missing
    return rec


def main() -> int:
    if not PDF_DIR.exists() or not any(PDF_DIR.glob("*.pdf")):
        print(f"no PDFs in {PDF_DIR}", file=sys.stderr)
        return 3
    OCR_DIR.mkdir(parents=True, exist_ok=True)
    listing = {}
    if LISTING.exists():
        for line in LISTING.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                listing[r["pdf_filename"]] = r

    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    out = []
    full = partial = poor = 0
    for i, fp in enumerate(pdfs, 1):
        # Reuse cached OCR text when present — re-extraction (regex tuning)
        # is then fast and does not re-run Tesseract on every PDF.
        cache = OCR_DIR / f"{fp.stem}.txt"
        if cache.exists() and cache.stat().st_size > 0:
            text = cache.read_text(encoding="utf-8")
        else:
            try:
                text = ocr_pdf(fp)
            except Exception as exc:
                print(f"  OCR error {fp.name}: {exc!r}", file=sys.stderr)
                text = ""
            cache.write_text(text, encoding="utf-8")
        lr0 = listing.get(fp.name, {})
        rec = extract_fields(text, lr0.get("sale_date", ""))
        rec["pdf_path"] = f"data/el_paso_tx/raw/foreclosure_notices/pdfs/{fp.name}"
        rec["pdf_filename"] = fp.name
        lr = listing.get(fp.name, {})
        rec["listing_sale_date"] = lr.get("sale_date", "")
        rec["listing_url"] = lr.get("listing_url", "")
        got = len(REQUIRED) - len(rec["missing_fields"])
        if got == len(REQUIRED):
            full += 1
        elif got >= len(REQUIRED) - 1:
            partial += 1
        else:
            poor += 1
        out.append(rec)
        if i % 20 == 0:
            print(f"  OCR'd {i}/{len(pdfs)}", file=sys.stderr, flush=True)

    with open(EXTRACTED, "w", encoding="utf-8") as fh:
        for r in out:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    n = len(out)
    print(f"\n=== foreclosure_notices OCR + extraction ===")
    print(f"PDFs processed:        {n}")
    print(f"all 5 required fields: {full} ({100*full//max(n,1)}%)")
    print(f"4/5 fields:            {partial}")
    print(f"<4/5 (review):         {poor}")
    print(f"wrote {EXTRACTED.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
