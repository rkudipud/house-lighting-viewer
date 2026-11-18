"""Publish a path-redacted copy of a completed offline browser verification receipt."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname


ap = argparse.ArgumentParser()
ap.add_argument("--receipt", required=True, type=Path)
ap.add_argument("--site", required=True, type=Path)
ap.add_argument("--out", required=True, type=Path)
args = ap.parse_args()
source, site, out = args.receipt.resolve(), args.site.resolve(), args.out.resolve()
if out.exists():
    raise FileExistsError("Choose a new, empty verification destination")

def sha(data):
    return hashlib.sha256(data).hexdigest()

original = source.read_bytes()
report = json.loads(original.decode("utf-8-sig"))
build = json.loads((site / "build-info.json").read_text(encoding="utf-8"))
viewer = (site / "index.html").read_bytes()
if sha(viewer) != build["htmlSha256"]:
    raise ValueError("The delivered HTML differs from its build receipt")
summary = report["summary"]
checks = report["checks"]
if summary["failed"] or summary["passed"] != summary["total"] or len(checks) != summary["total"] or not all(c["pass"] for c in checks):
    raise ValueError("The browser verification receipt is incomplete or has failures")
if set(report["profiles"]) != {"desktop", "mobile"}:
    raise ValueError("Expected desktop and mobile verification profiles")

redacted = []
def clean(value, field=""):
    if isinstance(value, str) and value.startswith("file://"):
        parsed = urlparse(value)
        if parsed.scheme != "file" or parsed.netloc:
            raise ValueError(f"Unexpected file URL at {field}")
        local = Path(url2pathname(parsed.path)).resolve()
        try:
            relative = local.relative_to(site)
        except ValueError as exc:
            raise ValueError(f"File URL escapes the delivered site at {field}") from exc
        if not local.is_file():
            raise ValueError(f"File referenced by verification does not exist at {field}")
        redacted.append(field)
        return "offline:" + relative.as_posix()
    if isinstance(value, list):
        return [clean(v, f"{field}[{i}]") for i, v in enumerate(value)]
    if isinstance(value, dict):
        return {k: clean(v, f"{field}.{k}" if field else k) for k, v in value.items()}
    return value

public = clean(report)
if public["url"] != "offline:index.html":
    raise ValueError("The receipt was not captured from this exact delivered viewer")
text = json.dumps(public, indent=2, ensure_ascii=False) + "\n"
for pattern in (r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]{1,2}", r"(?i)file:///+[A-Za-z]:",
                r"(?<![A-Za-z0-9])/(?:home|Users)/[^/\s\"'\\]+", r"(?i)\.copilot"):
    if re.search(pattern, text):
        raise ValueError("Private path remains in the verification derivative")
out.mkdir(parents=True)
public_path = out / "browser-verification-review.json"
public_path.write_text(text, encoding="utf-8", newline="\n")
receipt = {
    "status": "REVIEW DRAFT - not a construction release",
    "authoritative_master_sha256": build["masterSha256"],
    "viewer_html_sha256": build["htmlSha256"],
    "original_browser_receipt_sha256": sha(original),
    "public_browser_receipt_sha256": sha(public_path.read_bytes()),
    "transformation": "Only file URLs were replaced with offline: paths relative to the verified site; all other browser verification fields and values are unchanged.",
    "redacted_fields": redacted,
    "checks": summary,
}
(out / "verification-privacy-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8", newline="\n")
print(json.dumps(receipt, indent=2))
