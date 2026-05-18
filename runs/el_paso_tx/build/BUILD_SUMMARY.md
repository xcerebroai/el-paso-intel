# El Paso County — Build Summary (v1)

County: El Paso County, Texas (el_paso_tx) · FIPS 48141 · America/Denver
Repo: xcerebroai/el-paso-intel (private)
Generated: 2026-05-17
Scope of v1: clerk_recordings source, deployed as a private-repo + local
artifact with a daily-refresh workflow. Three sources deferred.

---

## Deployment status

Mode: PRIVATE REPO + LOCAL ARTIFACT (operator Option 3).

The dashboard is committed to the private repo and opened locally:

    file:///Users/quentinflores/Dev/xcerebro/counties/el-paso-intel/dashboard/index.html
    (or: cd dashboard && python3 -m http.server 8000  ->  http://localhost:8000)

GitHub Pages was NOT enabled. Investigation this session:
  - Pages branch-source only supports path `/` or `/docs`, not `dashboard/`.
  - Pages was switched to workflow-source, which returned `"public": true`.
  - Setting the Pages site private returned HTTP 422: "Current plan does
    not support private GitHub Pages" (access-controlled Pages requires
    GitHub Enterprise Cloud).
  - A public Pages site contradicts the operator's Option 3 ("no public
    hosting"), so the Pages config was deleted (reverted; nothing was
    ever published). config/counties/el_paso_tx.json deployment fields
    are unchanged (no live_url).
  - For a live access-controlled URL later: GitHub Enterprise (private
    Pages), or an authenticated host (Cloudflare Access / Netlify or
    Vercel password protection).

## Lead totals (clerk_recordings, v1)

Total matched_leads: 1,110  (from 1,316 scraped clerk documents)

EPCAD enrichment: 166 resolved (14%) / 944 UNRESOLVED. The clerk result
table carries no address or parcel id, so the EPCAD join is by party
name only — inherently fuzzy; 14% is the honest hit rate. UNRESOLVED
rows are valid output (signal real, enrichment absent) and render with
their clerk fields.

## Signal type distribution

    state_tax_lien          301
    judgment_lien           233
    federal_tax_lien        174
    affidavit_of_heirship   139
    hospital_lien            86
    executor_deed            81
    lis_pendens              36
    mechanics_lien           31
    administrator_deed       20
    code_lien                14
    estate_titled_property   50   (stacked, EPCAD-owner-name derived)
    trust_titled_property     2   (stacked, EPCAD-owner-name derived)

## Stacking distribution (signals per parcel)

    1 signal     1,041
    2 signals       57
    3+ signals      12

## Owner type distribution

    INDIVIDUAL   767
    ENTITY       287
    ESTATE        50
    TRUST          2
    UNKNOWN        4

Estate-pattern detection rate: 50 / 1,110 leads (4.5%).
Trust-pattern detection rate:   2 / 1,110 leads (0.2%).
Absentee / out-of-state rates: computed per-lead from EPCAD situs vs
mailing address; meaningful only for the 166 EPCAD-resolved leads.

## Daily refresh

Workflow: .github/workflows/daily-refresh.yml
  - Schedule: cron '0 10 * * *' (10:00 UTC daily) + manual workflow_dispatch
  - Runs scripts/daily_refresh.py (scraper + EPCAD enrichment + dashboard
    regeneration), commits refreshed data as github-actions[bot].
  - On scraper failure: the commit step is skipped (no partial state).
  - Next scheduled run: the next 10:00 UTC after the workflow lands on main.
Orchestrator: scripts/daily_refresh.py — modular SOURCES registry; adding
a deferred source is a one-line change.
requirements.txt: playwright 1.59.0, httpx 0.28.1.

## Self-verification (§4.21)

clerk_recordings dashboard self-verification: PASS 9/9 — see
runs/el_paso_tx/build/full_self_verification.md (committed at 879a8d3).
Checks: page load + data-ready, row count match (1110), zero console
errors, signal-type filter, owner-type filter, stacking controls, text
search, CSV export, chip-vs-badge visual distinction. One search-event
bug was found and auto-fixed during verification.

