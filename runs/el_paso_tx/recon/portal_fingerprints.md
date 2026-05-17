# Phase 0.C — Portal Fingerprinting — El Paso County, Texas

Slug: el_paso_tx
Generated: 2026-05-17
Protocol: knowledge_base/protocols/01_county_recon.md §01.8

Fingerprint scope: every VERIFIED_OFFICIAL source that will become a
county-config source block. Kofile QuickLink and the criminal-case search
are excluded (REFERENCE_ONLY / non-build per §01.10).

Difficulty scale: LOW (server-rendered HTML, no auth) / MEDIUM (SPA, no
auth) / HIGH (SPA + dynamic auth or per-request tokens) / VERY_HIGH
(Cloudflare challenge, CAPTCHA gate, IP block, anti-scrape headers).

---

name: clerk_recordings (Official Public Records)
vendor: County-hosted public-records application on apps.epcountytx.gov.
    Not matched to a named vendor family in
    knowledge_base/engineering/08_vendor_portal_library.md — the same
    county apps domain also hosts a Tyler Odyssey CRS instance, but the
    /publicrecords/ application does not expose vendor branding in its
    markup. Treated as a county-hosted custom/whitelabel app.
detection_heuristics: URL path /publicrecords/OfficialPublicRecords on the
    official .gov apps host; server-rendered search form; no vendor footer.
architecture: server-rendered HTML search form (classic ASP.NET-style).
search_interface: form-based POST — fields for document number, deed
    name (text match), subdivision, style/document type, book, page, lot,
    block, unit, tract, file-date range.
result_url_pattern: results render off the same /publicrecords/
    OfficialPublicRecords path after form submission (to confirm in
    Build Mode).
detail_url_pattern: per-document detail / image view; index allows
    viewing up to 10 documents per search before resubmission.
scrape_difficulty: LOW

---

name: foreclosure_notices (Foreclosures search + map)
vendor: County-hosted, same /publicrecords/ application family as
    clerk_recordings. The map view is a county-hosted web map.
detection_heuristics: /publicrecords/Foreclosures path on apps.epcountytx
    .gov; companion /Foreclosures/Map path.
architecture: server-rendered HTML search form; separate map view.
search_interface: form-based POST — instrument number, sale-date range,
    subdivision/lot/block/unit/tract.
result_url_pattern: results off the /publicrecords/Foreclosures path.
detail_url_pattern: foreclosure-document references; map view exposes a
    per-property pop-up.
scrape_difficulty: LOW

---

name: court_civil and court_probate (Odyssey CRS)
vendor: Tyler Technologies — Odyssey CRS (Case Records Search). Matches
    the Tyler family in the vendor portal library; this is the older
    Odyssey "CRS / Public Access" product, county-hosted on
    apps.epcountytx.gov/odysseyCrsPublic/ (a parallel Tyler portal also
    exists at portal-txelpaso.tylertech.cloud).
detection_heuristics: URL segment /odysseyCrsPublic/; "Public Access"
    header; Soundex name-search options; case-type/category filters.
architecture: server-rendered HTML (Odyssey CRS classic). The
    tylertech.cloud mirror is a redirect-heavy SPA — the county-hosted
    odysseyCrsPublic path is the cleaner target.
search_interface: form-based POST — case number, party/business/attorney
    name + Soundex, bar number, case-type category, open/closed status,
    on/before + on/after date filters.
result_url_pattern: result list off /odysseyCrsPublic/CivilFamilyProbateCase.
detail_url_pattern: per-case detail page (register of actions).
scrape_difficulty: LOW to MEDIUM — the county-hosted CRS form is
    server-rendered; the tylertech.cloud mirror is redirect-heavy and
    should be avoided. A CAPTCHA was reported by third-party sources as
    "may be required" under high traffic; not observed on the search form
    during recon. Flagged as an open question.

---

