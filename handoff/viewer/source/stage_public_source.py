"""Stage the current viewer and drawing generators without local/private source paths."""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path


ap = argparse.ArgumentParser()
ap.add_argument("--site", required=True, type=Path)
ap.add_argument("--out", required=True, type=Path)
ap.add_argument("--generation-source", type=Path, help="original drawing-generator snapshot directory")
ap.add_argument("--drawings", type=Path, help="privacy-safe drawing pack with generator receipts")
args = ap.parse_args()
root = Path(__file__).resolve().parent
site = args.site.resolve()
out = args.out.resolve()
if out.exists():
    raise FileExistsError("Choose a new, empty public-source destination")

def sha(data):
    return hashlib.sha256(data).hexdigest()

html = (site / "index.html").read_bytes()
info = json.loads((site / "build-info.json").read_text(encoding="utf-8"))
privacy = json.loads((site / "privacy-transform.json").read_text(encoding="utf-8"))
if sha(html) != info["htmlSha256"] or sha(html) != privacy["viewerHtmlSha256"]:
    raise ValueError("The delivered HTML differs from its build and privacy receipts")

def script_bytes(identifier):
    pattern = rb'<script id="' + identifier.encode() + rb'" type="application/json">(.*?)</script>'
    matches = re.findall(pattern, html, flags=re.DOTALL)
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one {identifier} script")
    return matches[0]

plan = script_bytes("plan-data")
heat = script_bytes("heat-data")
if sha(plan) != privacy["embeddedPlanDataSha256"] or sha(heat) != privacy["embeddedHeatDataSha256"]:
    raise ValueError("Embedded data differ from the privacy receipt")
generated = json.loads((root / "src" / "house-data.generated.json").read_text(encoding="utf-8"))
if generated.get("plan") != json.loads(plan) or generated["plan"]["master"]["sha256"] != privacy["authoritativeMasterSha256"]:
    raise ValueError("Generated source does not match the delivered embedded plan and master")

files = [
    "analysis-data.mjs", "build.mjs", "tour-data.mjs", "drawing-source.mjs",
    "floorplan.mjs", "layout_views.mjs", "render_floorplan.py", "render_layout_views.py",
    "render_curtain_section.py", "capture_review_renders.py", "verify_site.py",
    "rebuild-public.mjs", "stage_public_source.py", "stage_public_drawings.py", "stage_public_verification.py",
    "template.html", "package.json", "package-lock.json",
]
files += [str(p.relative_to(root)) for p in sorted((root / "src").glob("*.js"))]
files += [str(Path("src") / "house-data.generated.json")]
files += [str(p.relative_to(root)) for p in sorted((root / "layout_views").glob("*.mjs"))]
for relative in files:
    source = root / relative
    target = out / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
(out / "data").mkdir(parents=True)
(out / "data" / "heat-data.json").write_bytes(heat)
shutil.copyfile(site / "THREE-LICENSE.txt", out / "THREE-LICENSE.txt")
shutil.copyfile(site / "privacy-transform.json", out / "privacy-transform.json")
if bool(args.generation_source) != bool(args.drawings):
    raise ValueError("Provide both --generation-source and --drawings, or neither")
original_generators = {}
if args.generation_source:
    floor_receipt = json.loads((args.drawings / "working-plan" / "floorplan-verification.json").read_text(encoding="utf-8"))
    layout_receipt = json.loads((args.drawings / "layout-views" / "layout-views-verification.json").read_text(encoding="utf-8"))
    for name in ("floorplan.mjs", "drawing-source.mjs"):
        data = (args.generation_source / name).read_bytes()
        if sha(data) != floor_receipt["generators"][name] or (name == "drawing-source.mjs" and sha(data) != layout_receipt["generators"][name]):
            raise ValueError(f"Original generator snapshot does not match the drawing receipt: {name}")
        target = out / "provenance" / "generation-source" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        original_generators[name] = sha(data)