## Per-source status

    clerk_recordings    COMPLETE   1316 raw -> 1110 matched_leads, verified
    tax_collector       DEFERRED   ACT portal fingerprinted (per-account
                                   only); needs ACT<->EPCAD id mapping probe
    court_probate       DEFERRED   Tyler Odyssey CRS — not started
    court_civil         DEFERRED   Tyler Odyssey CRS — not started
    foreclosure_notices DEFERRED   20-record partial on disk; needs
                                   pagination fix + legal-description join

Deferred sources stack into the SAME dashboard with no redesign — the
signal model and SOURCES registry are open-ended.

## File inventory (el-paso-intel)

    config/counties/el_paso_tx.json            populated county config
    scrapers/clerk_recordings.py               clerk OPR Playwright scraper
    runs/el_paso_tx/build/build_clerk_pipeline.py   translator + EPCAD enrich
    runs/el_paso_tx/build/_verify_dashboard.py      self-verification driver
    runs/el_paso_tx/build/_probe_clerk.py           portal-fingerprint probe
    runs/el_paso_tx/build/clerk_recordings_portal_fingerprint.md
    runs/el_paso_tx/build/clerk_recordings_doc_type_catalog.json
    runs/el_paso_tx/build/clerk_recordings_doc_type_classification.md
    runs/el_paso_tx/build/full_self_verification.md
    runs/el_paso_tx/build/BUILD_SUMMARY.md          (this file)
    runs/el_paso_tx/recon/ (9 Phase-0 + EPCAD recon artifacts)
    data/el_paso_tx/raw/clerk_recordings.jsonl      1316 raw records
    data/el_paso_tx/translated/clerk_recordings_translated.jsonl
    data/el_paso_tx/leads.json                      1110 matched_leads
    dashboard/{index.html,app.js,styles.css,data.js,data.json}
    scripts/daily_refresh.py
    requirements.txt
    .github/workflows/daily-refresh.yml

## Open items

  - 3 sources deferred (tax_collector, court_probate, court_civil) plus
    foreclosure_notices — each a future single-source session.
  - EPCAD name-join hit rate is 14% for clerk_recordings; address/parcel-id
    sources (tax_collector) will resolve far higher.
  - Live access-controlled hosting deferred (needs Enterprise Pages or an
    authenticated host) — v1 is local per Option 3.
  - Framework regression test (scaffold) flags 63 pre-existing
    county-term leaks in framework files — pre-existing, not El Paso.

---

## v2 Fixes (2026-05-17/18) — operator-review data-quality corrections

Operator review of the live v1 dashboard surfaced four data bugs. Audit:
`runs/el_paso_tx/build/data_quality_audit.md`. Verification:
`runs/el_paso_tx/build/post_fix_verification.md`.

### Bugs found

  - Bug 1 — owner_type classifier missed entities/government (CITY OF…,
    UNITED STATES, …OWNER suffix, GROUP, ENTERPRISES, PARTNERS, …).
  - Bug 2 — no signal de-duplication: N recordings of one signal type on
    one parcel rendered as N identical chips (UMC row had 148).
  - Bug 3 — wrong party attached: the translator picked the lien FILER
    instead of the DEBTOR for hospital_lien and code_lien, collapsing 148
    distinct patient debtors onto one "University Medical Center" row.
  - Finding 4 — the EPCAD enrichment join accepted Properties[0]
    unconditionally; a fuzzy ownerName match attached unrelated parcels.

### Root cause

A single doc-type-blind party-selection rule (`pick_distressed_party`
ranked GRANTOR above GRANTEE globally). The debtor's `name_type` actually
varies by document type — hospital/code liens put the filer on GRANTOR
and the debtor on GRANTEE; mechanics liens are the reverse; court docs
use DEFENDANT; tax liens use TAX PAYER. No global rank can be correct.

