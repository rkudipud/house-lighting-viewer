"""Inventory the local review handoff without changing any source-pack artifacts."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath


def repository_path(root, value):
    if not isinstance(value, str) or "\\" in value:
        raise ValueError(f"Invalid evidence path: {value!r}")
    relative = PurePosixPath(value)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts or ":" in value:
        raise ValueError(f"Unsafe evidence path: {value!r}")
    path = root.joinpath(*relative.parts).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"Evidence path leaves repository: {value!r}")
    return path


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_cleanup(root, cleanup, master_sha256):
    if cleanup["masterSha256"] != master_sha256:
        raise ValueError("Cleanup receipt is bound to a different master")
    for item in cleanup["removedArtifacts"]:
        if repository_path(root, item["path"]).exists():
            raise ValueError(f"Retired artifact was reintroduced: {item['path']}")
    for item in cleanup["retainedEvidence"]:
        if file_hash(repository_path(root, item["path"])) != item["sha256"]:
            raise ValueError(f"Required cleanup evidence changed: {item['path']}")


def verify_review_overlay(root, overlay, master_sha256, viewer_successors):
    """Recheck each successor copy against its pinned receipt and source manifest."""
    if overlay.get("masterSha256") != master_sha256:
        raise ValueError("Final overlay is bound to a different master")
    receipts = {}
    for receipt_name, expected_hash in overlay["copyReceiptSha256"].items():
        receipt_path = repository_path(root, receipt_name)
        if file_hash(receipt_path) != expected_hash:
            raise ValueError(f"Final overlay copy receipt changed: {receipt_name}")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8-sig"))
        if receipt["basisMasterSha256"] != master_sha256 or receipt["constructionRelease"] is not False:
            raise ValueError(f"Final overlay copy receipt has an invalid basis: {receipt_name}")
        entries = {item["path"]: item for item in receipt["files"]}
        if len(entries) != len(receipt["files"]):
            raise ValueError(f"Duplicate paths in {receipt_name}")
        manifest_name = receipt["sourceManifest"]
        manifest_entry = entries.get(manifest_name)
        if not manifest_entry or manifest_entry["sourceSha256"] != receipt["sourceManifestSha256"]:
            raise ValueError(f"Source manifest is not bound by {receipt_name}")
        manifest_path = repository_path(root, (receipt_path.parent / manifest_name).relative_to(root).as_posix())
        if manifest_path.suffix.lower() == ".txt":
            source_files = {}
            for line in manifest_path.read_text(encoding="utf-8-sig").splitlines():
                digest, name = line.split(maxsplit=1)
                source_files[name.lstrip("*").replace("\\", "/")] = digest
        else:
            source_files = {
                name: item["sha256"]
                for name, item in json.loads(manifest_path.read_text(encoding="utf-8-sig"))["files"].items()
            }
        for name, item in entries.items():
            path = repository_path(root, (receipt_path.parent / name).relative_to(root).as_posix())
            relative = path.relative_to(root).as_posix()
            successor = viewer_successors.get(relative)
            digest = file_hash(path)
            if successor:
                if receipt_name != "handoff/viewer/source/final-review-source-copy.json" or (
                    successor["previousReviewedSha256"] != item["sha256"] or successor["currentSha256"] != digest
                ):
                    raise ValueError(f"Viewer successor differs from {receipt_name}: {name}")
            elif path.stat().st_size != item["bytes"] or digest != item["sha256"]:
                raise ValueError(f"Reviewed copy differs from {receipt_name}: {name}")
            if name != manifest_name and name not in source_files:
                if receipt_name != "handoff/electrician/lighting/final-review-source-copy.json" or name != "verification.json":
                    raise ValueError(f"Reviewed copy is absent from its source manifest: {name}")
            elif name != manifest_name and source_files[name] != item["sourceSha256"]:
                raise ValueError(f"Source hash differs from its manifest: {name}")
        for item in receipt.get("omittedFiles", []):
            if source_files.get(item["path"]) != item["sourceSha256"]:
                raise ValueError(f"Omitted source is not bound by its manifest: {item['path']}")
            if repository_path(root, (receipt_path.parent / item["path"]).relative_to(root).as_posix()).exists():
                raise ValueError(f"Omitted third-party source is still present: {item['path']}")
        receipts[receipt_name] = entries

    lighting_root = root / "handoff" / "electrician" / "lighting"
    lighting_manifest = json.loads((lighting_root / "manifest.json").read_text(encoding="utf-8-sig"))
    lighting_verification = json.loads((lighting_root / "verification.json").read_text(encoding="utf-8-sig"))
    lighting_copy = json.loads((lighting_root / "final-review-source-copy.json").read_text(encoding="utf-8-sig"))
    if (lighting_manifest["master_sha256"] != master_sha256
            or lighting_verification["status"] != "PASS"
            or lighting_verification["master_sha256"] != master_sha256
            or lighting_verification["manifest_sha256"] != lighting_copy["sourceManifestSha256"]
            or lighting_manifest["exporter_sha256"] != file_hash(lighting_root / "source" / "export_current_lighting.py")
            or lighting_manifest["workbench_template_sha256"] != file_hash(lighting_root / "source" / "lighting-workbench.template.html")
            or lighting_verification["verifier_sha256"] != file_hash(lighting_root / "source" / "verify_current_lighting.py")):
        raise ValueError("Lighting exporter, template, verifier, manifest or current master is not bound")
    load_sheet = overlay["lightingLoadSheet"]
    if (load_sheet["master_sha256"] != master_sha256
            or load_sheet["generator_sha256"] != file_hash(lighting_root / "source" / "build_load_sheet.py")
            or set(load_sheet["outputs"]) != {"lighting-load-per-room.pdf", "lighting-load-per-room.xlsx"}
            or any(file_hash(lighting_root / name) != digest for name, digest in load_sheet["outputs"].items())):
        raise ValueError("Lighting load-sheet generator, outputs or current master is not bound")

    for item in overlay["postCopyOverlays"]:
        evidence = item["evidence"]
        if "copyReceipt" in evidence:
            receipt_name = evidence["copyReceipt"]
            source_name = evidence["sourcePath"]
            source = receipts[receipt_name][source_name]
            receipt_dir = repository_path(root, receipt_name).parent
            expected_path = (receipt_dir / source_name).relative_to(root).as_posix()
            if item["path"] != expected_path or item["currentSha256"] != source["sha256"]:
                raise ValueError(f"Overlay does not match its reviewed copy: {item['path']}")
        elif evidence.get("lightingGenerator") == "exporter":
            if item["path"] != "handoff/electrician/lighting/source/export_current_lighting.py" or item["currentSha256"] != lighting_manifest["exporter_sha256"]:
                raise ValueError("Lighting exporter overlay is not bound to the generated manifest")
        elif evidence.get("lightingGenerator") == "verifier":
            if item["path"] != "handoff/electrician/lighting/source/verify_current_lighting.py" or item["currentSha256"] != lighting_verification["verifier_sha256"]:
                raise ValueError("Lighting verifier overlay is not bound to its verification receipt")
        elif evidence.get("lightingGenerator") == "workbench":
            if item["path"] != "handoff/electrician/lighting/source/lighting-workbench.template.html" or item["currentSha256"] != lighting_manifest["workbench_template_sha256"]:
                raise ValueError("Lighting workbench overlay is not bound to the generated manifest")
        elif evidence.get("lightingGenerator") == "loadSheet":
            if item["path"] != "handoff/electrician/lighting/source/build_load_sheet.py" or item["currentSha256"] != load_sheet["generator_sha256"]:
                raise ValueError("Lighting load-sheet overlay is not bound to its generated outputs")
        else:
            raise ValueError(f"Missing final overlay evidence for {item['path']}")


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
    parser.add_argument("--publication-authorized", action="store_true",
                        help="Record authorization to publish the current review handoff, not construction approval")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    build = json.loads((root / "build-info.json").read_text())
    if build["masterSha256"] != args.master_sha256:
        parser.error("Integrated viewer does not match the confirmed canonical master")
    cleanup = json.loads((root / "handoff" / "cleanup-receipt.json").read_text(encoding="utf-8"))
    verify_cleanup(root, cleanup, args.master_sha256)
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
    viewer_overlay_path = "handoff/viewer/verification/2026-11-20-simple-lighting-overlay-receipt.json"
    viewer_overlay = json.loads((root / viewer_overlay_path).read_text(encoding="utf-8"))
    if viewer_overlay["masterSha256"] != args.master_sha256 or viewer_overlay["constructionRelease"] is not False:
        raise ValueError("Viewer overlay has an invalid basis")
    viewer_successors = {item["path"]: item for item in viewer_overlay["postCopyOverlays"]}
    overlay_paths = (
        "handoff/decisions/2026-11-18-material-selection-receipt.json",
        "handoff/viewer/verification/2026-11-18-viewer-update-receipt.json",
        "handoff/viewer/verification/2026-11-19-cbr-r05-overlay-receipt.json",
        "handoff/viewer/verification/2026-11-19-final-handoff-overlay-receipt.json",
        viewer_overlay_path,
    )
    overlays = {}
    for overlay_path in overlay_paths:
        overlay_data = json.loads((root / overlay_path).read_text())
        if overlay_path.endswith("2026-11-19-final-handoff-overlay-receipt.json"):
            verify_review_overlay(root, overlay_data, args.master_sha256, viewer_successors)
        overlays.update({item["path"]: (item, overlay_path) for item in overlay_data["postCopyOverlays"]})
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
    manifest = {
        "schema": "house-handoff-inventory/1",
        "status": "current-design-review-not-construction-released",
        "coordinatorReview": review,
        "coordinatorReviewNote": "This records the earlier local review; it is not construction or product approval.",
        "masterSha256": args.master_sha256,
        "constructionRelease": False,
        "productRelease": False,
        "procurementRelease": False,
        "fabricationRelease": False,
        "publicationAuthorized": args.publication_authorized or args.decision_addendum_publication_authorized,
        "publicationScope": ("Current design-review handoff; no construction or product release."
                             if args.publication_authorized
                             else "Dated owner-decision addendum and review overlays only; no design or construction release."
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
        "note": "Original master, public-copy and delivered hashes are distinct. Viewer/workbench maps are provisional frozen analytic estimates, not measured or product-specific. Site and professional approvals remain open. Manifest excludes itself.",
        "files": records,
    }
    (root / "handoff" / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Inventoried {len(records)} files, {sum(item['bytes'] for item in records):,} bytes")


if __name__ == "__main__":
    main()
