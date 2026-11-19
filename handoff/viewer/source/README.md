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
and offers whole-house HIGH/LOW masters plus selected-room lighting controls. Its downloads
are PDF-only. To reproduce the exact verified HTML with Node.js, restore the pinned packages
with `npm ci`, then run `node rebuild-public.mjs --out <new-index.html>`. The command refuses
to write unless the result matches the recorded HTML hash. Keep the repository `downloads`,
`handoff/electrician`, and `handoff/mason-civil` folders alongside the published viewer for
its PDF links.

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
