"""Inventory the local review handoff without changing any source-pack artifacts."""

import argparse
import hashlib
import json
from pathlib import Path


def coverage(path):
    tags = set()
    name = Path(path).name
    if path.startswith("handoff/decisions/"):
        tags.add("owner-decision-addendum")
        if name == "2026-11-18-material-selection.md":
            tags.add("wardrobe-material-selection")
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
    parser.add_argument("--decision-addendum-publication-authorized", action="store_true")
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
    overlay_paths = (
        "handoff/decisions/2026-11-18-material-selection-receipt.json",
        "handoff/viewer/verification/2026-11-18-viewer-update-receipt.json",
        "handoff/viewer/verification/2026-11-19-cbr-r05-overlay-receipt.json",
    )
    overlays = {}
    for overlay_path in overlay_paths:
        overlay_data = json.loads((root / overlay_path).read_text())["postCopyOverlays"]
        overlays.update({item["path"]: (item, overlay_path) for item in overlay_data})
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
                matched = overlays.get(relative)
                if not matched:
                    raise ValueError(f"Imported artifact changed without a verified overlay: {relative}")
                overlay, receipt_path = matched
                previous_copy_value = overlay.get("previousCopyReceiptValue", overlay["previousCopySha256"])
                if previous_copy_value != source["sha256"] or overlay["currentSha256"] != sha:
                    raise ValueError(f"Imported artifact changed without a verified overlay: {relative}")
                record["postCopyOverlayReceipt"] = receipt_path
                if previous_copy_value != overlay["previousCopySha256"]:
                    record["correctedPriorCopySha256"] = overlay["previousCopySha256"]
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
        "publicationAuthorized": args.decision_addendum_publication_authorized,
        "publicationScope": ("Dated owner-decision addendum and review overlays only; no design or construction release."
                             if args.decision_addendum_publication_authorized else "No publication authorization asserted."),
        "decisionAddendum": {
            "path": "handoff/decisions/2026-11-18-owner-selections.md",
            "scope": "Six loft doors, three retained trays, matte-black handle finish; retain prior OPT-E matte-laminate material and master split only. Shutter mechanism, shade and complete interiors remain provisional.",
            "modelAndHistoricalOutputsRegenerated": False,
        },
        "materialSelectionAddendum": {
            "path": "handoff/decisions/2026-11-18-material-selection.md",
            "scope": "BWP plywood wardrobe carcasses with granite plinths; retain OPT-E matte-laminate shutters and master split. Granite shelves and unrelated utility/outdoor joinery are not included.",
            "modelAndHistoricalOutputsRegenerated": False,
            "historicalCostOutputsRepriced": False,
        },
        "note": "Original master, public-copy and delivered hashes are distinct. The dated material addendum supersedes only the stale WR-H630 material-pending and DEC-ST-01 readiness-pending entries; its construction details remain unapproved. Viewer/workbench maps remain frozen analytic estimates; the separate exploratory Radiance addendum is generic, provisional and not measured or product-specific. Manifest excludes itself.",
        "files": records,
    }
    (root / "handoff" / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Inventoried {len(records)} files, {sum(item['bytes'] for item in records):,} bytes")


if __name__ == "__main__":
    main()
