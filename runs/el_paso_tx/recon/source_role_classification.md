# Phase 0.E — Source Role Classification — El Paso County, Texas

Slug: el_paso_tx
Generated: 2026-05-17
Protocol: knowledge_base/protocols/01_county_recon.md §01.10
Authority: knowledge_base/architecture/13_lead_origination_contract.md
    §13.2 (primary lead source categories), §13.3 (enrichment categories)

Canonical roles: PRIMARY_LEAD_SOURCE, SUPPORTING_LEAD_SOURCE,
ENRICHMENT_SOURCE, REFERENCE_ONLY, REJECTED_SOURCE.

---

name: clerk_recordings
source_role: PRIMARY_LEAD_SOURCE
rationale: County Clerk recorded instruments — deeds, deeds of trust,
    liens, judgments, lis pendens, releases. These are discrete, dated,
    recorded distress / transfer / legal-action events. The canonical
    primary lead source class.
section_13_reference: §13.2 — clerk / recorder recorded instruments.

---

name: foreclosure_notices
source_role: PRIMARY_LEAD_SOURCE
rationale: County Clerk-published notices of public real-property sales —
    notices of substitute trustee's sale (Texas non-judicial foreclosure),
    tax-foreclosure sale notices, resales, contractual-lien sales. Each is
    a dated recorded foreclosure event. This is the single cleanest P0
    source for an El Paso build — a county-published, fully open
    foreclosure feed with a companion map.
section_13_reference: §13.2 — foreclosure notices / recorded notices.

---

name: court_civil
source_role: PRIMARY_LEAD_SOURCE
rationale: District / county court civil and family filings — judicial
    foreclosure suits, civil judgments, divorces with property
    settlements, evictions where exposed. Dated court events that
    originate leads.
section_13_reference: §13.2 — court filings (civil, family, foreclosure).

---

name: court_probate
source_role: PRIMARY_LEAD_SOURCE
rationale: Probate cases and guardianships filed with the County Clerk and
    indexed in Odyssey CRS — estate openings, dependent administrations,
    heirships. Dated court events; the estate lead pattern.
section_13_reference: §13.2 — probate / estate records.

---

name: tax_collector
source_role: PRIMARY_LEAD_SOURCE
rationale: El Paso Consolidated Tax Office per-account records expose
    delinquent tax balances — a tax-delinquency distress event tied to a
    property and an owner. Texas tax debt is a public record by statute.
section_13_reference: §13.2 — tax delinquency events.

---

name: sheriff_sales
source_role: PRIMARY_LEAD_SOURCE
rationale: El Paso County Sheriff online sale of real property for tax
    foreclosures (RealAuction) — a dated sheriff-sale event with sale
    date, property, minimum bid, defendant. A §13.2 primary category.
    Carries a technical WAF blocker (see access_classification.md and
    build_eligibility_handoff.md); the role is unaffected by the blocker.
section_13_reference: §13.2 — sheriff sale records / tax sale events.

---

name: parcel_master  (EPCAD)
source_role: ENRICHMENT_SOURCE
rationale: El Paso Central Appraisal District parcel master — owner,
    situs/mailing address, geographic ID, appraised/assessed value, year
    built, property class, exemptions. Parcel-state metadata. Per the
    §13.4 hard rule, this CANNOT originate a lead; it attaches context to
    leads that already exist from a primary source.
section_13_reference: §13.3 — appraisal-district / parcel / valuation data.

---

name: gis_parcels  (El Paso County GIS Open Data)
source_role: ENRICHMENT_SOURCE
rationale: ArcGIS parcel geometry, parcel IDs, subdivisions, precincts.
    Geospatial enrichment — map rendering, deep links, parcel-ID join key.
    Cannot originate a lead.
section_13_reference: §13.3 — GIS / parcel-geometry data.

---

name: Kofile QuickLink (historic deed books 1874–1963)
source_role: REFERENCE_ONLY
rationale: Historic deed index images, county origin through 1963. Real
    distress events, but entirely outside the daily-distress window the
    product serves. Useful for title context, not for current leads.
section_13_reference: not a §13.2 active-lead source — historic scope.

---

name: Odyssey CRS Criminal Case search
source_role: REJECTED_SOURCE
rationale: Criminal cases are not a real-estate distress signal. Verified
    official for checklist completeness, then excluded from the build. No
    config source block created.
section_13_reference: outside §13.2 and §13.3 — not a real-estate source.

---

## Role summary

    PRIMARY_LEAD_SOURCE:    6 — clerk_recordings, foreclosure_notices,
                                court_civil, court_probate, tax_collector,
                                sheriff_sales
    SUPPORTING_LEAD_SOURCE: 0  (no standalone supporting source; document
                                images and case detail pages are reached
                                inside the primary portals above)
    ENRICHMENT_SOURCE:      2 — parcel_master (EPCAD), gis_parcels
    REFERENCE_ONLY:         1 — Kofile QuickLink (historic)
    REJECTED_SOURCE:        1 — Odyssey CRS Criminal

Five PRIMARY_LEAD_SOURCEs are OPEN_PUBLIC and fully accessible
(clerk_recordings, foreclosure_notices, court_civil, court_probate,
tax_collector). The §01.11 / §13.5 requirement — at least one accessible
primary lead source — is satisfied several times over.
