# El Paso County — v5 Semantic Verification

Target: https://xcerebroai.github.io/el-paso-intel/
Generated: 2026-05-18T19:57:10Z
lead_total: 1646  ·  actionable: 1633  ·  review_required: 13  ·  EPCAD resolved: 514

## Result: 19/19 checks passed

| Check | Result | Detail |
|---|---|---|
| 'CITY OF EL PASO' never appears as owner_name | PASS |  |
| 'TEXAS WORKFORCE COMMISSION' never appears as owner_name | PASS |  |
| 'THE HOSPITALS OF PROVIDENCE' never appears as owner_name | PASS |  |
| 'UNIVERSITY MEDICAL CENTER' never appears as owner_name | PASS |  |
| 'ROCKY MOUNTAIN MORTGAGE' never appears as owner_name | PASS |  |
| REVIEW_REQUIRED rows show placeholder owner (filer never owner) | PASS | (13 review rows, 9 with filer_entity captured) |
| 'MARIO AYALA REAL ESTATE GROUP LLC' -> ENTITY | PASS | owner_type=ENTITY |
| foreclosure rows are property-identifiable (addr or legal) | PASS | 348/357 |
| no hospital_lien row owned by a hospital entity | PASS | (249 hospital rows) |
| no ESTATE owner_type is a real-estate company | PASS | (51 estate rows) |
| page renders, lead count matches data.json | PASS | rendered=1646 |
| no console / page errors | PASS |  |
| all preset quick-views run without error | PASS |  |
| preset 'Foreclosures next 21 days' matches data | PASS | ui=103 data=103 |
| preset 'Estate-titled properties' matches data | PASS | ui=51 estate-leads=51 |
| detail panel expands on row click | PASS |  |
| mark-for-review persists across reload (localStorage) | PASS | markedCount=1 |
| sale-date sort surfaces foreclosure rows at top | PASS |  |
| export filtered CSV fires a download | PASS |  |

