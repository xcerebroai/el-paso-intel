# Phase 0.A — Source Discovery — El Paso County, Texas

Slug: el_paso_tx
Generated: 2026-05-17
Protocol: knowledge_base/protocols/01_county_recon.md §01.6

County context:

    County: El Paso County, Texas
    FIPS: 48141
    County seat: El Paso
    Time zone: America/Denver (Mountain) — El Paso County is one of two
        Texas counties on Mountain Time. This is a recon finding that
        affects every refresh-cadence and sale-date calculation downstream.
    Official county domain: epcountytx.gov (migrated from epcounty.com;
        legacy epcounty.com links still resolve in places but several
        now 404 — treat epcountytx.gov as authoritative).
    Foreclosure / sale-date rule: Texas non-judicial foreclosure; sales
        held the first Tuesday of each month at the county courthouse.

Candidate sources discovered, one entry per source:

---

name: El Paso County Clerk — Official Public Records
official_url: https://apps.epcountytx.gov/publicrecords/OfficialPublicRecords
page_title: County of El Paso Texas - Official Public Records
gov_or_aggregator: GOVERNMENT (county-hosted on apps.epcountytx.gov)
records_covered: deeds, deeds of trust / mortgages, liens, trusts, powers
    of attorney, divorces, judgments, certificates — the recorded land /
    official public records index of the County Clerk.
discovered_via_query: "El Paso County Texas county clerk official records"

---

name: El Paso County Clerk — Foreclosures (search + map)
official_url: https://apps.epcountytx.gov/publicrecords/Foreclosures
page_title: County of El Paso Texas - Foreclosures
gov_or_aggregator: GOVERNMENT (county-hosted; linked from the County
    Clerk page epcountytx.gov/204/County-Clerk and epcountytx.gov/576)
records_covered: public sales of real property — judicial foreclosures,
    tax sales / resales, contractual-lien (substitute trustee) sales, and
    other statutorily mandated courthouse sales. Companion map view at
    https://apps.epcountytx.gov/publicrecords/Foreclosures/Map
discovered_via_query: "El Paso County Texas county clerk foreclosure
    notices trustee sale"

---

name: El Paso County Courts — Odyssey CRS (Civil / Family / Probate)
official_url: https://apps.epcountytx.gov/odysseyCrsPublic/CivilFamilyProbateCase
page_title: El Paso County Civil/Family/Probate Case Search
gov_or_aggregator: GOVERNMENT (county-hosted Tyler Odyssey CRS public
    portal; linked from epcountytx.gov/576/Records-Search)
records_covered: civil suits, family-law cases, probate cases and
    guardianships — open and closed — searchable by case number, party,
    business, attorney, bar number, case type, status, and date range.
discovered_via_query: "El Paso County Texas district clerk court records"

---

name: El Paso County Courts — Odyssey CRS (Criminal)
official_url: https://apps.epcountytx.gov/odysseyCrsPublic/CriminalCase
page_title: El Paso County Criminal Case Search
gov_or_aggregator: GOVERNMENT (county-hosted Tyler Odyssey CRS)
records_covered: criminal case database. Recorded for completeness of the
    checklist; criminal cases are not a real-estate distress lead source.
discovered_via_query: "El Paso County Texas district clerk court records"

---

name: El Paso Consolidated Tax Office — property tax search (ACT)
official_url: https://actweb.acttax.com/act_webdev/elpaso/index.jsp
page_title: El Paso Property Tax Search
gov_or_aggregator: VENDOR PORTAL (ACT / acttax.com), hosting the El Paso
    Consolidated Tax Office (City of El Paso Tax Office collects property
    tax for the county and most jurisdictions). Linked from
    elpasotexas.gov/tax-office.
records_covered: per-account tax balance, delinquent balance, payment
    history, tax certificates. Search by owner, address, account number,
    fiduciary number, property ID.
discovered_via_query: "El Paso County Texas tax office delinquent property"

---

name: El Paso County Sheriff — online real-property sale (RealAuction)
official_url: https://elpaso.texas.sheriffsaleauctions.com/
page_title: El Paso County Sheriff Sale (RealAuction)
gov_or_aggregator: VENDOR PORTAL (RealAuction.com), contracted by the El
    Paso County Sheriff's Office / County Administration / Auditor / City
    of El Paso Tax Office to host online tax-foreclosure real-property
    sales under Tex. Tax Code 34.01 / 34.05 (live since Aug 2021).
records_covered: tax-foreclosure sale calendar and lot list — sale date,
    property, minimum bid, case reference, defendant.
discovered_via_query: "El Paso County sheriff realauction online tax
    foreclosure sale website"

---

name: El Paso Central Appraisal District (EPCAD) — property search
official_url: https://go.epcad.org/search  (also https://epcad.org/Search)
page_title: El Paso Central Appraisal District - Property Search
gov_or_aggregator: GOVERNMENT (the statutory appraisal district for El
    Paso County).
records_covered: parcel master — owner, situs / mailing address,
    geographic ID / property ID, appraised and assessed value, year built,
    property class, exemptions. Enrichment data, not distress events.
discovered_via_query: "El Paso Central Appraisal District property search"

---

name: El Paso County GIS Open Data Portal (ArcGIS Hub)
official_url: https://opendata-elpasoco.hub.arcgis.com/
page_title: El Paso County GIS Open Data Portal
gov_or_aggregator: GOVERNMENT (El Paso County GIS, ArcGIS Hub).
records_covered: 100+ GIS layers — parcels, subdivisions, centerlines,
    commissioner precincts, county facilities. Downloadable as CSV, KML,
    GeoJSON, GeoTIFF, Zip; GeoServices / WMS / WFS APIs. Enrichment.
discovered_via_query: "El Paso County Texas GIS parcel open data ArcGIS"

---

name: Kofile QuickLink — historic deed index books (1874–1963)
official_url: https://kofilequicklinks.com/ElPaso/
page_title: Welcome to QuickLink for El Paso County, Texas
gov_or_aggregator: VENDOR PORTAL (Kofile), linked from the County Clerk
    page. Historic-only scope.
records_covered: enhanced-image historic deed index books, county origin
    through 1963. Out of the daily-distress window; reference only.
discovered_via_query: "El Paso County Texas county clerk official records"

---

## Sources searched for and NOT found as distinct online portals

    Standalone county-wide code-enforcement / demolition / condemnation
    portal — NOT_FOUND. Code enforcement in El Paso County is run per
    municipality (chiefly the City of El Paso) and by the County Fire
    Marshal for unincorporated areas; no consolidated public county-wide
    code-violation search portal was discovered. Per
    domain/02_signals_and_sources.md, county-wide code enforcement is
    out of scope for an initial build unless the operator prioritizes a
    single municipality.

    Separate "delinquent tax roll" dump — NOT_FOUND as a distinct file.
    Delinquency is exposed per-account inside the ACT tax portal and as a
    sale list inside the Sheriff RealAuction site; there is no separate
    bulk delinquent-roll download.

## Aggregators explicitly excluded (not recon targets, per §01.6)

    texasfile.com, govbackgroundchecks.com, elpasorecords.org,
    texascourtrecords.us, courtcasefinder.com, staterecords.org,
    liensuite.com, taxnetusa.com, auction.com, foreclosure.com,
    foreclosurelistings.com — third-party paid/SEO reseller layers.

    elpasopublictrustee.com and treasurer.elpasoco.com — these belong to
    El Paso County, COLORADO, not Texas. Discarded as wrong-county
    results. (Texas has no "public trustee"; foreclosure notices are
    filed with the County Clerk.)
