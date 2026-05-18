# foreclosure_notices — v2 Recon (data-exposure re-verification)

Date: 2026-05-18 · Recon only, no build.
Trigger: operator review — foreclosure notices DO contain street
addresses, debtor names, document numbers and sale dates; the Phase 0
"deferred pending bulk enrichment index" classification was based on an
incorrect assumption (that only legal descriptions were available).

---

## STEP 1 — Portal fingerprint

Search portal: https://apps.epcountytx.gov/publicrecords/Foreclosures
Results:       https://apps.epcountytx.gov/publicrecords/Foreclosures/ForeclosureSearchResults

  - Search form fields: InstrumentNumber, SaleDateFrom, SaleDateTo,
    Subdivision, Lot, Block, Unit, Tract. A date window is the practical
    query (results do not load without a search).
  - Anti-scraping: reCAPTCHA **v3** (invisible) on the search form —
    passes for a real browser; a Playwright Chromium session clears it
    with no solver. No Cloudflare. No v2 challenge.
  - Flow: POST /Foreclosures/ForeclosureSearch -> HTTP 302 -> GET
    /Foreclosures/ForeclosureSearchResults. Pagination: `?page=N`,
    20 rows/page, 500-record hard cap.
  - Record counts (by sale-date window): 06/01–08/31/2026 = 102 records;
    05/01–12/31/2026 hit the 500 cap. A rolling forward window of
    upcoming sales runs ~150–350 active notices.

### Results-table columns (what the listing row exposes)

    Instrument # | Subdivision | Lot | Block | Unit | Tract |
    Page Count | Sale Date | Document(View link)

  - **Instrument #** renders as a masked sequential placeholder
    ("00000000001", "00000000002", …) — NOT a usable real number.
  - Subdivision / Lot / Block / Unit / Tract are **frequently empty**
    (all blank on the 06–08/2026 sample rows).
  - **Sale Date** is the ONLY reliably-usable field in the listing row.
  - "View Document" is JS-wired (no href): click -> POST
    /Foreclosures/GetDocumentURL/ -> returns an InCaptureWeb viewer URL
    (`/InCaptureWeb/Document/Index?sessionId=<uuid>`) -> viewer popup ->
    the PDF is served at `/incaptureweb/Document/Display`
    (content-type application/pdf), session/signalR-bound. Retrievable
    via Playwright route interception (confirmed — 5 PDFs downloaded).

## STEP 2 — Sample record inspection (5 PDFs pulled)

PDF nature: every sample is a **scanned image** — 0 embedded text
characters, exactly 1 image per page, 3–4 pages. `pdfplumber` / `pymupdf`
text extraction returns nothing. **OCR is required.** The scans are
clean, crisp printed documents (high DPI) — OCR accuracy will be high.

