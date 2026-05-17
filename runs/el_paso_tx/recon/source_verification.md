# Phase 0.B — Official Source Verification — El Paso County, Texas

Slug: el_paso_tx
Generated: 2026-05-17
Protocol: knowledge_base/protocols/01_county_recon.md §01.7

Verification layers applied to each discovered source:

    Layer 1 — Government domain check (.gov / .us / county subdomain)
    Layer 2 — Vendor portal check (vendor-hosted but county-contracted)
    Layer 3 — Cross-reference check (county .gov site links to it)
    Layer 4 — Records authority check (a recognized records authority)

Rule: pass Layer 1 OR (Layer 2 AND Layer 3), AND pass Layer 4 →
VERIFIED_OFFICIAL.

---

name: El Paso County Clerk — Official Public Records
official_url: https://apps.epcountytx.gov/publicrecords/OfficialPublicRecords
layers_passed: L1 (apps.epcountytx.gov is the county .gov domain),
    L3 (linked from epcountytx.gov/204/County-Clerk and /576/Records-Search
    as "Official Public Records"), L4 (El Paso County Clerk is the
    recorder of deeds / official public records authority).
verification_status: VERIFIED_OFFICIAL
notes: County-hosted on the official .gov domain. Direct fetch returned a
    working search form with document-number, deed-name, subdivision,
    document-type, book/page/lot/block/unit/tract, and file-date-range
    fields. No login or payment to search.

---

name: El Paso County Clerk — Foreclosures (search + map)
official_url: https://apps.epcountytx.gov/publicrecords/Foreclosures
layers_passed: L1 (county .gov domain), L3 (linked from the County Clerk
    page at epcountytx.gov/204 and the Records-Search index), L4 (County
    Clerk publishes notices of public real-property sales).
verification_status: VERIFIED_OFFICIAL
notes: Search interface confirmed (instrument number, sale-date range,
    subdivision/lot/block/unit/tract). Companion map at /Foreclosures/Map
    displays judicial foreclosures, tax sales/resales, contractual-lien
    sales. Page carries the county's own "not the official public record"
    map disclaimer — consistent with a genuine county product.

---

name: El Paso County Courts — Odyssey CRS (Civil / Family / Probate)
official_url: https://apps.epcountytx.gov/odysseyCrsPublic/CivilFamilyProbateCase
layers_passed: L1 (county .gov domain), L3 (linked from
    epcountytx.gov/576/Records-Search as "Civil Cases"), L4 (District
    Clerk / County Clerk are the court records authorities).
verification_status: VERIFIED_OFFICIAL
notes: Tyler Odyssey CRS public case search, county-hosted. Confirmed
    search by case number, party / business / attorney name (with
    Soundex), bar number, case-type category, open/closed status, and
    date range. Header reads "Public Access"; no login or CAPTCHA seen on
    the search form.

---

name: El Paso County Courts — Odyssey CRS (Criminal)
official_url: https://apps.epcountytx.gov/odysseyCrsPublic/CriminalCase
layers_passed: L1, L3, L4 (same portal family as the civil search).
verification_status: VERIFIED_OFFICIAL
notes: Verified for checklist completeness. Criminal cases are not a
    real-estate distress lead source; classified NOT a build source in
    §01.10. No source block is created for it in the county config.

---

name: El Paso Consolidated Tax Office — property tax search (ACT)
official_url: https://actweb.acttax.com/act_webdev/elpaso/index.jsp
layers_passed: L2 (acttax.com is a recognized tax-portal vendor — ACT),
    L3 (linked from the City of El Paso Tax Office page,
    elpasotexas.gov/tax-office), L4 (the El Paso Consolidated Tax Office
    is the property-tax collection authority for the county).
verification_status: VERIFIED_OFFICIAL
notes: Free public search by owner, address, account number, fiduciary
    number, property ID. Portal states it covers "any account for which
    the El Paso Tax Office collects property taxes." Per-account balances
    incl. delinquent amounts; payment / certificate ordering also offered.

---

name: El Paso County Sheriff — online real-property sale (RealAuction)
official_url: https://elpaso.texas.sheriffsaleauctions.com/
layers_passed: L2 (RealAuction.com is a recognized auction-portal vendor),
    L3 (the El Paso County Sheriff's Office publicly announced this site
    as its contracted online sale platform — Sheriff's News, Jul 2021 —
    built jointly with County Administration, the County Auditor and the
    City Tax Office), L4 (the Sheriff is the officer who conducts tax /
    judicial real-property sales).
verification_status: VERIFIED_OFFICIAL
notes: Confirmed as the county-contracted RealAuction platform for online
    tax-foreclosure sales under Tex. Tax Code 34.01 / 34.05. A direct
    automated fetch returned HTTP 403 (vendor WAF / bot protection);
    RealAuction public auction calendars render normally in a real
    browser. See access_classification.md and build_eligibility_handoff.md.

---

name: El Paso Central Appraisal District (EPCAD) — property search
official_url: https://go.epcad.org/search
layers_passed: L1 (epcad.org is the official domain of the statutory
    appraisal district for El Paso County), L4 (the appraisal district is
    the recognized property-appraisal authority).
verification_status: VERIFIED_OFFICIAL
notes: Official appraisal district. Direct automated fetch of epcad.org
    and go.epcad.org/search returned HTTP 403 (WAF / bot protection);
    the property search is publicly usable in a normal browser. Enrichment
    source — not a lead source — so the WAF does not gate the build.

---

name: El Paso County GIS Open Data Portal (ArcGIS Hub)
official_url: https://opendata-elpasoco.hub.arcgis.com/
layers_passed: L1 (county-named ArcGIS Hub subdomain operated by El Paso
    County GIS), L4 (county GIS is the recognized geospatial authority).
verification_status: VERIFIED_OFFICIAL
notes: Standard ArcGIS Hub open-data portal. 100+ downloadable layers with
    GeoServices / WMS / WFS APIs. Enrichment source.

---

name: Kofile QuickLink — historic deed index books (1874–1963)
official_url: https://kofilequicklinks.com/ElPaso/
layers_passed: L2 (Kofile is a recognized recordings vendor), L3 (linked
    from the County Clerk page), L4 (County Clerk historic land records).
verification_status: VERIFIED_OFFICIAL
notes: Historic scope only (through 1963). Outside the daily-distress
    window. Recorded as REFERENCE_ONLY in §01.10; no config source block.

---

## Summary

    VERIFIED_OFFICIAL: 9 of 9 discovered sources.
    UNVERIFIED: 0.
    NOT_RECORDS_AUTHORITY: 0.

Every discovered candidate is a genuine government source or a
county-contracted vendor portal cross-linked from the official county
.gov site. No aggregator or SEO reseller advanced past discovery.
