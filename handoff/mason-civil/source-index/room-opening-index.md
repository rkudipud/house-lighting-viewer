# Room and opening source index - review only

**Canonical master SHA-256:** `79ece2aef1acd63ee401702149a91e29a6ed660123c4d9d3640ab5304ed89822`. Not for construction or fabrication.

The 14 records include rooms, service areas, a lift footprint and a margin. The 21 openings include doors, windows, vents, niche fronts and a parapet opening. Each modeled span is an identification aid, not a measured size. Survey each actual floor separately; F1-F4 do not establish storey labels or identical built layouts.

Room dimensions below are recorded by the master as homeowner-confirmed measured labels, but none is independently verified. Historical P page 1 references are numerical provenance only; the retired original layout was not consulted or used for geometry. Exact canonical pointers and evidence fields are in `room-opening-index.json`.

## Rooms and areas

| ID | Room / area | Homeowner-reported nominal feet / inches | Metres | Evidence |
|---|---|---|---|---|
| R01 | Living | 14' x 17'-6" | 4.2672 x 5.334 | Homeowner reported; not independently surveyed |
| R02 | Dining | 14' x 9'-9" | 4.2672 x 2.9718 | Homeowner reported; not independently surveyed |
| R03 | Kitchen | 14' x 10' | 4.2672 x 3.048 | Homeowner reported; not independently surveyed |
| R04 | M bed room | 12'-6" x 15'-4.5" | 3.81 x 4.6863 | Homeowner reported; not independently surveyed |
| R04a | M bedroom dressing / ensuite approach | Not supplied | - | Measure on site |
| R05 | C bed room | 12'-6" x 15' | 3.81 x 4.572 | Homeowner reported; not independently surveyed |
| R06 | Toilet, rear/upper | 8'-9" x 5'-6" | 2.667 x 1.6764 | Homeowner reported; not independently surveyed |
| R07 | Toilet, front/lower | 8'-9" x 5'-6" | 2.667 x 1.6764 | Homeowner reported; not independently surveyed |
| R08 | Utility, labelled area | 15'-6" x 4'-6" | 4.7244 x 1.3716 | Homeowner reported; not independently surveyed |
| R08a | Washing bay | Not supplied | - | Measure on site |
| R09 | Balcony / front arrival | 11' x 8' | 3.3528 x 2.4384 | Homeowner reported; not independently surveyed |
| R10 | Lift footprint | 5' x 5' | 1.524 x 1.524 | Homeowner reported; not independently surveyed |
| R12 | Common washbasin niche and access | Not supplied | - | Measure on site |
| R13 | Side margin / setback strip | 1'-6" | 0.4572 | Homeowner reported; not independently surveyed |

R01 includes a lift-side cutout; R08/R08a are one utility/washing area whose scope needs reconciliation. R10 is a lift footprint, not an accessible room. R13 is one offset, not a confirmed continuous legal setback.

## Openings

| ID | Current-model identification | Model width m | Basis | Actual width / height |
|---|---|---:|---|---|
| D01 | Main entrance door | 1.10 | scaled_model_not_measured | Unmeasured |
| D02 | Master bedroom door | 0.86 | scaled_model_not_measured | Unmeasured |
| D03 | Children's bedroom door | 0.85 | assumed_not_measured | Unmeasured |
| D04 | TL1 door | 0.80 | assumed_not_measured | Unmeasured |
| D05 | TL2 door | 0.79 | assumed_not_measured | Unmeasured |
| D06 | Kitchen-utility double-leaf door | 0.91 | scaled_model_not_measured | Unmeasured |
| G01 | Entry side panel | 0.56 | scaled_model_not_measured | Unmeasured |
| G02 | Entry side panel | 0.56 | scaled_model_not_measured | Unmeasured |
| PN1 | Pooja niche, recessed (built; HD-16 / HD-18 estimates) | 0.61 | homeowner_estimate_unverified | Unmeasured |
| SN1 | TL1 shower niche | 0.75 | proposed_model_not_measured | Unmeasured |
| SN2 | TL2 shower niche | 0.75 | proposed_model_not_measured | Unmeasured |
| UP1 | Utility parapet opening (assumed, OI-UTL-01) | 4.12 | assumed_not_measured | Unmeasured |
| V01 | TL1 vent / window | 1.00 | scaled_model_not_measured | Unmeasured |
| V02 | TL2 vent / window | 1.00 | scaled_model_not_measured | Unmeasured |
| W01 | Kitchen exterior window | 1.22 | scaled_model_not_measured | Unmeasured |
| W02 | Kitchen-to-utility window | 1.22 | scaled_model_not_measured | Unmeasured |
| W03 | Master window | 0.91 | assumed_not_measured | Unmeasured |
| W04 | Master side window | 1.83 | scaled_model_not_measured | Unmeasured |
| W05 | Children's side window | 0.75 | assumed_not_measured | Unmeasured |
| W06 | Living side window | 1.83 | scaled_model_not_measured | Unmeasured |
| W07 | Dining side window | 1.83 | scaled_model_not_measured | Unmeasured |

D01 leaf count conflicts between architecture and visualization. W03 offsets are unmeasured; W05 is a visual placeholder. PN1 is an already-built niche with homeowner-estimated dimensions; its extension and support are unverified. No new or deeper cutting is authorised.

## Connections, stair and heights

The following are carry-forward model relationships, not verified site openings. Widths are not supplied:

| ID | Connects | Model note |
|---|---|---|
| O01 | R01 to R02 | Open furnishing division; no doorway. |
| O02 | R02 to R03 | Open beside counter/peninsula; no leaf. |
| O03 | C01 to R12 | Common circulation to wash niche. |
| O04 | R09 to S01 | Open stair approach; no access gate shown. |
| O05 | R08 to R08a | Service-strip continuity; subdivision is graphical. |
| O06 | R04 to R04a | Private dressing extension off M bedroom; no separating leaf. |
| O07 | R01 to C01 | Conceptual link from living to common lane; not another wall opening. |
| O08 | R02 to C01 | Conceptual link from dining to common lane; not another wall opening. |
| O09 | R03 to C01 | Conceptual link from kitchen to common lane; not another wall opening. |
| LX01 | R10 to unknown | Lift door is not shown; no route through shaft. |

S01: two modeled flights and a turning area; the drawn 7 / 15 tread lines are illustrative, not verified riser counts. Measure rise, going, flight width, landing, arrival direction, headroom and guard per floor.

HD-11: homeowner-stated 11 ft floor-to-floor and approximately 9 in band drop, not measured on site. The older 3.188 m slab and 2.959 m band estimates depend on assumed slab and finish thicknesses. R05 is separately homeowner-reported at a 3.048 m band and approximately 3.277 m centre; this conflicts with the older slab estimate. The R05 slab is unmeasured. Verify all levels and cavities on site.

South-up: page top south, bottom north, left east, right west. The homeowner-described compass is not a surveyed true bearing.

Current children's layout relationships cite MR.RAJESH_INTERIOR_RENDERS.pdf pages 16-18, which are undimensioned perspectives, not a scale survey.
