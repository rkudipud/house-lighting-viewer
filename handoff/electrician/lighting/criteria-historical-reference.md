> HISTORICAL RESEARCH REFERENCE: the rev 3.3 room comparison, tunable options and prior schedules below are not the current selected layout. Use lighting-specification.md and the current schedules for design review.

# Lighting criteria and combinations - Hyderabad 2BHK

Prepared 17 November 2026. **Data ready for the next design step; not a purchase, construction, health or statutory-compliance certificate.** Applies to one flat, to be checked separately before repeating across four storeys. Audit updated to the coordinator's authoritative **lighting model rev 3.3**, superseding the initial rev 3.2 comparison; no source files or solver edited.

**Main result:** general brightness is mostly sensible. Fix distribution before adding watts: kitchen worktop uniformity fails, children's HIGH uniformity fails, bedroom wardrobe light is low, full-output art accents are too strong, and several important task-plane checks are missing. Rev 3.3 includes the flat kitchen ceiling and flush pooja; their built geometry and optical performance remain provisional.

## 1. What the numbers mean

| Term | Plain meaning / how to use it |
|---|---|
| lm; lm/m; lm/m2 | Light emitted by a luminaire; strip output per metre; installed output per room area. None equals the lux reaching a task. |
| Eavg, Emin; U0 | Average and minimum illuminance on a stated surface; U0 = Emin/Eavg on the **same grid and scene**. |
| Ev; Ez | Vertical illuminance on a face; cylindrical illuminance averaged around a person. A single forward-facing Ev is not Ez. |
| Maintained lux | Light expected at the end of the chosen maintenance interval, not new-installation brightness. |
| Luminance | Surface brightness seen by an observer, in cd/m2. Lux ratios only approximate brightness ratios when reflectances match. |
| PASS / MARGINAL / FAIL | Meets the specified model check / missing evidence or a commissioning correction / numerical design shortfall. Not BIS/NBC certification. |

Assumptions: typical family without a known special visual need; useful task lighting rather than bright whole-house ceilings; measured daylight not available. Offer more local light for older eyes or small/low-contrast print. Do not prescribe medical treatment.

Model assumptions are MF=0.8, scalar reflectance RHO=0.45, cove UF=0.2, CAL=0.85, band=2.70 m and tray=2.88 m; slab=3.08 m comes from the brief. All eight kitchen downlights are now at 2.88 m. The flush pooja cavity is hypothetical at 115 mm, requiring structural sign-off. Coordinates are in feet. The survey is not an as-built. Room averages exclude a 0.5 m wall border: useful counter, wardrobe and door-edge tasks must be checked separately.

**Evidence labels:** **V** = stated claim verified from the cited public source; **V-secondary** = verified through an identified technical secondary source; **P** = this project's residential design choice, not a quoted statutory value; **UNVERIFIED** = original edition/clause/value was not accessible or checked. Publisher descriptions and tables of contents do not verify paid numerical tables.

## 2. Room and task criteria

All bands below are **P**, maintained values, excluding daylight for the electric-light check. Exceptions explicitly identified below are the EN office-task benchmark adopted by analogy. The upper end is an operating preference, not a safety ceiling. U0 applies to functional scenes, not deliberately dramatic accents.

| Room / task | Acceptable band; aim | Surface / uniformity | Basis |
|---|---|---|---|
| Living HIGH | 100-200 lx; aim 150 | Horizontal 0.75 m; U0 >=0.40 | P; SLL/LG9 framework [R2,R3] |
| Living LOW / social faces | 30-80 lx horizontal; face Ev 50-150 lx when socialising | Seated eyes ~1.2 m; record Ez separately; aim Ez >=50 lx, U0 >=0.10 | P; directional/cylindrical principles [R1] |
| Dining general / table | 100-200 / 200-300 lx | Table ~0.75 m; table U0 >=0.60, general >=0.40 | P [R2,R3] |
| Kitchen general | 200-300 lx | Usable 0.9 m plane; U0 >=0.40 | P [R2,R3] |
| Kitchen preparation | 500-750 lx; aim 500 | Actual counters ~0.9 m, including ends/sink/hob; U0 >=0.60 | P, demanding-task analogy to [R1]; not an EN domestic-kitchen quotation |
| Utility general / counter | 100-200 / 200-300 lx | Floor for movement; counter ~0.9 m; U0 >=0.40 / >=0.60 | P [R3]; raise task to 500 for fine repair/ironing |
| Master / children's general | 100-200 / 120-200 lx | Horizontal 0.75 m; U0 >=0.40 | P [R2,R3] |
| Bedroom LOW | 20-60 lx | Horizontal reference plane; lower for pre-sleep | P; eye exposure is a separate check [R5,R6] |
| Study / sustained reading | 500-750 lx; aim 500 | Actual desk/book, usually ~0.75 m; U0 >=0.60 | 500 lx and U0=.60 office-task benchmark V-secondary [R1]; upper band P |
| Short relaxed reading | 300-500 lx | Tilted book at actual seated/reclined position; U0 >=0.60 | P; switch to sustained-reading criterion for homework/small print |
| Dressing general / wardrobe | 150-300 lx / vertical 150-300 lx | General ~0.75 m; wardrobe usable front, U0 >=0.40 | P [R2,R3] |
| Dressing / bath grooming | Face Ev 300-500 lx | Face grid ~1.2 m seated, ~1.5-1.6 m standing; U0 >=0.60 | P; frontal light, not basin lux |
| Bath general / shower | 150-250 / 150-300 lx | Floor, dry and shower areas separately; U0 >=0.40 | P [R3] |
| Basin task / bath LOW | 300-500 / 20-60 lx | Basin horizontal / floor mood grid; basin U0 >=0.60 | P [R3] |
| Lobby / shared washbasin | 100-150 lx circulation; Ev 200-300 lx casual face washing | Floor / face; general U0 >=0.40 | P; hallway 100 lx benchmark V-secondary [R1a]. Use 300-500 for grooming |
| Balcony movement | 30-75 lx; aim 50 | Floor, including threshold; U0 >=0.40 | P [R3]; avoid light spill to neighbours |
| TV viewing | Ambient horizontal 10-50 lx, adjusted to screen brightness | No source reflected in screen; surrounding wall luminance low and comfortable | P; no HDR/display-calibration claim |
| Art / pooja, non-sensitive objects | Total target-surface illuminance about 3-5 times ambient-only **at that surface**; start ~150-300 lx | Vertical object and adjacent background; record peak/average and reflectance | P; accent, not uniform wallwash. Sensitive art requires its own conservator limit |
| Night route | Floor average 1-5 lx and minimum >=1 lx along the **actual route** | Bedroom-bed exit to bathroom, thresholds and turns; no dark gaps | P; not emergency escape lighting; eye exposure also checked [R6] |

