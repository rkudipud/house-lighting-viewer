# Electrical and wall-control handoff

**Review and quotation only - not for ordering, wiring or construction.** Working assumption: four storeys with one modelled 2BHK flat per floor (four flat schedules total). All quantities below are for **one flat** unless stated otherwise; confirm the actual floor and flat count and variations on site.

**Master SHA-256:** `{{MASTER_SHA}}`. {{MASTER_BINDING}}

**Release gates:** construction release **false**; product approval **false**; exact lighting/driver/control chain proven **false**. The electrician, engineer and suppliers must close the site, safety, product and performance holds before a separate construction release.

The homeowner selected fixed colour temperatures, four warm curtain-pocket strips on the existing room LOW controls, CBR H1-H6 for active review, and one larger living LOW supply. These decisions do **not** release dimensions, loads, fittings, electrical protection or installation. Wardrobe OPT-E and the master-bedroom split are separate interior decisions; the split is in principle only. The subsequently added wardrobe-interior reference remains provisional; no new wardrobe lighting has been selected or costed. Pooja display uses small idols with a framed picture; lighting geometry, clearances and support are still held.

## What this pack contains

* **104 base fixtures / 47 base circuits** plus four selected curtain-pocket strips and four circuit records = **108 fittings / 51 circuits**. Four added strips total **8.88 m / 71.04 W**, but their lengths are derived and **unmeasured**; they receive no lux credit.
* **21 single-colour brightness knobs**, 38 modeled outputs, three modeled repeaters/amplifiers, ten mains-dimmer groups on procurement hold, **12 planned 24 V supplies / 1,980 W total nameplate**, and one separate 48 V track driver per flat. Device counts and reference ratings are concepts, not approved equipment.
* Coves, decorative/mood strips and the selected pockets are fixed **2700 K**. Lobby and balcony HIGH remain **3000 K**; other HIGH fittings are **4000 K**. LOW and HIGH have independent local controls; a single knob does not change colour temperature. App, cloud and wireless operation are not required.
* The earlier fixed-white photometric package reported **82/82** checks on its verified source input. The children's room has a targeted generic-optics reanalysis of its provisional LINE paths; other rooms retain historical estimates. The CBR estimate includes held fittings and the four added curtain strips receive no lux credit. None are measured results.

The full machine-readable schedules are in `schedules/`. `circuit-schedule.csv` lists 51 groups; `wall-control-schedule.csv` lists 31 wall dimmers/knobs; the six fitting controls and eight conceptual switch modules are separate. See `source-index.md` and `wholesale-rfq.md` for exact sources and purchasing requirements.

## Block diagrams and floor reference

![Independent lighting control responsibilities](figures/concept-flat.svg)

![Living LOW one-supply concept](figures/concept-living-low.svg)

![Flat controls and indicative positions](figures/controls-plan.svg)

The floor illustration uses current modelled fitting and switchboard positions, **not** surveyed walls or wiring routes. No supply hatches are plotted; the larger P01 supply's location, size, weight, heat and access must be surveyed. CBR H1-H6, cove and LINE are shown for review; installing the cove and LINE remains held. The north arrow is approximate.

![Curtain pocket section](figures/curtain-pocket.svg)

The four chosen strips use the respective room's existing LOW knob, with no new knob. `CURT-MBR-W03` remains excluded and held. Two possible profile positions are illustrated; choose neither until a measured mock-up confirms track/bracket clearance, diffuser, hidden sightline, return and service access. Do not locate a driver in the curtain pocket.

The source master links the same hall photo to LIV and DIN and a children's-room photo to CBR. No site photo is individually linked to `CURT-MBR-S`; verify that selected location on site. Neither photo is scaled or proves a pocket dimension.

![Source site photo: hall ceiling and recess](figures/photos/site-photo-hall-curtain-pocket.jpeg)
*Hall reference linked to the living and dining pockets; not a measured drawing.*

