"""Create a path-redacted drawing pack with separately recorded source and public hashes."""
import argparse
import hashlib
import html
import json
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath, PureWindowsPath

import pymupdf
from PIL import Image


ap = argparse.ArgumentParser()
ap.add_argument("--source", required=True, type=Path)
ap.add_argument("--out", required=True, type=Path)
ap.add_argument("--master", required=True)
ap.add_argument("--prior-master", required=True, help="Verified basis of unchanged floor and curtain drawings")
args = ap.parse_args()
source, out = args.source.resolve(), args.out.resolve()
if out.exists():
    raise FileExistsError("Choose a new, empty public drawing destination")
if not all(re.fullmatch(r"[a-f0-9]{64}", value) for value in (args.master, args.prior_master)):
    raise ValueError("Explicit current and predecessor SHA-256 values are required")

def digest(data):
    return hashlib.sha256(data).hexdigest()

def fingerprint(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": digest(data)}

floor = json.loads((source / "working-plan" / "floorplan-verification.json").read_text(encoding="utf-8-sig"))
layout = json.loads((source / "layout-views" / "layout-views-verification.json").read_text(encoding="utf-8-sig"))
curtain = json.loads((source / "curtain-section" / "curtain-section-verification.json").read_text(encoding="utf-8-sig"))
if (floor["source_master"]["sha256"] != args.prior_master or layout["source_master"]["sha256"] != args.master
        or curtain["master_sha256"] != args.prior_master or floor["construction_release"] is not False
        or layout["checks_passed"] != layout["checks_total"] or curtain["status"] != "REVIEW_DRAFT_NOT_CONSTRUCTION_RELEASED"):
    raise ValueError("Original drawing receipts do not bind the requested review master and holds")

paths = sorted(p for p in source.rglob("*") if p.is_file())
for path in paths:
    target = out / path.relative_to(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, target)

changes = []
def scrub(value, location, replacements):
    if isinstance(value, str):
        windows = bool(re.match(r"^[A-Za-z]:[\\/]", value)) or value.startswith("\\\\")
        posix = value.startswith(("/home/", "/Users/"))
        if windows or posix:
            replacement = (PureWindowsPath(value) if windows else PurePosixPath(value)).name
            replacements.append({"field": location, "original_value_sha256": digest(value.encode("utf-8")), "public_value": replacement})
            return replacement
        return value
    if isinstance(value, list):
        return [scrub(v, f"{location}[{i}]", replacements) for i, v in enumerate(value)]
    if isinstance(value, dict):
        return {k: scrub(v, f"{location}.{k}" if location else k, replacements) for k, v in value.items()}
    return value

def save_json(relative, data, replacements, reason):
    path = out / relative
    original = fingerprint(source / relative)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    changes.append({"file": relative.as_posix(), "original": original, "public": fingerprint(path),
                    "reason": reason, "path_fields_redacted": replacements})

svg_rel = Path("working-plan") / "house-working-floorplan.svg"
svg_original = (source / svg_rel).read_bytes().decode("utf-8")
match = re.search(r"(<metadata>)(.*?)(</metadata>)", svg_original, re.DOTALL)
if not match:
    raise ValueError("Working-plan SVG metadata is missing")
metadata = json.loads(html.unescape(match.group(2)))
replacements = []
public_metadata = scrub(metadata, "metadata", replacements)
if not replacements or public_metadata["master_sha256"] != args.prior_master:
    raise ValueError("Expected master path metadata or binding is missing")
new_metadata = html.escape(json.dumps(public_metadata, separators=(",", ":"), ensure_ascii=False), quote=True)
svg_public = svg_original[:match.start(2)] + new_metadata + svg_original[match.end(2):]
if svg_public[:match.start(2)] != svg_original[:match.start(2)] or not svg_public.endswith(svg_original[match.end(2):]):
    raise ValueError("SVG content outside metadata changed")
ET.fromstring(svg_public)
(out / svg_rel).write_bytes(svg_public.encode("utf-8"))
changes.append({"file": svg_rel.as_posix(), "original": fingerprint(source / svg_rel), "public": fingerprint(out / svg_rel),
                "reason": "Only non-rendered SVG metadata was path-redacted; all other SVG bytes are unchanged.",
                "path_fields_redacted": replacements})

sheets_rel = Path("layout-views") / "sheets.json"
sheets = json.loads((source / sheets_rel).read_text(encoding="utf-8-sig"))
replacements = []
sheets = scrub(sheets, "", replacements)
save_json(sheets_rel, sheets, replacements, "Only absolute path values were replaced with file names.")

floor_rel = Path("working-plan") / "floorplan-verification.json"
if floor["artifacts"]["svg"] != {"file": svg_rel.name, **fingerprint(source / svg_rel)}:
    raise ValueError("Original floor-plan SVG does not match its verification receipt")
replacements = []
floor = scrub(floor, "", replacements)
floor["artifacts"]["svg"].update(fingerprint(out / svg_rel))
save_json(floor_rel, floor, replacements, "Absolute paths redacted and SVG artifact hash/size rebound to the metadata-only public derivative.")

layout_rel = Path("layout-views") / "layout-views-verification.json"
if layout["manifest"] != {"file": sheets_rel.name, **fingerprint(source / sheets_rel)}:
    raise ValueError("Original sheets manifest does not match its verification receipt")
replacements = []
layout = scrub(layout, "", replacements)
layout["manifest"].update(fingerprint(out / sheets_rel))
save_json(layout_rel, layout, replacements, "Absolute paths redacted and sheets-manifest hash/size rebound to its public derivative.")

private_patterns = [
    re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]{1,2}"),
    re.compile(r"(?i)file:///+[A-Za-z]:"),
    re.compile(r"(?<![A-Za-z0-9])/(?:home|Users)/[^/\s\"'\\]+"),
    re.compile(r"(?i)\.copilot[\\/]{1,2}(?:session-state|attachments)"),
]
def scan(label, text):
    for pattern in private_patterns:
        if pattern.search(text):
            raise ValueError(f"Private absolute path remains in {label}")

