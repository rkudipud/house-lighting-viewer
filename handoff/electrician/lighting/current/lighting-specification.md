# Lighting specification and review handoff

**REVIEW ONLY - NOT FOR CONSTRUCTION.** Homeowner selections establish design direction, not fabrication, product approval, electrical protection or a proven dimming chain.

| Binding | SHA-256 |
|---|---|
| Current house master | `1fa6b0fa040d2f0c81427d9277eb9b98f23170b7f63446f287000d58fc9002a4` |
| Current lighting design-input record (canonical JSON) | `fd3ffb1db7f447566cb1f1b0af2b8ed3b0c5a69ebfe5eb9f9745f8b3632f3fc6` |
| Original photometry calculation input (canonical JSON) | `ca19a7b5cf2c0c92cf3120c95c812567fbdaa3325a7e18b3a132105e66aa604e` |
| Saved analytic heatmap | `e81bf2fbe1819f481c12b45aba9ead3352893f00abeaf6bf3fc1bbf698910b4a` |

The photometric calculations and heatmaps were **not recalculated** for this rebind. Original optical inputs, every fixture position and every room/task result were compared with the verified fixed-white source. The recent changes are status/selection and electrical topology changes. Generic optics, maintenance factor 0.8, estimated geometry and assumed reflectance remain; no measured lux or manufacturer IES/LDT equivalence is claimed.

## Fixed CCT and fitting schedule

All coves, decorative strips and selected curtain strips are **2700 K**. Living, dining and bedroom mains are proposed at **4000 K** for homeowner review; readers and art remain **3000 K**. Kitchen task, utility, dressing and bath face/task lights are **4000 K**. The CCT is fixed by fitting; the controls adjust brightness only. `fixture-ledger.csv` and `fixed-cct-map.json` give each fitting, rule and hold.

| Room | Base fittings | Fixed white bins |
|---|---:|---|
| Living (LIV) | 16 | 6 x 2700 K, 10 x 4000 K |
| Dining + passage (DIN) | 11 | 3 x 2700 K, 4 x 3000 K, 4 x 4000 K |
| Kitchen (KIT) | 13 | 1 x 2700 K, 12 x 4000 K |
| Utility (open-air) (UTL) | 4 | 4 x 4000 K |
| Master bedroom (MBR) | 15 | 5 x 2700 K, 2 x 3000 K, 8 x 4000 K |
| Dressing (DRS) | 2 | 2 x 4000 K |
| Bath 1 (attached) (TL1) | 10 | 3 x 2700 K, 7 x 4000 K |
| Lobby + common basin (LOB) | 4 | 1 x 2700 K, 2 x 3000 K, 1 x 4000 K |
| Bath 2 (common) (TL2) | 10 | 3 x 2700 K, 7 x 4000 K |
| Children's bedroom (CBR) | 14 | 5 x 2700 K, 2 x 3000 K, 7 x 4000 K |
| Balcony / entry court (BAL) | 5 | 3 x 2700 K, 2 x 3000 K |

Base: 104 fittings, 47 controlled groups. Selected extension: four additional curtain strips and four circuit records, with no lux credit. CBR-H1-H6 are shown as switchable review fittings on C37 at their existing locations; the C37 dimmer and other CBR ceiling/bed/desk/site holds remain.

## Curtain pockets: selected, not measured

| Strip | Existing LOW knob | Planned supply | Indicative m | Generic load W |
|---|---|---|---:|---:|
| CURT-LIV | K-LIV-LOW | P01 | 2.45 | 19.60 |
| CURT-DIN | K-DIN-LOW | P07 | 2.45 | 19.60 |
| CURT-MBR-S | K-MBR-LOW | P12 | 2.43 | 19.44 |
| CURT-CBR | K-CBR-LOW | P16 | 1.55 | 12.40 |

Indicative total **8.88 m / 71.04 W** assumes generic 8 W/m and 0.30 m returns. The inherited electrical scenario rounds individual strip loads to 0.1 W, so its per-supply loads differ slightly from the per-pocket figures above. No length is measured from a photo. Confirm pocket width/depth, two tracks, brackets, stack, hidden strip setback, profile, heat, access and cable route by site mock-up (**H-CURTAIN-POCKET**). CBR window is an unmeasured placeholder. MBR W03 is excluded and remains held. A shared LOW knob means the curtain strip cannot be independently off from that room's cove.

