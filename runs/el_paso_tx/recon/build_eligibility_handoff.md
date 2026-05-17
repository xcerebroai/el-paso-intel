# Phase 0.G + Build Eligibility Gate Handoff — El Paso County, Texas

Slug: el_paso_tx
Generated: 2026-05-17
Protocol: knowledge_base/protocols/01_county_recon.md §01.13, §01.15, §01.16
Verdict enum: MASTER_PROMPT.md §4.10

---

## Counts

VERIFIED_OFFICIAL sources carried into the config: 8
    (clerk_recordings, foreclosure_notices, court_civil, court_probate,
     tax_collector, sheriff_sales, parcel_master, gis_parcels)
Verified-but-not-carried: 2 (Kofile QuickLink — REFERENCE_ONLY historic;
     Odyssey CRS Criminal — REJECTED_SOURCE, not a real-estate source)

By role:
    PRIMARY_LEAD_SOURCE     6  (clerk_recordings, foreclosure_notices,
                                court_civil, court_probate, tax_collector,
                                sheriff_sales)
    SUPPORTING_LEAD_SOURCE  0
    ENRICHMENT_SOURCE       2  (parcel_master, gis_parcels)

By access classification:
    OPEN_PUBLIC             6  (clerk_recordings, foreclosure_notices,
                                court_civil, court_probate, tax_collector,
                                gis_parcels)
    BLOCKED (technical WAF) 2  (sheriff_sales, parcel_master)

## Accessible primary sources count

5 of 6 PRIMARY_LEAD_SOURCEs are OPEN_PUBLIC and immediately buildable
without operator escalation: clerk_recordings, foreclosure_notices,
court_civil, court_probate, tax_collector.

The 6th primary (sheriff_sales) is BLOCKED at the access layer by a
technical vendor WAF — not a permission blocker.

## Accessible primary document types

From document_type_discovery.md, the five accessible primary sources
cover the canonical primary spread:
    foreclosure  — NOTICE_OF_SUBSTITUTE_TRUSTEE_SALE, TAX_FORECLOSURE_
                   NOTICE, LIS_PENDENS, FINAL_JUDGMENT_OF_FORECLOSURE
    tax          — delinquent tax balance signal, FEDERAL/STATE_TAX_LIEN,
                   TAX_SALE_CERTIFICATE
    lien         — MECHANICS/CONSTRUCTION/JUDGMENT/HOA/HOSPITAL_LIEN
    estate       — LETTERS_OF_ADMINISTRATION, LETTERS_TESTAMENTARY,
                   DETERMINATION_OF_HEIRSHIP, AFFIDAVIT_OF_HEIRSHIP
    divorce      — DIVORCE_FILING, MARITAL_PROPERTY_DIVISION
    transfer     — QUITCLAIM_DEED (lead-generating sub-type)

## Phase 0.5 — Blocker classification and auto-resolve

Two sources were carried into Phase 0.5. Neither is verdict-critical.

sheriff_sales
    blocker: RealAuction vendor WAF / bot filter — HTTP 403 to automated
        fetch of elpaso.texas.sheriffsaleauctions.com.
    blocker_type: TECHNICAL (not a login wall, not a paywall, not a
        CAPTCHA gate; RealAuction public auction calendars are designed
        to be browsable without an account).
    auto-resolve attempts:
        1. find_official_vendor_link — SUCCESS. The county-contracted
           RealAuction URL is confirmed and officially announced by the
           Sheriff's Office; no homepage-to-portal substitution needed.
        2. use_playwright — DEFERRED. Rendering past the WAF requires a
           real browser. That is a Build-Mode portal-fingerprinting /
           scraper task and is explicitly out of scope for this Phase 0
           Recon-Mode run (LAUNCH_EL_PASO_TX.md). Estimated cost: FREE
           (no solver, no proxy, no credentials) — so no operator
           approval is required to attempt it later.
    auto_resolve_status: PARTIALLY_RESOLVED (official endpoint confirmed;
        WAF render deferred to Build Mode).
    final_resolution_status: PARTIALLY_RESOLVED.

parcel_master (EPCAD)
    blocker: EPCAD WAF / bot protection — HTTP 403 to automated fetch of
        epcad.org and go.epcad.org/search.
    blocker_type: TECHNICAL.
    auto-resolve attempts:
        1. find_official_vendor_link — SUCCESS. epcad.org is the official
           appraisal-district domain; the search path is confirmed.
        2. use_playwright — DEFERRED to Build Mode (FREE). EPCAD also
           publishes an Open Government / open-records channel that may
           yield a cleaner bulk path; to evaluate in Build Mode.
    auto_resolve_status: PARTIALLY_RESOLVED.
    final_resolution_status: PARTIALLY_RESOLVED.

