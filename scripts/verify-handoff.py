"""Verify the locally integrated handoff manifest without network access."""

import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path, PurePosixPath
import re
import sys
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET


REQUIRED_COVERAGE = {
    "room-opening-index",
    "lighting-workbench",
    "control-options",
    "switchboard-control-schedule",
    "heatmaps",
    "floorplan",
    "dimensioned-wall-layouts",
    "threejs-viewer",
    "lighting-placement",
    "wiring-electrical-layout",
    "location-specification-bom",
    "wardrobe-interiors",
    "ceiling",
    "renders",
    "editable-sources",
    "approved-references",
    "exploratory-raytracing",
}

PRIVATE_PATH = re.compile(
    r"[A-Za-z]:[\\/]+(?:Users|personal)[\\/]+|file:///[A-Za-z]:"
)


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.targets = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        self.targets.extend(attrs[key] for key in ("href", "src") if attrs.get(key))


def check_html_links(root, path):
    page = Links()
    page.feed(path.read_text(encoding="utf-8-sig"))
    errors = []
    for target in page.targets:
        url = urlsplit(target)
        if url.scheme in {"https", "http", "data", "mailto", "tel", "blob"}:
            continue
        if url.scheme or url.netloc or url.path.startswith("/"):
            errors.append(f"{path.relative_to(root)}: non-relative local link {target}")
            continue
        resolved = (path.parent / unquote(url.path)).resolve() if url.path else path
        if not resolved.is_relative_to(root) or not resolved.is_file():
            errors.append(f"{path.relative_to(root)}: missing or unsafe target {target}")
        elif url.fragment and resolved.suffix.lower() == ".html":
            destination = page
            if resolved != path:
                destination = Links()
                destination.feed(resolved.read_text(encoding="utf-8-sig"))
            if unquote(url.fragment) not in destination.ids:
                errors.append(f"{path.relative_to(root)}: missing fragment {target}")
    return errors


def repository_file(root, value):
    if not isinstance(value, str) or "\\" in value:
        raise ValueError(f"Expected repository-relative URL path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or ":" in value or not path.parts:
        raise ValueError(f"Unsafe repository path: {value!r}")
    target = root.joinpath(*path.parts).resolve()
    if not target.is_relative_to(root):
        raise ValueError(f"Path leaves repository: {value!r}")
    return target


def verify(root, manifest, expected_master):
    errors = []
    if manifest.get("masterSha256") != expected_master:
        errors.append("Manifest does not match the confirmed canonical master SHA-256")
    if manifest.get("constructionRelease") is not False:
        errors.append("Manifest must explicitly set constructionRelease to false")
    records = manifest.get("files", [])
    if not isinstance(records, list) or not records:
        return errors + ["Manifest files must be a non-empty list"]
    seen = set()
    coverage = set()
    extensions = set()
    for record in records:
        try:
            path = record["path"]
            target = repository_file(root, path)
            if path in seen:
                raise ValueError(f"Duplicate manifest path: {path}")
            seen.add(path)
            data = target.read_bytes()
            if len(data) != record["bytes"]:
                errors.append(f"{path}: byte-size mismatch")
            if hashlib.sha256(data).hexdigest() != record["sha256"]:
                errors.append(f"{path}: SHA-256 mismatch")
            if not isinstance(record.get("coverage"), list):
                raise ValueError(f"{path}: coverage must be a list")
            coverage.update(record["coverage"])
            extensions.add(target.suffix.lower())
            if target.suffix.lower() in {".json", ".md", ".html", ".svg", ".csv", ".py", ".js", ".mjs", ".txt", ".cal", ".rad"}:
                if PRIVATE_PATH.search(data.decode("utf-8-sig")):
                    errors.append(f"{path}: private absolute source path")
            if target.suffix.lower() == ".html" and not target.name.endswith(".template.html"):
                errors.extend(check_html_links(root, target))
            if target.suffix.lower() == ".svg":
                if ET.fromstring(data).tag.split("}")[-1] != "svg":
                    errors.append(f"{path}: SVG root element is missing")
            elif target.suffix.lower() == ".pdf":
                if not data.startswith(b"%PDF-") or b"%%EOF" not in data[-2048:]:
                    errors.append(f"{path}: PDF header or end marker is missing")
            elif target.suffix.lower() == ".png":
                if not data.startswith(b"\x89PNG\r\n\x1a\n"):
                    errors.append(f"{path}: PNG signature is missing")
        except (KeyError, OSError, TypeError, ValueError, UnicodeError, ET.ParseError) as error:
            errors.append(str(error))
    missing = REQUIRED_COVERAGE - coverage
    if missing:
        errors.append("Missing deliverable coverage: " + ", ".join(sorted(missing)))
    missing_formats = {".pdf", ".svg", ".png"} - extensions
    if missing_formats:
        errors.append("Missing handoff formats: " + ", ".join(sorted(missing_formats)))
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="handoff/manifest.json")
    parser.add_argument("--master-sha256", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-f0-9]{64}", args.master_sha256):
        parser.error("--master-sha256 must be a lowercase SHA-256")
    root = Path(__file__).resolve().parents[1]
    try:
        manifest_path = repository_file(root, args.manifest)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise ValueError("Manifest must be an object")
        errors = verify(root, manifest, args.master_sha256)
    except (OSError, ValueError) as error:
        errors = [str(error)]
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(f"PASS: {len(manifest['files'])} files match the canonical handoff manifest")
    print("File integrity only; render, link, viewer and professional site checks remain separate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
