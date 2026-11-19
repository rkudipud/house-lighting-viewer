"""Merge verified civil drawings and produce a source/artifact hash receipt."""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pymupdf


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def data(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


parser = argparse.ArgumentParser()
parser.add_argument("--master", required=True, type=Path)
parser.add_argument("--pack", required=True, type=Path)
parser.add_argument("--sha", required=True)
parser.add_argument("--revision-validation", required=True, type=Path)
parser.add_argument("--revision-receipt", required=True, type=Path)
args = parser.parse_args()
master = args.master.resolve()
pack = args.pack.resolve()
master_bytes = master.read_bytes()
if hashlib.sha256(master_bytes).hexdigest() != args.sha:
    sys.exit("Master changed; refuse to finalize a stale drawing pack.")

layout = pack / "layout-views"
details = pack / "site-details"
index = pack / "source-index"
layout_receipt = data(layout / "layout-views-verification.json")
detail_receipt = data(details / "site-details-verification.json")
index_receipt = data(index / "source-index-verification.json")
for receipt in [layout_receipt, detail_receipt]:
    if receipt["checks_passed"] != receipt["checks_total"]:
        sys.exit("A drawing check failed; refuse to finalize.")
    if receipt["source_master"]["sha256"] != args.sha:
        sys.exit("A drawing set is bound to a different master.")
    if any(not c["ok"] for c in receipt["checks"]):
        sys.exit("A check is marked failed despite the receipt count.")

layout_pdf = layout / "current-layout-views.pdf"
detail_pdf = details / "site-coordination-details.pdf"
if digest(layout_pdf) != layout_receipt["combined_pdf"]["sha256"]:
    sys.exit("Layout PDF changed after verification.")
if digest(detail_pdf) != detail_receipt["pdf"]["sha256"]:
    sys.exit("Civil detail PDF changed after verification.")
if (index_receipt["source_master"]["sha256"] != args.sha
        or index_receipt["source_register_sha256"] != digest(details / "opening-register.json")
        or index_receipt["construction_release"]
        or index_receipt["checks"]["rooms"] != 14
        or index_receipt["checks"]["model_openings"] != 21
        or not index_receipt["checks"]["all_opening_geometry_pointers_resolved"]
        or not index_receipt["checks"]["all_actual_opening_dimensions_unmeasured"]
        or not index_receipt["checks"]["master_hash_and_construction_hold_on_every_page"]):
    sys.exit("Source index is stale or lacks required evidence checks.")
for entry in index_receipt["files"]:
    if digest(index / entry["file"]) != entry["sha256"]:
        sys.exit(f"Source index artifact changed after verification: {entry['file']}")
index_pdf = index / "room-opening-index.pdf"

base = master.parent
integration_path = base / "generated" / "homeowner-final-coordination-integration.json"
pooja_path = base / "generated" / "pooja-display-decision-receipt.json"
supply_path = base / "generated" / "living-supply-and-cabinet-selections-receipt.json"
wardrobe_path = base / "generated" / "wardrobe-interiors-reference-receipt.json"
notation_path = base / "fragments" / "pooja-notation-hd18.json"
integration, pooja, supply = data(integration_path), data(pooja_path), data(supply_path)
wardrobe = data(wardrobe_path)
revision_validation = data(args.revision_validation)
revision_receipt = data(args.revision_receipt)
revision_checks = {c["check"]: c for c in revision_validation["checks"]}
required_revision_checks = ("master hash", "validated CCT-only successor",
                            "validated provisional CBR successor", "receipt chain",
                            "wardrobe reference linkage", "all release flags false")
if (revision_receipt["validation_sha256"] != digest(args.revision_validation)
        or revision_receipt["master_sha256"] != args.sha
        or revision_validation["master_sha256"] != args.sha
        or revision_validation["status"] != "PASS"
        or revision_receipt["validation_checks_passed"] != len(revision_validation["checks"])
        or any(revision_checks.get(name, {}).get("status") != "PASS" for name in required_revision_checks)):
    sys.exit("Current electrical revision validation is missing, unbound or failed.")
cct_revision = revision_checks["validated CCT-only successor"]["detail"]
cbr_revision = revision_checks["validated provisional CBR successor"]["detail"]
if (integration["after_master_sha256"] != pooja["before_master_sha256"]
        or pooja["after_master_sha256"] != supply["before_master_sha256"]
        or supply["after_master_sha256"] != wardrobe["before_master_sha256"]
        or wardrobe["after_master_sha256"] != cct_revision["prior_master_sha256"]
        or cct_revision["current_master_sha256"] != cbr_revision["prior_master_sha256"]
        or cbr_revision["current_master_sha256"] != args.sha):
    sys.exit("Homeowner, wardrobe, CCT and CBR receipts do not form the expected master chain.")
if (integration["holds_preserved"]["construction_release"] or pooja["retained"]["construction_release"]
        or supply["holds"]["construction_release"] or wardrobe["retained"]["construction_release"]
        or wardrobe["retained"]["homeowner_interior_approval"]):
    sys.exit("Source receipt unexpectedly claims construction release.")
current_house = json.loads(master_bytes.decode("utf-8-sig"))
reference = current_house["storage"]["wardrobe_interiors_review"]
fragment_path = base / reference["file"]
if reference != wardrobe["reference"] or digest(fragment_path) != reference["sha256"]:
    sys.exit("Wardrobe reference differs from its receipt.")

pdf = pymupdf.open()
toc = []
for source_pdf, receipt in [(layout_pdf, layout_receipt), (detail_pdf, detail_receipt), (index_pdf, index_receipt)]:
    with pymupdf.open(source_pdf) as p:
        titles = [s["title"] for s in receipt["sheets"]]
        if len(p) != len(titles):
            raise RuntimeError(f"Sheet/page count differs in {source_pdf.name}")
        offset = len(pdf)
        pdf.insert_pdf(p)
        toc.extend([[1, title, offset + i + 1] for i, title in enumerate(titles)])
pdf.set_toc(toc)
pdf.set_metadata({"title": "Civil coordination pack - review only, not for construction",
                  "subject": f"Canonical house-design.json sha256 {args.sha}"})
combined = pack / "contractor-civil-review.pdf"
pdf.save(combined, garbage=4, deflate=True)
pdf.close()

with pymupdf.open(combined) as p:
    pages = [" ".join(page.get_text().split()) for page in p]
    if len(p) != 20 or p.get_toc() != toc:
        raise RuntimeError("Combined PDF does not contain 20 bookmarked sheets.")
    if any(args.sha not in t or "not a construction release" not in t.lower() for t in pages):
        raise RuntimeError("A combined PDF page lacks the master hash or construction hold.")
    required = [
        (0, ["Furnished floor plan", "HD-15"]),
        (1, ["Reflected ceiling plan", "H1-H6", "H-MBR-W03", "beyond a modeled room corner",
             "1050 mm", "modelled ON", "H-CBR-CEIL"]),
        (7, ["3.048", "3.277", "homeowner-reported", "conflicts", "H-CBR-CEIL"]),
        (13, ["SCHEMATIC SECTION", "CURT-MBR-W03", "model clash",
              "3.048", "3.277", "slab unmeasured", "conflicts"]),
        (14, ["OPENING IDS", "STAIR", "D01", "W05"]),
        (15, ["small idols", "framed picture", "No niche deepening"]),
        (16, ["CBR-H1-H6", "387.6 mm", "back / base finish", "ST-R04a-WR01", "ST-R08-UC01", "480 W", "12.5 A"]),
        (17, ["Rooms and areas", "14 master records", "independent site verification", "R13"]),
        (18, ["Openings", "unmeasured", "D01", "W05"]),
        (19, ["Connections", "S01", "illustrative", "not measured",
              "3.048", "3.277", "slab unmeasured", "conflicts"]),
    ]
    for index, terms in required:
        missing = [term for term in terms if term.lower() not in pages[index].lower()]
        if missing:
            raise RuntimeError(f"PDF page {index+1} lacks expected text: {missing}")

if master.read_bytes() != master_bytes:
    raise RuntimeError("Canonical master changed during finalization.")

excluded = {"artifact-receipt.json", "SHA256SUMS.txt"}
files = []
for p in sorted(pack.rglob("*")):
    if p.is_file() and p.name not in excluded:
        if p.name.startswith("_part_"):
            raise RuntimeError(f"Temporary render part remains: {p}")
        files.append({"path": str(p.relative_to(pack)), "bytes": p.stat().st_size, "sha256": digest(p)})
receipt = {
    "schema": "civil_coordination_pack/1",
    "verified_utc": datetime.now(timezone.utc).isoformat(),
    "purpose": "Contractor-facing civil coordination review; no construction or product release",
    "construction_release": False,
    "source_master": {"path": str(master), "sha256": args.sha, "bytes": len(master_bytes)},
    "source_receipts": [
        {"path": str(integration_path), "sha256": digest(integration_path),
         "after_master_sha256": integration["after_master_sha256"]},
        {"path": str(pooja_path), "sha256": digest(pooja_path),
         "before_master_sha256": pooja["before_master_sha256"], "after_master_sha256": pooja["after_master_sha256"]},
        {"path": str(supply_path), "sha256": digest(supply_path),
         "before_master_sha256": supply["before_master_sha256"], "after_master_sha256": supply["after_master_sha256"]},
        {"path": str(wardrobe_path), "sha256": digest(wardrobe_path),
         "before_master_sha256": wardrobe["before_master_sha256"], "after_master_sha256": wardrobe["after_master_sha256"]},
        {"path": str(fragment_path), "sha256": digest(fragment_path), "status": reference["status"],
         "homeowner_interior_approval": False, "construction_release": False},
        {"path": str(notation_path), "sha256": digest(notation_path)},
        {"path": str(args.revision_validation), "sha256": digest(args.revision_validation),
         "status": revision_validation["status"]},
        {"path": str(args.revision_receipt), "sha256": digest(args.revision_receipt),
         "master_sha256": revision_receipt["master_sha256"]},
    ],
    "source_compatibility": {
        "wardrobe_reference_master_sha256": wardrobe["after_master_sha256"],
        "cct_revision": cct_revision,
        "cbr_revision": cbr_revision,
        "compatibility_basis": "The separately verified electrical receipt binds the checked CCT and CBR successor chain to the current master.",
        "provisional_interior_reference_does_not_replace_geometry_or_approvals": True,
    },
    "checks": {"layout": f'{layout_receipt["checks_passed"]}/{layout_receipt["checks_total"]}',
               "site_details": f'{detail_receipt["checks_passed"]}/{detail_receipt["checks_total"]}',
               "source_index": {"rooms": 14, "homeowner_reported_dimensions": 21, "model_openings": 21, "connections": 10},
               "combined_pdf_pages": 20, "source_hash_on_every_page": True, "construction_hold_on_every_page": True},
    "files": files,
}
receipt_path = pack / "artifact-receipt.json"
receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
hash_lines = [f'{f["sha256"]}  {f["path"]}' for f in files]
hash_lines.append(f'{digest(receipt_path)}  artifact-receipt.json')
(pack / "SHA256SUMS.txt").write_text("\n".join(hash_lines) + "\n", encoding="utf-8")
print(json.dumps({"master_sha256": args.sha, "combined_pdf_sha256": digest(combined),
                  "receipt_sha256": digest(receipt_path), "sha256sums_sha256": digest(pack / "SHA256SUMS.txt"),
                  "files": len(files) + 2, "pages": len(pages)}, indent=2))