## Brightness scenes

These are illustrative settings of the already separate controls, not a claim that the house has a scene controller. Percentages are relative model settings; individual users may adjust. A dash means not specified; `None` accents use the separate accent study. Off and Night have no saved room-grid map.

| Setting | Relative levels |
|---|---|
| Off | all off |
| Mood | COVE 40%, LINE 30%, MOOD 60%, ACCENT see accent study, PERIM 25% |
| Relax | HIGH 30%, COVE 60%, LINE 50%, MOOD 50%, ACCENT see accent study, READ 60%, PERIM 35% |
| Work | HIGH 100%, COVE 50%, TASK 85%, MIRROR 100%, STUDY 100%, READ 100%, PERIM 100%, FACE 100% |
| Full | HIGH 100%, COVE 100%, LINE 100%, MOOD 100%, ACCENT 100%, TASK 100%, MIRROR 100%, STUDY 100%, READ 100%, PERIM 100%, FACE 100% |
| Night | NIGHT 100% |

Bathroom grooming is modeled with the independent face control at 100% and the corresponding HIGH control at 30-50%; the selected face/driver/dimmer chain is unverified.

## Selected S1 controls and supply

Per flat: **21** single-colour brightness knobs, **38** modeled outputs, **3** modeled PWM repeaters, **10** mains-dimmer groups on procurement hold, **12** planned 24 V supplies totaling **1,980 W**. The 104-fitting base alone has 12 supplies / 1,890 W; the S1 overlay includes P07/P12 changes and all four strips. The 48 V track driver is separate.

K-LIV-LOW uses **P01 at 480 W class**, C03/C04/C05/X-CURT-LIV, six modeled outputs and two modeled repeaters. The strip load is **181.52 W / 7.56 A at 24 V**, excluding auxiliary and feeder loss. The reference Mean Well HLG-480H-24 is **not** a selected or approved SKU. `0.60 = 0.80 x 0.75` is only a project planning allowance, not an approved thermal rating.

| PSU | Selected S1 circuits | Planned nameplate W | Generic load W |
|---|---|---:|---:|
| P01 | C03; C04; C05; X-CURT-LIV | 480 | 181.52 |
| P04 | C06A; C06B | 60 | 27.7 |
| P05 | C07; C08 | 100 | 38.6 |
| P06 | C10 | 30 | 8.0 |
| P07 | C12; X-CURT-DIN | 150 | 69.3 |
| P08 | C17 | 150 | 70.6 |
| P10 | C16 | 60 | 31.8 |
| P11 | C19 | 30 | 11.0 |
| P12 | C21; C22; C23; X-CURT-MBR-S | 240 | 110.2 |
| P14 | C27; C28; C29A; C29B; C30A; C30B | 200 | 106.1 |
| P15 | C31; C32; C34; C35A; C35B; C36A; C36B | 240 | 116.1 |
| P16 | C38; C39; C40; X-CURT-CBR | 240 | 121.0 |

**OPEN, no breaker PASS:** the 20 A reference exceeds the candidate T1-K's 12.5 A input nameplate. Distribution, branch and equipment protection, exact chain, low-end dimming/flicker, heat and supply location need licensed electrician and manufacturer design. Old P01/P03 living voltage-drop checks and LT-4/LT-5 inrush screens are invalid. The HLG-480H datasheet and retained installation table disagree on B16/C16 unit limits; obtain manufacturer guidance. P16 remains 121 W on 240 W; modeled S1 C39 3.3% and C40 3.6% are MARGINAL, not a cable-size instruction. `voltage-drop-selected-s1.csv` marks five living sections HOLD and unknown.

## Calculated results: limitations

Kitchen K-2 (KIT-T4 plus KIT-T1 at generic 650 lm/m) retains **518 lx average / 323 lx minimum / U0 0.623** on the modeled worktop. It becomes marginal in the documented lower-reflectance, lower-output or cabinet-offset sensitivity cases. Room grids in `heatmaps.json` and the workbench are at their stated receiver planes; they are not worktop, face or reading measurements. Living LOW and scenes using accent retain an inherited pooja allowance and are not current niche photometry. Pooja display is small idols with a framed picture behind, conceptual only; niche dimensions, light geometry, thermal/fire clearance and support remain held. No final aim or cutting instruction is authorized.

