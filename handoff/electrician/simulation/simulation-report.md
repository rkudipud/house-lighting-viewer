# Room-light simulation on master b6f6bf1a (exploratory)

> **Public-copy compute note:** Supplied base and paired sensitivity results are preserved. Execution-host and job details are not distributed. The source receipt's parity diagnostic is excluded from reported results. Original/public hashes and omissions are recorded in `repository-copy-receipt.json`.

**Status:** EXPLORATORY - generic provisional photometry; not product-specific, not measured, not a release. No fitting was moved; nothing was released, published or pushed.

Master `b6f6bf1a127c7e39086deb9fd1d2c0dff79a495381e1a4b9457f6a9a468f23ac` (read-only). Delivered `lighting-current-review` pack unchanged (check E2).

## What was run

| Item | Value |
|---|---|
| Engine | Radiance rcontrib 6.0a (pyradiance wheel bundle) (backward Monte-Carlo ray tracing with full inter-reflection) |
| Settings | ab 8, ad 512, lw 1e-05; -dj 0.7 -ds 0.02 -dt 0 -dc 1 -st 0 -ss 0 -I+ -V+ |
| Output | illuminance (lx) per fitting at every analytic grid point, 0.75 m workplane (task grids at their own heights), MF 0.8 applied |
| Photometry | GENERIC: point fittings = cos^m intensity, m = ln0.5/ln(cos(beam/2)) (min 0.6), catalogue lumens taken as luminaire output; strips = Lambertian 10 mm emitters at catalogue lm/m. No IES/LDT, no product LOR, no cut-off/baffle optics. |
| Surfaces | ceiling 0.8, walls 0.55, floor 0.25, furniture 0.4 (all diffuse, assumed) |
| Geometry | lighting calculation polygons extruded (not surveyed masonry); LIV+DIN one open-plan enclosure; doors/windows/curtains not modelled (walls everywhere); unfurnished except kitchen counters/wall cabinets and the CBR desk shelf |
| Covers | tray recess at tray_h inside the tray path; cove pocket = band slab (12 mm) + lip + outer upstand; strip on the pocket floor facing up at pocket_w/2 outside the tray edge (pocket width and lip unmeasured); kitchen: flat ceiling with a shadow slot slot_w x slot_d outside the cove path; strip on the slot inner face aimed outward (variant: down-facing); slot size unmeasured |

## Independent checks

