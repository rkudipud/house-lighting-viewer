"""Import the pinned exploratory simulation without executing any simulation code."""

import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path, PureWindowsPath
import re
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "handoff" / "electrician" / "simulation"
MASTER = "b6f6bf1a127c7e39086deb9fd1d2c0dff79a495381e1a4b9457f6a9a468f23ac"
RECEIPT_SHA = "504395aadbff043b1e5d2e4fad7ed9356b974ec44e8f3d4dc4a8a6446b6f0960"
REPORT_SHA = "bcf194bdf33ea3a78bd10aafa7bdb211a346925fd1374ca050308305d280b2dd"
OMIT = {
    "run_remote_sens.py": "Private compute-host/job submission tooling is not distributed.",
    "make_report.py": "Upstream report-regeneration/job bookkeeping is not required for reading results.",
    "run_sens.py": "Historical low-sampling driver includes superseded kitchen cases; not a reproduction recipe.",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def public_simulator(text):
    lines = text.splitlines(keepends=True)
    replacements = []
    for node in ast.parse(text).body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id in {"REMOTE_LOGIN", "REMOTE_ROOT", "REMOTE_PYRAD"}
            for target in node.targets
        ):
            replacements.append((node.lineno - 1, node.end_lineno, []))
        elif isinstance(node, ast.FunctionDef) and node.name == "run_rcontrib_remote":
            replacements.append((node.lineno - 1, node.end_lineno, [
                "def run_rcontrib_remote(rad_path, mods, P, args, tag):\n",
                "    raise RuntimeError('Remote execution is omitted from this public source snapshot.')\n",
            ]))
    if len(replacements) != 4:
        raise ValueError("Unexpected upstream remote-execution structure; review before importing")
    for start, end, replacement in sorted(replacements, reverse=True):
        lines[start:end] = replacement
    result = "".join(lines).replace(
        "compute node hostname (zsc15); rcontrib runs there via the login jump host",
        "Remote execution is unavailable in this public source snapshot",
    )
    ast.parse(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve()
    receipt_bytes = (source / "simulation-receipt.json").read_bytes()
    if sha(receipt_bytes) != RECEIPT_SHA:
        raise ValueError("Source simulation receipt differs from the coordinator-supplied hash")
    receipt = json.loads(receipt_bytes)
    if receipt["master"]["sha256"] != MASTER:
        raise ValueError("Wrong simulation master")
    spec = importlib.util.spec_from_file_location("stage_reviewed", ROOT / "scripts" / "stage-reviewed-pack.py")
    stage = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stage)
    validated = {}
    for name, expected in receipt["files"].items():
        path, _ = stage.relative_file(source, name)
        data = path.read_bytes()
        if sha(data) != expected:
            raise ValueError("Source receipt hash mismatch: " + name)
        validated[name] = data
    if sha(validated["simulation-report.md"]) != REPORT_SHA:
        raise ValueError("Source report differs from the coordinator-supplied hash")
    mappings = [
        (PureWindowsPath(str(source)), DEST.relative_to(ROOT).as_posix()),
        (PureWindowsPath(receipt["master"]["path"]).parent, "handoff/source-basis"),
        (PureWindowsPath(receipt["delivered_review_manifest"]["path"]).parent, "handoff/electrician/lighting"),
    ]
    validated["simulation-receipt.json"] = receipt_bytes
    records = []
    for name, data in validated.items():
        if name in OMIT:
            continue
        public = data
        transformations = []
        if name.endswith(".json"):
            original = json.loads(data)
            safe = stage.redact(original, mappings)
            if safe != original:
                public = (json.dumps(safe, indent=2) + "\n").encode()
                transformations.append("Absolute source paths replaced with repository-relative references.")
        elif name == "sim_radiance.py":
            text = public_simulator(data.decode("utf-8"))
            original = receipt["master"]["path"]
            if text.count(original) != 1:
                raise ValueError("Unexpected simulator master-path reference")
            text = text.replace(original, "handoff/source-basis/house-design.json")
            public = text.encode("utf-8")
            transformations.append("Private master path redacted; host/user/shared-filesystem constants and remote execution body removed; remote call explicitly fails. Local model mathematics retained.")
        elif name == "simulation-report.md":
            text, count = re.subn(
                r"^> \*\*Compute:\*\*.*$",
                "> **Public-copy compute note:** Supplied base and paired sensitivity results are preserved. "
                "Execution-host and job details are not distributed. The source receipt's parity diagnostic "
                "is excluded from reported results. Original/public hashes and omissions are recorded in "
                "`repository-copy-receipt.json`.",
                data.decode("utf-8"), flags=re.MULTILINE,
            )
            if count != 1:
                raise ValueError("Unexpected report compute-provenance paragraph")
            text = "\n".join(
                line for line in text.splitlines()
                if not any(line.startswith("| `" + omitted + "`") for omitted in OMIT)
            ) + "\n"
            public = text.encode("utf-8")
            transformations.append("Compute-host/job paragraph replaced with public provenance note; three omitted tooling rows removed. All numerical findings, assumptions and holds retained.")
        target = DEST / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(public)
        records.append({
            "path": name, "bytes": len(public), "sha256": sha(public),
            "sourceSha256": sha(data), "publicCopyModified": public != data,
            "transformations": transformations,
        })
    copy = {
        "status": "EXPLORATORY_local_design_review_only",
        "constructionRelease": False, "publicationAuthorized": False,
        "basisMasterSha256": MASTER,
        "sourceManifest": "simulation-receipt.json",
        "sourceManifestSha256": RECEIPT_SHA,
        "sourceReportSha256": REPORT_SHA,
        "verifiedUpstreamReceiptEntries": len(receipt["files"]),
        "radianceExecutedDuringIntegration": False,
        "sourcePacksModified": False,
        "omittedFiles": [
            {"path": name, "sourceSha256": receipt["files"][name], "reason": reason}
            for name, reason in OMIT.items()
        ],
        "unlistedArtifactPolicy": "Nonreceipt scratch scenes, binaries, host/job logs and excluded parity artifacts are not copied.",
        "sourceManifestNote": "The public simulation receipt describes original upstream hashes, including omitted tooling; delivered hashes are in this copy receipt and the main repository inventory.",
        "files": records,
    }
    (DEST / "repository-copy-receipt.json").write_text(json.dumps(copy, indent=2) + "\n", encoding="utf-8")
    (DEST / "public-file-hashes.json").write_text(
        json.dumps({record["path"]: record["sha256"] for record in records}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Verified {len(receipt['files'])} upstream hashes; imported {len(records)} bounded public copies")


if __name__ == "__main__":
    main()