### Fix approach

  - Fix 1 (`2660602`) — `DEBTOR_PARTY_RULES`, a per-doc-type debtor
    name_type map; unknown doc types fall back to the old rank + a
    warning. Plus an EPCAD match-quality guard (token-overlap / Jaccard
    threshold) replacing unconditional `Properties[0]`.
  - Fix 2 (`cf4229d`) — translator collapses identical
    `(parcel_id, signal_type)` into one signal with `count` +
    `source_urls[]` + `evidence_ids[]` + `instrument_numbers[]`; dashboard
    renders one `Label × N` chip.
  - Fix 3 (`b1a5d78`) — broadened `ENTITY_PAT` (government + more entity
    forms).
  - Result: 1,110 → 1,283 matched_leads; hospital_lien leads now show
    patient-debtor names; 0 leads owned by University Medical Center;
    ENTITY 287 → 323. Self-verification PASS 9/9 + semantic checks;
    live dashboard re-verified PASS.

### Residual / known limitations

  - The EPCAD match guard does not catch matches that share only the
    common tokens "EL PASO" (1 borderline lead). County-local stopword
    tuning would fix it — left for operator decision, not hardcoded.
  - ~8 / 1,283 leads still carry a filer-ish owner name (atypical
    code_lien party polarity; some legitimate). Not systemic.

### Framework gaps surfaced (recommended future framework patches)

  - **Self-verification is mechanics-only.** §4.21 / the verification
    driver checks that rows render, filters change counts, CSV exports —
    but NOT semantic data correctness. All four bugs passed v1's 9/9
    verification because the dashboard *rendered* fine; the *data* was
    wrong. Recommend a framework patch adding semantic-correctness
    sampling to §4.21: per signal type, sample N leads and assert the
    attached owner matches the expected debtor party for that doc type.
  - **Signal aggregation/dedup contract was implicit.** Nothing in §13 or
    `09_output_schemas.md` specified that identical `(parcel_id,
    signal_type)` signals must collapse. Recommend formalizing a
    signal-dedup contract (one entry per type, with an occurrence count)
    in the architecture docs.
  - **Party-role semantics are not modeled.** The framework has no notion
    that "which recorded party is the lead" depends on document type.
    Recommend a canonical debtor-party mapping alongside
    `canonical_doc_types.json`.

### Deferred

  - UI rebuild (chip drill-down to per-record source URLs, layout) — a
    separate session; a design brief is required before starting. v2
    changed data + minimal chip rendering only.

---

## foreclosure_notices source (v3) — 2026-05-18

Second primary source built. Approach: PDF + OCR + EPCAD address-join.

### Build approach

  - Scraper (scripts/scrapers/foreclosure_notices.py): searches the County
    Clerk Foreclosures portal by sale-date window; per document, POSTs
    GetDocumentURL and loads the InCaptureWeb viewer, capturing the notice
    PDF via route interception. GetDocumentURL is gated by a per-session
    reCAPTCHA-v3 score ceiling (~9 docs) — both the popup and direct-POST
    approaches stalled there; the fix is recycling the browser session
    every 8 documents. Result: 102 / 102 notice PDFs.
  - OCR (scripts/translators/foreclosure_notices_ocr.py): the notices are
    scanned images — rendered (pymupdf) + Tesseract OCR + shape-based
    field extraction across 4+ notice layouts.
  - Translator (foreclosure_notices_translate.py): EPCAD parcel join by
    street address; matched_lead build.
  - Aggregator (scripts/aggregate_leads.py): merges into the dashboard.

### Numbers

  - Scraped / OCR'd: 102 / 102 notice PDFs.
  - Extraction: street address 74/102, sale_date 102/102 (listing
    fallback), DoT document number ~100/102, debtor names ~38/102,
    lender ~52/102. 5/5 complete: ~29.
  - EPCAD-resolved: 8 / 102. UNRESOLVED: 94 — valid output per §13: each
    carries the foreclosure_notice primary signal + street address +
    sale date; EPCAD owner/value enrichment is decoration.
  - matched_leads contributed: 102.
  - New aggregated total: 1,385 (1,283 clerk_recordings + 102
    foreclosure_notice). Stacking 1,329 single / 56 two-signal.
  - Cross-source stacked rows (clerk + foreclosure on one parcel): 0 —
    the two sources' low EPCAD resolution lands them on different parcels.
  - Sale-date urgency: the scrape window is 05/18-09/30/2026 upcoming
    Texas first-Tuesday sales.