For a 500 lx desk, adopt ~300 lx in its immediate surrounding work area where practical, rather than a bright desk in a dark room. This is a project design choice here; original EN surrounding-area table is **UNVERIFIED**. Do not apply a room-wide 500 lx requirement to bedrooms.

## 3. Colour, eyes and comfortable brightness

| Item | Procurement / commissioning target | Important limit |
|---|---|---|
| Colour rendering | Ra/CRI >=90 and R9 >=50 for occupied interiors; prefer Ra>=95, R9>=80 at art, pooja, food and grooming | P. Ra excludes saturated-red R9; high Ra alone is insufficient. |
| TM-30 | Prefer Rf>=90, Rg 95-105; request full report and red-hue fidelity/vector graphic at each CCT | P, not a claimed TM-30 mandatory acceptance limit. Exact TM-30 edition/report clauses UNVERIFIED [R11]. |
| White consistency | Initial SDCM <=3 within each continuous run and matched group; same batch/bin; record replacement bin | P. It does not guarantee colour stability over life or when dimmed. |
| Day / task | 3500-4000 K for kitchen/study/grooming; 3000-4000 K general at user preference | CCT is not brightness or a circadian dose. 6500 K is not necessary for useful study light. |
| Evening / pre-sleep | 2700-3000 K social; 2200-2700 K dim-to-warm optional before sleep; night 2200-2700 K | Keep light reaching eyes low; dimming fixed-white LEDs does not normally change their CCT. |
| Multi-CCT options | Simplest: fixed 4000 K HIGH + fixed 2700/3000 K LOW, independently dimmed. Optional tunable 2700-4000 K via matched dual-white controller; matched dim-to-warm HIGH is another option | Blending separate fixed whites is **not** calibrated tunable white. Installer 3-CCT selection or power-cycle colour change is not proof of dimming. |
| Continuous ceiling plane | Match adjacent cove and lit groove to one chosen white (2700 or 3000 K); use the same choice along connected living/dining cove | Functional neutral task light may differ deliberately; avoid random neighbouring 2700/3000/4000 K segments. |
| Melanopic EDI | Calculate at the eye from spectrum: mEDI = vertical photopic lux x melanopic DER | CIE S 026 is metrology, not a prescription [R5]. Reflected spectra matter; CCT/CRI/room lux cannot establish mEDI. |
| Healthy-adult exposure context | Brown et al. recommend daytime >=250 lx mEDI, <=10 for the 3 hours before bed, and <=1 during sleep | V [R6]; daylight is the first daytime resource. Not universal medical/child/elderly thresholds; visual safety takes priority while moving. |
| WELL | Legacy WELL v1 Feature 54 Part 2 uses 200 EML day / <=50 EML night at specified heights | V for that legacy web feature only [R7]. EML is not numerically interchangeable with S 026 mEDI; current WELL v2 thresholds UNVERIFIED. No WELL claim. |

Example only: if a source's measured melanopic DER is 0.5, 250 mEDI needs 500 photopic lx **at the eye**, not on the desk. A 150 lx room-average model therefore cannot prove daytime circadian adequacy. No spectrum or eye grid is present in rev 3.3.

