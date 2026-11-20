# Viewer and drawing generators

Review draft; not a construction release. The offline viewer is distributed separately.
This source bundle excludes the old local master snapshot, local cache, dependencies and
reference imagery. `src/house-data.generated.json` and `data/heat-data.json` are the
privacy-redacted viewer inputs, not the complete authoritative master.

The original master SHA-256, derived-data hashes, precise transformation and verified
HTML hash are in `privacy-transform.json` and `public-source-manifest.json`.
Geometry and non-path fields in the derived viewer input are unchanged by redaction;
provisional dimensions, review status and site/professional holds remain.

The viewer hides architectural door leaves, shows provisional storage interiors by default,
and offers whole-house HIGH/LOW brightness sliders, plus a compact fitting list. Its downloads
are PDF-only. To reproduce the current published HTML with Node.js, restore the pinned packages
with `npm ci`, then run `node rebuild-public.mjs --out <new-index.html>`. The command refuses
to write unless the result matches the current `build-info.json` HTML hash.
For intentional viewer source changes, run `npm run build:viewer`. This rebuilds the root
`index.html` and updates its build/privacy hashes while retaining the original verified
hashes. The source manifest and copy receipts describe the historical producer delivery,
not subsequent viewer UI changes. Plan and frozen heat-map data remain hash-checked.
Keep the repository `downloads`,
`handoff/electrician`, and `handoff/mason-civil` folders alongside the published viewer for
its PDF links.

The renderer uses fixed exposure, a soft ambient fill and separate area-normalized
HIGH/LOW bounce sources. These compressed visual sources are not calibrated lux;
fixture wattage, lumens, fixed colour and held status remain unchanged. HIGH retains
local floor pools and wall washes; LOW retains cove and curtain effects.

`build.mjs` rebuilds from the authoritative master and independently verified input
packs and receipts. It requires `--prior-master`, `--cct-master` and Python to
validate the CCT-only revision and the subsequent provisional children's-ceiling
revision against their predecessors. The layout views use the latest master; unchanged
floor-plan, curtain-section and wardrobe outputs retain their verified earlier basis.
The redacted viewer data cannot be substituted as a byte-identical master. Drawing
generators require the corresponding current canonical master and fragments. Generated
local verification receipts can contain local paths; review them before publication.
When supplied, the `provenance` directory retains original generator snapshots for checking the drawing
receipts; they are historical evidence, not the current generator, and can emit local
paths if run. Current generators and the public drawing staging script avoid or remove
those path fields.
Three.js is bundled under MIT; see `THREE-LICENSE.txt`.
