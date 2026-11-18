# Civil coordination pack — review only

**Not construction, fabrication, electrical or product release.** These drawings are a coordination reference for the mason, ceiling installer, joiner, electrician and responsible structural professional. Do not set out work from model dimensions; survey each floor and obtain the appropriate professional approvals.

## Files

- `contractor-civil-review.pdf`: combined 20-page plan, reflected ceiling plan, room elevations, civil details and source index.
- `layout-views\current-layout-views.pdf`: 13 original-style plan, ceiling and elevation sheets. The corresponding 13 SVGs and PNGs are in the same folder.
- `site-details\site-coordination-details.pdf`: four supplementary ceiling-section, opening/stair, pooja/loft and per-floor site-check sheets. Corresponding SVGs and PNGs are in that folder.
- `site-details\opening-register.json`: 21 model opening identifiers and spans, clearly marked unmeasured; no actual opening sizes are asserted.
- `source-index\room-opening-index.pdf` / `.md` / `.json`: 14 room/area records, 21 model openings, 10 carry-forward connections and S01, with precise canonical pointers and evidence status. Its three individual pages also have SVG and PNG exports.
- `source-index\source-index-verification.json`: source-pointer, dimension-status and index-export checks.
- `layout-views\layout-views-verification.json` and `site-details\site-details-verification.json`: drawing, rendering and source checks.
- `artifact-receipt.json` and `SHA256SUMS.txt`: source receipt and SHA-256 for the delivered files.
- `generator\`: local copy of the current drawing generator, updated for the integrated homeowner decisions. It reads the canonical master and its HD-18 notation fragment; it does not edit either.

## Binding and orientation

Canonical `house-design.json` SHA-256: `b6f6bf1a127c7e39086deb9fd1d2c0dff79a495381e1a4b9457f6a9a468f23ac`. The homeowner-signoff integration, pooja-display, living-supply/cabinet and provisional wardrobe-interior reference receipts form the source chain to this master. The retired original layout is not a geometry source.

The latest change adds only a versioned provisional wardrobe-interior reference, its source-register entry and the update timestamp. A parsed comparison against the previous master verifies that existing geometry, dimensions, decisions and holds are unchanged. The interior proposal is not homeowner-approved or fabrication-released; no compartment geometry or wardrobe lighting is newly added to these civil drawings.

Sheets retain the preferred simple style and south-up orientation: sheet-top South, bottom North, left East, right West. North is homeowner-described cardinal north, not a surveyed true bearing. The master has four requested instances F1–F4; their actual storey labels, elevations and variations are unverified. Complete a separate checklist for each actual floor.

## Decisions already recorded

- Fixed CCT by fitting, with 2700 K coves and selected curtain-pocket strips. CBR-H1–H6 are active and switchable at accepted positions for review; the C37 exact dimmer chain remains a procurement hold.
- CURT-LIV, CURT-DIN, CURT-MBR-S and CURT-CBR are selected conditionally on site measurements and mock-up. CURT-MBR-W03 remains held and excluded. The S1 extension is separate from the 104-base-fitting / 47-base-group lighting ledger.
- The assumed MBR-S and CBR strip return lines each extend approximately 0.30 m beyond their modeled room corner. This is a clash in unmeasured model geometry, not an as-built finding. Measure actual pocket ends and coordinate a site-fit solution; do not extend or cut on the basis of the lines.
- The master-bedroom split wardrobe is approved in principle; OPT-E BWP plywood carcass and laminate shutters are selected. Dimensions and loft supports are held for site measurement. Fixed bedside cabinets remain omitted.
- The dressing cabinet ST-R04a-WR01 and utility under-counter cabinet ST-R08-UC01 are selected subject to site-measured fit and service/route access. Drawn dimensions are unmeasured placeholders, not fabrication sizes.
- A single 24 V, 480 W nameplate supply concept P01 is selected for living LOW. The product, access, distribution, controller/repeater, branch protection and inrush remain engineering holds; the 20 A reference supply exceeds a candidate controller's 12.5 A input rating.
- HD-15 keeps the children's layout unchanged. The approximately 387.6 mm model bed-to-study-return pinch is not a comfortable route. Measure the actual bed frame, return and unobstructed route; do not relocate furniture in these drawings or re-ask the resolved design choice.
- The existing pooja display is selected conceptually as small idols with a framed picture behind. A platform is intended roughly halfway up; actual dimensions and position remain unknown. The back/base finish remains an open homeowner design choice.

## Site and professional holds

Measure actual rooms, openings, wall thicknesses, floor levels, ceiling/beam soffits, niche and loft geometry, stair dimensions and room-to-room connections on every floor. HD-11's 11 ft floor-to-floor and approximately 9 in band drop are homeowner-stated, not surveyed; the 3.188 m slab and 2.959 m band elevations are derived from assumed slab/finish thicknesses. Raised-panel level, cavity depth, bathroom and utility ceilings and most opening dimensions remain unmeasured.

The current model depicts D01 as a single leaf while the architecture description says double leaf. Confirm the existing entrance rather than treating either as fabrication instruction. W05 is a visual placeholder; W03 offsets and toilet hinges remain site checks. Model stair tread lines are not a verified rise count.

The pooja extension and reinforcement are homeowner-reported, not independently verified. Obtain structural review of its support and allowable load, as well as loft supports, stair safety and applicable rules. No new or deeper niche cutting, concrete chasing or structural alteration is authorised. Verify curtain track/profile clearance, concealed strip visibility, driver access, thermal/fire clearance and electrical product compatibility before installation.