| Glare / reflection issue | Design response |
|---|---|
| UGR | Aim calculated UGR <=19 at study; <=22 is a project screening goal for other functional seated areas. The 19 office benchmark is V-secondary [R1]; 22 is P. A product marked "UGR<19" is not a room result; UGR is observer/layout dependent and may not suit small accent sources. |
| Shielding | Trial deep-recess optics (~25-40 mm recess) with at least ~30 degrees shielding measured above horizontal; verify the manufacturer's angle convention. These dimensions are P, not verified EN minimums. Confirm source is hidden from sofa/bed sightlines. |
| Glossy vitrified tiles | Light-coloured glossy tile can still mirror bright LED dots. Use broader/lower-luminance sources, position outside dominant reflected sightlines, and inspect while seated and standing. LRV does not describe specular glare. |
| TV / glass art | Do not aim gimbals at the screen. Switch/dim TV-wall accents separately; check black screen from every seat. Shift/aim art spots until reflections miss the viewer; begin ~30 degrees from vertical as a mock-up, not a universal rule. |
| Mirrors | Diffused face bars at the sides/front; avoid exposed dots visible in mirror. Downlights over the head are not substitutes for face light. |
| Brightness balance | Near a task, start with task-to-immediate-surround luminance <=3:1 and task-to-distant-background <=10:1; P comfort heuristics, not certified thresholds. Dim accents and light a little background rather than flooding everything. |
| Fan shadows | Keep beams clear of blade sweep where practicable; test actual fan at all speeds. A low-flicker driver cannot eliminate mechanical chopping. |

## 4. Reflectance, lumens and layout calculations

| Surface | Planning reflectance / LRV | Action |
|---|---|---|
| Matte ceiling / inside cove | rho 0.80-0.90 / LRV 80-90 | Obtain paint LRV; keep reflector surface light and clean. |
| Light walls | rho 0.50-0.70 / LRV 50-70 | Use measured/declared values; don't infer from "cream" or "white". |
| Floor | Diffuse rho 0.20-0.40 initially | Measure/select actual tile; model gloss separately. |
| Black groove | rho about 0.05 / LRV about 5 | Assumption, not a paint measurement. Keep black on decorative visible edges, not on the main cove reflector. |

All ranges are P, not quoted EN reflectance tables. For a diffuse surface, **L = E x rho / pi** [R1, Figure 2]. At 100 lx, rho=.80 gives ~25.5 cd/m2; rho=.05 gives ~1.6 cd/m2: a 16:1 brightness contrast at equal illuminance. A narrow black groove does not reduce whole-room light by 94%; its area, position and view factors determine loss.

**Lumen method:** Eavg = total delivered luminaire lm x CU x MF / area. CU (coefficient of utilisation) depends on geometry, distribution and surface reflectances; do not substitute rho for CU. Count diffuser/profile losses once. For illustration, 150 lx at MF=.8 needs 313 lm/m2 if CU=.6, but 469 lm/m2 if CU=.4: a 50% lumen increase. Actual dark-wall CU must be calculated, not assumed.

| Use | Starting installed output, not a pass/fail criterion |
|---|---|
| Living / bedroom HIGH | ~200-450 delivered lm/m2 |
| Kitchen general HIGH | ~400-650 delivered lm/m2, plus local counter light |
| Bath / dressing general | ~300-650 delivered lm/m2; small rooms can need more because of edge losses |
| Balcony general | ~100-200 delivered lm/m2 |
| Indirect LOW | ~150-400 source lm/m2 with provisional CU=.2, MF=.8 -> ~24-64 lx; geometry can change this greatly |

Rev 3.3 HIGH emits ~322 lm/m2 living, 261 dining, 455 kitchen, 223 master and 248 children. Utility ~617 and lobby ~652 warrant efficacy/placement review rather than automatic failure.

### Beam spread is not a spacing guarantee

For a symmetric beam at perpendicular distance H, **D = 2H tan(beam angle/2)**. D is the nominal beam footprint (usually at half peak intensity), not a sharp lit/unlit boundary. Off-axis illuminance needs intensity data and the cosine law, not lumen/spot-area alone.

| Beam | D/H | D at H=1.95 m (2.70 m ceiling minus 0.75 m task) | Conservative trial S/H ceiling for a general-light grid |
|---|---:|---:|---:|
| 24 degrees | 0.425 | 0.83 m | 0.35; normally accent only |
| 36 degrees | 0.650 | 1.27 m | 0.50; not preferred for whole-room HIGH |
| 50 degrees | 0.933 | 1.82 m | 0.75 |
| 60 degrees | 1.155 | 2.25 m | 0.90 |
| 70 degrees | 1.400 | 2.73 m | 1.10 |
| 90 degrees | 2.000 | 3.90 m | 1.25 |

S/H values are **P layout starting caps only**, not IES spacing criteria or a derived uniformity proof. Use the tighter of these starts and manufacturer spacing criteria, then verify the entire grid with IES/LDT photometry. A 60-degree start gives S<=1.76 m at H=1.95 m. Recess/honeycomb/tilt can change the distribution.

For a smooth wallwash, begin with a true asymmetric wallwasher ~0.25-0.33 x wall height away (~0.68-0.89 m for 2.70 m), spacing no greater than the setback until photometry supports otherwise. These are P mock-up values. Near-wall narrow spots produce scallops; either use closer overlap/wider wallwash optics or accept a deliberate accent. A gimbal is not automatically a wallwasher. Very close grazing intentionally reveals texture and wall defects.

### Cove / linear starting specification