for path in sorted(p for p in out.rglob("*") if p.is_file()):
    label = path.relative_to(out).as_posix()
    if path.suffix.lower() in {".json", ".svg", ".md"}:
        text = path.read_text(encoding="utf-8-sig")
        scan(label, html.unescape(text))
        if path.suffix.lower() == ".json":
            def scan_values(value):
                if isinstance(value, str):
                    scan(label, value)
                elif isinstance(value, list):
                    for item in value:
                        scan_values(item)
                elif isinstance(value, dict):
                    for key, item in value.items():
                        scan(label, key)
                        scan_values(item)
            scan_values(json.loads(text))
        elif path.suffix.lower() == ".svg":
            ET.fromstring(text)
            if path.relative_to(out) != svg_rel and path.read_bytes() != (source / path.relative_to(out)).read_bytes():
                raise ValueError(f"Unchanged SVG bytes differ: {label}")
    elif path.suffix.lower() == ".pdf":
        with pymupdf.open(path) as doc:
            scan(label, json.dumps(doc.metadata) + "".join(page.get_text() for page in doc))
        if path.read_bytes() != (source / path.relative_to(out)).read_bytes():
            raise ValueError(f"PDF bytes changed: {label}")
    elif path.suffix.lower() == ".png":
        with Image.open(path) as image:
            scan(label, repr(image.info) + repr(dict(image.getexif())))
            image.load()
        with Image.open(path) as image:
            image.verify()
        if path.read_bytes() != (source / path.relative_to(out)).read_bytes():
            raise ValueError(f"PNG bytes changed: {label}")

def verify_artifact(base, item):
    path = base / item["file"]
    if fingerprint(path) != {k: item[k] for k in ("bytes", "sha256")}:
        raise ValueError(f"Public artifact hash differs from its receipt: {item['file']}")

for item in floor["artifacts"].values():
    verify_artifact(out / "working-plan", item)
verify_artifact(out / "layout-views", layout["manifest"])
verify_artifact(out / "layout-views", layout["combined_pdf"])
for sheet in layout["sheets"]:
    verify_artifact(out / "layout-views", sheet["svg"])
    verify_artifact(out / "layout-views", sheet["png"])
for item in curtain["artifacts"]:
    verify_artifact(out / "curtain-section", item)

receipt = {
    "status": "REVIEW DRAFT - not a construction release",
    "authoritative_master_sha256": args.master,
    "unchanged_floor_and_curtain_master_sha256": args.prior_master,
    "transformation": "Public derivatives replace absolute local paths with file names in SVG metadata and JSON. Receipt references to changed public artifacts were rebound. All PNG and PDF bytes and every SVG drawing outside its metadata remain unchanged. Original evidence and hashes are retained locally and recorded below.",
    "graphics_changed": False,
    "changed_files": changes,
    "files": {p.relative_to(out).as_posix(): fingerprint(p) for p in sorted(out.rglob("*")) if p.is_file()},
    "privacy_path_scan": "PASS for SVG, JSON, README, PDF text/metadata and PNG metadata",
    "artifact_receipt_checks": "PASS",
}
receipt_path = out / "drawing-public-privacy-receipt.json"
receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8", newline="\n")
scan("drawing-public-privacy-receipt.json", receipt_path.read_text(encoding="utf-8"))
print(json.dumps({"files": len(receipt["files"]), "changed_files": len(changes),
                  "master": args.master, "privacy_path_scan": "PASS", "artifact_receipt_checks": "PASS"}, indent=2))
