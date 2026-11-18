# Layout views (read-only) - REVIEW DRAFT, not construction released

Drawn only from the canonical master `house-design.json`, sha256 `b6f6bf1a127c7e39086deb9fd1d2c0dff79a495381e1a4b9457f6a9a468f23ac`.
REVIEW DRAFT; not construction-released
This is a new review edition on the homeowner-signed fixed-CCT master; the earlier published set (bound to master 124ef698) is a separate folder and is not overwritten.
Nothing here edits the master, adds a design decision or replaces a drawing in it. Not a construction release.
Sheet drawings are south-up: the page is **not rotated**, and the north arrow on every sheet points to the bottom of the page.

**Look and feel.** This is the original sheet style (the same 13 sheets, "Sheet n / 13" headers, pastel room fills, right-hand schedule/legend/notes). The later "drafter" redesign was rejected by the homeowner and is archived, not used. The roll-back is style only: the data underneath is the current finalised layout (HD-11 levels, current lighting, compass names). The original layout is retired (HD-13) and is not used as a source.

## Sheets (also merged, in this order, into `current-layout-views.pdf`)

| # | Sheet | Files |
|---|---|---|
| 1 | Furnished floor plan (top-down) | `01-plan-furnished.svg` / `.png` |
| 2 | Reflected ceiling plan (bottoms-up) | `02-rcp.svg` / `.png` |
| 3 | Elevations — R01 Living | `03-elev-R01-living.svg` / `.png` |
| 4 | Elevations — R02 Dining | `04-elev-R02-dining.svg` / `.png` |
| 5 | Elevations — R03 Kitchen | `05-elev-R03-kitchen.svg` / `.png` |
| 6 | Elevations — R04 Master bedroom | `06-elev-R04-master.svg` / `.png` |
| 7 | Elevations — R04a Master dressing | `07-elev-R04a-dressing.svg` / `.png` |
| 8 | Elevations — R05 Children's bedroom | `08-elev-R05-children.svg` / `.png` |
| 9 | Elevations — R06 TL1 attached toilet | `09-elev-R06-TL1.svg` / `.png` |
| 10 | Elevations — R07 TL2 common toilet | `10-elev-R07-TL2.svg` / `.png` |
| 11 | Elevations — R08 Utility + washing | `11-elev-R08-utility.svg` / `.png` |
| 12 | Elevations — R09 Entry / balcony | `12-elev-R09-entry.svg` / `.png` |
| 13 | Elevations — R12 Common lobby | `13-elev-R12-lobby.svg` / `.png` |

1. **Top-down** = a colour-filled furnished plan with room names, confirmed sizes, walls, door swings, windows, the parapet opening, stairs, lift and essential furniture/storage.
2. **Bottoms-up** = the reflected ceiling plan (the ceiling as seen looking up): the ~9 in perimeter band (underside 2.959 m), the raised centre as a separate gypsum/POP panel below the slab (level and cavity depth unmeasured; the 3.19 m slab underside is only a reference plane), the flat kitchen ceiling, cove lines, bath/utility/lobby ceilings (levels not provided), lofts, curtain pockets (two tracks), fan points and all 104 canonical base `lighting.fixtures` in 47 base controlled groups, plus four homeowner-selected S1 curtain strips. **Fixed CCT by fitting, 2700 K coves/selected strips; not construction-released.** Hold marks (CR, HB, DS, PG) outline fittings that remain conditional: CR means product-fit/access, HB hall beam, DS dressing sweep, PG pooja count/load allowance. A small "conditional details" block shows the raised-centre product-fit/access idea and the two-track curtain pocket, schematically and not to scale.
3. **All walls** = interior elevations of every wall of every room, each with a key plan and a view arrow. The living east-wall sheet carries the pooja niche PN1 and an enlarged niche detail.

## How to read the compass
- Source: `visualization_geometry.orientation`: approximate homeowner north, not a surveyed true bearing. The entrance/balcony/stairs side faces **NORTH**.
- Sheet-top = South, sheet-bottom = North, sheet-left = East, sheet-right = West. Only the four cardinal directions are recorded; true bearing and magnetic declination are not surveyed.
- Walls are named by compass ("Master bedroom - south wall (wardrobes, W03 bay)"). The small grey tags such as `master-s` are only drawing IDs.