| Item | Practical starting range / decision |
|---|---|
| Hidden tray cove | 24 V, 600-1000 source lm/m, roughly 6-10 W/m; existing 720 lm/m at 8 W/m is a plausible start, not guaranteed output |
| Exposed lit groove / flat-ceiling perimeter | Diffused aluminium profile, ~400-800 **delivered** lm/m, roughly 6-10 W/m; separate photometry from an indirect cove |
| Under-cabinet | ~800-1200 delivered lm/m, often 8-14 W/m depending on efficacy/profile; front-offset under cabinet to avoid body shadow; avoid reflected line on polished stone |
| Tray mock-up geometry | Start pocket usable width ~100-150 mm, strip setback behind lip ~50-100 mm, optical rise to reflecting surface ~75-150 mm, shielding lip ~30-50 mm; measure actual section before adoption |
| Ceiling height constraint | Existing band-to-tray difference is only 180 mm; the ranges are not additive construction dimensions. A joiner/lighting sample must prove fit, hiding, heat dissipation and access. |
| COB vs SMD | COB makes a close-view continuous line easier; high-density SMD with adequate mixing distance/diffuser can be equally good. Neither guarantees CRI, life or dimming. |
| Diffuser or open | Fully hidden indirect cove may omit diffuser after mock-up, improving output; use diffusion where source/reflected dots can be seen. Measure transmission; do not assume 100%. |
| Uniformity | Inspect straight run, corners, joins and end feeds at minimum/maximum dim; consistent bins, level mounting, adequate mixing depth. Longer strips need electrical voltage-drop design, not just a bigger PSU. |
| White | 2700 K intimate / 3000 K slightly crisper; one choice per continuous cove and adjacent LINE. |
| Flat kitchen revision | Rev 3.3 raises all downlights to 2.88 m and describes a perimeter shadow-slot pocket; it retains the 8.82 m strip path, UF=.2 and LOW77 lx. Accept these only as provisional inputs. Confirm whether the built section is indirect, direct or grazing and replace the uniform-cove approximation with its actual distribution. |

## 5. Dimming, durability and safety

| Requirement | Target / evidence to ask for |
|---|---|
| Wall-first control | Independent local HIGH and LOW controls wherever both lanes exist. No cloud dependency. Rev 3.3 Option A leaves several HIGH circuits switched-only: this is a requirement gap, not something a software slider fixes. |
| Dimming depth | Stable measured 5-100% light output minimum for HIGH; prefer 1-100%. LOW prefer 1-100%; night circuits may require still lower dedicated output. Test start-up at minimum, off glow, pop-on, dropout, audible noise and power-restoration state. |
| Compatibility | Exact luminaire + driver + dimmer + load-count approval; minimum and maximum LED load, inrush/derating and leading/trailing edge. A fan regulator or incandescent watt rating is not approval. Do not stack independent power dimmers. |
| PWM | Prefer measured low-modulation/current dimming where available; if PWM, project preference >=3 kHz, preferably >=4 kHz for deep-dim strips. Frequency alone proves neither low flicker nor camera compatibility; 100 Hz mains ripple can coexist. |
| Flicker metrics | Specify PstLM<=1 and SVM<=0.4 at full, 50%, 10% and minimum usable output, at all CCT endpoints/mixes. EU full-load benchmark is verified [R10]; extending it to dimming is P, not an Indian statutory limit. |
| Metric limits | IEC TR 63158 SVM scope is typical indoor >100 lx and moderate movement [R9]. At very low levels record waveform/modulation and visual results too; don't label a night light "safe" from SVM alone. Phone slow-motion is only a screening test. IEEE 1789-2015 is now Inactive-Reserved [R8]. |
| LED maintenance | Target projected L70 >=50,000 h, based on traceable LM-80 results and a TM-21 projection at applicable LED temperature/current [R12]. Ask test duration, sample count, extrapolation limit and report edition; don't accept an unsupported 50,000 h sticker. |
| Whole-system life | L70 is lumen maintenance, not 70% units surviving, a B50 claim, driver lifetime or warranty. Ask driver survival/life at declared tc, chromaticity drift, connector/optic ageing and replaceability. |
| Hyderabad temperature | Design scenario: outside/void may exceed 40 C; verify actual worst-case occupied top-floor void. Prefer equipment rated for at least 45 C ambient, 50 C where measured conditions require; never exceed rated ta/tc. Ratings are P selection starting points, not measured site conditions. |
| Thermal management | Aluminium profile with good thermal contact for strip; do not bury drivers in insulation or sealed gypsum. Provide accessible, ventilated service positions and obey manufacturer clearances. IP encapsulation can worsen heat. |
| Capacitors / derating | Request PSU derating and lifetime curves. The common approximately 2x life per 10 C cooler electrolytic heuristic is not a driver guarantee; ripple, hotspot temperature and component construction matter. |
| PSU capacity | Run at <=70-80% of the manufacturer's **temperature-derated usable continuous rating**. Check tunable-white worst case and controller channel limits. Current budget's nominal loads ~34-72% are promising, not thermal approval. |
| Supply / surge | Specify operation over at least 207-253 V AC (230 V +/-10%) at 50 Hz as a project procurement envelope, not a verified utility guarantee. Request broader range if site measurement warrants, over/under-voltage behaviour and declared surge test ratings/modes. Protection coordination belongs to the electrical engineer. |
| Wet / outdoor | Planning targets: bath general IP44 minimum outside direct wet exposure; prefer IP65 where splashes/cleaning exposure justify it. Utility and exposed balcony IP65, utility preferably IK08; sheltered balcony IK06 where impact exposure warrants. IP67 only for genuinely required immersion exposure, not a substitute for IPX5 jet performance. |
| Installed protection | IP applies to the complete installed assembly, including ends/connectors/glands and orientation. IP alone does not establish safe bathroom voltage/zone suitability. 24/48 V alone does not prove SELV. |
| BIS documents | Verify exact model registration and applicable category: IS 15885 Part 2/Sec 13 controlgear, IS 16103 Part 1:2012 standalone LED modules; luminaire categories under IS 10322 Part 5, including Sec 2:2012 recessed [R4]. Recheck active editions/transitions; BIS registration is not CRI/dimming/life evidence. |
| Access / cleaning | Hatches sized to remove the largest driver, without cutting gypsum; labels and approved isolation by electrician. Inspect/clean indoor optics and coves initially every 6-12 months; dustier utility more often. Confirm MF with that maintenance plan. |
| MF versus 50,000 h | MF=.8 cannot automatically represent L70 end of life: .70 LED maintenance x .90 dirt factor = .63 before other losses. If MF=.63 rather than .8, predicted lux falls to 78.75% of rev 3.3. Define replacement/cleaning interval, not an unqualified lifetime lux promise. |
| Spares / warranty | Common cutouts, accessible replaceable drivers; hold ~5-10% matching light/strip spares and at least one approved driver per family across four flats. Seek 3-5 year written India warranty, authorised invoice, local claim route, exclusions for surge/heat/humidity and labour/access coverage. No guarantee of local stock yet. |

