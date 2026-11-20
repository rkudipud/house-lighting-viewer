# Hyderabad 2BHK light planner

Review draft. Not a construction release and not product approval.

A static, offline-capable viewer for the proposed lighting of a four-storey-house flat.
Open `index.html` (or the published page): choose a room, walk or orbit the flat, switch lights
on and off, and switch LOW (cove / mood) and HIGH (main) lighting per room or across the home.
Open Light specifications or tap a fitting marker for its name, type, wattage, lumens,
spec, beam angle, colour, location and code. Rendering uses balanced visual lighting;
the light maps remain saved estimates, not live lux measurements.
Colour temperatures are fixed per fitting and are not adjustable.
- Fixed CCT per base fitting from the integrated master: 30 x 2700 K, 12 x 3000 K, 62 x 4000 K. Brightness controls only.
- The fixed-temperature schedule and placement holds are available in the linked handoff; brightness controls do not change colour temperature.
- Four selected 2700 K curtain strips follow existing LOW controls. The review schedule has 108 fittings / 51 circuits including these additions; the frozen photometric baseline remains 104 / 47 with no curtain-strip lux credit. Pocket sizes are unmeasured and CURT-MBR-W03 remains held and unlit.
- The children's fan is illustrated at the nominal room centre with a 1050 mm planning sweep (product not selected; airflow adequacy for this room unconfirmed). The intact cove (C39) and outward LINE (C40) are modelled ON with scheduled lumens in the review simulation; they remain site-held (H-CBR-CEIL) and are not installed, measured or approved. R05 band 3.048 m / centre approx. 3.277 m are homeowner-reported; slab height unmeasured.
- Lighting switches change the visual preview only; the lux maps are frozen generic-optics estimates and are not recomputed.
- The four bedside readers and two PIR night lights are individual fitting previews, off by default; held readers cannot be enabled. The actual readers dim on the fitting and the night lights are PIR-operated, not extra wall dimmers.
- The selected dressing and utility cabinets are unmeasured conditional illustrations (FH-ST-03 / FH-ST-12), not construction-ready. One living LOW supply is selected for review; product, protection and electrical design remain on hold.
- Wardrobe interiors are provisional and unapproved; the viewer's open-cabinet illustration is not measured joinery. Measurement and sign-off remain open.
- Door leaves are hidden in the viewer; openings remain in the design. D01's leaf arrangement remains a site check. Assumed MBR-S and CBR pocket returns extend about 0.30 m beyond modeled room corners. The viewer clips them only for display; actual pocket ends remain unmeasured and held.
- The linked review PDFs are in the adjacent `downloads` folder. When the viewer is opened from disk, a browser may open a PDF in a new tab; use the PDF viewer's Save button.
- The [trade handoff](handoff/index.html) links the current plans, schedules, drawings and renders. Build provenance is retained in `build-info.json`.
- Three.js 0.181.1 is bundled into `index.html`; its MIT notice is embedded and provided as `THREE-LICENSE.txt`. No CDN or network access is needed at runtime.
