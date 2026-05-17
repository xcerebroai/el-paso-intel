# clerk_recordings — Portal Fingerprint (live, Step 1)

Source: clerk_recordings — El Paso County Clerk Official Public Records
URL: https://apps.epcountytx.gov/publicrecords/OfficialPublicRecords
Fingerprinted: 2026-05-17 (live Playwright probe)

## Portal architecture

- County-hosted ASP.NET application on the official .gov domain
  (`apps.epcountytx.gov/publicrecords/`). Same app family as the
  Foreclosures portal.
- Server-rendered HTML. Search form POSTs, results are server-rendered.
- reCAPTCHA **v3** (invisible, score-based) — `api.js?render=<sitekey>`,
  sitekey `6LfRwuUkAAAAAIZCe5AUWKd2brVg6VQPAycoYRVO`. Passes for a real
  browser; a Playwright Chromium session clears it with no solver.
  (Phase 0 recon recorded "no CAPTCHA" — corrected: it is reCAPTCHA v3.)

## Search form fields

    DocumentNumber   text    11-digit instrument number
    Name             text    grantor/grantee party name
    Subdivision      text
    Lot / Block / Unit / Track   text   legal-description parts (Track = Tract, sic)
    Book / Page      text
    Style            SELECT  document type — 254 options (the doc-type catalog)
    InstrumentDateFrom / InstrumentDateTo   text   mm/dd/yyyy date window
    g-recaptcha-response   hidden  reCAPTCHA v3 token (auto-filled by page JS)
    version          hidden
    #submit          submit button

## Search + results flow

- Submit: POST `/OfficialPublicRecords/OfficialPublicRecordsSearch`
  -> HTTP 302 -> GET `/OfficialPublicRecords/OfficialPublicRecordsSearchResults`
- Results page header: "<N> Records Found" (N capped at 500).
- Results table columns:
      Document #, Page Count, Date, Name, Name Type, Book, Page,
      Type, Style, Subdivision, Document(View-Document link)
- **One table row per (document x party-name).** A single recording with
  multiple parties produces multiple rows sharing one Document #. The
  scraper groups rows by Document # into one record.
- Document # is the **real** 11-digit instrument number (e.g.
  `20260005072` for a 2026 filing) — not a display artifact. No JS
  extraction needed for the instrument number.
- The "View Document" link is JS-driven (empty href); the real document
  reference is the Document # itself.
- Result rows carry NO street address and NO parcel id; Subdivision is
  frequently blank. Consequence: EPCAD enrichment for clerk_recordings
  must join primarily by party name (ownerName search) — lower
  confidence — per the build spec Step 4.

## Pagination

- 20 data rows per page.
- `GET /OfficialPublicRecordsSearchResults?page=N` returns page N
  directly (the result set is held server-side after the POST). Confirmed
  working by direct GET.
- Page count = ceil(records_found / 20). 500-record cap => max 25 pages.

## Observed sample

- Style=108 (LIS PENDENS), InstrumentDateFrom 01/01/2026, To 05/17/2026
  -> "118 Records Found", 6 pages.
- Style=16 (ABSTRACT OF JUDGMENT) with no date filter -> 500 (cap),
  oldest-first (1928) — confirms the date filter is mandatory to get
  current distress recordings.

## Anti-scrape / rate behavior

- No CAPTCHA challenge surfaced (v3 passed). No WAF block. No rate-limit
  response observed. Scraper uses a 15s inter-doc-type delay (polite).
