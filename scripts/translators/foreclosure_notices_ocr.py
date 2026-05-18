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
        if 3 <= len(n) <= 70 and re.search(r"[A-Za-z]", n):
            names.append(n)
    return names


def extract_fields(text: str) -> dict:
    """Per-layout regex extraction over a notice's OCR text."""
    t = re.sub(r"[ \t]+", " ", text)
    rec = {f: ("" if f != "debtor_names" else []) for f in FIELDS}

    # --- sale_date: "Date: June 02, 2026" / "Date: 6/2/2026". Skip any
    # "Date:" preceded by "trust"/"recorded" — those are the Deed-of-Trust
    # date or recording date (layout D: "Deed of Trust Date: ..."), NOT the
    # foreclosure sale date. ---
    for m in re.finditer(r"\bDate:\s*([A-Z][a-z]+\s+\d{1,2},?\s+20\d\d"
                         r"|\d{1,2}/\d{1,2}/20\d\d)", t):
        pre = t[max(0, m.start() - 14):m.start()].lower()
        if "trust" in pre or "record" in pre:
            continue
        rec["sale_date"] = m.group(1).strip()
        break

    # --- dot_document_number: Clerk's File No / File No <9-13 digits> ---
    m = re.search(r"(?:CLERK[’'`]?S?\s+FILE\s+NO|File\s+No)\.?\s*(\d{9,13})",
                  t, re.I)
    if m:
        rec["dot_document_number"] = m.group(1)

    # --- debtor_names: layout B "Grantor(s):", layout A "executed by" ---
    m = re.search(r"Grantor\(s\):\s*(.+?)(?:\n\s*\n|Original Trustee|"
                  r"Original Mortgagee|Current Mortgagee)", t, re.I | re.S)
    if not m:
        m = re.search(r"executed by\s+(.+?),?\s+securing", t, re.I | re.S)
    if not m:
        m = re.search(r"Texas,?\s+with\s+(.+?),?\s+grantor", t, re.I | re.S)
    if m:
        rec["debtor_names"] = _clean_names(m.group(1))

    # --- common_street_address ---
    m = re.search(r"Commonly known as:\s*(.+?)(?:\n|$)", t, re.I)
    if m:
        rec["common_street_address"] = re.sub(r"\s+", " ", m.group(1)).strip(" ,.")
    else:
        # layout A: street + city/ST/ZIP on the first lines of the page
        m = re.search(r"^\s*(\d{2,6}\s+[A-Z][A-Z0-9 .]+?)(?:\s+\d{8,})?\s*\n"
                      r"\s*([A-Z][A-Z .]+,?\s*TX\s*\d{5})", text, re.M)
        if m:
            rec["common_street_address"] = re.sub(
                r"\s+", " ", f"{m.group(1)}, {m.group(2)}").strip(" ,.")

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
        try:
            text = ocr_pdf(fp)
        except Exception as exc:
            print(f"  OCR error {fp.name}: {exc!r}", file=sys.stderr)
            text = ""
        (OCR_DIR / f"{fp.stem}.txt").write_text(text, encoding="utf-8")
        rec = extract_fields(text)
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