| Check | Result | Detail |
|---|---|---|
| A1 isotropic point source vs inverse-square cosine law | PASS | {"max_rel_err": 0.00372, "reused": true} |
| A2 cos^m downlight (simulator primitive) vs I0 cos^m law, flux-normalised (-dj 0) | PASS | {"m": 4.819, "max_rel_err": 0.00034, "reused": true} |
| A2b cos^m downlight with production jitter (-dj 0.7): mean of 8 passes vs law | PASS | {"single_pass_max_rel_err": 0.03449, "mean8_max_rel_err": 0.0056, "reused": true} |
| A3 Lambertian strip (simulator primitive) vs exact view factor | PASS | {"sim": 64.165, "exact": 64.133, "reused": true} |
| A4 integrating cube rho 0.5, ab 2: indirect vs truncated series | PASS | {"sim": 1.3807, "expected": 1.3708, "captured_of_infinite": 0.7555, "reused": true} |
| A4 integrating cube rho 0.5, ab 5: indirect vs truncated series | PASS | {"sim": 1.7716, "expected": 1.7706, "captured_of_infinite": 0.9693, "reused": true} |
| A4 integrating cube rho 0.5, ab 8: indirect vs truncated series | PASS | {"sim": 1.8248, "expected": 1.8206, "captured_of_infinite": 0.9984, "reused": true} |
| B0 base run bound to master b6f6bf1a and units declared | PASS | {"master": "b6f6bf1a", "units": {"xyz": "metres; x = plan x_ft*0.3048, y = plan z_ft*0.3048 (sheet-down), z = height above local floor", "E": "lux, maintained (MF applied), per fixture at 100 % output"}} |
| B1 every room with fixtures is simulated | PASS | {"missing": []} |
| B2 fixture accounting: simulated + reported-skipped = all lux-credited fixtures in the master lighting inputs | PASS | {"simulated": 103, "skipped": {"LIV-P1": "inherited pooja U-strip record (x 2.15 ft, z 37.45-40.15 ft, behind the x 2.25 ft wall face) lies outside the canonical niche cavity (z 39.93-41.93 ft); not physically placeable in this geometry - pooja lighting HELD"}, "total": 104} |
| B3 every result vector has one finite, non-negative lux value per point; room grids identical to the analytic heat-map grids/masks | PASS | {"bad": [], "grid_shapes": {"LIV": {"grid": [72, 56], "points": 3733}, "DIN": {"grid": [40, 56], "points": 2240}, "KIT": {"grid": [40, 56], "points": 2240}, "MBR": {"grid": [61, 50], "points": 3050}, "CBR": {"grid": [60, 50], "points": 2724}, "UTL": {"grid": [16, 58], "points": 928}, "DRS": {"grid": [25, 14], "points": 350}, "LOB": {"grid": [22, 14], "points": 308}, "TL1": {"grid": [22, 35], "points": 770}, "TL2": {"grid": [22, 35], "points": 770}, "BAL": {"grid": [32, 42], "points": 1344}}} |
| B4 fixture positions inside their simulated enclosures (known exceptions reported, not moved) | PASS | {"outside": [{"fixture": "LIV-P1", "enclosure": "HALL", "n_outside": 2, "example_ft": [2.15, 37.45]}, {"fixture": "KIT-L1", "enclosure": "KIT", "n_outside": 8, "example_ft": [11.951, 15.451]}]} |
| B5 children's room coverage: L-shaped grid fully masked, H1-H6 simulated and lighting it, desk grid inside the room | PASS | {"H_mean_lx_on_grid": {"CBR-H1": 19.8, "CBR-H2": 23.8, "CBR-H3": 17.8, "CBR-H4": 19.8, "CBR-H5": 20.2, "CBR-H6": 21.7}, "desk_points": 264, "desk_shape": [11, 24], "grid_points": 2724, "poly_ft": [[16.75, 28.2557], [29.25, 28.2557], [29.25, 43.2557], [19.7028, 43.2557], [19.7028, 37.5142], [16.75, 37.5142]]} |
| B6 pooja coverage: canonical niche back/opening planes sampled inside the canonical aperture; inherited records reported | PASS | {"back_shape": [34, 12], "niche_z_m": [12.1690384, 12.7786384], "sill_top_m": [0.4318, 2.1336], "depth_m_HOLD": 0.381, "LIV_P2_aim_ft": [2.05, 38.8, 1.1]} |
| D0 sampling convergence (KIT ab 8: ad 128 vs ad 1024): room-mean difference per fixture | PASS | {"worst_mean_diff_pct": 4.28} |
| D1 sweep baseline sens128-base (ab 8 / ad 128) vs base run (ab 8 / ad 512): room-mean difference for MBR/CBR | PASS | {"max_abs_pct": 1.35} |
| D1 sweep baseline sens512kit-base (ab 8 / ad 512) vs base run (ab 8 / ad 512): room-mean difference for KIT | PASS | {"max_abs_pct": 1.04} |
| D1 sweep baseline sens128hall-base (ab 8 / ad 128) vs base run (ab 8 / ad 512): room-mean difference for LIV/DIN | PASS | {"max_abs_pct": 0.96} |
| E1 master unchanged (b6f6bf1a) | PASS | {"sha": "b6f6bf1a"} |
| E2 delivered lighting-current-review manifest unchanged (a852f200) | PASS | {"sha": "a852f200"} |

**20/20 checks passed.**

