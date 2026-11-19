"""Copy a hash-verified review pack, redacting local source-path metadata."""

import argparse
import hashlib
import json
from pathlib import Path, PureWindowsPath
import re
import shutil


def digest(data):
    return hashlib.sha256(data).hexdigest()


def relative_file(root, name):
    relative = Path(name.replace("\\", "/"))
    target = (root / relative).resolve()
    if relative.is_absolute() or ":" in name or not target.is_relative_to(root):
        raise ValueError(f"Unsafe manifest path: {name}")
    return target, relative


def redact(value, mappings):
    if isinstance(value, dict):
        return {key: redact(item, mappings) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item, mappings) for item in value]
    if isinstance(value, str) and re.match(r"^[A-Za-z]:[\\/]", value):
        path = PureWindowsPath(value)
        if len(path.parts) == 2 and path.name.lower() == "users":
            return value
        if len(path.parts) > 1 and path.parts[1].lower().startswith("program files"):
            return value
        for original, public in mappings:
            if path.is_relative_to(original):
                return (Path(public) / Path(*path.relative_to(original).parts)).as_posix()
        return "not-distributed/" + path.name
    return value


def externalize_pdf(data, literature, receipt_name):
    import pymupdf

    changed = False
    with pymupdf.open(stream=data, filetype="pdf") as document:
        for page in document:
            for link in page.get_links():
                local = link.get("file")
                if not local:
                    continue
                name = "sources/" + PureWindowsPath(local).name
                if name not in literature:
                    raise ValueError(f"Unmapped local PDF link: {name}")
                page.delete_link(link)
                page.insert_link({
                    "kind": pymupdf.LINK_URI,
                    "from": link["from"],
                    "uri": literature[name],
                })
                changed = True
        if not changed:
            return data
        notice = document.new_page(pno=0)
        notice.insert_textbox(
            pymupdf.Rect(54, 72, notice.rect.width - 54, notice.rect.height - 72),
            "PUBLIC-COPY SOURCE LITERATURE NOTICE\n\n"
            "DESIGN REVIEW ONLY - NOT FOR CONSTRUCTION OR PROCUREMENT.\n\n"
            "Third-party manufacturer PDFs are not redistributed in this repository because "
            "redistribution rights have not been established. Links in the following source "
            "index now open the official manufacturer publications instead of private local copies.\n\n"
            "The following pages preserve the original source review. References to archived or "
            "retained manufacturer copies describe the privately inspected source evidence, "
            "not files included in this public-ready handoff. Historical downloaded-file hashes "
            "do not guarantee the bytes currently served by a manufacturer URL.\n\n"
            "All product, exact-chain, availability, pricing, installation and professional "
            "approval holds remain. Source-versus-delivered hashes and explicit omissions are "
            f"recorded in {receipt_name}.",
            fontsize=12,
        )
        return document.tobytes(garbage=4, deflate=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    manifests = parser.add_mutually_exclusive_group(required=True)
    manifests.add_argument("--manifest", help="Manifest inside the source pack")
    manifests.add_argument("--selection-manifest", type=Path,
                           help="External hash manifest for an explicitly bounded source selection")
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--master-sha256", required=True)
    parser.add_argument("--status", required=True)
    parser.add_argument("--reference-map", nargs=2, action="append", default=[],
                        metavar=("SOURCE_PREFIX", "REPOSITORY_PREFIX"))
    parser.add_argument("--extra-verified-file", nargs=2, action="append", default=[],
                        metavar=("SOURCE_FILE", "SHA256"))
    parser.add_argument("--external-literature-map", type=Path,
                        help="Official URL map; matching source PDFs are verified but not copied")
    parser.add_argument("--receipt-name", default="repository-copy-receipt.json",
                        help="Output receipt filename; use a distinct name to preserve an earlier copy receipt")
    args = parser.parse_args()
    source = args.source.resolve()
    destination = args.destination.resolve()
    repo = Path(__file__).resolve().parents[1]
    if not destination.is_relative_to(repo / "handoff"):
        parser.error("Destination must be inside this repository's handoff directory")
    if (Path(args.receipt_name).name != args.receipt_name
            or not args.receipt_name.endswith(".json")
            or args.receipt_name == "public-file-hashes.json"):
        parser.error("Receipt name must be a plain JSON filename distinct from public-file-hashes.json")
    mappings = [(PureWindowsPath(str(source)), destination.relative_to(repo).as_posix())]
    for original, public in args.reference_map:
        relative_file(repo, public)
        mappings.append((PureWindowsPath(original), public))
    literature = {}
    if args.external_literature_map:
        literature = json.loads(args.external_literature_map.read_text(encoding="utf-8"))
        for name, url in literature.items():
            relative_file(source, name)
            if not name.lower().endswith(".pdf") or not url.startswith("https://"):
                parser.error(f"Invalid official literature mapping: {name}")
    if args.selection_manifest:
        manifest_path = args.selection_manifest.resolve()
        manifest_relative = Path("selected-source-file-hashes.json")
    else:
        manifest_path, manifest_relative = relative_file(source, args.manifest)
    manifest_bytes = manifest_path.read_bytes()
    if digest(manifest_bytes) != args.manifest_sha256:
        parser.error("Source manifest SHA-256 does not match the approved receipt")
    if manifest_path.suffix == ".json":
        entries = json.loads(manifest_bytes)
        if isinstance(entries, dict) and "files" in entries:
            basis = entries.get("master_sha256") or entries.get("masterSha256")
            if basis and basis != args.master_sha256:
                parser.error("Source manifest is bound to a different master")
            entries = entries["files"]
    else:
        entries = {}
        for line in manifest_bytes.decode("utf-8-sig").splitlines():
            if line.strip():
                sha, name = line.split(maxsplit=1)
                entries[name] = sha
    if not isinstance(entries, dict):
        parser.error("Expected a filename-to-SHA-256 source manifest")
    entries = dict(entries)
    for name, sha in args.extra_verified_file:
        if name in entries:
            parser.error(f"Duplicate extra file: {name}")
        entries[name] = sha
    validated = []
    for name, specification in entries.items():
        path, relative = relative_file(source, name)
        data = path.read_bytes()
        sha = specification["sha256"] if isinstance(specification, dict) else specification
        if digest(data) != sha:
            parser.error(f"Source file SHA-256 mismatch: {name}")
        if isinstance(specification, dict) and specification.get("bytes", len(data)) != len(data):
            parser.error(f"Source file byte-size mismatch: {name}")
        validated.append((path, relative, data))
    validated.append((manifest_path, manifest_relative, manifest_bytes))
    destination.mkdir(parents=True, exist_ok=True)
    records = []
    omissions = []
    for path, relative, data in validated:
        if relative.as_posix() in literature:
            omissions.append({
                "path": relative.as_posix(),
                "sourceSha256": digest(data),
                "officialUrl": literature[relative.as_posix()],
                "reason": "Third-party literature: redistribution rights not established",
            })
            continue
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        public = data
        if path.suffix == ".json":
            original = json.loads(data)
            safe = redact(original, mappings)
            if safe != original:
                public = (json.dumps(safe, indent=2, ensure_ascii=False) + "\n").encode()
        elif path.suffix == ".md":
            text = data.decode("utf-8-sig")
            safe = re.sub(
                r"`([A-Za-z]:[\\/][^`\r\n]+)`",
                lambda match: "`" + redact(match.group(1), mappings) + "`",
                text,
            )
            if safe != text:
                public = safe.encode("utf-8")
        elif path.suffix == ".py":
            text = data.decode("utf-8-sig")
            safe = re.sub(
                r"""(?P<raw>r?)(?P<quote>["'])(?P<path>[A-Za-z]:[\\/][^"'\r\n]+)(?P=quote)""",
                lambda match: match.group("raw") + match.group("quote")
                + redact(match.group("path"), mappings) + match.group("quote"),
                text,
            )
            if safe != text:
                public = safe.encode("utf-8")
        elif path.suffix.lower() == ".pdf" and literature:
            public = externalize_pdf(data, literature, args.receipt_name)
        paths_redacted = public != data
        if literature and path.suffix in {".md", ".html"}:
            text = public.decode("utf-8-sig")
            for name, url in literature.items():
                text = text.replace(name, url)
            if path.parent == source:
                note = (
                    "Public-copy note: manufacturer PDFs are not redistributed. Links open "
                    "official sources; mentions of retained archives describe the privately "
                    "inspected source evidence. Source and delivered hashes differ where "
                    f"paths or links were adapted; see {args.receipt_name}."
                )
                if path.suffix == ".md":
                    text = "> " + note + "\n\n" + text
                else:
                    text = re.sub(
                        r"(<body\b[^>]*>)", lambda match: match.group(1)
                        + '<aside style="padding:1rem;border:2px solid #98610d">'
                        + note + "</aside>", text, count=1,
                    )
            public = text.encode("utf-8")
        if public == data:
            shutil.copyfile(path, target)
        else:
            target.write_bytes(public)
        records.append({
            "path": relative.as_posix(),
            "bytes": len(public),
            "sha256": digest(public),
            "sourceSha256": digest(data),
            "localPathsRedacted": paths_redacted,
            "publicCopyModified": public != data,
        })
    receipt = {
        "status": args.status,
        "constructionRelease": False,
        "basisMasterSha256": args.master_sha256,
        "sourceManifest": manifest_relative.as_posix(),
        "sourceManifestSha256": digest(manifest_bytes),
        "sourceFiles": len(entries),
        "omittedFiles": omissions,
        "note": (
            "Original source files are untouched. Local absolute paths in public metadata copies "
            "are replaced by repository-relative references, or not-distributed source labels "
            "for source material not included here. Copied upstream hash manifests "
            "and verification receipts describe original source bytes; use this receipt for "
            "public-copy hashes. When literature is omitted, public HTML/Markdown and PDF "
            "links target official publications and adapted PDFs include a public-copy notice. "
            "This is a review pack, not a construction release."
        ),
        "files": records,
    }
    receipt_path = destination / args.receipt_name
    receipt_path.write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    public_hashes = {record["path"]: record["sha256"] for record in records}
    public_hashes[args.receipt_name] = digest(receipt_path.read_bytes())
    (destination / "public-file-hashes.json").write_text(
        json.dumps(public_hashes, indent=2) + "\n", encoding="utf-8"
    )
    print(f"PASS: copied {len(records)} verified files to {destination.relative_to(repo)}")
    print(f"Redacted local path metadata in {sum(r['localPathsRedacted'] for r in records)} files")


if __name__ == "__main__":
    main()