readme = """# Viewer and drawing generators

Review draft; not a construction release. The offline viewer is distributed separately.
This source bundle excludes the old local master snapshot, local cache, dependencies and
reference imagery. `src/house-data.generated.json` and `data/heat-data.json` are the
privacy-redacted viewer inputs, not the complete authoritative master.

The original master SHA-256, derived-data hashes, precise transformation and verified
HTML hash are in `privacy-transform.json` and `public-source-manifest.json`.
Geometry and non-path fields in the derived viewer input are unchanged by redaction;
provisional dimensions, review status and site/professional holds remain.

To reproduce the exact verified HTML with Node.js, restore the pinned packages with
`npm ci`, then run `node rebuild-public.mjs --out <new-index.html>`. The command refuses
to write unless the result matches the recorded HTML hash. Keep the separately supplied
`downloads` folder alongside the rebuilt HTML for the four PDF links.

`build.mjs` rebuilds from the original authoritative master and its independently
verified input packs and receipts; it deliberately requires that original byte hash.
The redacted viewer data cannot be substituted as a byte-identical master. Drawing
generators require the corresponding current canonical master and fragments. Generated
local verification receipts can contain local paths; review them before publication.
When supplied, the `provenance` directory retains original generator snapshots for checking the drawing
receipts; they are historical evidence, not the current generator, and can emit local
paths if run. Current generators and the public drawing staging script avoid or remove
those path fields.
Three.js is bundled under MIT; see `THREE-LICENSE.txt`.
"""
(out / "README.md").write_text(readme, encoding="utf-8", newline="\n")

private_patterns = [
    re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]{1,2}"),
    re.compile(r"(?i)file:///+[A-Za-z]:"),
    re.compile(r"(?<![A-Za-z0-9])/(?:home|Users)/[^/\s\"'\\]+"),
    re.compile(r"(?i)\.copilot[\\/]{1,2}(?:session-state|attachments)"),
]
def scan(label, text):
    for pattern in private_patterns:
        if pattern.search(text):
            raise ValueError(f"Private absolute path found in {label}")

for path in sorted(out.rglob("*")):
    if not path.is_file():
        continue
    text = path.read_text(encoding="utf-8")
    scan(str(path.relative_to(out)), text)
    if path.suffix == ".json":
        def scan_values(value):
            if isinstance(value, str):
                scan(str(path.relative_to(out)), value)
            elif isinstance(value, list):
                for item in value:
                    scan_values(item)
            elif isinstance(value, dict):
                for key, item in value.items():
                    scan(str(path.relative_to(out)), key)
                    scan_values(item)
        scan_values(json.loads(text))
scan("delivered index.html", html.decode("utf-8"))
for identifier, data in [("plan-data", plan), ("heat-data", heat)]:
    def scan_embedded(value):
        if isinstance(value, str):
            scan(identifier, value)
        elif isinstance(value, list):
            for item in value:
                scan_embedded(item)
        elif isinstance(value, dict):
            for key, item in value.items():
                scan(identifier, key)
                scan_embedded(item)
    scan_embedded(json.loads(data))

artifacts = {}
for path in sorted(out.rglob("*")):
    if path.is_file():
        data = path.read_bytes()
        artifacts[path.relative_to(out).as_posix()] = {"bytes": len(data), "sha256": sha(data)}
manifest = {
    "status": "REVIEW DRAFT - not a construction release",
    "authoritativeMasterSha256": privacy["authoritativeMasterSha256"],
    "embeddedPlanDataSha256": privacy["embeddedPlanDataSha256"],
    "embeddedHeatDataSha256": privacy["embeddedHeatDataSha256"],
    "viewerHtmlSha256": privacy["viewerHtmlSha256"],
    "privacyPathScan": "PASS for staged text, JSON values and delivered HTML; original master omitted",
    "originalDrawingGeneratorSha256": original_generators,
    "files": artifacts,
}
(out / "public-source-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
scan("public-source-manifest.json", (out / "public-source-manifest.json").read_text(encoding="utf-8"))
print(json.dumps({"files": len(artifacts), "master": manifest["authoritativeMasterSha256"],
                  "embedded_plan": manifest["embeddedPlanDataSha256"], "viewer": manifest["viewerHtmlSha256"],
                  "privacy_path_scan": "PASS"}, indent=2))