**Electrical boundary:** a licensed electrician/electrical engineer specifies protection, earthing, isolation, bathroom zones, ingress exposure, mains/control segregation, surge coordination and emergency/common-area lighting under currently applicable rules. This document contains no wiring instructions. Do not allow dimmers or night scenes to disable required safety lighting.

## 6. Luminaire type x role x room

| Type | Role | Recommended rooms / purpose | Caution / alternative |
|---|---|---|---|
| COB downlight | HIGH | Living, dining, kitchen, bedrooms | COB is an emitter construction, not a glare rating |
| Deep-recess anti-glare downlight | HIGH | Living and bedroom seated/reclined sightlines | Broad enough optic; don't fill room with narrow hotspots |
| Adjustable gimbal | HIGH / accent | Wardrobe, pooja or selected wall | Re-aim away from TV/eyes; no automatic wallwash claim |
| True asymmetric wallwasher | HIGH / accent | Art backdrop, wardrobe wall | Needs setback and photometric overlap |
| Diffused linear profile | LOW / optional HIGH / task | Lit false grooves; flat kitchen perimeter; shelf | Role follows orientation/output, not its name |
| Cove COB strip | LOW | Living/dining and bedroom trays | Aluminium mount; matched batch; hidden source |
| Cove high-density SMD strip | LOW | Same coves with sufficient mixing distance | Legitimate economical substitute after dot/reflection test |
| Magnetic track | Accent | Dining/master-dressing showpiece wall only | Matched rail/heads/PSU/dimming ecosystem; avoid whole-house proliferation |
| Cylinder, surface or suspended | Accent / HIGH | Art wall alternative; IP-rated balcony | Suspended cylinders only outside circulation/head-strike envelope |
| Pendant | Task / LOW | Dining table | Keep separately adjustable if cove and table need different scenes |
| Step / path light | Night | Master, children, lobby and bathroom approach | Aim at floor; prove entire route, not one bright patch |
| Mirror face bar / sconce | Task | Baths, dressing, common basin | Diffused frontal light; not backlight-only mirror |
| IP65 bulkhead | HIGH | Open-air utility | Broad distribution, cleanable, IK08 preferred |
| Up/down wall light | LOW / accent | Balcony wall | Shield spill; not sole floor/threshold safety light |
| Under-cabinet strip | Task | Kitchen preparation, utility shelf | Continuous useful counter coverage; cleanable diffuser |
| Niche / under-vanity strip | LOW / night | Bath and pooja niche | Night use needs its own suitable low level; wet-system detailing |
| Spot / pinspot | Accent / task | Pooja, art, local book reading | Check true task plane; avoid reflected pinpoint glare |
| Diffused opal downlight | HIGH | Bathrooms, compact dressing/lobby | Pair with face task light where needed |

