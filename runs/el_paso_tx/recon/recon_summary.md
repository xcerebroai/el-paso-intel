# Recon Summary — El Paso County, Texas

Slug: el_paso_tx
Generated: 2026-05-17
Framework: v5.1.2-beta-r3
Protocol: knowledge_base/protocols/01_county_recon.md

## Build Eligibility Gate verdict

    BUILD VERDICT: READY_TO_BUILD

El Paso County, Texas is buildable. Five verified primary lead sources are
fully public, free, and login-free; two enrichment sources are verified;
the P0 daily-refresh gate is satisfied. No Do Not Proceed condition fires.

## What was found

El Paso County exposes an unusually clean public-records surface. The
County Clerk runs its own record applications on the official county .gov
domain (apps.epcountytx.gov) with no login wall:

  - Official Public Records (deeds, deeds of trust, liens, judgments,
    lis pendens) — OPEN_PUBLIC, free search and document viewing.
  - Foreclosures search + map (substitute-trustee sales, tax-foreclosure
    sales, resales) — OPEN_PUBLIC, county-published. This is the cleanest
    P0 anchor and the recommended MVP-first source.

Court records are on a county-hosted Tyler Odyssey CRS public portal —
civil, family, and probate / guardianship cases in one search, plus
criminal (excluded as not a real-estate source). OPEN_PUBLIC, free.

Property tax runs through the El Paso Consolidated Tax Office on an ACT
vendor portal — free per-account search exposing delinquent balances.

Two sources sit behind technical vendor WAFs that returned HTTP 403 to
automated recon fetches:
  - sheriff_sales — the county's RealAuction online tax-foreclosure sale
    site (a primary lead source; not verdict-critical).
  - parcel_master — El Paso Central Appraisal District search (enrichment).
Both WAFs are technical, not permission blockers; both are FREE to clear
with a real browser (Playwright) in Build Mode. Neither gates the build.

Enrichment is covered: EPCAD parcel master and the El Paso County GIS Open
Data portal (ArcGIS Hub, open REST APIs).

## Recon detail (4-space note)

    Time zone: El Paso County is on Mountain Time (America/Denver) — one
        of only two Texas counties not on Central Time. Carried into the
        county config; affects every cadence and sale-date calculation.
    County domain migrated epcounty.com -> epcountytx.gov. Several legacy
        epcounty.com links now 404; epcountytx.gov is authoritative.
    Wrong-county trap avoided: "El Paso public trustee" and
        treasurer.elpasoco.com results belong to El Paso County,
        COLORADO. Texas has no public trustee — foreclosure notices are
        filed with the County Clerk. Those results were discarded.

## Source ledger

    clerk_recordings     PRIMARY  P0  OPEN_PUBLIC  HIGH    build target
    foreclosure_notices  PRIMARY  P0  OPEN_PUBLIC  HIGH    MVP-first
    court_civil          PRIMARY  P0  OPEN_PUBLIC  HIGH    build target
    court_probate        PRIMARY  P0  OPEN_PUBLIC  HIGH    build target
    tax_collector        PRIMARY  P0  OPEN_PUBLIC  HIGH    build target
    sheriff_sales        PRIMARY  P1  BLOCKED-WAF  MEDIUM  Build-Mode unblock
    parcel_master        ENRICH   P2  BLOCKED-WAF  MEDIUM  Build-Mode unblock
    gis_parcels          ENRICH   P2  OPEN_PUBLIC  HIGH    enrichment

## Verdict reasoning

READY_TO_BUILD per MASTER_PROMPT.md §4.10: at least one verified
PRIMARY_LEAD_SOURCE accessible at HIGH/MEDIUM confidence with search
possible (here, five), plus enrichment available (two). P0 gate satisfied
by foreclosure_notices and clerk_recordings. Phase 0.5 ran on the two
WAF-blocked sources, classified both as technical and FREE-to-resolve, and
deferred the real-browser render to Build Mode; the verdict is plain
READY_TO_BUILD because the five verdict-critical sources were never
blocked. Full justification trail in build_eligibility_handoff.md.

## Next phase

Verdict is READY_TO_BUILD → the protocol hands off to the Build Mode
Approval Gate (MASTER_PROMPT.md §4.15). Build Mode does NOT start without
explicit operator approval. Recommended next action: approve Build Mode
and build foreclosure_notices first as the MVP source.

## Artifacts in this recon dossier

    source_discovery.md
    source_verification.md
    portal_fingerprints.md
    access_classification.md
    source_role_classification.md
    document_type_discovery.md
    build_eligibility_handoff.md
    recon_summary.md   (this file)

Companion: config/counties/el_paso_tx.json (the populated, schema-valid
county config) and runs/el_paso_tx/operator_notes.md.