Engine accuracy: point source 0.37%, cos^m downlight 0.03% (deterministic); single-pass source jitter up to 3.4% per point (averages out: 8-pass 0.56%); strip 0.05%; integrating cube at ab 8 within 0.3% of the truncated series.

## Rooms: simulation vs delivered analytic model (task area, 100 %)

Values are avg / min / U0 in lux. Grades use the same bands as the analytic pack.

| Room | HIGH sim | HIGH analytic | LOW sim | LOW analytic | HIGH+LOW sim | HIGH+LOW analytic | Grade sim / analytic |
|---|---|---|---|---|---|---|---|
| LIV | 159 / 51 / 0.32 | 152 / 66 / 0.43 | 146 / 65 / 0.45 | 120 / 99 / 0.83 | 305 / 142 / 0.47 | 272 / 172 / 0.63 | MARGINAL / PASS |
| DIN | 159 / 90 / 0.57 | 145 / 89 / 0.61 | 216 / 81 / 0.38 | 199 / 114 / 0.57 | 375 / 186 / 0.50 | 344 / 209 / 0.61 | PASS / PASS |
| KIT | 309 / 105 / 0.34 | 267 / 111 / 0.42 | 86 / 25 / 0.29 | 77 / 77 / 1.00 | 395 / 173 / 0.44 | 344 / 188 / 0.55 | MARGINAL / PASS |
| MBR | 186 / 94 / 0.51 | 164 / 89 / 0.54 | 166 / 84 / 0.50 | 115 / 84 / 0.73 | 352 / 189 / 0.54 | 279 / 177 / 0.64 | PASS / PASS |
| CBR | 144 / 83 / 0.58 | 127 / 78 / 0.61 | 186 / 91 / 0.49 | 142 / 104 / 0.73 | 330 / 202 / 0.61 | 270 / 193 / 0.72 | PASS / PASS |
| UTL | 211 / 175 / 0.83 | 132 / 107 / 0.81 | - | - | - | - | PASS (above band at 100 %; dim) / PASS |
| DRS | 197 / 190 / 0.96 | 157 / 151 / 0.96 | - | - | - | - | PASS / PASS |
| LOB | 264 / 255 / 0.97 | 208 / 202 / 0.97 | - | - | - | - | PASS (above band at 100 %; dim) / PASS (above band at 100 %; dim) |
| TL1 | 257 / 167 / 0.65 | 228 / 159 / 0.70 | 186 / 144 / 0.77 | 159 / 159 / 1.00 | 443 / 311 / 0.70 | 387 / 319 / 0.82 | PASS (above band at 100 %; dim) / PASS |
| TL2 | 257 / 168 / 0.65 | 228 / 159 / 0.70 | 186 / 152 / 0.82 | 159 / 159 / 1.00 | 443 / 320 / 0.72 | 387 / 319 / 0.82 | PASS (above band at 100 %; dim) / PASS |
| BAL | 75 / 49 / 0.65 | 64 / 43 / 0.67 | 54 / 36 / 0.66 | 40 / 31 / 0.78 | 130 / 95 / 0.73 | 104 / 74 / 0.71 | PASS / PASS |

**Reading this:** simulated means are typically 5-25 % above the analytic pack (the analytic model applies an extra 0.85 factor and simpler inter-reflection). Simulated uniformity is lower, especially for coves (the analytic model treats a cove as an even line source). LIV and KIT HIGH drop to U0 0.32-0.34 (MARGINAL vs 0.40): the low points lie 2-3 ft inside the room edge, not a lumen shortfall. The LIV minimum (x 10.6, z 27.4 ft) is at the open-plan boundary with dining; counting the dining fittings, LIV HIGH U0 is 0.51. The KIT minimum is near the x 14.4 ft side (2 ft in). Cheapest response if confirmed on site: aim/spacing review in the next product-specific run, not more lumens. BAL is modelled as an enclosed room, so its numbers are overstated.

