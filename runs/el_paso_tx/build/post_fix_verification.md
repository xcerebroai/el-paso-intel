# El Paso clerk_recordings — Post-Fix Verification (v2)

Date: 2026-05-17 · after Fixes 1-3 (commits 2660602, cf4229d, b1a5d78)
and the consolidated pipeline re-run.

## Lead total

    before fixes: 1,110 matched_leads
    after fixes:  1,283 matched_leads   (+173 — collapsed leads re-expanded)

Within the predicted ~1,250-1,300 range.

## Self-verification — local dashboard (§4.21): PASS 9/9

    [PASS] page loads + data-ready=1
    [PASS] rows render, count matches data file (1283 / 1283)
    [PASS] no console errors
    [PASS] signal-type filter works (1283 -> 21 on one type)
    [PASS] owner-type filter works (1283 -> 960)
    [PASS] stacking controls produce different counts (ANY 1283, 2+ 56, 3+ 0)
    [PASS] text search works ('ESTATE' -> 34)
    [PASS] CSV export downloads with data (1284 lines)
    [PASS] distress chips visually distinct from enrichment badges

## Extra semantic checks (Fix 4A)

    [PASS] Bug 2 — no row has a vertical stack of identical-type chips.
           Max DISTINCT chips on any row: 2. Largest same-type group is
           rendered as ONE chip with a "x 10" suffix (was 148 separate
           chips on the UMC row).
    [PASS] Bug 3 — hospital_lien leads now show PATIENT names as owner:
           RODRIGUEZ ELIZABETH, BOETA MARIA D, DIAZ RAUL E, PADILLA ROLAND,
           QUINTANA LISA R, BELTRAN REYMUNDO, SANTOS MARISA G, FUENTES
           LEONOR, CARILLOSOTO CLAUDIA VANESSA, ZAPATA ELFIDA — not
           "UNIVERSITY MEDICAL CENTER".
    [PASS] Bug 3 — leads owned by "UNIVERSITY MEDICAL CENTER*": 0
           (was a single 148-signal collapse row).
    [PASS] Bug 1 — owner_type ENTITY count 287 -> 323 (+36); all 7
           operator-reported names now classify ENTITY.
    [PASS] "CITY OF EL PASO" — 1 lead remains, carrying FTL/STL signals
           only (never had hospital liens).

## Bug status

    Bug 1 — owner_type classifier .......... FIXED + VERIFIED
    Bug 2 — duplicate identical chips ...... FIXED + VERIFIED
    Bug 3 — wrong party (filer vs debtor) .. FIXED + VERIFIED
    Finding 4 — fuzzy EPCAD match .......... FIXED (substantially) + VERIFIED

## Known residual limitations (honest disclosure)

  - EPCAD match guard: the token-overlap guard rejects most false matches
    (resolved count 166 -> 158, false City/US matches removed). It does
    NOT catch one class — names sharing the two common tokens "EL PASO"
    (e.g. "EL PASO LTACH PARTNERS LP" still scores 0.5 token-overlap
    against a "CITY OF EL PASO" parcel). 1 borderline "CITY OF EL PASO"
    lead remains. Treating "EL"/"PASO" as county-local stopwords would
    fix this but is a county-specific tuning choice — left for operator
    review rather than hardcoded.
  - ~8 of 1,283 leads still carry a filer-ish owner name. These are
    edge cases: a few code_lien records have atypical grantor/grantee
    polarity, and some are legitimate (e.g. a business with "HOSPITALITY"
    in its name; a hospital that is itself a judgment debtor). Not a
    systemic misattribution — the 148-record hospital collapse is gone.

## EPCAD enrichment

    resolved 158 / 1283 (12%) · unresolved 1125. The drop from 166 is the
    match guard correctly rejecting fuzzy matches. Name-only join remains
    inherently low-yield for clerk_recordings (no address/parcel id in the
    source); address/parcel-keyed sources will resolve far higher.
