# El Paso clerk_recordings — Data Quality Audit

Diagnostic only — no fixes applied, nothing committed.
Generated: 2026-05-17 · against dashboard/data.json (1,110 matched_leads)
and data/el_paso_tx/raw/clerk_recordings.jsonl (1,316 raw records).

---

## Root-cause summary

Three reported bugs — and all three trace, in large part, to ONE root
cause: the translator's party-selection logic. A fourth related finding
(fuzzy EPCAD enrichment matching) is documented below because it
compounds the symptoms.

---

## Name-type semantics by document type (empirical, from raw data)

The clerk result table tags each party with a name_type. Distribution:

    lis_pendens       DF-Defendant 71,  PF-Plaintiff 44
    judgment_lien     DF-Defendant 258, PF-Plaintiff 237
    federal_tax_lien  TP-Tax Payer 216, GR-Grantor 6, GE-Grantee 6
    state_tax_lien    TP-Tax Payer 309, (few SP/GR)
    mechanics_lien    GR-Grantor 48,    GE-Grantee 38
    hospital_lien     GR-Grantor 249,   GE-Grantee 249
    code_lien         GR-Grantor 14,    GE-Grantee 17
    affidavit_of_heirship  GR 172, GE 326
    executor_deed     GR 180, GE 179
    administrator_deed GR 43, GE 30

CRITICAL: the debtor/target party is on a DIFFERENT name_type per doc
type — there is no universal rule:

    doc type          debtor/lead party    filer/non-lead party
    lis_pendens       DF - Defendant       PF - Plaintiff
    judgment_lien     DF - Defendant       PF - Plaintiff
    federal_tax_lien  TP - Tax Payer       (n/a) — or GE when GR/GE-typed
    state_tax_lien    TP - Tax Payer       (n/a)
    hospital_lien     GE - Grantee         GR - Grantor  (hospital files)
    code_lien (ATL)   GE - Grantee         GR - Grantor  (TWC files)
    mechanics_lien    GR - Grantor         GE - Grantee  (contractor files)

hospital_lien and code_lien have the OPPOSITE grantor/grantee polarity
from mechanics_lien.

---

## STEP 1 — Bug 3 sample analysis (wrong party attached)

The translator's `pick_distressed_party()` ranks DEFENDANT > GRANTOR >
other > PLAINTIFF and picks the lowest rank. It is doc-type-blind.

**Sample 1 — CITY OF EL PASO** (owner_type INDIVIDUAL, RESOLVED, 7 signals
FTL+STL). Sample FTL instr 20260017727 raw party:
    TP - Tax Payer | EL PASO LTACH PARTNERS LP
The translator picked the right party ("EL PASO LTACH PARTNERS LP", the
taxpayer). But the lead's owner_name displays "CITY OF EL PASO" — the
EPCAD ownerName search for "EL PASO LTACH PARTNERS LP" FALSE-MATCHED a
City-owned parcel (fuzzy match on "EL PASO"). See Finding 4.

**Sample 2 — UNITED STATES OF AMERICA (TR)** (INDIVIDUAL, RESOLVED, 6
FTL). Sample FTL instr 20260026350 raw parties:
    GR - Grantor | UNITED STATES DISTRICT COURT
    GE - Grantee | SOTO JESUS J
This FTL is GR/GE-typed (6 such records exist). Translator picks GRANTOR
= "UNITED STATES DISTRICT COURT" — WRONG. The debtor is the GRANTEE
"SOTO JESUS J". Lead is misattributed to the federal government.

**Sample 3 — UNIVERSITY MEDICAL CENTER OF EL PASO PATIENT FINANCIAL
SERVICES** (INDIVIDUAL, RESOLVED, **148 signals**, all hospital_lien).
Sample instr 20260000742 raw parties:
    GR - Grantor | UNIVERSITY MEDICAL CENTER OF EL PASO
    GE - Grantee | DIAZ RAUL
Translator picks GRANTOR = the hospital. Every hospital-lien record where
UMC is grantor picks UMC as the party → all resolve to UMC's own EPCAD
parcel → **148 distinct patient debtors collapse into ONE lead**. The
real debtors (DIAZ RAUL, PADILLA ROLAND, QUINTANA LISA R, …) are erased
from the board. This single row is bug 2 + bug 3 together.

**Samples 4-5 — code_lien / mechanics_lien polarity:**
  code_lien raw: GR | TEXAS WORKFORCE COMMISSION ; GE | VILLEREAL
    TRANSPORT EXPRESS LLC. Translator picks GRANTOR = TWC (filer) —
    WRONG; debtor is the GRANTEE business.
  mechanics_lien raw: GR | TORRES ISIDRO ; GE | RT CONTRACTORS LLC.
    Translator picks GRANTOR = TORRES ISIDRO (property owner) —
    CORRECT; mechanics liens happen to have owner=grantor.

Verdict: bug 3 is real for hospital_lien, code_lien, and GR/GE-typed
federal_tax_lien. lis_pendens, judgment_lien, the TP-typed tax liens,
and mechanics_lien are attributed correctly by luck of polarity.

---

## STEP 2 — Bug 1: owner_type classifier gap

