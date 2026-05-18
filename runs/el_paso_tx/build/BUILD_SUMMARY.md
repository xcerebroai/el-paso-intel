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