| Room | Recommended combination |
|---|---|
| Living | Deep-recess HIGH + one continuous warm cove LOW; optional sparse diffused LINE; shielded reading lamp; restrained TV surround light; separately controlled pooja |
| Dining | Broad HIGH + warm cove LOW + separately controlled table pendant; one art system, track **or** cylinders, not both |
| Kitchen | Broad HIGH + dimmable flat perimeter LOW + continuous under-cabinet task; don't use the perimeter as a task substitute |
| Utility | IP65 bulkheads + IP-rated under-shelf task; decorative LOW is unnecessary |
| Master | Deep-recess HIGH + cove LOW + wardrobe frontal/wash light + individual reading lights + floor night route; LINE optional |
| Children | Broad overlapping HIGH + cove LOW + separate 500 lx desk task + reading and night route; no visible strips from bed |
| Dressing | Diffused HIGH + frontal face bars/wardrobe light; LOW optional, not essential |
| Each bath | Diffused general HIGH + shielded shower light + mirror face bars; dimmable perimeter/niche/vanity LOW, with very-low-output night option |
| Lobby/shared basin | Modest general HIGH + face bar + shielded night path |
| Balcony | Shielded IP-rated general/cylinder + optional restrained up/down/plinth LOW |
| Pooja | Concealed warm niche strip + low-output aimed spot; reduce reflective-metal glare; keep lighting clear of lamp/incense heat |

### Six scene starting presets

Percentages mean approximate **light-output fractions**, not knob angles or power percentages. Values are commissioning starts, not guarantees of lux or CCT. If a circuit is switched-only, only 0/100 is available until hardware changes.

| Scene | HIGH | LOW | LINE | Task | Accent | Night | CCT intent |
|---|---:|---:|---:|---:|---:|---:|---|
| Off | 0 | 0 | 0 | 0 | 0 | 0 | None; required safety systems independent |
| Mood | 0 | 30% | 0 | 0 | 20% if wanted | 0 | Warm 2700-3000 K |
| Relax | 20% | 60% | 0 | 0; local reading by choice | 20% | 0 | 2700-3000 K if tunable; fixed HIGH stays 4000 K |
| Work | 100% | 25% | 0 | 100% where working | 0 | 0 | Task/HIGH 3500-4000 K; fixed LOW remains warm |
| Full | 100% | 100% | 50% optional | 100% where needed | 20%, not full art output | 0 | 3000-4000 K uniform option if tunable; otherwise mixed fixed sources |
| Night | 0 | 0 | 0 | 0 | 0 | Calibrated to 1-5 lx route | 2200-2700 K; fixed 2700 K acceptable start |

Exceptions: bath Mood LOW ~20-30% gives ~35-53 lx in the existing model, never use 100% as "mood". Bedroom night is not a whole cove at 30%. Dining LOW includes the pendant in rev 3.3: split controls/model if table and cove need independent scenes. A reading task may need 300-500/500-750 lx even during Relax. Match scene output to task needs, not scene names.

**Avoid:** random mixed whites on one ceiling line; tiny high-output spots reflected in tiles; blackening the cove reflector; bright line next to a near-black groove without dimming; cheap low-frequency PWM; one inaccessible central PSU; calling switch-select CCT "tunable and dimmable"; adding ceiling watts to fix a shaded counter; treating U0=1 cove output as measured uniformity; treating a home night route as emergency lighting.

## 7. Rev 3.3 room-by-room check and cheapest fixes

Numbers below are exactly the saved model's rounded values unless a derived value is identified. **Every status is against project criteria, not legal compliance.** Global unverified items (colour, flicker, photometry, thermal/IP and actual controls) apply even to a PASS.