County-level Phase 0.5 outcome:
    auto_resolve_status: PARTIALLY_RESOLVED
    final_resolution_status: PARTIALLY_RESOLVED
    Both residual blockers are TECHNICAL and FREE to clear with a real
    browser in Build Mode. Neither blocks the verdict, because the five
    verdict-critical primary sources were never blocked.

## Recommended provisional verdict

READY_TO_BUILD

Justification: §4.10 READY_TO_BUILD requires at least one verified
PRIMARY_LEAD_SOURCE accessible at HIGH/MEDIUM confidence with
sample_search_possible true, plus at least one enrichment source. El Paso
County clears this several times over — five HIGH-confidence primary lead
sources are OPEN_PUBLIC, free, and login-free, and two enrichment sources
are verified. The verdict is plain READY_TO_BUILD rather than
AUTO_RESOLVED_READY_TO_BUILD because the verdict-critical sources were
directly buildable from Phase 0; Phase 0.5 only touched two non-critical
sources.

## Justification trail (per source)

clerk_recordings    PRIMARY  OPEN_PUBLIC  HIGH   → counts toward verdict.
                    County Clerk Official Public Records, county .gov
                    host, free search + document viewing, no login.
foreclosure_notices PRIMARY  OPEN_PUBLIC  HIGH   → counts toward verdict
                    and is the cleanest P0 anchor. County Clerk
                    foreclosure search + map, free, official.
court_civil         PRIMARY  OPEN_PUBLIC  HIGH   → counts. Odyssey CRS
                    public case search, county .gov host, free.
court_probate       PRIMARY  OPEN_PUBLIC  HIGH   → counts. Same Odyssey
                    CRS portal; probate / estate case types.
tax_collector       PRIMARY  OPEN_PUBLIC  HIGH   → counts. El Paso
                    Consolidated Tax Office (ACT), free per-account
                    search exposing delinquent balances.
sheriff_sales       PRIMARY  BLOCKED(WAF) MEDIUM → does NOT count toward
                    the verdict; technical WAF blocker, Build-Mode
                    resolvable, FREE. Additive when cleared.
parcel_master       ENRICH   BLOCKED(WAF) MEDIUM → enrichment; technical
                    WAF, Build-Mode resolvable, FREE.
gis_parcels         ENRICH   OPEN_PUBLIC  HIGH   → satisfies the
                    enrichment-availability half of READY_TO_BUILD.

## Do Not Proceed Matrix (§4.11) — check

    1. No clerk/recorder source found ............... NO  (verified)
    2. No primary lead source verified .............. NO  (6 verified)
    3. Only enrichment sources found ................ NO
    4. All P0 sources blocked ....................... NO  (5 P0 open)
    5. County config fails schema validation ........ checked in Step 4
    6. Portal proof missing for required P0 sources . NO
    7. Dashboard would contain zero event leads ..... NO
    8. Only parcel/GIS/CAD data available ........... NO
    9. Paid/login required, no operator credential .. NO  (no paid/login
       on any primary source)
   10. Cannot verify public access to records ....... NO
   11. No P0 source reached HIGH/MEDIUM confidence ... NO  (5 at HIGH)
    No Do Not Proceed condition fires.

## P0 gate

GATE PASS. At least one P0 daily-refresh distress source is unblocked and
free: foreclosure_notices and clerk_recordings are both OPEN_PUBLIC,
county-published, and continuously updated. The P0 gate is satisfied
without any unblock plan.

## Recommended operator next actions

1. Approve entry into Build Mode for El Paso County.
2. Recommended MVP-first source: foreclosure_notices — county-published,
   fully open foreclosure feed with a companion map; mirrors the Bexar
   foreclosure_notices_map build that anchored that county's MVP.
3. In Build-Mode portal fingerprinting: enumerate the document-type
   dropdown on clerk_recordings and the Odyssey CRS case-type categories;
   confirm CSV/PDF export on the foreclosure portal; confirm whether the
   Odyssey CRS traffic-triggered CAPTCHA ever fires.
4. Plan a real-browser (Playwright) adapter for sheriff_sales and EPCAD
   parcel_master to clear the vendor WAFs — FREE, no operator action
   needed, additive coverage.