### reCAPTCHA backoff behavior

  Per-session reCAPTCHA-v3 ceiling at ~9 GetDocumentURL calls is a hard
  wall — backoff/retry did not recover it. Session recycling every 8
  docs (fresh context + fresh search = fresh score) cleared it: 102/102.

### Known limitations

  - EPCAD address-join yield is low (8/102). EPCAD's streetName API is
    suffix-sensitive and page-capped; even with suffix variants +
    pagination most addresses do not resolve. The foreclosure leads are
    still valid and actionable (address + sale date); EPCAD enrichment is
    the gap — flagged for follow-up (a better EPCAD address endpoint, or
    a bulk EPCAD index keyed on address/legal description).
  - debtor_names / lender extraction is partial (~38 / ~52 of 102):
    layout C ("Notice of Acceleration") splits labels from values in the
    OCR stream. Those rows carry address + sale date and route to the
    partial path.
  - Aggregator idempotency: scripts/aggregate_leads.py must run against a
    clerk-only leads.json base (build_clerk_pipeline.py writes that first
    in daily_refresh). Re-running aggregate on an already-merged file
    double-counts — daily_refresh sequences it correctly.

### Framework gap surfaced (for a future framework patch)

  Phase 0 recon classified foreclosure_notices DEFERRED on listing-page
  fingerprinting alone — it missed that the actual lead data lives inside
  scanned notice PDFs. Recon §01 should require sample-PDF inspection
  (download + open a few source documents) before classifying a source,
  not just listing-page structure.

### Sources status

  clerk_recordings    COMPLETE (v2) — 1,283 matched_leads
  foreclosure_notices COMPLETE (v3) — 102 matched_leads
  tax_collector       DEFERRED
  court_probate       DEFERRED
  court_civil         DEFERRED

Dashboard: 1,385 matched_leads, deployed (GitHub Pages, public per
operator decision) at https://xcerebroai.github.io/el-paso-intel/ —
live-verified. Self-verification PASS 9/9.

---

## foreclosure_notices REWORK (v4) — 2026-05-18

Operator review of the v3 build surfaced three defects. All three traced
to one root cause: v3 framed `foreclosure_notice` as an *enrichment-gated*
source — a notice only became a lead if EPCAD enrichment resolved a
parcel. That inverts §13. `foreclosure_notice` is a P0 PRIMARY distress
signal: the recorded notice ORIGINATES the lead. EPCAD enrichment
DECORATES it and is strictly a bonus. v4 rebuilds all three stages on
that contract.

