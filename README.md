# Hyderabad 2BHK light planner

Review draft. Not a construction release and not product approval.

A static, offline-capable viewer for the proposed lighting of a four-storey-house flat.
Open `index.html` (or the published page): choose a room, walk or orbit the flat, switch lights
on and off, and set LOW (cove / mood) and HIGH (main) brightness per room.
Colour temperatures are fixed per fitting and are not adjustable.

- Dimming is visual only; the lux maps are frozen generic-optics estimates and are not recomputed.
- Export the current view as PNG, the fixture / circuit schedules as CSV, and the drawings as PDF.
- Bound to the integrated lighting master SHA-256 `e0bf1af22850905405eec2e8c07940f9e8d5a6ac04baecc03547a3fdcc733b72`.
- Three.js 0.181.1 is bundled into `index.html`; no CDN or network access is needed at runtime.