## Tasks

| Task | Simulation | Analytic | Target | Finding |
|---|---|---|---|---|
| Kitchen worktop HIGH+TASK 100 % | 647 / 407 / 0.63 | 513 / 333 / 0.65 | 500-750 lx avg, U0 >= 0.60 (EN 12464-1 / criteria pack) | PASS; sink/window end weakest (407 lx min) |
| Children's desk STUDY 100 % | 691 / 376 / 0.54 | 501 / 290 / 0.58 | 500-750 lx, U0>=0.6 | level PASS; U0 slightly short alone |
| Children's desk HIGH+STUDY 100 % | 767 / 458 / 0.60 | 583 / 355 / 0.61 | 500-750 lx, U0>=0.6 | U0 met; avg just above 750 - dim slightly |
| Lobby mirror face Ev HIGH+bar | 398 | 342 | 300-500 lx, U0 0.6 | PASS |
| Pooja idol (canonical niche) ACCENT | 29.3 | HOLD | accent >= 3x surround | HOLD: accent/surround ratio 0.2; LIV-P2 (as recorded) is aimed at the inherited idol point behind the wall face; its beam lands on the wall south of the canonical niche, so the canonical niche receives little accent light. Pooja accent remains HOLD until the niche is measured and the spot aim/strip are re-set. |

## Sensitivity (paired runs: each variant against a baseline at identical sampling)

- `sens128-*` (ab 8 / ad 128) reported for MBR/CBR: baseline vs ad 512 base run MBR:HIGH_100 -0.0 %, MBR:LOW_100 -0.6 %, CBR:HIGH_100 +0.0 %, CBR:LOW_100 -1.4 %; not used (superseded): KIT:HIGH_100 +0.1 %, KIT:LOW_100 +8.9 %.
- `sens512kit-*` (ab 8 / ad 512) reported for KIT: baseline vs ad 512 base run KIT:HIGH_100 -0.0 %, KIT:LOW_100 +1.0 %.
- `sens128hall-*` (ab 8 / ad 128) reported for LIV/DIN: baseline vs ad 512 base run LIV:HIGH_100 -0.5 %, LIV:LOW_100 +1.0 %, DIN:HIGH_100 -0.0 %, DIN:LOW_100 -0.7 %.

KIT rows come from the ad 512 sweep. The ad 128 sweep read the fully indirect slot cove (KIT LOW) about 9 % high, so its KIT rows are superseded and not shown.

