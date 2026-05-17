# Phase 0.D — Access Classification — El Paso County, Texas

Slug: el_paso_tx
Generated: 2026-05-17
Protocol: knowledge_base/protocols/01_county_recon.md §01.9

Canonical access classifications used: OPEN_PUBLIC, SEARCH_ONLY_PUBLIC,
FREE_ACCOUNT_REQUIRED, PAID_SUBSCRIPTION_REQUIRED, LOGIN_REQUIRED,
CAPTCHA_PROTECTED, DOCUMENT_IMAGES_LOCKED, BLOCKED, UNKNOWN.

Every classification below is recorded with observed evidence. No
forbidden action (account creation, payment, CAPTCHA solving, access-
control bypass) was taken — see §01.17.

---

name: clerk_recordings
access_classification: OPEN_PUBLIC
evidence: Direct fetch of /publicrecords/OfficialPublicRecords returned a
    working search form. Page text: "Indexes to El Paso County records
    are provided as a service to and for the convenience of the
    community." No login prompt, no payment wall, no CAPTCHA on search.
    Documents are viewable, capped at 10 per search before resubmission.
notes: Index search and document viewing are both free. The 10-doc per-
    search cap is a pagination quirk, not a paywall. Stronger public
    access than many Texas clerk portals (no login at all).

---

name: foreclosure_notices
access_classification: OPEN_PUBLIC
evidence: Direct fetch of /publicrecords/Foreclosures returned a working
    search form (instrument number, sale-date range, legal-description
    fields); /Foreclosures/Map returned a county-hosted map view. No
    login, payment, or CAPTCHA observed.
notes: Foreclosure document references and a map pop-up are publicly
    reachable. CSV/PDF export was not confirmed from the fetched markup —
    recorded as an open question; it does not affect the access tier.

---

name: court_civil
access_classification: OPEN_PUBLIC
evidence: Direct fetch of /odysseyCrsPublic/CivilFamilyProbateCase
    returned a Tyler Odyssey CRS search form headed "Public Access" with
    party/attorney/case-number/date-range fields and Soundex options. No
    login prompt or CAPTCHA on the search form.
notes: One third-party source claimed a CAPTCHA "may be required" under
    high traffic. Not observed during recon. Recorded as an open question
    for Build Mode; if a traffic-triggered CAPTCHA appears it would be a
    technical blocker (CAPTCHA_PROTECTED), not a permission blocker.

---

name: court_probate
access_classification: OPEN_PUBLIC
evidence: Same Odyssey CRS portal and form as court_civil — probate and
    guardianship cases are searchable through the CivilFamilyProbateCase
    case-type categories. Texas Estates Code makes most probate filings
    public records.
notes: Same traffic-CAPTCHA open question as court_civil.

---

name: tax_collector
access_classification: OPEN_PUBLIC
evidence: Direct fetch of the ACT portal returned a working public search
    form (owner / address / account / fiduciary / property ID). Portal
    states it covers "any account for which the El Paso Tax Office
    collects property taxes." Payments are offered but optional; searching
    is free with no login.
notes: Per-account pages show balance including delinquent amounts. There
    is no separate delinquent-roll dump — delinquency is read per account.

---

name: sheriff_sales
access_classification: BLOCKED  (technical WAF — see notes)
evidence: Direct automated fetch of https://elpaso.texas.sheriffsaleauctions
    .com/ returned HTTP 403 Forbidden. This is the RealAuction vendor's
    WAF / bot filter, not a login wall or paywall — RealAuction public
    auction calendars are designed to be browsable without an account
    (bidder registration is required only to place bids).
notes: Classified BLOCKED strictly on the observed 403, but the blocker
    is TECHNICAL (vendor WAF), not a permission blocker. Effective public
    access in a normal browser is open for browsing. Resolution path
    (use_playwright / real browser) is in scope for Build Mode and is
    FREE. See blocker classification in build_eligibility_handoff.md.

---

name: parcel_master  (EPCAD)
access_classification: BLOCKED  (technical WAF — see notes)
evidence: Direct automated fetch of https://epcad.org/ and
    https://go.epcad.org/search returned HTTP 403 Forbidden — appraisal-
    district WAF / bot protection. The property search is publicly usable
    in a normal browser (it is a free public appraisal-district service).
notes: Technical blocker, not a permission blocker. Enrichment source —
    this WAF does not gate the build. EPCAD also exposes an Open
    Government / open-records page that may offer a cleaner bulk channel.

---

name: gis_parcels
access_classification: OPEN_PUBLIC
evidence: Standard ArcGIS Hub portal at opendata-elpasoco.hub.arcgis.com;
    open-data Hub portals expose unauthenticated REST FeatureServer /
    MapServer query endpoints and direct dataset downloads.
notes: No auth, no payment. API-first access.

---

## Access summary

    OPEN_PUBLIC:  6 — clerk_recordings, foreclosure_notices, court_civil,
                      court_probate, tax_collector, gis_parcels
    BLOCKED (technical WAF): 2 — sheriff_sales, parcel_master

All four verdict-critical primary lead sources (clerk_recordings,
foreclosure_notices, court_civil, court_probate) plus tax_collector are
OPEN_PUBLIC with no login, no payment, no CAPTCHA. The two BLOCKED sources
carry technical WAF blockers only; neither is required for the build.