| Room | Result / status | Reason and least-cost next action |
|---|---|---|
| Living LIV | **MARGINAL**; HIGH 152 lx, U0=.40; LOW 67; BOTH 220 | Horizontal general checks pass, but U0 is only just at target and faces/TV glare are not proven. TV wall average155, peak429 is wall lux, not screen glare. Re-aim/switch TV gimbals; add face/observer grids before any extra fittings. |
| Dining DIN | **MARGINAL**; HIGH154, U0=.58; LOW135; BOTH289 | General passes. 289 room-average is not 200-300 on a verified table grid; LOW135 exceeds a 20-80 mood operating band. Dim/split pendant and cove; calculate table U0 before procurement. Art checked separately below. |
| Kitchen KIT | **FAIL**; HIGH278, U0=.39; worktop HIGH+TASK619, min218 => U0=.352 | Average is adequate; general uniformity <.40 and worktop <.60. At average619, task minimum must be >=371.4, not218. Reposition/extend existing task strip to weak areas and redistribute downlight beams before increasing total power. Uniform dimming cannot fix U0. Room HIGH+TASK369, LOW77 and BOTH355 remain provisional; confirm the flat shadow-slot section and distribution. |
| Utility UTL | **MARGINAL**; HIGH136, U0=.85; counter236, min167 => U0=.708 | Numeric general-reference/counter checks pass. General grid is at0.9 m, not floor; counter note explicitly lacks shelf occlusion. Add shelf/body obstruction and floor grid, then shift existing under-shelf strip if needed. |
| Master MBR | **FAIL for wardrobe; other tasks MARGINAL**; HIGH151, U0=.59; LOW49; BOTH200 | General/mood pass. Wardrobe Ev97 <150; add/redirect frontal wardrobe light rather than room watts. READ average4 is room-plane contribution, not book lux. NIGHT avg1/min0 is rounded on0.75 m plane, not a valid floor-path result. Compute book, wardrobe and full route grids. |
| Dressing DRS | **MARGINAL**; HIGH192, U0=.96 | General passes; no dressing face grid or face-bar evidence. Reuse bath mirror for grooming if convenient; otherwise add frontal diffused light and validate Ev300-500. |
| Attached bath TL1 | **MARGINAL**; HIGH162, U0=.58; shower225/min163; face438/min434; basin411/min270 | Functional grids pass (basin U0=.657). LOW174 at100% fails20-60 mood but ~30%=52 passes. Set a low preset; do not add fixtures. Validate zones/IP/thermal and a separate safe night level. |
| Lobby LOB | **MARGINAL**; HIGH208, U0=.97; face201/min199 | General exceeds100-150 at the model's0.75 m plane; shared face-wash meets200-300, not grooming300-500. Reduce/replace output after floor check (rough start ~60%=125 lx on existing plane). NIGHT3/min3 is not a floor result. Hardware is presently switched-only. |
| Common bath TL2 | **MARGINAL**; HIGH164, U0=.59; shower228/min169; face440/min436; basin414/min273 | Functional checks pass (basin U0=.659); correct face maximum average is440, not "up to438" for both baths. LOW178 needs dimming to~30%=53. No extra light indicated. |
| Children CBR | **FAIL**; HIGH148, U0=.36; LOW44; BOTH192, U0=.51 | HIGH-only general uniformity fails; wardrobe Ev91 also falls below150. First redistribute optics/wardrobe light; provisional HIGH100%+LOW25% gives ~159 avg/~64 min, U0~.40 **only under the existing uniform-cove approximation**. Actual desk/book lux and complete night path absent; STUDY42 is a room average, not desk brightness. |
| Balcony BAL | **PASS**, modeled illuminance only; HIGH64, U0=.67; LOW40, U0=.78 | Each lane alone meets30-75 on floor. BOTH104 exceeds preferred band; use one lane or dim. Check installed IP, threshold coverage, spill and glare before physical acceptance. |
| Art wall | **FAIL at full accent output**; track art559 + ambient49 gives ~12.4:1; cylinders509 +49 gives~11.4:1 | Target3-5:1. Start track at20-30% ->~161-217 lx total, ~3.3-4.4:1 with current HIGH ambient. Retune when ambient dims. Cylinder peak1059/min99 is severe; dimming preserves that unevenness, so re-aim/widen/overlap. Texture-graze is not a uniform wallwash. |
| Flush pooja | **MARGINAL**; idol face243 from ceiling spot201 + strip42; ambient at mouth87; reported3.8:1 | Rev 3.3 uses a 6 W/480 lm/24-degree ceiling spot at2.70 m. Reported ratio apparently uses(243+87)/87, not established ambient at the idol plane. Back panel479 remains brighter than idol. Verify same-plane contrast, aiming and structural viability of115 mm cavity. Reported spot66% for3:1 assumes strip remains unchanged; source also says same pooja circuit/dimmer, so that independent adjustment is not established. Do not treat it as a commissioned setting. |

The model's uniformly added cove light produces U0=1 in several LOW scenes. That is a modelling approximation, not proof of perfect indirect distribution. "ALL" also means the model's listed combination, not automatically every task/accent/night circuit; use explicit scene membership.

### Next solver inputs, in priority order

| Priority | Needed correction / evidence |
|---|---|
| 1 | Confirm actual flat kitchen shadow-slot section and fixture distributions; counter grid with shelf/body occlusion; address task min218 and HIGH U0=.39. |
| 2 | Children's HIGH layout; study desk and both rooms' tilted book grids; wardrobe vertical grids. |
| 3 | True floor night-path grids in both bedrooms/lobby/bath approaches, including thresholds; do not reuse0.75 m results. |
| 4 | Dining table, dressing face and living face/Ez grids; art/pooja ambient-only and total on identical surfaces. |
| 5 | Separate ceiling/wall/floor reflectances and black-groove geometry; glossy material/observer checks; non-uniform indirect transport instead of a uniform cove offset. |
| 6 | Matched dimming/CCT control schedule, measured dim curves and spectra; temperature-specific life/MF and vendor evidence. |

## 8. Citation register and verification boundaries

Only small factual summaries are used; paid standards have not been reproduced.