Current logic (build_clerk_pipeline.py):

    ENTITY_PAT = re.compile(r"\b(LLC|L\.?L\.?C|INC|CORP|CORPORATION|
      L\.?P\.?|LTD|COMPANY|CO|PARTNERSHIP|HOLDINGS|PROPERTIES|
      INVESTMENTS|BANK|ASS'?N|ASSOCIATION)\b", re.I)
    def classify_owner_type(name):
        if ESTATE_HIGH.search(name): return "ESTATE"
        if TRUST_PAT.search(name):   return "TRUST"
        if ENTITY_PAT.search(name):  return "ENTITY"
        return "INDIVIDUAL"

Missing entity/government patterns:
  - `OWNER` suffix              (JOULE LAS PALMAS OWNER)
  - `CITY OF` / `COUNTY OF`     (CITY OF EL PASO)
  - `UNITED STATES` / `USA`     (UNITED STATES OF AMERICA (TR))
  - `STATE OF` / `COMMISSION`   (TEXAS WORKFORCE COMMISSION)
  - `GROUP`                     (TRIPLE G AUTO GROUP)
  - `ENTERPRISES`               (MERCHANT ENTERPRISES)
  - `PARTNERS` / `LP`           (SIERRA PROVIDENCE MEDICAL PARTNERS;
                                 EL PASO LTACH PARTNERS LP)
  - `MEDICAL CENTER` / `HOSPITAL` / `AUTHORITY` / `DISTRICT` /
    `SERVICES` / `MANAGEMENT` / `FUND` / `REALTY` / `MORTGAGE`

Confirmed impact: 7 of 1,110 leads tagged INDIVIDUAL that are clearly
entities/government — MERCHANT ENTERPRISES, CITY OF EL PASO, UNITED
STATES OF AMERICA (TR), TRIPLE G AUTO GROUP, UNIVERSITY MEDICAL CENTER…,
JOULE LAS PALMAS OWNER, SIERRA PROVIDENCE MEDICAL PARTNERS.

---

## STEP 3 — Bug 2: signal de-duplication state

There is NO de-duplication. The aggregation loop in
build_clerk_pipeline.py does `lead["signals"].append({...})` for every
raw record; the dashboard's `chipsHtml()` renders one chip per signal
entry. Identical (parcel_id, signal_type) pairs are never collapsed.

Confirmed impact:
  - 17 leads carry ≥1 duplicated signal_type chip.
  - 201 redundant signal entries total (would collapse on dedup).
  - Worst row: UMC … PATIENT FINANCIAL SERVICES — 148 hospital_lien
    chips (147 redundant). This row's duplication is a SYMPTOM of bug 3,
    not independent — those 148 are 148 different debtors wrongly merged.
  - Residual genuine duplicates after bug 3 is fixed: ~54 entries across
    ~16 leads (real cases — e.g. one parcel with two judgment liens).

---

## Finding 4 (related, beyond the 3 reported) — fuzzy EPCAD match

The EPCAD enrichment join searches `GetProperties?ownerName=<party>` and
accepts `Properties[0]` unconditionally. EPCAD ownerName is a partial
match, so "EL PASO LTACH PARTNERS LP" returned a parcel owned by "CITY
OF EL PASO". When a lead is RESOLVED, owner_name is overwritten with the
(wrong) EPCAD owner. This corrupts owner display and owner_type even
when bug 3 picked the right party. A match-quality guard is needed
(require a token overlap between the searched name and the returned
EPCAD owner, or reject single-common-word matches like "EL PASO").

---

## Recommended fix order

**1. Bug 3 — party selection (FIRST, root cause).** Replace the global
`rank()` in `pick_distressed_party()` with a doc-type-aware debtor-party
map:
    lis_pendens, judgment_lien      -> DF - Defendant
    federal_tax_lien, state_tax_lien-> TP - Tax Payer, else GE - Grantee
    hospital_lien, code_lien        -> GE - Grantee
    mechanics_lien                  -> GR - Grantor
    affidavit_of_heirship/exec/admin-> GR - Grantor (estate side; lower stakes)
Fix this first because it changes which leads exist and how records
group — bugs 1 and 2 must be re-measured on the corrected data.

**2. Finding 4 — EPCAD match-quality guard (with the bug-3 fix).** Same
function family; add a token-overlap check before accepting an EPCAD
match. Do these two together.

**3. Bug 2 — dedup (SECOND).** After bug 3, collapse identical
(parcel_id, signal_type) signals into one chip carrying an occurrence
count. Residual is small (~54 genuine duplicates).

**4. Bug 1 — owner_type classifier (LAST).** Broaden ENTITY/government
patterns. Independent, cosmetic (badge + filter), 7 leads. Re-measure
after bug 3 because the misclassified-owner set changes.

After bugs 3 + Finding 4, the pipeline must be re-run (the ~35-min EPCAD
enrichment) and the dashboard self-verification repeated.

---

## Estimated impact on the 1,110-lead total

  - Bug 3: ~86 hospital_lien leads + ~14 code_lien leads + ~6 GR/GE-typed
    FTL = roughly 100+ leads currently misattributed to filers
    (hospitals, Texas Workforce Commission, the federal government).
  - The 148-into-1 UMC collapse means ~147 real patient-debtor leads are
    MISSING from the board entirely; smaller collapses exist for code_lien
    (TWC) and the GR/GE FTLs.
  - Net effect of fixing bug 3: the 1,110 total is simultaneously
    inflated (filer pile-up rows) and deflated (missing debtor leads).
    Expect the corrected total to GROW materially — likely into the
    ~1,250-1,300 range as collapsed records re-expand into individual
    debtor leads. Exact figure only known after the re-run.
  - Bug 2: 201 redundant chips today; ~54 remain after bug 3.
  - Bug 1: 7 leads with an incorrect owner_type badge.
  - mechanics_lien (31), lis_pendens (36), judgment_lien (233), TP-typed
    tax liens — attributed correctly today; unaffected by the bug-3 fix.

DATA QUALITY AUDIT COMPLETE — AWAITING OPERATOR DECISION ON FIX ORDER