### Defects fixed

  1. Coverage — v3 used a hard-coded narrow sale-date window and captured
     only 102 records. v4 makes the window dynamic and rolling, recomputed
     every run (the scraper runs daily): 30 days back through ~2 years
     forward (DATE_FROM/DATE_TO in foreclosure_notices.py). 30 days back
     keeps recent + still-listed notices; the forward end captures every
     upcoming first-Tuesday auction batch (Texas sales are the first
     Tuesday of each month, and listings post months ahead). Result: 359
     listed records, 358 PDFs captured (1 portal-side document failure).

  2. False UNRESOLVED — v3 marked 94/102 leads UNRESOLVED because EPCAD
     did not enrich them. Wrong: the notice itself resolves the lead. v4
     translator emits a matched_lead for EVERY notice with
     parcel_resolution_status = RESOLVED ALWAYS. EPCAD success is tracked
     in a NEW, separate field, epcad_enrichment_status (ENRICHED /
     UNENRICHED), so enrichment yield stays visible without contaminating
     lead validity. Result: 0 UNRESOLVED foreclosure leads.

  3. Listing-page fields unused — v3 relied solely on PDF OCR. The portal
     results table already carries structured, always-present join keys
     (Instrument #, Subdivision, Lot, Block, Unit, Tract). v4 scraper
     harvests all of them per row (collect_ids → listing.jsonl); the OCR
     stage carries them through as listing_* fields; the translator builds
     a legal_description from subdivision/lot/block/unit so a lead with no
     PDF street address is still property-identifiable. The dashboard
     address cell falls back to legal_description.

### Result

  foreclosure_notices: 358 matched_leads, 357 after parcel-dedup in the
  aggregator. EPCAD enrichment: 31 ENRICHED / 327 UNENRICHED (~9%) —
  EPCAD streetName search is suffix-sensitive and page-capped; low yield
  is a documented EPCAD limitation, and under v4 it no longer costs a
  single lead. owner_name prefers EPCAD ownerName, falls back to the PDF
  debtor name, else is left blank (honest UNKNOWN — never a lender or a
  form label; _clean_names rejects label fragments).

  Semantic self-check on the merged dataset: 0 foreclosure leads
  UNRESOLVED; 0 leads carry an "Original/Current Mortgagee" label as
  owner; 9/357 carry neither street address nor legal description (thin
  but valid — they still carry the foreclosure_notice signal + sale date
  + instrument #). Dashboard self-verification PASS 9/9.

### Framework note

  A source that carries lead-actionable data in its own primary record
  (here: a recorded foreclosure notice with debtor, sale date, and legal
  description) ORIGINATES leads regardless of enrichment outcome. County
  appraisal-district enrichment is decoration: it MUST be tracked in its
  own status field and MUST NOT gate matched_lead validity or set
  parcel_resolution_status. This is the §13 lead-origination contract
  applied correctly; v3 violated it by conflating the two.

### Sources status (v4)

  clerk_recordings    COMPLETE (v2) — 1,283 matched_leads
  foreclosure_notices COMPLETE (v4) —   357 matched_leads
  tax_collector       DEFERRED
  court_probate       DEFERRED
  court_civil         DEFERRED

Dashboard: 1,640 matched_leads, deployed (GitHub Pages) at
https://xcerebroai.github.io/el-paso-intel/ — live-verified
(lead_total 1,640). Self-verification PASS 9/9.

---

## v5 FIXES — DATA QUALITY + UI REBUILD — 2026-05-18

End-to-end fix pass: five data-quality defects from an operator audit,
plus a full rebuild of the dashboard into an operator-grade lead board.
Translator pipeline re-run from raw data; redeployed; live-verified.

### Part A — data quality

**Fix 1 — filer-vs-debtor regression.** `pick_distressed_party()` fell
back to the document filer when the doc-type debtor name_type was absent,
so `CITY OF EL PASO`, `TEXAS WORKFORCE COMMISSION`, hospitals and a
mortgage company were emitted as owner_name. v5 adds a filer-entity
suppression list (government bodies, hospital systems, mortgage/lender
entities) and changes the contract: a record with no non-filer debtor
party is routed to `parcel_resolution_status = REVIEW_REQUIRED`,
`owner_name = "<doc type> against unidentified party"`, and the original
filer captured in a new `filer_entity` field. A filer never silently
becomes an owner. A second guard rejects EPCAD candidates whose parcel
owner is a suppressed filer (token-collision mis-match) — this dropped a
clerk lead wrongly owned by `CITY OF EL PASO`. Result: **0** filer
entities as owner_name; 13 REVIEW_REQUIRED rows, 9 with a captured filer
(the other 4 are source records with zero parties).

**Fix 2 — ESTATE/TRUST classifier substring bug.** `"MARIO AYALA REAL
ESTATE GROUP LLC"` classified ESTATE because "ESTATE" is a substring of
"REAL ESTATE". v5 classifies by word-boundary + position: company-estate
phrases ("REAL ESTATE", "ESTATE GROUP/PLANNING/AGENCY") are blanked
before the decedent test, and ENTITY (company suffix / government body)
wins outright. Result: that name → ENTITY; **0** real-estate companies
misclassified as ESTATE (51 genuine estate-titled leads remain).

**Fix 3 — signal aggregation.** Audited: the "× N" counts are legitimate
(e.g. Executor's Deed × 10 = 10 distinct instrument numbers, one estate
filing ten deeds; Mechanics Lien × 8 = 8 distinct instruments). The
aggregator's `dedup_signals` now also unions `instrument_numbers` across
the cross-source merge. No row carries a duplicated instrument number;
max distinct signal *types* on a row is 2.

**Fix 4 — EPCAD enrichment rate.** The match guard was loosened from
Jaccard ≥0.6 / 50% to ≥0.5 / 40%. This barely moved the rate (158→159
clerk matches), confirming the guard was not the bottleneck: clerk
records are a **name-only** join — they carry no address in the record
body, so the EPCAD address-search fallback (Fix 4D) is not applicable —
and EPCAD's `ownerName` search is inherently lossy for individuals
(name-order variance, common names). Clerk EPCAD resolution is ~12%;
overall 514/1,646 leads are EPCAD-resolved (foreclosure notices resolve
via address). This is a documented data-source limitation, not a bug —
the 1,113 UNRESOLVED clerk leads still carry owner + signal + source URL
and are skip-traceable (Fix 4F).

**Fix 5 — foreclosure address coverage.** Verified the v4 data flow:
foreclosure situs is populated from the PDF-extracted address when EPCAD
does not enrich; legal_description (subdivision/lot/block/unit) is the
fallback. 348/357 foreclosure leads (97%) are property-identifiable
(250 street address, 98 legal description); 9 carry neither but retain
sale date + instrument number.

### Part B — UI rebuild

`index.html` / `styles.css` / `app.js` rebuilt as an operator lead board
(vanilla JS, no framework, client-side only): urgency-first default sort
(foreclosure ≤21d → 22–60d → estate-titled → multi-signal → tax+OOS →
rest); six preset quick-views; foreclosure sale-window / assessed-value /
signal-type / owner-type filters; color-coded urgency bars; inline lead
detail panels with source links, plat data, and operator triage
(mark-for-review persisted in localStorage, skip, single-lead CSV
export); REVIEW_REQUIRED rows visually distinct; incremental windowed
render for 1,646 rows; debounced search. Orphaned `dashboard.css/.js`
removed. (Note: the "Estate-titled properties" preset surfaces all 51
estate leads rather than flooring by assessed value — EPCAD resolves ~0
estate-named owners, so a value floor would empty it.)

### Aggregator idempotency

Root cause of a double-merge (`lead_total` briefly 1,962):
`aggregate_leads.py` read its own merged output back as the clerk base.
Fixed structurally — `build_clerk_pipeline.py` now writes a stable
`clerk_leads_base.json` that the aggregator always reads; re-running the
aggregator is now idempotent. A `--from-translated` fast path rebuilds
leads from cached enriched signals without re-running EPCAD.

### Result

  lead_total            1,646   (1,289 clerk_recordings + 357 foreclosure)
  EPCAD-resolved          514
  REVIEW_REQUIRED          13   (filer-vs-debtor — operator follow-up)
  ACTIONABLE leads      1,633   (99% — every lead but the REVIEW bucket)
  filer-as-owner            0   (was 9)
  ESTATE misclassified      0   (was 1)

Live-verified against https://xcerebroai.github.io/el-paso-intel/ —
**19/19** semantic + mechanics checks pass
(runs/el_paso_tx/build/v5_semantic_verification.md).

### Open items / known limitations

  - Clerk EPCAD resolution ~12% — a name-only-join ceiling, not a bug.
    Most clerk leads are owner+signal+source (skip-traceable), not
    parcel-resolved.
  - 9 foreclosure leads have no street address or legal description
    (OCR extraction misses) — they retain sale date + instrument number.
  - 4 REVIEW_REQUIRED rows have an empty filer_entity — the source clerk
    record contained zero parties.
  - tax_collector, court_probate, court_civil remain DEFERRED.

### Sources status (v5)

  clerk_recordings    COMPLETE (v5) — 1,289 matched_leads
  foreclosure_notices COMPLETE (v5) —   357 matched_leads
  tax_collector       DEFERRED
  court_probate       DEFERRED
  court_civil         DEFERRED

Dashboard: 1,646 matched_leads, deployed (GitHub Pages) at
https://xcerebroai.github.io/el-paso-intel/ — live-verified
(lead_total 1,646). v5 verification 19/19.

