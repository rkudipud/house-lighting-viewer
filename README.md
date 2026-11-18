# Hyderabad 2BHK coordinated review handoff

**Design review only. Not a construction, fabrication, product or procurement
release. The owner decision update is separately versioned from unchanged
master-bound models and outputs.**

Coordinator review is **accepted for local design review only**, not construction,
product, procurement or fabrication approval. This focused decision update is
authorized for repository/Pages publication; all professional and site holds remain open.

The simulation addendum now includes the separately verified
[six-room sensitivity revision](handoff/electrician/simulation/revision-all-rooms/index.html).
Its integration awaits coordinator review; the earlier scoped acceptance is not
technical approval of this addition or a final construction handoff.

Start with the [trade handoff](handoff/index.html), the [offline Three.js viewer](index.html),
or the [three final review renders and drawing issue](handoff/viewer/index.html).

Read the [18 November owner decision addendum](handoff/decisions/2026-11-18-owner-selections.md)
with all packs: matte-black handles, three retained trays and six children's loft
doors. General interiors, pooja finish and soft-close hardware remain
proposals. Model/drawing/cost outputs have not been regenerated for these choices.
The [separate visual wardrobe review](handoff/decisions/2026-11-18-wardrobe-review.html)
highlights these choices over the unchanged provisional source interiors. The earlier
OPT-E matte-laminate material and master split are retained; shutter mechanism, exact shade,
full interiors and measured fit remain unresolved.

| Review material | Entry point |
| --- | --- |
| Electrician: workbench, control options, switchboards, wiring concepts, heatmaps and location/specification BOM | [Lighting and electrical](handoff/electrician/index.html) |
| Separate exploratory Radiance report, paired sensitivity results and static ray-tracing heatmaps | [Simulation evidence addendum](handoff/electrician/simulation/index.html) |
| Mason/civil: source-based room/opening index, dimensioned review plans, ceiling and wall drawings, site/structural holds | [Civil coordination](handoff/mason-civil/index.html) |
| Contractor/joinery: selected scope, provisional wardrobe interiors, costs and editable public source | [Wardrobe and contractor](handoff/contractor/index.html) |
| Current visual floorplan, curtain section, source-rebuild guide and three renders | [Viewer and drawings](handoff/viewer/index.html) |
| Three approved user photographs, explicitly not measured evidence | [Site views](handoff/index.html#site-views) |

The original canonical master SHA-256 is
`b6f6bf1a127c7e39086deb9fd1d2c0dff79a495381e1a4b9457f6a9a468f23ac`.
The viewer's privacy-derived embedded plan SHA-256 is
`33dd7317e805a9c9bc790c160dcfd6187c38fed9fffd97c13ba74b64267ed600`.
Original, public-copy and delivered hashes are distinct and documented in the
[inventory](handoff/manifest.json), pack receipts and [viewer privacy record](privacy-transform.json).
The [historical provenance correction](handoff/source-basis/generated/wardrobe-interiors-provenance-correction.json)
records an unavailable intermediate lighting manifest; it is not reconstructed or verified.

The viewer works offline, with bundled Three.js 0.181.1 and its
[MIT notice](THREE-LICENSE.txt). Choose a room, walk/orbit, preview fixed-CCT
fittings, adjust visual HIGH/LOW brightness and optionally illustrate provisional
cabinet interiors. Four selected curtain strips bring the review schedule to
108 fittings/strips and 51 circuits; the frozen optical baseline remains 104/47.
PNG, CSV and four current PDF downloads are available from the viewer.

**The viewer's visual lighting is illustrative; its maps remain frozen analytic estimates.**
The separate Radiance addendum supplies generic provisional ray-tracing estimates,
not product-specific or measured validation, and is not connected to viewer controls.
Selected curtain strips have no lux credit. The current 3D
viewer withholds the older children's grid; retained workbench/source estimates
do not validate corrected room geometry or installation performance.

The simulation excludes LIV-P1; both pooja records and KIT-L1's 0.4 ft polygon
overrun remain held. UTL/BAL remain enclosed approximations. The added six-room
revision supersedes only the historical small-room sensitivity not-run statement.
Pocket narrow/wide are identical-scene controls, **not physical pocket sensitivity**;
bathroom results are floor-plane and DRS/LOB task U0 uses only 12/8 points.
Glare/daylight are not computed. No fixtures, canonical data or approval holds changed.

Site dimensions, door/route clearances, curtain-pocket fit, loft/support loads,
wall changes, structural fixings, electrical protection, earthing, supply/controller
ratings, inrush and exact dimmer/driver compatibility remain professional holds.
Wardrobe interiors and shutters remain provisional; measured quotations and the
480 W living supply price delta are unverified. Public access is not approval.

Third-party manufacturer PDFs are not redistributed; twelve omissions and
official links are recorded in the electrical public-copy receipt. Only the
three approved house photographs are included. Retired floorplans, old G-series
joinery, raw private drawing/verification folders and private wardrobe master
snapshots are excluded from the active reading set.

## Verification and editable sources

Run `python scripts\verify-handoff.py --master-sha256 b6f6bf1a127c7e39086deb9fd1d2c0dff79a495381e1a4b9457f6a9a468f23ac`
for file integrity, required coverage, relative HTML links and source-path checks.
Rendering and browser evidence is recorded separately in the local integration receipt.
Optional local checks are `python scripts\check-handoff-artifacts.py` (PyMuPDF,
Pillow and Markdown) and `python scripts\check-local-viewer.py` (Playwright,
Pillow and installed Microsoft Edge). They render/decode the deliverables and
exercise the offline viewer and a temporary localhost Pages-style URL prefix;
they do not publish anything.
`python -B scripts\verify-simulation.py` checks the separate simulation's original/public
hashes, grid/CSV/SVG fidelity and PNG sample pixels without invoking Radiance.
`python -B scripts\verify-remaining-sensitivity.py` recomputes 612 statistic sets
from the added six-room vectors and checks its 54-case CSV and identical-scene controls.
It does not verify private master/approval chains or run Radiance.

The [viewer public-source guide](handoff/viewer/source/README.md) rebuilds the exact
verified HTML from privacy-safe data and pinned packages. The
[wardrobe public-source guide](handoff/contractor/wardrobe/README.md) supports
snapshot regeneration and text/render comparisons, not private master or approval
chain verification. Civil generators and lighting/electrical source snapshots
retain their documented original-input and portability limits.

The complete inventory includes PDFs, SVGs, PNGs, approved JPEGs, editable JSON,
CSV, source scripts, templates, requirements, package locks, licences and receipts.
This decision update is authorized for the repository's `main` branch and Pages;
public availability does not release any construction or professional/site holds.
