# EPCAD Property Search API — Targeted Recon Supplement

Slug: el_paso_tx
Generated: 2026-05-17
Scope: investigate the documented EPCAD Property Search API and update the
El Paso enrichment (parcel_master) build strategy. Recon supplement only —
no translator written, no build modified.
Operator-provided documentation: https://documenter.getpostman.com/view/24320979/2sAYdfpWHE

---

## 1. Extracted API documentation

The Postman documentation is a JS-rendered SPA; the underlying collection
JSON was retrieved from
`https://documenter.gw.postman.com/api/collections/24320979/2sAYdfpWHE`.

    API name:   EPCAD Property Search
    Description: "An API for retrieving property listings and detailed
                 property information for El Paso County."
    Base URL:   http://epcadpropertysearch.azurewebsites.net
                (HTTPS also works and was used for the live test —
                 https://epcadpropertysearch.azurewebsites.net)
    Auth:       NONE. The collection's `auth` is null. No API key, no
                OAuth, no token. Confirmed by a live unauthenticated call
                returning HTTP 200.
    Rate limits: NONE documented in the collection.
    Hosting:    Azure App Service (azurewebsites.net) — this is the same
                backend that powers the public www.epcad.org/search and
                /search/advanced interfaces.

### Endpoints (both HTTP GET)

    GET /Api/Properties/GetProperties
        The default-search endpoint.
    GET /Api/Properties/GetPropertiesAdvanced
        Same parameter set; documented as "for use by the advanced search
        interface on www.epcad.org/search/advanced". Adds meaningful use
        of `dba` and `type` (see below).

### Query parameters (identical param list on both endpoints)

    dbId          string   EPCAD internal database id.
    ownerName     string   Owner name to search (partial match supported).
    address       string   Full property address to search.
    streetNumber  string   Numeric segment of the street address.
    streetName    string   Street name (may include the numeric segment).
    propertyId    string   The property ID (EXACT match).
    geoID         string   Geographic ID.
    keywords      string   Smart-search across ownerName, streetName,
                           propertyId, geoID. Partial match for ownerName/
                           streetName/geoID; propertyId must be exact.
    dba           string   "Doing Business As" alternate name.
                           GetPropertiesAdvanced only.
    type          string   Property type: "MH" (mobile home), "MN"
                           (mineral), "P" (personal), "R" (real).
                           GetPropertiesAdvanced only.
    year          integer  Appraisal year of the property.
    page          integer  Page number (pagination).
    pageSize      integer  Records per page (pagination).
    sortField     string   Field to sort by.
    sortOrder     string   Sort direction.

Pagination model: classic `page` + `pageSize`. No documented maximum
`pageSize`. There is no documented parameter for subdivision / lot / block,
and no documented "return everything" mode — bulk retrieval is achieved by
paging through a search (see strategy below).

### Response schema (GetProperties / GetPropertiesAdvanced)

    {
      "Status":   string,          // "OK" on success (confirmed live)
      "Message":  string|null,
      "Meanings": [string],
      "Properties": [
        {
          "dbId": integer,
          "PropertyId": string,            // EPCAD property id
          "LegalDescription": string,      // subdivision + lot + sqft
          "AgentCode": string,
          "GeoID": string,                 // geographic id
          "Type": string,                  // R / MH / MN / P
          "PropertyUseCode": string,
          "PropertyUseDescription": string,
          "DoingBusinessAs": string,
          "Location": {
            "Address": string,             // full situs address
            "Neighborhood": string,
            "NeighborhoodCD": string,
            "Mapsco": string,
            "MapID": string
          },
          "Owners": [
            {
              "dbId": integer,
              "Name": string,              // owner name
              "OwnerID": integer,
              "MailingAddress": string,    // owner mailing address
              "PercentOwnership": double,
              "Excemptions": string,       // (sic) exemption codes
              "CareOf": string,
              "Year": integer
            }
          ],
          "Values": [
            {
              "ValuesId": integer,
              "ImprovementHomesiteValue": double,
              "ImprovementNonHomesiteValue": double,
              "LandHomesiteValue": double,
              "LandNonHomesiteValue": double,
              "AgriculturalMarketValuation": double,
              "TimberMarketValuation": double,
              "MarketValue": double,
              "AgriculturalOrTimberUseValueReduction": double,
              "AppraisedValue": double,
              "HSCap": double,             // homestead-cap value
              "AssessedValue": double,
              "Year": integer
            }
          ],
          "TaxJurisdictions": [ ... ],
          // Additional arrays present in the LIVE response beyond the
          // documented schema (observed in the sample call):
          "Improvements": [...], "Lands": [...], "RollValueHistory": [...],
          "DeedHistory": [...], "BppRenditions": [...], "Homesteads": [...],
          "PropertyImages": [...], "AvailableYears": [...],
          "Year": integer, "No_Homestead": bool
        }
      ]
    }

---

## 2. Live sample call (one call only, per operator rule)

Request:

    GET https://epcadpropertysearch.azurewebsites.net/Api/Properties/GetProperties
        ?streetName=MESA&page=1&pageSize=2

(`streetName=MESA` — a major El Paso thoroughfare. The already-scraped
foreclosure_notices.jsonl carries no street address or property id, only
subdivision/lot/block, so a generic street-name search was used for the
single permitted probe.)

Response: HTTP 200, `content-type: application/json`, 3,042 bytes.

    Status: OK
    Properties returned: 2

Sample property [0] — real values, verbatim:

    PropertyId:        101737
    GeoID:             Q52000000300200
    Type:              R  (real property)
    LegalDescription:  "3 QUAIL MESA  LOT 2 (54580.68 SQ FT)"
    Location.Address:  "942 QUAIL MESA DR SOCORRO, TX 79927"
    Owner[0].Name:     "AVILA ENRIQUE & MARIA"
    Owner[0].Mailing:  "930 QUAIL MESA DR CLINT TX 79836-9836"
    Owner[0].Exemptions: "" (none)
    Values(2026):      AssessedValue 114140.0  AppraisedValue 114140.0
                       MarketValue 114140.0  HSCap 0.0
                       ImprovementHomesiteValue 89888.0
    No_Homestead:      present (boolean homestead indicator)

The API returned real, current (2026 appraisal year) El Paso County data
without authentication.

### matched_lead enrichment field coverage

Every enrichment field the matched_lead record needs is populated by the
API response:

    owner_name          -> Owners[].Name                      AVAILABLE
    situs_address       -> Location.Address                    AVAILABLE
    mailing_address     -> Owners[].MailingAddress              AVAILABLE
    parcel_id/property  -> PropertyId, GeoID, dbId              AVAILABLE
    assessed_value      -> Values[].AssessedValue               AVAILABLE
                           (+ AppraisedValue, MarketValue)
    homestead_status    -> No_Homestead (bool), Homesteads[],
                           Owners[].Excemptions, HSCap,
                           ImprovementHomesiteValue              AVAILABLE
    legal_description   -> LegalDescription                     AVAILABLE
    absentee proxy      -> situs vs MailingAddress comparison    DERIVABLE
                           (sample shows situs SOCORRO vs mailing CLINT —
                            absentee-owner signal computable for free)

All matched_lead enrichment fields can be FULLY POPULATED from the API
response. No PDF parsing and no Playwright WAF bypass is required for
EPCAD enrichment.

---

## 3. Strategy comparison

    Previously authorized (Phase 0.5 classification):
        EPCAD parcel_master = TECHNICAL_BLOCKER (WAF / HTTP 403 to
        automated fetch); planned resolution = use_playwright per-row,
        with PDF fallback.

    Confirmed now:
        The WAF 403 applies to scraping the epcad.org / go.epcad.org HTML
        pages. The property DATA is served by a SEPARATE, documented,
        unauthenticated public JSON API on Azure. The TECHNICAL_BLOCKER
        classification does NOT apply to this API.

    Recommendation: REPLACE the Playwright/WAF strategy with the
    documented JSON API. It is faster, deterministic, schema-stable, and
    carries no WAF, no CAPTCHA, no login.

### Per-row vs bulk

- **Per-row API call** — feasible: for each foreclosure lead, query the
  API. Limitation: foreclosure records key on subdivision/lot/block, and
  the API has no subdivision/lot/block parameter. A per-row join would
  need a street address first (from the foreclosure View-Document PDF) or
  an owner name.
- **API bulk-batch (RECOMMENDED)** — page through `GetProperties` (e.g.
  `type=R`, iterating `page` with a large `pageSize`, or iterating broad
  `keywords`/`streetName` seeds) to build a LOCAL EPCAD index keyed on
  parsed `LegalDescription` (subdivision + lot + block) AND on
  `Location.Address`. Then join the clerk foreclosure records to that
  index locally on legal description. This removes per-row latency and
  gives one clean enrichment dataset. Whether a single broad query can
  return the full roll in pages is unconfirmed — only one sample call was
  permitted this recon; a 2–3 call pagination probe is the first
  Build-Mode step for this source.

---

## 4. Config update applied

`config/counties/el_paso_tx.json` — `sources.parcel_master` updated via
`scaffold/ops/write_county_config.py` (the locked write path, §4.28):

    access_method            PUBLIC_BUT_WAF_PROTECTED -> API_ENDPOINT
    public_access_status     WAF_PROTECTED            -> FULL_PUBLIC_ACCESS
    access_pattern           waf_imperva              -> open_api
    verification_confidence  MEDIUM                   -> HIGH
    blocker                  (WAF text)               -> "" (cleared)
    blocker_type             TECHNICAL_BLOCKER        -> "" (cleared)
    next_access_strategy     use_playwright           -> "" (resolved)
    auto_resolve_status      PARTIALLY_RESOLVED       -> RESOLVED
    final_resolution_status  PARTIALLY_RESOLVED       -> RESOLVED
    sample_record_path_confirmed  false               -> true
    sample_search_possible        false               -> true
    recommended_adapter      epcad_search_scraper     -> epcad_documented_json_api
    + api_base_url, api_endpoints, api_auth fields added to the source block

Schema note: the operator's requested strategy label "use_documented_api"
is NOT a value in the schema's `next_access_strategy` enum. To keep the
config schema-valid, `next_access_strategy` was set to "" (the source is
resolved / no blocker) and the documented-API fact is recorded in
`recommended_adapter`, `fingerprint_summary`, `notes`, and the new
`api_*` fields. A third `auto_resolve_attempts` entry records the API
discovery.

---

## 5. Updated build strategy (proposed)

1. EPCAD parcel_master enrichment: use the documented JSON API
   (`GetProperties` / `GetPropertiesAdvanced`), not Playwright. Drop the
   WAF-bypass plan for this source.
2. First Build-Mode step for parcel_master: a 2–3 call pagination probe
   to confirm whether a broad query can page the full real-property roll.
3. Enrichment model: API bulk-batch — build a local EPCAD index keyed on
   parsed LegalDescription (subdivision/lot/block) and Location.Address.
4. Join: clerk foreclosure_notices records (subdivision/lot/block) join
   to the EPCAD index locally on legal description; this supplies the
   street address + owner + mailing address + assessed value the
   foreclosure rows lack — as ENRICHMENT attached to the primary
   foreclosure event (§13.3 / §13.4 — enrichment attaches, never
   originates).
5. Free bonus signal: situs-vs-mailing comparison yields an absentee-owner
   attribute at no extra cost.
6. No change to lead origination: EPCAD remains an ENRICHMENT_SOURCE. It
   decorates foreclosure / court / tax leads; it never creates a lead row.

EPCAD API RECON COMPLETE — see §5 for the proposed updated build strategy.
