# Hyderabad 2BHK light planner

Review draft. Not a construction release and not product approval.

A static, offline-capable viewer for the proposed lighting of a four-storey-house flat.
Open `index.html` (or the published page): choose a room, walk or orbit the flat, switch lights
on and off, and set LOW (cove / mood) and HIGH (main) brightness per room.
Colour temperatures are fixed per fitting and are not adjustable.
- Fixed CCT per base fitting from the integrated master: 30 x 2700 K, 40 x 3000 K, 34 x 4000 K. Brightness controls only.
- Current lighting-review fixed-CCT map SHA-256 `291d7aef0d70152ebb56085cdc94b49edefe1eeaa6154b5f811a17bb670fcbb4`; its placement holds are retained separately from viewer on/off state.
- Four selected 2700 K curtain strips follow existing LOW controls. The review schedule has 108 fittings / 51 circuits including these additions; the frozen photometric baseline remains 104 / 47 with no curtain-strip lux credit. Pocket sizes are unmeasured and CURT-MBR-W03 remains held and unlit.
- Dimming is visual only; the lux maps are frozen generic-optics estimates and are not recomputed.
- The four bedside readers and two PIR night lights are individual fitting previews, off by default; held readers cannot be enabled. The actual readers dim on the fitting and the night lights are PIR-operated, not extra wall dimmers.
- The selected dressing and utility cabinets are unmeasured conditional illustrations (FH-ST-03 / FH-ST-12), not construction-ready. One living LOW supply is selected for review; product, protection and electrical design remain on hold.
- Wardrobe interiors are provisional and unapproved; the viewer's open-cabinet illustration is not measured joinery. The current-bound wardrobe review PDF identifies the unchanged original interior-generation basis as 2ce3fcb4; measurement and sign-off remain open.
- D01 is single-leaf in the model but double-leaf in the architectural description; confirm on site. Assumed MBR-S and CBR pocket returns extend about 0.30 m beyond modeled room corners. The viewer clips them only for display; actual pocket ends remain unmeasured and held.
- Export the current view as PNG and the fixture / circuit schedules as CSV. The linked PDFs are in the adjacent `downloads` folder. When the viewer is opened from disk, a browser may open a PDF in a new tab; use the PDF viewer's Save button.
- Bound to the integrated lighting master SHA-256 `b6f6bf1a127c7e39086deb9fd1d2c0dff79a495381e1a4b9457f6a9a468f23ac`.
- Three.js 0.181.1 is bundled into `index.html`; its MIT notice is embedded and provided as `THREE-LICENSE.txt`. No CDN or network access is needed at runtime.