![Source site photo: children's room ceiling and recess](figures/photos/site-photo-children-curtain-pocket.jpeg)
*Children's-room reference linked to the CBR pocket; not a measured drawing.*

## Living LOW supply and controls

| Group | Planned strip length | Assumed W/m | Strip W | Modeled outputs |
|---|---:|---:|---:|---:|
| C03 living cove | 11.53 m | 8 | 92.24 | 2 |
| C04 TV bias | 1.68 m | 6 | 10.08 | 1 |
| C05 linear | 7.45 m | 8 | 59.60 | 2 |
| X-CURT-LIV | 2.45 m, unmeasured | 8 | 19.60 | 1 |
| **Total** | | | **181.52** | **6** |

Retain **P01** as the one 24 V constant-voltage supply and remove P03; the four groups remain on **K-LIV-LOW**, with **two modeled repeaters** and no extra wall knob. The supply is preferably **480 W class**, with Mean Well HLG-480H-24 cited as a manufacturer reference only. The exact SKU, suffix, supplier and compatibility are not approved.

At nominal 24 V the strip load is approximately **7.56 A**, excluding unquantified controller/repeater consumption, cable losses and tolerances. The old project allowance is **0.60 = 0.80 assumed thermal factor x 0.75 assumed loading factor**; neither factor is a manufacturer-specific derating. Thus 181.52 / 0.60 = 302.53 W, rounded up to **303 W**. A 480 W nameplate gives 288 W at that planning factor. The previous additional 90% cap was a separate project reserve, not another manufacturer rule; do not silently stack it. The selected unit's actual input and temperature curves, mounted `tc` temperature, measured loads and any separately justified reserve govern the professional design.

The reference 480 W unit can supply **20 A** while the T1-K candidate has a **12.5 A input nameplate**. This does not mean 20 A is forced through a healthy load, but faults, branch protection, conductors, connectors, controller and repeaters must be engineered to their real ratings. No direct connection is approved. A single supply avoids the old two-supply common-reference question but is a single point of failure; agree an accessible replacement strategy.

The manufacturer's HLG-480H-24 datasheet states **262 x 125 x 43.8 mm**, approximately **2.8 kg**, and 90-305 V AC input subject to its curves. Its ambient-temperature graph shows 100% load through 60 C above 230 V AC, and through 50 C at 110 V AC, with both curves reducing to about 60% at 65 C. Its input graph shows 80% at 90 V AC and 100% from 110 V AC; maximum stated case temperature is 90 C. These graph conditions are not a guarantee of combined worst-case performance: confirm actual input, mounting and measured `tc` with the manufacturer. Check actual support, ventilation and access. Old P01/P03 living voltage-drop results are **invalid for this changed distribution**. The LT-4 and LT-5 supply membership and inrush screens are also **open / not revalidated**.

The HLG-480H specification lists a maximum of 2 units on a B16 or 3 on a C16 at 230 V, while the retained manufacturer installation lookup states 1 and 2. Reconcile this conflict with the manufacturer for the exact breaker, mixed supply group, ambient and installation. Neither table is a breaker selection.

## Circuit schedule

Loads are modeled LED-side or fixture allowances, **not measured AC input**, installed wattage or breaker settings. Fixture and CCT detail is in `schedules/fixtures.csv`; a group name is not proof of compatible products. Status of every product remains on hold.

{{CIRCUIT_TABLE}}

## Wall controls and supplementary switches

Each listed wall control is local and brightness-only. The six integral reader/PIR controls are listed after the 31 wall controls; see the CSV for individual switch positions and the conceptual two-way/intermediate arrangements.

{{CONTROL_TABLE}}

{{FITTING_CONTROLS_TABLE}}

Pooja C06A strip and C06B spot **must remain separately controllable**: dimming a spot does not eliminate a worshipper's shadow. C10 passage keeps its dimmer. Bathroom face controls remain separate; relevant product/IP and electrical zones need professional approval.

## Power supply and distribution review

These are **planning classes**, not procurement selections. The nameplate allowance is not a measured site capacity. Accessible, ventilated and safely isolated service locations, thermal mounting, inrush, protection and local replacement are mandatory professional design checks. Each flat's circuits, neutrals, low-voltage return and control power stay separate. Common stairs/landings use a separate building supply/control.

{{SUPPLY_TABLE}}

{{DISTRIBUTION_TABLE}}

The distribution groups are conceptual allocation, not an instruction to install particular breakers, cable sizes or isolators. LT-4/LT-5 no longer inherit their previous PASS; all other historical inrush screens remain indicative only and do not replace protective coordination. A physically daisy-chained cable can serve loads electrically in parallel. Never infer a constant-current LED-module connection from a constant-voltage strip concept; follow the selected driver's instructions.

## Voltage drop, heat and other site holds

* **Living LOW:** the previous split-P01/P03 feeder and branch voltage drops do not validate the one-supply distribution. Recalculate with the actual location, route, branch currents, temperature, terminations, real copper area, strip end-to-end drop, repeater losses and protection. Split-feed/injection is a design option only when the exact strip and controller maker permits it.
* **Children's room:** the assumed S1 routes give C39 **3.3%** and the provisional shifted C40 route **3.9%**, both **MARGINAL**. CBR-L1 and CBR-X1-X4 are modelled ON with their scheduled lumens in the design-review simulation only; installation, procurement and operation remain held (H-CBR-CEIL). The provisional fan is at the nominal room centre with a 1050 mm planning sweep (no product selected; fan load excluded from these lighting loads). Verify the real room centre, fan product, drop and airflow, cove section, strip, downlight-cutout and loft/curtain-pocket clearances, site route and ceiling levels before release. The shared P16-to-SB-08 feed had a **2.5 mm2 candidate** for its assumed target; actual route, load, protection and current standards need the electrician's design. Do not treat 2.5 mm2 as an installation instruction. The measured strip and route may change both results.
* **Curtains and joinery:** measure all pocket widths/depths, returns, bracket and curtain-stack clearance; confirm the strip is hidden from seated and standing eye height. The section drawings and the 0.30 m return are assumptions. Seek the approved aluminium profile and diffuser; a site mock-up decides visibility and colour.
* **Bathroom / balcony / utility:** the schedule's IP values are project targets, not certification or proof of zone suitability. Confirm complete luminaire, connector, driver location, ingress rating, corrosion/condensation and all current wet-zone requirements with the qualified electrician.
* **Service:** protect and label cables, use manufacturer-approved aluminium heat-sinking, avoid enclosed hot drivers, and allow accessible isolation and replacement. Confirm power-on memory, mains-voltage range, surge coordination, inrush, power-factor/VA, thermal limits, low-level flicker and fan/strobing interaction.
* **Pooja:** the chosen display arrangement is conceptual. Preserve independent strip and spot controls and verify idol/picture positions, shadow, shelf/support load, heat and fire clearance at site.

## Sampling and handover gates

1. Obtain written specifications and India order codes for each proposed luminaire or strip, its exact LED driver / CV supply, wall dimmer, repeater, profile and accessories. The supplier must explicitly document their combined dimming and allowable group size; a shared brand or voltage label is insufficient.
2. Bench-test representative shortest/longest strips and the intended minimum/maximum group sizes: smooth low and full output, colour match, flicker, hum, cold starts, OFF glow, power-loss memory, actual power and temperature, repeater tracking and switch-on surges. Check strobing near fans and filmed scenes.
3. Measure the four curtain pockets and site routes; record product-specific voltage drop, dimmer box fit, protected branch limits, mounting temperatures, P16 C39/C40 outcome and wet-area approvals. Do not accept the previous living-drop or LT-4/LT-5 screens.
4. Collect Hyderabad availability, GST, delivery, labour, warranty, importer/service address, spare parts and replacement lead time for the exact order codes. A quote must separate optional upgrades and all exclusions.
5. Qualified professionals document current applicable standards, supply segregation, earthing, isolation, overcurrent / residual-current / surge coordination, wet zones, inverter and common-area arrangements. The homeowner reviews the physical mock-up and appearance; a later explicit construction release is still required.

## Budget and open decisions

The older **S1 two-supply** allowance was INR **312,513-769,083 per flat** and INR **1,250,052-3,076,332 for four flats**, including a 12% contingency and some modeled point/profile labour. It excluded GST, freight, curtain tracks/carpentry and electrical DB, protection and site works. Supply-size changes within a broad BoM class were assigned zero incremental cost only as an unverified assumption. It was an allowance, not a quote, and **does not include the one-480 W-supply revision**. No verified current installed price or supply-cost delta exists; request the itemised RFQ before treating any figure as the final budget.

**Homeowner review:** approve measured pocket samples and sightlines, lighting colour/finish samples, physical knob positions and the final quoted budget after supplier and professional checks. No extra curtain knob is requested.

**Professional / supplier work:** close exact chains, product ratings and local support; redesign living distribution and inrush; resolve P16/C39/C40 and actual routes; validate hatch fit/thermal management, zones/protection/segregation and the retained pooja and CBR site holds. These are engineering checks, not homeowner substitutes for technical approval.
