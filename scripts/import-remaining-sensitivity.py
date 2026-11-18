"""Import and present the pinned six-room revision without executing upstream code."""

import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path, PureWindowsPath
import sys

import markdown

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "handoff" / "electrician" / "simulation"
DEST = PACK / "revision-all-rooms"
PINS = {
    "simulation-report-remaining.md": "520968933b162cf398eb57368195f83f5e4a298a9528a74c89e26b74d8653759",
    "simulation-receipt-remaining.json": "0a28c98621b2523156370f062d922d6872850af4438824d2ca7776f8f686dbcb",
    "independent-verification.json": "0f6f13e09f85961d163db80548b4208f36f481499f730232ece6979fdb068cc5",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def remove_host_metadata(value, changes, prefix=""):
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            path = prefix + "/" + key
            if key in {"host", "nproc", "remote_cleanup"}:
                changes.append(path)
            else:
                result[key] = remove_host_metadata(item, changes, path)
        return result
    if isinstance(value, list):
        return [remove_host_metadata(item, changes, prefix + "/" + str(i)) for i, item in enumerate(value)]
    return value


def payload(value):
    if "enclosures" in value:
        return {key: value[key] for key in
                ("master_sha256", "variant", "V", "MF", "assumptions", "params", "units", "enclosures")}
    return {key: item for key, item in value.items() if key != "engines"}


def canonical_sha(value):
    return sha(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve()
    for name, expected in PINS.items():
        if sha((source / name).read_bytes()) != expected:
            raise ValueError("Coordinator pin mismatch: " + name)
    receipt = json.loads((source / "simulation-receipt-remaining.json").read_bytes())
    stage = module("stage_reviewed", "stage-reviewed-pack.py")
    presentation = module("simulation_presentation", "render-simulation-evidence.py")
    inputs = {}
    omitted = []
    for original, expected in receipt["files"].items():
        path, relative = stage.relative_file(source, original)
        data = path.read_bytes()
        if sha(data) != expected:
            raise ValueError("Source receipt hash mismatch: " + original)
        name = relative.as_posix()
        if (name in {"analysis-remaining.json", "simulation-report-remaining.md",
                     "analyse_remaining.py", "verify_remaining.py"}
                or name.endswith(("/sim-results.json", ".rad"))):
            inputs[name] = data
        else:
            omitted.append({
                "path": name, "sourceSha256": expected,
                "reason": "Compiled scene, execution/cleanup/job tooling or operational log; not needed to inspect results.",
            })
    for name in ("simulation-receipt-remaining.json", "independent-verification.json"):
        inputs[name] = (source / name).read_bytes()
    maps = [
        (PureWindowsPath(str(source)), DEST.relative_to(ROOT).as_posix()),
        (PureWindowsPath(str(source.parent)), PACK.relative_to(ROOT).as_posix()),
        (PureWindowsPath(receipt["master"]["path"]).parent, "handoff/source-basis"),
        (PureWindowsPath(receipt["delivered_review_manifest"]["path"]).parent, "handoff/electrician/lighting"),
    ]
    records = []
    for name, data in inputs.items():
        delivered = data
        changes = []
        numeric_hash = None
        if name.endswith(".json"):
            original = json.loads(data)
            metadata_safe = remove_host_metadata(original, changes)
            safe = stage.redact(metadata_safe, maps)
            if safe != metadata_safe:
                changes.append("Absolute source paths replaced with repository-relative references; original hashes still describe original bytes.")
            if safe != original:
                delivered = (json.dumps(safe, indent=2) + "\n").encode()
            if name == "analysis-remaining.json" or name.endswith("/sim-results.json"):
                numeric_hash = canonical_sha(payload(original))
                if canonical_sha(payload(safe)) != numeric_hash:
                    raise ValueError("Privacy transformation altered model/results: " + name)
        elif name == "simulation-report-remaining.md":
            text = data.decode()
            excluded_prefixes = (
                "- `run_remaining.py`", "- `remote-cleanup.json`",
                "- `stream-A.log`",
            )
            text = "\n".join(line for line in text.splitlines()
                             if not line.startswith(excluded_prefixes)) + "\n"
            text += ("\nPublic-copy note: operational job/log/cleanup artifacts and compiled scenes are omitted. "
                     "Analysis and verification scripts are archived source snapshots, not a portable "
                     "verification of the private master/receipt chain. Source/public hashes and omissions "
                     "are recorded in `repository-copy-receipt.json`.\n")
            source_tables = [line for line in data.decode().splitlines() if line.startswith("|")]
            if source_tables != [line for line in text.splitlines() if line.startswith("|")]:
                raise ValueError("Report tables changed")
            delivered = text.encode()
            changes.append("Operational evidence bullets omitted; public source/chain limitation appended; all tables and findings unchanged.")
        target = DEST / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(delivered)
        record = {"path": name, "bytes": len(delivered), "sha256": sha(delivered),
                  "sourceSha256": sha(data), "publicCopyModified": delivered != data,
                  "removedMetadataOrChanges": changes}
        if numeric_hash:
            record["modelPayloadSha256"] = numeric_hash
        records.append(record)
    public = {
        "status": "EXPLORATORY_six_room_revision_for_local_design_review",
        "basisMasterSha256": receipt["master"]["sha256"],
        "sourceManifest": "simulation-receipt-remaining.json",
        "sourceManifestSha256": PINS["simulation-receipt-remaining.json"],
        "sourceReportSha256": PINS["simulation-report-remaining.md"],
        "sourceIndependentVerificationSha256": PINS["independent-verification.json"],
        "verifiedUpstreamReceiptEntries": len(receipt["files"]),
        "radianceExecutedDuringIntegration": False, "sourcePacksModified": False,
        "constructionRelease": False, "publicationAuthorized": False,
        "note": "Original file hashes are not delivered hashes. Only host/CPU/cleanup metadata and private path references are removed; model payload digests protect every result/point/mask/parameter. Remote operational cleanup holds are not engineering approvals.",
        "omittedFiles": omitted, "files": records,
    }
    (DEST / "repository-copy-receipt.json").write_text(json.dumps(public, indent=2) + "\n", encoding="utf-8")
    (DEST / "public-file-hashes.json").write_text(
        json.dumps({record["path"]: record["sha256"] for record in records}, indent=2) + "\n",
        encoding="utf-8",
    )
    analysis = json.loads((DEST / "analysis-remaining.json").read_text())
    with (DEST / "sensitivity-summary.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["room", "variant", "interpretation", "plane_m", "task_points",
                         "HIGH_avg_lx", "HIGH_min_lx", "HIGH_U0",
                         "LOW_avg_lx", "LOW_min_lx", "LOW_U0", "HIGH_change_pct", "LOW_change_pct"])
        for room, variants in analysis["rooms"].items():
            for variant, result in variants.items():
                interpretation = ("identical-scene repeat control, not physical pocket sensitivity"
                                  if variant.startswith("pocket_") else "baseline" if variant == "base"
                                  else "hypothetical generic-optics sensitivity, not a design change")
                lo = result["LOW"] or {}
                writer.writerow([room, variant, interpretation,
                                 analysis["grid_shapes"][room]["plane_m"],
                                 analysis["grid_shapes"][room]["task_points"],
                                 result["HIGH"]["avg"], result["HIGH"]["min"], result["HIGH"]["U0"],
                                 lo.get("avg"), lo.get("min"), lo.get("U0"),
                                 result["delta_pct"]["HIGH"], result["delta_pct"]["LOW"]])
    body = markdown.markdown((DEST / "simulation-report-remaining.md").read_text(), extensions=["tables", "fenced_code"])
    banner = '<a href="index.html">Revision evidence and limitations</a> / <a href="../index.html">Earlier report and base grids</a>'
    (DEST / "simulation-report-remaining.html").write_text(presentation.page("Six-room sensitivity revision", banner + body), encoding="utf-8")
    links = "".join(
        f'<li><a href="{record["path"]}">{record["path"]}</a></li>'
        for record in records if record["path"].endswith((".rad", "/sim-results.json"))
    )
    intro = """
<a href="../index.html">Earlier report and base heatmaps</a>
<h1>Remaining-room sensitivity revision</h1>
<p class="hold"><strong>EXPLORATORY, GENERIC, NOT MEASURED OR PRODUCT-SPECIFIC.
All construction, product, procurement, fabrication and publication holds remain.</strong>
This revision supersedes only the earlier statement that small-room sensitivity was not run.
It supplements rather than rewrites the historical report. No fixtures, canonical data or prior holds changed.</p>
<p>Six rooms (UTL, DRS, LOB, TL1, TL2, BAL), nine cases each: 54 enclosure/case calculations.
Pocket narrow/wide are <strong>identical-scene controls, not physical pocket sensitivity</strong>;
actual pocket geometry response remains unknown. No-op scatter is not a confidence interval.</p>
<p class="hold">UTL/BAL remain enclosed approximations of open-air spaces.
Bathrooms use the floor plane (samples 0.0005 m above it), not face/mirror validation.
Dressing/lobby task U0 uses only 12/8 mask points, not whole-room uniformity.
Pooja, KIT-L1, curtain-strip and all earlier holds remain. Glare/UGR and daylight are not computed.</p>
<p><a href="simulation-report-remaining.html">Readable revision report</a> /
<a href="simulation-report-remaining.md">Markdown</a> /
<a href="analysis-remaining.json">Full model/sensitivity analysis</a> /
<a href="sensitivity-summary.csv">54-case CSV</a> /
<a href="independent-verification.json">Producer independent verification</a> /
<a href="simulation-receipt-remaining.json">Public copy of source receipt</a> /
<a href="public-file-hashes.json">Public file hash index</a> /
<a href="repository-copy-receipt.json">Original/public hashes and omissions</a> /
<a href="local-revision-verification.json">Local fidelity verification</a>.</p>
<p>The original 33 base heatmap pairs remain base-run estimates, not the new sensitivity vectors.
Viewer/workbench maps remain separate frozen analytic estimates with no dynamic coupling.
Archived analysis/verification source is available as
<a href="analyse_remaining.py">analysis snapshot</a> and <a href="verify_remaining.py">verification snapshot</a>;
private input/receipt chains are not publicly reproducible. No Radiance rerun occurred during integration.</p>
<p>Editable .rad scenes retain exact original bytes; their generic
<a href="../cosm.cal">cos^m formula</a> is available separately. No .oct binaries, host/job logs
or execution/cleanup scripts are distributed. Source hash identifiers in the redacted producer
receipt still refer to original bytes, not public copies. Use the copy receipt for delivered hashes.
Run <code>python -B scripts\\verify-remaining-sensitivity.py</code> from the repository root
for public-only numerical/scene-control/CSV fidelity checks, not private master or approval-chain verification.</p>
<details><summary>All included raw result and editable scene evidence</summary><ul>
"""
    (DEST / "index.html").write_text(presentation.page("Remaining-room sensitivity", intro + links + "</ul></details>"), encoding="utf-8")
    print(f"Verified {len(receipt['files'])} upstream entries; imported {len(records)} public files and 54-case CSV")


if __name__ == "__main__":
    main()
