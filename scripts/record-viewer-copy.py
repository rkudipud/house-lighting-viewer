"""Verify and record the current viewer and its delivered PDF copies."""
import argparse
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--site", required=True, type=Path)
parser.add_argument("--master", required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
site = args.site.resolve()
info = json.loads((site / "build-info.json").read_text(encoding="utf-8"))
privacy = json.loads((site / "privacy-transform.json").read_text(encoding="utf-8"))
if info["masterSha256"] != args.master or privacy["authoritativeMasterSha256"] != args.master:
    raise ValueError("Viewer source and privacy receipt do not bind the requested master")

def fingerprint(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

names = ["index.html", "build-info.json", "privacy-transform.json", "THREE-LICENSE.txt", ".nojekyll"]
names += [row["href"] for row in info["downloads"]]
records = []
for name in names:
    source, delivered = site / name, root / name
    expected, got = fingerprint(source), fingerprint(delivered)
    if got != expected:
        raise ValueError(f"Viewer copy differs from its verified source: {name}")
    records.append({"path": name, **got, "sourceSha256": expected["sha256"]})
if records[0]["sha256"] != info["htmlSha256"] or records[0]["sha256"] != privacy["viewerHtmlSha256"]:
    raise ValueError("HTML fingerprint differs from its build and privacy receipts")
for row in info["downloads"]:
    if fingerprint(root / row["href"]) != {"bytes": row["bytes"], "sha256": row["sha256"]}:
        raise ValueError(f"Viewer download differs from its build receipt: {row['href']}")
receipt = {"status": "verified-provisional-review-not-construction-released",
           "constructionRelease": False, "masterSha256": args.master,
           "viewerHtmlUnchangedFromProducer": True, "files": records}
(root / "handoff" / "viewer" / "site-repository-copy-receipt.json").write_text(
    json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
print(f"Verified {len(records)} viewer and download copies")
