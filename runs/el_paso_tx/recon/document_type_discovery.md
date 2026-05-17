# Phase 0.F — Document Type Discovery — El Paso County, Texas

Slug: el_paso_tx
Generated: 2026-05-17
Protocol: knowledge_base/protocols/01_county_recon.md §01.12
Registry: knowledge_base/domain/canonical_doc_types.json

Scope: VERIFIED_OFFICIAL sources with role PRIMARY_LEAD_SOURCE /
SUPPORTING_LEAD_SOURCE and access OPEN_PUBLIC / SEARCH_ONLY_PUBLIC. That
is the five fully-accessible primary sources. sheriff_sales is excluded
here because its access tier is BLOCKED (technical WAF) — its document /
lot taxonomy is captured in Build Mode once the WAF is rendered past.

This phase is METADATA-ONLY. It captures the document-type vocabulary the
portals use and proposes the §13.2 mapping. It does NOT scrape records.

Important honesty note: the recon fetch is metadata-only and did not
enumerate the exact contents of the portals' "document type" dropdowns.
The mappings below are at the record-CATEGORY level (what each portal
publishes) cross-referenced to canonical_doc_types.json. Exact dropdown-
value capture is a Build-Mode portal-fingerprinting task and is recorded
as the recommended next action per source.

---

source_name: clerk_recordings
document_type_taxonomy_field_name: "Style / Document Type" (a document-
    type filter on the Official Public Records search form; exact option
    list not enumerated during metadata-only recon)
total_types_observed: not enumerated (dropdown values to be captured in
    Build Mode portal fingerprinting)
types_mapped_to_canonical_primary: the recorded-instrument categories the
    portal advertises map to these canonical primary (lead_generating)
    types —
        NOTICE_OF_SUBSTITUTE_TRUSTEE_SALE  (foreclosure)
        APPOINTMENT_OF_SUBSTITUTE_TRUSTEE  (foreclosure)
        TRUSTEES_DEED_UPON_SALE / SHERIFF_DEED  (foreclosure)
        LIS_PENDENS  (foreclosure)
        FEDERAL_TAX_LIEN / STATE_TAX_LIEN  (tax)
        TAX_SALE_CERTIFICATE  (tax)
        MECHANICS_LIEN / CONSTRUCTION_LIEN / JUDGMENT_LIEN /
            HOA_LIEN / HOSPITAL_LIEN  (lien)
        QUITCLAIM_DEED  (transfer, lead_generating)
        EXECUTORS_DEED / ADMINISTRATORS_DEED /
            PERSONAL_REPRESENTATIVE_DEED  (estate)
        AFFIDAVIT_OF_HEIRSHIP  (estate)
        DEED_IN_LIEU_OF_FORECLOSURE  (foreclosure)
types_mapped_to_canonical_enrichment: WARRANTY_DEED, SPECIAL_WARRANTY_DEED,
    DEED_OF_TRUST / MORTGAGE, ASSIGNMENT_OF_MORTGAGE, EASEMENT,
    RIGHT_OF_WAY, PLAT — recorded but enrichment / non-lead.
types_unknown: powers of attorney, "trusts", assorted certificates — to
    be classified against the registry once the dropdown is enumerated.
recommended_primary_doc_types_for_build: lead on the foreclosure, tax,
    lien and estate canonical types above. Treat satisfactions, releases
    and reconveyances as negative_signal (suppression) per
    domain/09_document_lifecycle.md.

---

source_name: foreclosure_notices
document_type_taxonomy_field_name: implicit — the Foreclosures dataset is
    itself a single notice class (public sales of real property); the map
    view distinguishes sale categories.
total_types_observed: ~3 sale categories advertised — mortgage / contractual-
    lien (substitute trustee) sales, tax-foreclosure sales, and resales /
    other statutorily mandated courthouse sales.
