# Historical reference simulations

**Generic, unmeasured estimates; not product validation or construction approval.**
The [gallery](index.html) contains 30 SVG/PNG pairs for ten rooms.
Superseded children's-room images and derived CSV rows have been removed.
Use the [current review heatmaps](../lighting/heatmaps-summary.pdf) for CBR.
The [historical report](simulation-report.html) is not current CBR photometry.
Viewer/workbench maps are separate frozen analytic estimates, not dynamic ray tracing.

## Required numerical evidence

The [original grids](analysis/sim-heatmaps.json), base per-fitting vectors,
paired-sensitivity runs, [summary](analysis/sim-summary.json) and
[checks](analysis/checks.json) retain their original bytes. Mixed-room source
files still contain historical CBR data; those are not current results.
The lower-sampling KIT values inside the shared MBR/CBR sweep are not used in
the reported higher-sampling KIT sensitivity.

`runs/smoke3/sim-results.json` and `runs/smoke4/sim-results.json` are required
KIT ad1024/ad128 sampling-convergence inputs, despite their early filenames.
The verifier recomputes all 13 fitting rows of the retained report's D0 table
from them; they are not unused smoke-test logs.

The [original source receipt](simulation-receipt.json) and
[copy receipt](repository-copy-receipt.json) distinguish original and public
hashes. The [cleanup receipt](../../cleanup-receipt.json) records exact retired
files and the evidence retained. Original source packs were not changed.

## Regeneration and checks

From the repository root:

```powershell
python -B scripts\render-simulation-evidence.py
python -B scripts\verify-simulation.py
python -B scripts\verify-remaining-sensitivity.py
```

These require Markdown, PyMuPDF and Pillow; they do not execute Radiance.
The first command renders the retained ten-room grids and
[CSV](heatmap-cells.csv). SVG values/masks, PNG sample pixels, source hashes and
KIT convergence are checked in the [local verification](local-simulation-verification.json).
The 0-750 lux colour scale clips colour only, not numerical exports.

The [six-room sensitivity revision](revision-all-rooms/index.html) retains
54 cases, nine raw result files and 54 editable scenes. Its public verifier
recomputes 612 statistic sets. Pocket narrow/wide cases are **identical-scene
controls, not physical pocket sensitivity**. Revision JSON is path/host-redacted;
its [copy receipt](revision-all-rooms/repository-copy-receipt.json) preserves
original and public hashes and unchanged numerical payload digests.

## Limits

[Simulator](sim_radiance.py), [analysis source](check_sim.py) and
[source formula](cosm.cal) are review snapshots requiring the original guarded
master/dependency chain, NumPy and Radiance 6.0a/pyradiance. Do not substitute
the redacted public master or bypass that guard. No independent Radiance rerun
or private approval-chain verification is claimed.

Pooja geometry/aim and KIT-L1 slot remain held; living/kitchen evenness is
marginal. UTL/BAL assume enclosure; bathroom results are floor-plane and DRS/LOB
task masks have only 12/8 points. Curtain strips have no lux credit.
Glare/UGR, daylight and selected-product compatibility are not validated.
Site, electrical, structural and fabrication approvals remain open.