Document structure: page 1 is the County Clerk recording **cover sheet**
(clerk metadata only — instrument/receipt number, recorded date). The
**Notice of (Substitute) Trustee's Sale content begins on page 2.** At
least two notice form layouts were seen ("Notice of [Substitute]
Trustee's Sale" and "Appointment of Substitute Trustee and Notice of
Trustee's Sale").

Fields confirmed present in the notice (visually inspected, 3 samples):

    sample_1 — 7212 GOLDEN HAWK DR, EL PASO, TX 79912
      debtors: ALMA P VAZQUEZ A/K/A PATRICIA VAZQUEZ AND GLORIA L VAZQUEZ
      DoT doc no: 20150036831   sale: 06/02/2026 10:00 AM, El Paso County
      Coliseum   servicer: ROCKET MORTGAGE, LLC (f/k/a Quicken Loans)

    sample_2 — 11125 ELEANOR COLDWELL LANE, SOCORRO, TX 79927
      debtors: JAIME RAFAEL GANDARA AND BLANCA ESTELA DOMINGUEZ
      legal: LOT 24 BLOCK 3 CIELO DEL RIO UNIT 1
      DoT doc no: 20170077414   DoT dated 10/13/2017   sale: 06/02/2026
      servicer: FREEDOM MORTGAGE CORPORATION   T.S.# 2026-22505-TX

    sample_3 — 11117 LOMA GRANDE DR, EL PASO, TX 79934
      debtor: LAURA VALERY REY, AN UNMARRIED WOMAN
      legal: LOT 17 BLOCK 19 NORTH HILLS UNIT FIVE
      DoT doc no: 20170095144   DoT dated 12/20/2017   sale: 06/02/2026
      servicer: FREEDOM MORTGAGE CORPORATION   T.S.# 2025-17901-TX

Every needed field — **common street address, debtor name(s), original
deed-of-trust document number, sale date / time / place, lender /
mortgage servicer, legal description** — is present in the notice. The
operator's premise is CONFIRMED. It is just not machine-text; it is a
scanned image requiring OCR.

## STEP 3 — Build-path recommendation

**BUILD PATH: B — PDF + OCR.** (Not Path A — the listing row has no
address/debtor and a masked instrument number. Not Path B as originally
framed — `pdfplumber` text parsing CANNOT work; the PDFs are scanned
images. The viable path is PDF download + OCR.)

Build outline:
  1. Scraper: search by rolling sale-date window, page through results,
     for each row capture sale_date + drive the View Document flow
     (GetDocumentURL -> InCaptureWeb -> route-intercept
     /Document/Display) to download the notice PDF.
  2. Render PDF pages to images (pymupdf) and OCR (Tesseract via
     pytesseract). Page 1 is the clerk cover sheet — OCR page 2+.
  3. Field extraction: per-template regex over OCR text — "Commonly
     known as:" -> street address; grantor/borrower block -> debtor
     names; "CLERK'S FILE NO" -> original DoT document number; sale
     date/time/place; "Mortgage Servicer" -> lender. Handle both notice
     layouts; route-by-title.
  4. Translator: signal_type `foreclosure_notice`; EPCAD enrichment by
     **street address** (streetNumber + streetName) with the Fix-1
     token-overlap match guard — far higher yield than the name-only
     join used for clerk_recordings (the notice gives a real situs
     address; legal description gives a second join key).
  5. Aggregate into matched_lead; dedup per Fix 2.

  - Signal type: `foreclosure_notice`. Subtype optionally differentiated
    by notice title (substitute-trustee mortgage foreclosure vs other
    courthouse sales — the portal also covers tax sales / resales).
  - Refresh frequency: DAILY (notices file continuously ahead of the
    Texas first-Tuesday sale; rolling forward ~120-day window).
  - Estimated active record count: ~150–350 upcoming-sale notices at any
    time (102 in the 3-month sample; ~500+/year).
  - Estimated build time: ~4–6 hours — larger than the operator's
    "Path B ~2–3 h pdfplumber" estimate because OCR is required:
    Tesseract setup (local + a CI `apt-get install tesseract-ocr`
    step), PDF->image rendering, OCR, and multi-template field parsing.

### Risks

  - OCR field-parsing reliability: scans are clean (high expected
    accuracy) but ≥2 notice layouts exist and older notices may scan
    poorly; needs per-template regex + fallbacks + a review-queue path
    for low-confidence parses.
  - Per-document fetch cost: each PDF requires opening the InCaptureWeb
    viewer (signalR session) — ~3–5 s/document; 150–350 docs ≈ 10–30 min
    per refresh. Acceptable for a daily job.
  - Stable record ID: the listing instrument # is masked; a stable
    dedup key must come from OCR (cover-sheet receipt/document number or
    the notice T.S.#) or be derived from (sale_date + address).
  - Tesseract is a new dependency for the daily-refresh CI workflow.

## STEP 4 — Conclusion

The Phase 0 / v1 "DEFERRED_PENDING_BULK_ENRICHMENT_INDEX" classification
for foreclosure_notices is **INVALIDATED**. Its stated blocker — "rows
carry only legal description, no EPCAD join key, needs a bulk EPCAD
index" — does not hold: the notice PDFs carry a real **street address**,
so per-row EPCAD address-join works directly, no bulk index required.
foreclosure_notices IS buildable. The real remaining work is OCR of the
scanned notice PDFs — a build-effort item, not a buildability blocker.

FORECLOSURE_NOTICES RECON COMPLETE — BUILD PATH: B (PDF + OCR) — ESTIMATED ~150-350 ACTIVE RECORDS, ~4-6 HOUR BUILD TIME — AWAITING OPERATOR APPROVAL TO BUILD