types_mapped_to_canonical_primary:
        NOTICE_OF_SUBSTITUTE_TRUSTEE_SALE  (foreclosure)
        TAX_FORECLOSURE_NOTICE  (tax)
        NOTICE_OF_SALE  (foreclosure — resale / other courthouse sale)
types_mapped_to_canonical_enrichment: none — every row here is a
    lead_generating foreclosure / tax event.
types_unknown: none material.
recommended_primary_doc_types_for_build: all rows. This is the cleanest
    P0 feed for El Paso — a county-published, fully open foreclosure
    notice set. The translator should split mortgage-foreclosure vs
    tax-foreclosure into the `foreclosure` and `tax` patterns
    respectively, mirroring the Bexar foreclosure_notices_map translator.

---

source_name: court_civil
document_type_taxonomy_field_name: "Case Type / Category" (Odyssey CRS
    case-type filter; exact option list not enumerated during recon)
total_types_observed: not enumerated (Odyssey CRS case-type categories
    to be captured in Build Mode)
types_mapped_to_canonical_primary: civil/family case categories map to —
        FINAL_JUDGMENT_OF_FORECLOSURE  (foreclosure)
        JUDGMENT_LIEN  (lien — abstracts of judgment)
        DIVORCE_FILING / FINAL_DECREE_OF_DIVORCE /
            MARITAL_PROPERTY_DIVISION  (divorce)
        EVICTION_FILING / WRIT_OF_POSSESSION  (eviction, where the JP /
            county-court eviction docket is exposed)
        PARTITION_ACTION / QUIET_TITLE_ACTION  (title_issue)
types_mapped_to_canonical_enrichment: none — court filings are events.
types_unknown: full Odyssey case-type list pending enumeration.
recommended_primary_doc_types_for_build: lead on judicial-foreclosure,
    judgment, divorce-with-property and (if exposed) eviction case types.

---

source_name: court_probate
document_type_taxonomy_field_name: "Case Type / Category" (probate and
    guardianship categories within Odyssey CRS CivilFamilyProbateCase)
total_types_observed: not enumerated (probate case-type categories to be
    captured in Build Mode)
types_mapped_to_canonical_primary:
        LETTERS_TESTAMENTARY  (estate)
        LETTERS_OF_ADMINISTRATION  (estate)
        DETERMINATION_OF_HEIRSHIP  (estate)
        MUNIMENT_OF_TITLE  (estate)
        AFFIDAVIT_OF_HEIRSHIP  (estate)
types_mapped_to_canonical_enrichment: none.
types_unknown: guardianship sub-categories — relevant only where they
    touch real property; classify in Build Mode.
recommended_primary_doc_types_for_build: lead on estate-opening case
    types (administrations, testamentary, heirship, muniment of title).

---

source_name: tax_collector
document_type_taxonomy_field_name: not a document-type portal — it
    exposes per-account tax STATUS, not a recorded-document index.
total_types_observed: n/a — the lead-bearing signal is a single derived
    state: delinquent tax balance on an account.
types_mapped_to_canonical_primary: the per-account delinquency state maps
    to the `tax` pattern (a tax-delinquency event). It is not a recorded
    document type; the translator derives the signal from the balance and
    delinquency fields.
types_mapped_to_canonical_enrichment: assessed value, exemption status —
    enrichment context carried on the same account page.
types_unknown: none.
recommended_primary_doc_types_for_build: derive a `tax` delinquency
    signal from accounts past the Feb 1 delinquency date with a non-zero
    delinquent balance.

---

## Summary

Across the five accessible primary sources, El Paso County exposes the
full canonical primary spread the framework wants: foreclosure
(substitute-trustee and tax), tax delinquency / tax liens, judgment and
mechanics liens, estate / probate, divorce, and — pending confirmation —
eviction. No accessible primary source is enrichment-only. Exact
document-type and case-type dropdown enumeration is the first Build-Mode
portal-fingerprinting task for clerk_recordings, court_civil and
court_probate.
