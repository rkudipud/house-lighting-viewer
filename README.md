# Hyderabad 2BHK light planner

Review draft. Not a construction release and not product approval.

A static, offline-capable viewer for the proposed lighting of a four-storey-house flat.
Open `index.html` (or the published page): choose a room, walk or orbit the flat, switch lights
on and off, and set LOW (cove / mood) and HIGH (main) brightness per room.
Colour temperatures are fixed per fitting and are not adjustable.
- Fixed CCT per base fitting from the integrated master: 30 x 2700 K, 12 x 3000 K, 62 x 4000 K. Brightness controls only.
- Current lighting-review fixed-CCT map SHA-256 `b673bf4189c251f28fb9327bfbc7e45e2009b452bc727cdaeca158a27eb7aa4f`; its placement holds are retained separately from viewer on/off state.
- Four selected 2700 K curtain strips follow existing LOW controls. The review schedule has 108 fittings / 51 circuits including these additions; the frozen photometric baseline remains 104 / 47 with no curtain-strip lux credit. Pocket sizes are unmeasured and CURT-MBR-W03 remains held and unlit.
- Dimming is visual only; the lux maps are frozen generic-optics estimates and are not recomputed.
- The four bedside readers and two PIR night lights are individual fitting previews, off by default; held readers cannot be enabled. The actual readers dim on the fitting and the night lights are PIR-operated, not extra wall dimmers.
- The selected dressing and utility cabinets are unmeasured conditional illustrations (FH-ST-03 / FH-ST-12), not construction-ready. One living LOW supply is selected for review; product, protection and electrical design remain on hold.
- Wardrobe interiors are provisional and unapproved; the viewer's open-cabinet illustration is not measured joinery. The current-bound wardrobe review PDF identifies the unchanged original interior-generation basis as 2ce3fcb4; measurement and sign-off remain open.
- Door leaves are hidden in the viewer; openings remain in the design. D01's leaf arrangement remains a site check. Assumed MBR-S and CBR pocket returns extend about 0.30 m beyond modeled room corners. The viewer clips them only for display; actual pocket ends remain unmeasured and held.
- The linked review PDFs are in the adjacent `downloads` folder. When the viewer is opened from disk, a browser may open a PDF in a new tab; use the PDF viewer's Save button.
- Bound to the integrated lighting master SHA-256 `1fa6b0fa040d2f0c81427d9277eb9b98f23170b7f63446f287000d58fc9002a4`.
- Three.js 0.181.1 is bundled into `index.html`; its MIT notice is embedded and provided as `THREE-LICENSE.txt`. No CDN or network access is needed at runtime.