| Variant | Room | Sampling | HIGH avg change | HIGH U0 base->var | LOW avg change | LOW U0 base->var | Task (base -> var) |
|---|---|---|---|---|---|---|---|
| beam_minus10 | MBR | ab 8 / ad 128 | 7.9 % | 0.51->0.46 | -0.1 % | 0.46->0.48 |  |
| beam_minus10 | CBR | ab 8 / ad 128 | 8.5 % | 0.58->0.47 | -0.2 % | 0.51->0.44 | avg 767->771, min 465->461 |
| beam_minus10 | KIT | ab 8 / ad 512 | 6.9 % | 0.34->0.28 | -0.3 % | 0.4->0.41 | avg 647->680, min 407->436; KIT cove avg 87->86 |
| beam_minus10 | LIV | ab 8 / ad 128 | 0.6 % | 0.31->0.22 | 0.0 % | 0.38->0.34 |  |
| beam_minus10 | DIN | ab 8 / ad 128 | 8.3 % | 0.56->0.5 | 2.5 % | 0.38->0.34 |  |
| beam_plus10 | MBR | ab 8 / ad 128 | -7.0 % | 0.51->0.55 | 0.1 % | 0.46->0.46 |  |
| beam_plus10 | CBR | ab 8 / ad 128 | -7.4 % | 0.58->0.64 | -0.0 % | 0.51->0.48 | avg 767->762, min 465->472 |
| beam_plus10 | KIT | ab 8 / ad 512 | -6.3 % | 0.34->0.39 | 0.2 % | 0.4->0.41 | avg 647->621, min 407->373; KIT cove avg 87->87 |
| beam_plus10 | LIV | ab 8 / ad 128 | -1.6 % | 0.31->0.38 | 0.6 % | 0.38->0.34 |  |
| beam_plus10 | DIN | ab 8 / ad 128 | -7.5 % | 0.56->0.62 | -1.3 % | 0.38->0.36 |  |
| ceil_minus0.1 | MBR | ab 8 / ad 128 | 2.3 % | 0.51->0.5 | 3.5 % | 0.46->0.4 |  |
| ceil_minus0.1 | CBR | ab 8 / ad 128 | 2.4 % | 0.58->0.55 | 3.2 % | 0.51->0.47 | avg 767->771, min 465->467 |
| ceil_minus0.1 | KIT | ab 8 / ad 512 | 2.5 % | 0.34->0.32 | 3.7 % | 0.4->0.35 | avg 647->665, min 407->433; KIT cove avg 87->90 |
| ceil_minus0.1 | LIV | ab 8 / ad 128 | 1.1 % | 0.31->0.3 | 3.5 % | 0.38->0.33 |  |
| ceil_minus0.1 | DIN | ab 8 / ad 128 | 2.8 % | 0.56->0.56 | 3.3 % | 0.38->0.32 |  |
| ceil_plus0.1 | MBR | ab 8 / ad 128 | -2.2 % | 0.51->0.52 | -3.2 % | 0.46->0.43 |  |
| ceil_plus0.1 | CBR | ab 8 / ad 128 | -2.4 % | 0.58->0.6 | -3.6 % | 0.51->0.47 | avg 767->763, min 465->464 |
| ceil_plus0.1 | KIT | ab 8 / ad 512 | -2.4 % | 0.34->0.36 | -4.7 % | 0.4->0.37 | avg 647->632, min 407->388; KIT cove avg 87->83 |
| ceil_plus0.1 | LIV | ab 8 / ad 128 | -0.8 % | 0.31->0.32 | -3.1 % | 0.38->0.34 |  |
| ceil_plus0.1 | DIN | ab 8 / ad 128 | -2.8 % | 0.56->0.59 | -2.2 % | 0.38->0.36 |  |
| pocket_narrow | MBR | ab 8 / ad 128 | 0.1 % | 0.51->0.5 | -8.5 % | 0.46->0.39 |  |
| pocket_narrow | CBR | ab 8 / ad 128 | 0.0 % | 0.58->0.58 | -7.9 % | 0.51->0.46 | avg 767->767, min 465->472 |
| pocket_narrow | LIV | ab 8 / ad 128 | 0.1 % | 0.31->0.32 | -11.1 % | 0.38->0.32 |  |
| pocket_narrow | DIN | ab 8 / ad 128 | 0.0 % | 0.56->0.57 | -3.8 % | 0.38->0.35 |  |
| pocket_wide | MBR | ab 8 / ad 128 | -0.0 % | 0.51->0.5 | -3.2 % | 0.46->0.47 |  |
| pocket_wide | CBR | ab 8 / ad 128 | -0.0 % | 0.58->0.58 | -3.1 % | 0.51->0.49 | avg 767->767, min 465->467 |
| pocket_wide | LIV | ab 8 / ad 128 | -0.1 % | 0.31->0.31 | -5.3 % | 0.38->0.36 |  |
| pocket_wide | DIN | ab 8 / ad 128 | -0.0 % | 0.56->0.56 | -2.9 % | 0.38->0.38 |  |
| rho_high | MBR | ab 8 / ad 128 | 13.3 % | 0.51->0.56 | 25.8 % | 0.46->0.53 |  |
| rho_high | CBR | ab 8 / ad 128 | 13.6 % | 0.58->0.62 | 24.2 % | 0.51->0.54 | avg 767->835, min 465->518 |
| rho_high | KIT | ab 8 / ad 512 | 16.8 % | 0.34->0.41 | 39.8 % | 0.4->0.49 | avg 647->753, min 407->500; KIT cove avg 87->121 |
| rho_high | LIV | ab 8 / ad 128 | 17.2 % | 0.31->0.38 | 23.0 % | 0.38->0.43 |  |
| rho_high | DIN | ab 8 / ad 128 | 11.3 % | 0.56->0.61 | 13.8 % | 0.38->0.41 |  |
| rho_low | MBR | ab 8 / ad 128 | -8.3 % | 0.51->0.47 | -22.1 % | 0.46->0.38 |  |
| rho_low | CBR | ab 8 / ad 128 | -8.7 % | 0.58->0.55 | -20.9 % | 0.51->0.42 | avg 767->707, min 465->430 |
| rho_low | KIT | ab 8 / ad 512 | -11.3 % | 0.34->0.29 | -35.8 % | 0.4->0.28 | avg 647->571, min 407->343; KIT cove avg 87->56 |
| rho_low | LIV | ab 8 / ad 128 | -12.3 % | 0.31->0.24 | -22.1 % | 0.38->0.35 |  |
| rho_low | DIN | ab 8 / ad 128 | -8.2 % | 0.56->0.53 | -11.9 % | 0.38->0.31 |  |
| kit_extend | KIT | ab 8 / ad 512 | -1.1 % | 0.34->0.34 | 11.6 % | 0.4->0.43 | avg 647->641, min 407->395; KIT cove avg 87->97 |
| kit_slot_down | KIT | ab 8 / ad 512 | 0.0 % | 0.34->0.34 | 69.1 % | 0.4->0.31 | avg 647->647, min 407->410; KIT cove avg 87->146 |

