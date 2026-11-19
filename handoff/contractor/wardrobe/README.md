# Wardrobe review pack: public reproduction

This folder is the public source subset. It excludes the private historical
master snapshots and integration receipts; those originals remain unchanged.
Do not copy the full private `reproduction-inputs` directory into this folder.

The interiors were originally generated against master `2ce3fcb4...`; the
review snapshot records a later reference-only binding to `b6f6bf1a...`. These
are recorded identifiers here, not independently verified master files.
Interior layouts remain provisional; site measurement, fit, support and
fabrication holds remain open.

The current post-master material choice is recorded separately in
[`../../decisions/2026-11-18-material-selection.md`](../../decisions/2026-11-18-material-selection.md):
BWP plywood wardrobe carcasses with granite plinths, retaining the previously
selected OPT-E matte-laminate shutters. It does not select granite shelves or
change the separate utility aluminium or outdoor/wet-area joinery. The source
snapshot and generated costs remain unchanged; thickness, grade, plinth detail,
waterproofing and other shop details require confirmation.

## Run in an isolated copy

The generator rewrites its own snapshot and `final` folder, and writes
supporting files to its parent. Do not run it in a published folder or beside
the canonical master. Python 3.15.1 on Windows with the pinned packages in
`requirements-wardrobe.txt` was used for the recorded verification. Do not use
Python's `-O` flag: the validator uses assertions.

```powershell
$src = (Get-Location).Path  # this public source folder
$work = Join-Path $env:TEMP ("wardrobe-public-" + [guid]::NewGuid().ToString("N"))
$dst = Join-Path $work "storage-design"
New-Item -ItemType Directory -Path $dst -Force | Out-Null
Copy-Item -Path (Join-Path $src "*") -Destination $dst -Recurse
Set-Location $dst
python -B .\signoff_pack.py
if ($LASTEXITCODE -ne 0) { throw "Generation failed" }
python -B .\verify_public.py
if ($LASTEXITCODE -ne 0) { throw "Validation failed" }
```

Install the exact requirements only if the dependencies are missing. Rebuilds
on other Python, OS or graphics versions may differ.

## Verification scope

The public check tests snapshot cost arithmetic, interiors and basic parameter
guards, and compares 31 output hashes to `public-reproduction-expected.json`.
It compares extracted text and 72-dpi render hashes for all 17 PDF pages; the
PDF bytes can differ because its trailer ID changes. It also checks the
recorded holds and relative image links.

It does **not** validate the snapshot against the historical masters, prove the
homeowner decisions or integration receipt chain, or verify historical master
hashes. It does not recreate the private `rollup-receipt.json`. Those checks
require the separately retained unredacted inputs and original
`verify_rollup.py`; do not treat public reproduction as provenance verification
or fabrication approval.

The expected reference is an independently recorded comparison baseline, not
proof that the baseline itself is authentic. Re-recording it would change what
is being tested. The included `public-reproduction-receipt.json` records the
isolated test and hashes of its source inputs.
