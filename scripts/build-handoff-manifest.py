"""Inventory the local review handoff without changing any source-pack artifacts."""

import argparse
import hashlib
import json
from pathlib import Path


def coverage(path):
    tags = set()
    name = Path(path).name
    if "source-index/room-opening-index" in path:
        tags.add("room-opening-index")
    if name == "lighting-workbench.html":
        tags.add("lighting-workbench")
    if name.startswith("control-options."):
        tags.add("control-options")
    if name in {"switchboard-schedule.csv", "wall-control-schedule.csv"}:
        tags.add("switchboard-control-schedule")
    if "/lighting/" in path and "heatmap" in path:
        tags.add("heatmaps")
    if path.startswith("handoff/electrician/simulation/") and name in {
        "simulation-report.md", "simulation-report.html", "sim-heatmaps.json", "sim-summary.json"
    }:
        tags.add("exploratory-raytracing")
    if "simulation/revision-all-rooms/" in path:
        tags.add("remaining-room-sensitivity")
    if path.startswith("handoff/viewer/drawings/working-plan/house-working-floorplan."):
        tags.add("floorplan")
    if "/layout-views/" in path and "-elev-" in name:
        tags.add("dimensioned-wall-layouts")
    if path == "index.html":
        tags.add("threejs-viewer")
    if name.startswith("lighting-plan-"):
        tags.add("lighting-placement")
    if name.startswith(("concept-flat.", "concept-living-low.", "controls-plan.")):
        tags.add("wiring-electrical-layout")
    if name == "location-linked-bom.csv":
        tags.add("location-specification-bom")
    if name == "wardrobe-interiors.json" or "-interior-elevation." in name:
        tags.add("wardrobe-interiors")
    if name.startswith(("02-rcp.", "C01-ceiling-section.")):
        tags.add("ceiling")
    if path.startswith("handoff/viewer/renders/") and name.endswith(".png"):
        tags.add("renders")
    if Path(path).suffix in {".py", ".js", ".mjs", ".json", ".csv", ".svg", ".rad", ".cal"}:
        tags.add("editable-sources")
    if path.startswith("handoff/references/") and name.endswith(".jpeg"):
        tags.add("approved-references")
    return sorted(tags)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master-sha256", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    build = json.loads((root / "build-info.json").read_text())
    if build["masterSha256"] != args.master_sha256:
        parser.error("Integrated viewer does not match the confirmed canonical master")
    imported = {}
    for receipt_path in (root / "handoff").rglob("*repository-copy-receipt.json"):
        receipt = json.loads(receipt_path.read_text())
        if "deliveredRoot" in receipt:
            base = root / receipt["deliveredRoot"]
        elif receipt_path.name == "site-repository-copy-receipt.json":
            base = root
        else:
            base = receipt_path.parent
        for item in receipt["files"]:
            path = (base / item["path"]).resolve()
            if not path.is_relative_to(root):
                raise ValueError("A copy receipt points outside the repository")
            imported[path.relative_to(root).as_posix()] = item
    paths = [
        root / name for name in (
            "README.md", "index.html", "build-info.json", "privacy-transform.json",
            "THREE-LICENSE.txt", ".nojekyll", ".gitattributes", ".gitignore",
        )
    ]
    for directory in ("handoff", "downloads", "scripts"):
        paths.extend(path for path in (root / directory).rglob("*") if path.is_file())
    records = []
    for path in sorted(set(paths)):
        relative = path.relative_to(root).as_posix()
        if relative == "handoff/manifest.json" or any(
            part in {"__pycache__", "node_modules", ".venv"} for part in path.parts
        ) or path.suffix == ".pyc":
            continue
        data = path.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        record = {"path": relative, "bytes": len(data), "sha256": sha, "coverage": coverage(relative)}
        if relative in imported:
            source = imported[relative]
            if source["sha256"] != sha or source["bytes"] != len(data):
                raise ValueError(f"Imported artifact changed since its copy receipt: {relative}")
            record["sourceSha256"] = source.get("sourceSha256", source["sha256"])
        records.append(record)
    integration = json.loads((root / "handoff" / "integration-receipt.json").read_text())
    review = integration["coordinatorReview"]
    accepted = review["status"] == "accepted" and review["scope"] == "local-design-review-only"
    manifest = {
        "schema": "house-handoff-inventory/1",
        "status": ("local-design-review-simulation-revision-pending"
                   if accepted and integration.get("simulationAddendum", {}).get("pendingSmallRoomRevision")
                   else "local-design-review-simulation-addendum-awaiting-review"
                   if accepted and integration.get("simulationAddendum", {}).get("integrationReview") == "pending"
                   else "local-design-review-accepted" if accepted else "local-review-awaiting-coordinator-approval"),
        "coordinatorReview": review,
        "masterSha256": args.master_sha256,
        "constructionRelease": False,
        "productRelease": False,
        "procurementRelease": False,
        "fabricationRelease": False,
        "publicationAuthorized": False,
        "note": "Original master, public-copy and delivered hashes are distinct. Viewer/workbench maps remain frozen analytic estimates; the separate exploratory Radiance addendum is generic, provisional and not measured or product-specific. Manifest excludes itself.",
        "files": records,
    }
    (root / "handoff" / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Inventoried {len(records)} files, {sum(item['bytes'] for item in records):,} bytes")


if __name__ == "__main__":
    main()