Linear scalings (no rerun): lumens +/-20 % -> linear: every value x0.8 / x1.2 (no rerun needed); MF 0.7/0.9 -> linear: every value x0.875 / x1.125 relative to MF 0.8.

**Not run:** sensitivity for utility, dressing, lobby, baths and balcony (small rooms; MBR/CBR/HALL stand in for the tray/cove construction). All planned MBR/CBR/KIT/LIV/DIN variants completed.

## Limitations and what stays held

| Topic | Status |
|---|---|
| Photometry | Generic shapes only; no IES/LDT files for selected products exist (no products selected). Real cut-off, LOR and beam tails will change point values and glare; NOT product-specific validation. |
| Reflectances | Assumed; paint/tile LRV unselected. Glossy floor specularity not modelled. |
| Geometry | Lighting polygons, not surveyed masonry; no doors/windows/curtains; mostly unfurnished; cove pocket, kitchen slot and pooja niche depth unmeasured (sensitivity shows their effect). |
| Pooja | HELD: LIV-P1 strip record lies outside the canonical niche; LIV-P2 aim misses the canonical niche. Re-aim/re-set after niche measurement. |
| Kitchen cove KIT-L1 | Path overruns the kitchen polygon by 0.4 ft (reported, not moved); result depends strongly on the unmeasured slot. |
| Balcony | Enclosed model overestimates (open sides lose light). |
| Curtain strips | Excluded - no lux credit, pockets unmeasured, mock-up hold remains. |
| Glare / UGR, daylight, flicker, thermal | Not computed by this run. |
| Approvals | construction_release, product_approval and exact_chain_proven remain false; this run does not change any hold. |

## Files

| File | Purpose |
|---|---|
| `sim_radiance.py` | simulator (hash-guards the master) |
| `cosm.cal` | cos^m intensity function |
| `check_sim.py` | independent checks + analysis |
| `runs/base/sim-results.json` | base per-fitting lux vectors |
| `analysis/sim-summary.json` | summary |
| `analysis/checks.json` | check results |
| `analysis/sim-heatmaps.json` | simulated heat-map grids |
| `simulation-receipt.json` | hashes |
