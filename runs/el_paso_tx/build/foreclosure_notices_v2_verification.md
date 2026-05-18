# clerk_recordings dashboard — Self-Verification (§4.21)

Verdict: **PASS**  (9/9 checks passed)
Target: local dashboard (file:///Users/quentinflores/Dev/xcerebro/counties/el-paso-intel/dashboard/index.html)
Expected leads: 1640

## Checks

- [PASS] page loads + data-ready=1 — dashboard booted
- [PASS] rows render, count matches data file — rendered 1640 vs expected 1640
- [PASS] no console errors — 0 error(s): []
- [PASS] signal-type filter works — all-types=1640, one-type=21
- [PASS] owner-type filter works — 1640 -> 1315
- [PASS] stacking controls produce different counts — ANY=1640, 2+=56, 3+=0
- [PASS] text search works — search 'ESTATE' -> 68
- [PASS] CSV export downloads with data — 1641 lines, header: owner_name,owner_type,property_full_address,property_city,pr
- [PASS] distress chips visually distinct from enrichment badges — chip bg=rgb(220, 38, 38), badge bg=rgba(0, 0, 0, 0), badge border=solid