## Site, layout and product holds

| ID | Issue | Before release |
|---|---|---|
| H-MBR-BED | MBR readers R1/R2, books, L2, plates SB-05L/R | tenant bed centreline/headboard rule and measured W04 jamb + curtain stack |
| H-MBR-W03 | MBR W03 (south) curtain pocket | measured section through W03, loft support and pocket (coordination hypothesis, not a certified clash) |
| H-MBR-STACK | W03 +/-0.30 m curtain stack vs split south wardrobe fronts | actual curtain fullness/stack and W03 jambs |
| H-DRS-SWEEP | DRS-H1/H2 (x 19.2 ft) and hatch P14 | actual shutter/loft support sweep (coordination hypothesis) |
| H-UTL-PARAPET | UTL reflectance | measured parapet height/finish |
| H-CBR-CEIL | CBR tray, cove and LINE frame | renderer ceiling/curtain section evidence and the fan selection (u>=2.0 is a project assumption) |
| H-CBR-CURTAIN | CBR west curtain pocket u 3.62-4.572 | measured window/jambs |
| H-CBR-BED | CBR readers R1/R2 and plates SB-08RL/RR | tenant bed; king at the same anchor fails CC-R05-05/12 (case-specific) |
| H-CBR-DESK | CBR-S1 desk strip | joinery drawing (shelf depth, strip lip) |
| H-LOFT | all ceiling items within 0.55 m of loft faces | measured section and hardware sweep; storage to restate loft top/shutter cap on HD-11 levels |
| H-HD11-LEVELS | every ceiling mounting height and the cove/tray step | site-measured FFL-to-band and FFL-to-soffit per room (OI-HEIGHT-01), then rerun |
| H-CENTRE-RECESS | plaster-in LINE profiles and pendant/track fixings in the raised centre panel | product-fit and access check with the selected profile/track: recess depth + fixing + cable bend <= provided cavity; junction boxes and every driver/PSU reachable from a band hatch (no driver above a sealed panel); measured panel level, then rerun (see calculations.hd14.centre_panel_height_sensitivity). No chasing, cutting or fixing into the RC slab is authorised (HD-14) |
| H-HALL-BEAM | fittings on the hall/kitchen beam band z 15.7-19.0 ft | measured beam soffit; if it is below the band, move or surface-mount these fittings |
| H-CEIL-PLACEHOLDER | baths TL1/TL2 2.40, lobby 2.70, balcony 2.70 and utility 2.95 m ceiling levels | homeowner/site levels for the bathrooms, lobby, balcony and utility (OI-HEIGHT-01) |
| H-CURTAIN-POCKET | ceiling fittings next to the two-track curtain pockets (LIV-H2, LIV-H3, DIN-H1; OPT-1 moved them 0.35 ft into the room: 0.193 m clear at the assumed 0.25 m pocket, TIGHT again only if the pocket exceeds about 0.34 m); four homeowner-selected S1 strips remain held for site mock-up and measurement | Measured pocket and track section per window; confirm track/stack/profile fit, strip setback and service access by site mock-up; the 0.25/0.20 m pocket values and 0.30 m returns remain assumptions. |
| H-POOJA-GEOMETRY | LIV-P1/P2 against the current provisional niche geometry | measure the existing cavity/aperture and exterior section; reconcile depth and strip/idol positions; then recalculate and set lengths/aim. No new recess, structural chasing or cutting; no ordering/construction release |

Also retain the ten mains-dimmer compatibility holds, bath-zone/earthing/segregation and dry/wet protection review, P16/C39/C40, inrush, manufacturer photometry, CCT binning, supply derating and electrical surge/environment checks. Qualify construction using measured conditions and local professional approval. OPT-E (BWP carcass, laminate shutters) is selected; the split master wardrobe and the dressing/utility cabinets have unmeasured widths/clearances and are not fabrication-ready.

`generic-product-search.csv` is a generic search list, not an order or current quote. Historical cost and compliance references are clearly labelled; do not use prior P01/P03 supply, output, voltage-drop or breaker totals as current.
