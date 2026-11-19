# Historical exploratory Radiance evidence

The children's-room grids and report predate the centred 1050 mm fan, shifted
LINE and modelled-ON LOW design. They are superseded for CBR; use the
[current review heatmaps](../lighting/current/heatmaps-summary.pdf) instead.

**Generic provisional ray-tracing estimates only. Not measured, not product-specific,
not construction, product, procurement or fabrication approval.**

Open the [report and static heatmaps](index.html), [full report](simulation-report.html),
[source report Markdown](simulation-report.md), [numerical model summary](analysis/sim-summary.json)
and [producer check results](analysis/checks.json).

The existing Three.js viewer and lighting workbench retain their separate frozen
analytic maps. This addendum is not dynamically connected to their controls.
No fixture location, aim, canonical master or approval hold was changed.

LIV-P1 was excluded: its inherited strip record is outside the canonical niche.
LIV-P2 misses that niche; both pooja records remain held. KIT-L1 overruns its
polygon by 0.4 ft; its unmeasured cove/slot remains held. Living/kitchen main-light
evenness is marginal under the stated model, not an instruction to move or add fittings.
UTL/BAL are enclosed approximations of open-air spaces. The
[six-room revision](revision-all-rooms/index.html) now supplies sensitivity for
UTL, DRS, LOB, TL1, TL2 and BAL, superseding only the earlier not-run statement.
Glare/UGR and daylight are not computed.
Selected curtain strips are excluded and receive no lux credit.

## What is preserved

In the earlier report's pack, the base per-fitting vectors, all source-receipt-listed sensitivity and convergence
JSON, summary, checks and heatmap grids retain their **exact original bytes**.
The low-sampling KIT results are retained as superseded evidence, not mixed into
the reported higher-sampling KIT sensitivity. See the report's paired-run groups.
Excluded parity diagnostics are not distributed or used for reported numbers.

[The public source receipt](simulation-receipt.json) preserves upstream hash
identifiers, not delivered-copy hash promises. Its private absolute paths are
replaced by meaningful repository-relative references.
[The copy receipt](repository-copy-receipt.json) records every included original
and public hash, precise transformations and three omitted tooling files.
Raw nonreceipt scenes, compiled binaries, host/job logs and scheduler tooling
are excluded. The report's host/job paragraph and omitted-tool rows are adapted;
its numerical findings, assumptions, sensitivity tables and holds are unchanged.
Original source packs were not modified.

## Editable source and reproduction limits

[Simulator](sim_radiance.py), [check/analysis code](check_sim.py) and
[cos^m formula](cosm.cal) are **source-review snapshots**,
not a portable repository-only simulation recipe. The simulator retains its
original-master hash guard, original `fm_*`/`lc_engine` dependencies, NumPy,
Windows/runtime assumptions and Radiance 6.0a / pyradiance 1.1.5 dependencies.
The public master is path-redacted and deliberately has different bytes;
substituting it must not bypass the guard.

Private remote-execution constants and implementation were removed from the
public simulator; requesting remote execution explicitly fails. The remote
driver, upstream report/job generator and historical low-sampling driver are
omitted. `check_sim.py` can itself invoke Radiance benchmarks: it was **not run**
as part of repository integration. Do not execute these snapshots against archived
evidence or treat them as independently rerun validation.

Static figures **can** be regenerated from delivered grids without Radiance:
from the repository root run `python -B scripts\render-simulation-evidence.py`
(requires Markdown and PyMuPDF). It writes only this addendum's derived figures,
CSV and readable HTML, not upstream evidence. Each SVG keeps every supplied
non-null rounded lux value and its mask; PNGs rasterize those SVGs.
The colour scale is fixed at 0-750 lux, with higher colours clipped but numerical
values untouched. Plan z increases downward. Task-area metrics come from the
report, not an average of the displayed cells.

[All grid cells as CSV](heatmap-cells.csv) retain blank outside-mask values.
[Derived evidence receipt](derived-evidence-receipt.json) records source hashes,
all image hashes and exhaustive SVG cell/mask verification.
[Independent local fidelity checks](local-simulation-verification.json) compare
all imported numeric hashes, every CSV/SVG cell and mask, and PNG sample pixels
without running Radiance (`python -B scripts\verify-simulation.py`, requires Pillow).

## Added remaining-room revision

The [historical report](simulation-report.md) and its source/public hashes remain
unchanged. Its statement that small-room sensitivity was not run is historical,
not the current coverage statement. The [revision report](revision-all-rooms/simulation-report-remaining.html)
supplements it with 54 room/case calculations and preserves every numerical table.
Pocket narrow/wide are **identical-scene controls, not physical pocket sensitivity**;
repeat spread is diagnostic, not a confidence interval. Actual pocket sensitivity
is unknown. UTL/BAL are enclosed approximations; bathrooms use floor-plane results
(samples 0.0005 m above floor); DRS/LOB task U0 uses only 12/8 points.

The revision includes nine raw result files, full analysis, 54 exact-byte editable
`.rad` scenes, archived analysis/verification source and producer verification.
Scenes use the separately included [generic cos^m formula](cosm.cal); no compiled
`.oct` files, execution/cleanup scripts or operational logs are distributed.
The archived source requires original evidence and receipt chains and must not
be run against public copies as a claim of full-chain reproduction.

Unlike the earlier pack's byte-identical numerical JSON, revision JSON has
private host/CPU metadata removed. Model/point/mask/vector payload digests are
unchanged; original and public file hashes are **different** where indicated in the
[revision copy receipt](revision-all-rooms/repository-copy-receipt.json).
Private absolute path references and the entire compute-job cleanup object
are removed from its public receipt. Compute-reservation cleanup is not an
engineering hold release. The receipt's original hash identifiers refer to
original upstream bytes, not redacted public bytes.

[The 54-case CSV](revision-all-rooms/sensitivity-summary.csv) and
[public-only verifier](revision-all-rooms/local-revision-verification.json) cover
612 recomputed raw statistic sets, numerical payload hashes, physical-sensitivity
report rows and 12 identical-scene control comparisons. Run
`python -B scripts\verify-remaining-sensitivity.py` from the repository root.
This does not rerun Radiance or verify private master/approval chains.
The 33 existing base map pairs are not sensitivity-case heatmaps, and the
viewer/workbench remains independent frozen analytic evidence.

This integrated addition awaits coordinator review. All technical and publication
holds remain; no fixture/canonical changes or simulation reruns were performed.