name: tax_collector (El Paso Consolidated Tax Office — ACT)
vendor: ACT (acttax.com) — recognized tax-portal vendor. Same vendor
    family as observed on other Texas county tax portals.
detection_heuristics: actweb.acttax.com host; /act_webdev/elpaso/ path;
    classic JSP server-rendered forms.
architecture: server-rendered HTML / JSP.
search_interface: form-based POST — owner name (last/business required),
    address (street number + name), account number, fiduciary number,
    property ID. Shopping-cart for payments (up to 50 accounts).
result_url_pattern: per-account result pages under /act_webdev/elpaso/.
detail_url_pattern: per-account tax statement page with balance,
    delinquent amount, payment history.
scrape_difficulty: LOW

---

name: sheriff_sales (RealAuction)
vendor: RealAuction.com — recognized auction-portal vendor (vendor
    library family "RealAuction"). Host elpaso.texas.sheriffsaleauctions
    .com follows the RealAuction <county>.<state>.sheriffsaleauctions.com
    pattern.
detection_heuristics: sheriffsaleauctions.com domain; RealAuction WAF
    response (HTTP 403 to automated fetch).
architecture: RealAuction ColdFusion-style web app (typically /index.cfm,
    /Auctions paths).
search_interface: vendor-proprietary — auction calendar + lot list;
    bidder registration required only to bid, not to browse.
result_url_pattern: RealAuction auction-day lot list (typically
    /index.cfm?... auction-date parameters).
detail_url_pattern: per-lot detail page with sale date, property,
    minimum bid, case reference.
scrape_difficulty: HIGH — RealAuction fronts the site with a WAF/bot
    filter that returned HTTP 403 to the recon fetcher. The public auction
    calendar renders in a normal browser; Build Mode will need a real
    browser (Playwright) and respectful pacing. Not a CAPTCHA gate.

---

name: parcel_master (EPCAD property search)
vendor: EPCAD-hosted property search (go.epcad.org). Not matched to a
    named vendor family from the markup available; the appraisal district
    runs a modern search app behind a WAF.
detection_heuristics: epcad.org / go.epcad.org hosts; WAF 403 to
    automated fetch.
architecture: modern web app (JS-rendered search), behind a WAF.
search_interface: by name, address, property ID, geographic ID.
result_url_pattern: to confirm in Build Mode (WAF blocked recon fetch).
detail_url_pattern: per-parcel property detail page.
scrape_difficulty: HIGH — WAF returns HTTP 403 to automated fetch.
    Enrichment source; Build Mode will use a real browser. EPCAD also
    publishes an Open Government / open-records channel that may offer a
    cleaner bulk path.

---

name: gis_parcels (El Paso County GIS Open Data — ArcGIS Hub)
vendor: Esri ArcGIS Hub (vendor library family "ArcGIS / Esri").
detection_heuristics: *.hub.arcgis.com host; ArcGIS Hub open-data UI;
    GeoServices / WMS / WFS API links.
architecture: ArcGIS Hub SPA over ArcGIS REST services.
search_interface: REST API — FeatureServer / MapServer /query endpoints;
    dataset download in CSV / GeoJSON / KML / Zip.
result_url_pattern: /<service>/FeatureServer/<layer>/query.
detail_url_pattern: per-feature attributes via the query API.
scrape_difficulty: LOW — open ArcGIS REST endpoints, no auth.

---

## Fingerprint notes for the vendor portal library

    New / reinforced observations worth carrying into the library:

    - A single county apps domain (apps.epcountytx.gov) can host BOTH a
      custom /publicrecords/ recordings application AND a Tyler Odyssey
      CRS instance under /odysseyCrsPublic/. Path segment is the reliable
      discriminator.
    - RealAuction <county>.<state>.sheriffsaleauctions.com fronts with a
      WAF that 403s automated fetchers while remaining publicly browsable
      — consistent with the existing RealAuction library entry; the WAF
      severity should be noted.