## What is real, what is assumed
- Room sizes come from the finalised master layout. **Most opening offsets are inherited or placeholder** values: every window/door is drawn at a "modelled plan position; not site verified", and a dagger (†) marks openings that are assumed, placeholder or centred-but-unmeasured.
- **Every level is unmeasured (HD-11).** Homeowner-stated: 11 ft floor-to-floor (3.353 m) and a ~9 in band drop. Derived from those (5 in slab and 1.5 in finish assumed): slab underside about 3.19 m, band underside 2.959 m, kitchen flat ceiling 2.959 m. The raised centre is a separate gypsum/POP panel below the slab (HD-14): its level and cavity depth are unmeasured. Not provided (placeholders): bathrooms 2.40 m, utility 2.95 m, lobby 2.70 m, balcony. Window and door heads and sills are assumptions. The hall cross-beam soffit is unmeasured (H-HALL-BEAM). Every sheet says so.
- The **loft** top of 3.08 m is an unmeasured legacy placeholder and is not raised to the slab (H-LOFT). The old 2.64 m curtain top is retired; 2.939 m is used only as an assumed HD-11 drawing top for the children's curtain, not measured hardware.
- Items whose height is not in the master (sofa, TV unit, tenant beds and so on) are drawn only as footprints below the floor line. No height was invented. Wall cabinets show a bottom of 1.45 m and no top.
- **Pooja niche PN1 (HD-16 / HD-18)** is already built at the north end of the living east wall. Its relationship is homeowner-confirmed, but the 609.6 mm width, 1701.8 mm opening height, 0.4318 m sill, 381.0 mm depth and modeled position are **homeowner estimates, not site measurements**. HD-18 clarifies feet-and-inches notation: sill 1 ft 5 in (0.4318 m), depth 1 ft 3 in (381 mm), north-corner gap 1 ft 4 in (0.4064 m). All remain homeowner estimates, not site measurements. Opening height 1701.8 mm is derived from the estimated top minus sill. The homeowner reports a reinforced slab extension beyond the 9-inch wall, top to bottom through the building; its geometry and capacity are unverified. The model does not contain this extension. Only the estimated front outline and dimensions are shown: **no physical back or structural cross-section is drawn**. This model mismatch does not establish that the existing niche is unsafe or impossible. Confirm dimensions, support/capacity and balcony-edge relation on site (OI-POOJA-01). No cutting or deepening is requested or approved; no finishes or frame construction are newly selected.
- **Pooja display:** small idols with a framed picture behind are homeowner-selected conceptually. Their positions and sizes, any platform fixings, thermal/fire clearance and support capacity remain unmeasured or unapproved.
- **W03** (master south window) is "centred (homeowner-confirmed); offsets unmeasured"; its curtain pocket is held (H-MBR-W03). **W05** (children's west window) is still a visual placeholder, concealed behind its curtain.
- Tenants bring their own beds: beds are dashed "tenant's bed - queen to king envelope" (1524-1829 x 1981 mm mattress), not joinery and not a tested frame (the 1.68 x 2.13 frame is not drawn). **Fixed bedside cabinets are omitted by the homeowner (HD-14: ST-R04-NS01, ST-R04-NS02, ST-R05-NS01)**; no optional outline is drawn and tenants may use movable tables. Room and bed positions are unchanged. The master's built queen bed is not drawn; the master bed position is a held test centreline (H-MBR-BED).
- **R05 clearance (HD-15):** keep the finalized room and furniture positions. The approximately 387.6 mm bed-foot/study-return clearance is a **site-check pinch, not a comfortable walking route**. Measure the actual tenant bed frame, fixed return and unobstructed route on site (OI-R05-03); no furniture relocation is authorised.
- The only switch zone in the master is the children's latch-side switch board (1.06-1.785 m along the south wall). No other switch plates are drawn because none are recorded.
- Retired wardrobe/joinery footprints are excluded: the five superseded ST-R04 records are suppressed. The master split wardrobe is approved in principle, with dimensions held for site measurement; OPT-E BWP plywood carcass and laminate shutters are selected.
- Dressing cabinet ST-R04a-WR01 and utility cabinet ST-R08-UC01 are homeowner-selected subject to measured fit, circulation and utility-service access. Dashed outlines and elevation dimensions are unmeasured placeholders, not fabrication dimensions.
- **Lighting:** Homeowner-signed fixed-CCT review candidate (104 fittings, 47 controlled groups base plus four selected S1 strips): 2700 K coves and pocket strips, with CCT fixed by fitting. CBR-H1 to H6 are active/switchable at accepted positions; the C37 exact dimmer chain remains held. CURT-MBR-W03 is held and excluded. Pocket dimensions, other CBR coordination, product fit and construction release remain held. Pooja fittings LIV-P1/P2 remain count/load allowances only. CBR-H1 to H6 are active/switchable in review; the other 8 children's-room fittings remain faded under coordination holds. Additional holds include H-CENTRE-RECESS (conditional product-fit/access check; no slab chase or structural cutting is authorised), H-HALL-BEAM, H-DRS-SWEEP, H-MBR-W03, H-MBR-BED and H-LOFT.
- **Raised centre (HD-14):** a separate gypsum/POP panel below the concrete slab. The homeowner confirms space will be provided for the aluminium profile/track and wiring; clear cavity depth, panel level, profile recess/fixing dimensions, wiring access and driver location are unmeasured. No categorical "no void / no space" claim is made.
- **Curtains (HD-14):** the living, master and children's rooms have two layers (sheer + blackout) on ceiling-mounted tracks concealed in recessed pockets, so each pocket needs two tracks. Pocket outlines on the RCP and elevations are indicative only; clear width, depth, track spacing and stack are unverified and no enlarged pocket is assumed.
- **Selected S1 strips:** CURT-LIV, CURT-DIN, CURT-MBR-S and CURT-CBR are selected conditionally on site measurement; the W03 strip remains held/excluded. Selected strips do not receive photometry credit. Total including S1 is 108 fittings / 51 groups, versus 104 / 47 base.
- **S1 geometry conflict:** assumed MBR-S and CBR return centre-lines extend about 0.30 m beyond their modeled room corners. This is a clash in the unmeasured model, not an as-built measurement or an instruction to cut or extend the pocket. Measure the actual ends and coordinate a site-fit solution before set-out.
- Curtain pockets on the RCP and elevations are ceiling-recessed track pockets (not rods over the windows, and not LED coves). Their sizes are indicative, not measured (see HD-14 above).

## Source status
- Bound master: `b6f6bf1a127c7e39086deb9fd1d2c0dff79a495381e1a4b9457f6a9a468f23ac` (the file was only read).

## Not elevated (and why)
- Open edges have no wall record, so no wall is invented: living-south, dining-north (open to each other), the lobby's east edge, and the balcony's west/north/east edges. Each is noted on its sheet.
- The lift shaft is not elevated (no interior finish data).
- Plan-only items (no elevation face): FURN-coffee, FURN-dining-table, FURN-plant-2, FURN-rug, FURN-sofa-return.
- Not drawn on the plan: ST-R05-BED01, ST-R05-NS01 (tenant-supplied beds; bedside units omitted by the homeowner, HD-14).

## Re-running
```
python walkthrough\render_layout_views.py --master <house-design.json> --out <this folder> --sha <expected master sha256> [--live <live master>] [--staging | --review-draft]
```
It refuses to draw if the master hash is not the expected one, then rebuilds every SVG, PNG and the PDF and rewrites the receipt.
PNGs are 2x; the PDF is vector and text-searchable (PDF timestamps differ between runs, SVG and PNG are reproducible).

`layout-views-verification.json` is the receipt: source hash, artifact hashes, sheet list, render checks (zero errors, no text outside the page, no network requests, drawn ids reconciled against the master) and the generator hashes.
`sheets.json` is the generator's per-sheet manifest of what was drawn.
