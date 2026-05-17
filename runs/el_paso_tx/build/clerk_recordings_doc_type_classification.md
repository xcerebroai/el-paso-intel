# clerk_recordings — Document Type Classification (Step 2)

Catalog: 254 `Style` options — full list in
`clerk_recordings_doc_type_catalog.json`. Classification per
`knowledge_base/architecture/13_lead_origination_contract.md` §13.

## PRIMARY_LEAD doc types (originate matched_lead rows)

    Style  Code/Name                              -> signal_type
    108    LIP - LIS PENDENS                       -> lis_pendens
    16     AOJ - ABSTRACT OF JUDGMENT              -> judgment_lien
    39     JUD - JUDGEMENT                          -> judgment_lien
    211    FJT - FINAL JUDGMENT                     -> judgment_lien
    101    CCJ - CERTIFIED COPY OF JUDGMENT         -> judgment_lien
    60     JQT - JUDGEMENT QUIETING TITLE           -> quiet_title
    92     FTL - FEDERAL TAX LIEN                   -> federal_tax_lien
    166    STL - STATE TAX LIEN                     -> state_tax_lien
    117    MEL - MECHANICS LIEN                     -> mechanics_lien
    103    LBL - LABORERS LIEN                      -> construction_lien
    104    LDL - LANDLORDS LIEN                     -> lien
    107    LIE - LIEN                               -> lien
    17     AOL - AFFIDAVIT OF LIEN                  -> lien
    217    CLL - COMMON LAW LIEN                    -> lien
    28     ATL - NOTICE OF ADMINISTRATIVE LIEN      -> code_lien
    94     HOS - HOSPITAL LIEN                      -> hospital_lien
    194    AFH - AFFIDAVIT OF HEIRSHIP              -> affidavit_of_heirship
    13     AOD - AFFIDAVIT OF DEATH                 -> affidavit_of_death
    89     EXR - EXECUTORS DEED                     -> executor_deed
    6      ADD - ADMINISTRATORS DEED                -> administrator_deed
    93     GUD - GUARDIANS DEED                     -> guardian_deed
    76     DSD - DISTRIBUTION DEED                  -> estate_distribution
    261    TDD - TRANSFER ON DEATH DEED             -> transfer_on_death
    43     CCP - CERTIFIED COPY OF PROBATE          -> probate_recording
    163    SHD - SHERIFFS DEED                      -> foreclosure_deed
    175    TRD - TRUSTEES DEED                      -> foreclosure_deed
    68     DIL - DEED IN LIEU                       -> deed_in_lieu
    138    WDF - WARRANTY DEED LIEU/FORECLOSURE     -> deed_in_lieu
    178    TXD - TAX DEED                           -> tax_deed
    30     BAN - BANKRUPTCY                         -> bankruptcy
    12     NTS - NOTICE OF TRUSTEES SALE            -> notice_of_trustee_sale
                                                       (overlaps the DEFERRED
                                                       foreclosure_notices source;
                                                       excluded from this scrape)

No child_support_lien, demolition_order, or condemnation Style code was
found in the El Paso catalog.

## SUPPRESSION doc types (negative signals — suppress prior signals)

    147  REL - RELEASE/SATISFACTION
    34   CAC - CANCELLATION
    219  REC / 25 RVE - RECONVEYANCE
    189  WLP - WITHDRAWAL OF LIS PENDENS
    215  CRF - CERTIFICATE OF RELEASE FTL
    85   ESL - RELEASE OF STL FILED IN ERROR
    213  NAF - NON ATTACHMENT OF FEDERAL TAX LIEN
    260  COL - CANCELLATION OF LEASE

## NOISE / ENRICHMENT doc types (do NOT originate leads)

    182 WAD warranty deed, 3 DDD deed, 75 DOT deed of trust, 263 GFT gift
    deed, 116 MDT master deed of trust, 143 QCD quitclaim deed (ambiguous
    — treated as noise for this build per the build spec's primary list),
    and the remaining ordinary deeds / agreements / certificates.

## This session's scrape set (focused, 10 high-value PRIMARY_LEAD types)

Single-session budget — scrape a focused, representative set; the rest
are classified above for later sessions.

    108 LIP -> lis_pendens          16  AOJ -> judgment_lien
    92  FTL -> federal_tax_lien     166 STL -> state_tax_lien
    117 MEL -> mechanics_lien       94  HOS -> hospital_lien
    28  ATL -> code_lien            194 AFH -> affidavit_of_heirship
    89  EXR -> executor_deed        6   ADD -> administrator_deed

Date window: 2026-01-01 .. 2026-05-17 (recent distress).