| ID | Document / edition / locator | Verified use and boundary |
|---|---|---|
| R1 | EN 12464-1:2021, through Laura Bellia, REHVA Journal06/2024 pp31-34, **Table2**, Figure2 and discussion | **V-secondary:** office writing/reading500 lx, U0=.60, Ra80, UGR limit19, cylindrical150; L=E*rho/pi; face-grid heights1.2/1.6 m. **Original EN clause/table number UNVERIFIED.** Indoor workplaces, applied to equivalent home tasks by analogy, not a domestic law. |
| R1a | EU-OSHA OSHwiki, *Lighting*, updated9 Aug2023, **Table1** | **V-secondary:** desk500 and hallway100; general quality/glare principles. |
| R2 | CIBSE/SLL *Code for Lighting*, **2022**, corrigendum25 Jul2023; contents Ch3,10-14,16-18 | **V metadata/scope/contents**; paid numeric recommendations/clauses **UNVERIFIED**. Do not cite our room bands as Code quotations. |
| R3 | CIBSE/SLL **LG9, third edition2022**, sections3.1/3.4,6,8,11-13 in public contents | **V metadata/scope/section titles**; covers multi-occupancy residential practice. Numerical tables **UNVERIFIED**. |
| R4 | BIS **Scheme-II compulsory-registration product list**, rows19,22,32,45,46 | **V listed identifiers/categories:** IS15885 Part2/Sec13; IS16103 Part1:2012; IS10322 Part5 Sec1, Sec2:2012 and Sec9:2017. Exact active editions/transitions must be rechecked. IS16103 Part2 performance, IS16104 driver performance and IS16106 test-method editions/clauses **UNVERIFIED**; not asserted as compulsory here. |
| R5 | **CIE S026/E:2018**, official abstract; DOI10.25039/S026.2018 | **V scope:** alpha-opic metrology380-780 nm; no complete application-dose/health prescription. Full clause numbers **UNVERIFIED**. |
| R6 | Brown et al., **2022**, PLoS Biology20(3):e3001571, **Figure2 and recommendations** | **V:** adult daytime/evening/sleep mEDI guidance and scope; not children's universal prescription. |
| R7 | WELL **v1 Feature54, Part2**, legacy public feature page | **V:** residential200 EML daytime and<=50 nighttime with its measurement conditions. Current v2/quarterly addenda **UNVERIFIED**. |
| R8 | **IEEE1789-2015**, official status/abstract page | **V identity/scope; Inactive-Reserved, inactivated26 Mar2026.** Numerical risk curves/clauses **UNVERIFIED**. PWM preference here is P, not an IEEE certification. |
| R9 | **IEC TR63158:2018**, edition1.0, July2018 corrigendum included; official abstract, scope refers to **A.1** | **V:** objective SVM method and >100 lx / <4 m/s scope; A.1 text and detailed test clauses **UNVERIFIED**. IEC TR61547-1 PstLM-method edition/clauses **UNVERIFIED**. |
| R10 | EU Regulation2019/2020, consolidated1 Sep2021, **AnnexII, section2, Table4** | **V:** PstLM<=1 full load and SVM<=.4 full load from1 Sep2024, stated scope/exemptions. Used as a procurement benchmark, not Indian law or a dimmed-output mandate. |
| R11 | IES **TM-30** family | Publisher access blocked; edition/clause/report prescriptions **UNVERIFIED**. Rf/Rg acceptance bands are explicit project targets. |
| R12 | IES **LM-80 / TM-21** families; IES **PS-10-18** publisher page located, access blocked | Full reports, current editions and projection clauses **UNVERIFIED**. Request traceable test/projection evidence; L70>=50,000 h is P, not a minimum imposed by these methods. |
| R13 | IES **RP-1 / Lighting Handbook** | Requested references; edition, task tables and clauses **UNVERIFIED**. No invented IES residential lux table used. |
| R14 | **NBC India2016 Part8 Section1** | Original wording, lighting tables and clause numbers **UNVERIFIED**; no numerical NBC-compliance claim. BIS homepage now lists **National Building Construction Standards2026 / SP7:2026**; detailed changes and Hyderabad adoption **UNVERIFIED**. Verify applicable edition before statutory review. |
| R15 | **IEC60529 / IEC62262** IP/IK families | Edition and clauses **UNVERIFIED**. IP/IK values here are project exposure targets; zone/legal suitability needs the electrician. |

[R1]: https://www.rehva.eu/rehva-journal/chapter/european-standard-for-visual-environment
[R1a]: https://oshwiki.osha.europa.eu/en/themes/lighting
[R2]: https://www.cibse.org/knowledge-research/knowledge-portal/sll-code-for-lighting-2022
[R3]: https://www.cibse.org/knowledge-research/knowledge-portal/lg9-lighting-for-communal-residential-buildings-2022/
[R4]: https://www.bis.gov.in/product-certification/products-under-compulsory-certification/scheme-ii-registration-scheme/?lang=en
[R5]: https://cie.co.at/publications/cie-system-metrology-optical-radiation-iprgc-influenced-responses-light-0
[R6]: https://journals.plos.org/plosbiology/article?id=10.1371/journal.pbio.3001571
[R7]: https://standard.wellcertified.com/light/circadian-lighting-design
[R8]: https://standards.ieee.org/ieee/1789/4479/
[R9]: https://webstore.iec.ch/en/publication/61455
[R10]: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:02019R2020-20210901
[R11]: https://www.ies.org/standards/standards-resources/ies-tm-30/
[R12]: https://ies.org/advocacy/ps-10-18/
[R13]: https://ies.org/products/recommended-practice-lighting-office-spaces/
[R14]: https://www.bis.gov.in/?lang=en

Authoritative source: `not-distributed/lighting_data.json`, revision3.3, SHA-256 `974f61dbf4e03b8b4289e6108e164bacf47a3335fb761d561be3da8455661167`. Machine-readable companion: `lighting_criteria.json`.

History: initial rev3.2 had kitchen worktop640/min226 and pooja face289; these are superseded, not alternative current results. Previous source SHA-256 `7a8031530cb8ca5e7ea12e620afe280703c7560666dd9063840f6aa3a97dc055` is retained in JSON provenance.
