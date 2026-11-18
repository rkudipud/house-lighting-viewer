"""Render/decode the local handoff and inspect links and private-path leakage."""

from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from urllib.parse import unquote, urlsplit

import markdown
from PIL import Image
import pymupdf

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "handoff" / "local-artifact-verification.json"
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("handoff_verifier", ROOT / "scripts" / "verify-handoff.py")
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


def main():
    counts = Counter()
    errors = []
    pdf_pages = 0
    photo_hashes = set()
    approved_photos = {
        "cbe2ec6b6a22db6e5d3165f734406cfd5f04ba431db36f0316d79532d7a2ba0f",
        "b3fdb9a4c247959bc8b6a3701fd3e2cb5004d069dfd25a279d5c056a855a56a2",
        "09f11696466e6a74659a8beab839fbb821963f5aa470c2368fcb7d8443c64358",
    }
    largest = {"bytes": 0}
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path == OUTPUT or any(
            part in {".git", "__pycache__", "node_modules", ".venv"} for part in path.parts
        ) or path.suffix == ".pyc":
            continue
        relative = path.relative_to(ROOT).as_posix()
        data = path.read_bytes()
        counts[path.suffix.lower() or "(no extension)"] += 1
        if len(data) > largest["bytes"]:
            largest = {"path": relative, "bytes": len(data)}
        if len(data) > 100 * 1024 * 1024:
            errors.append(relative + ": exceeds GitHub individual-file limit")
        try:
            suffix = path.suffix.lower()
            if suffix in {".json", ".md", ".html", ".svg", ".csv", ".py", ".js", ".mjs", ".txt", ".cal", ".rad"}:
                text = data.decode("utf-8-sig")
                if verifier.PRIVATE_PATH.search(text):
                    errors.append(relative + ": private absolute source path")
            if suffix == ".json":
                json.loads(text)
            elif suffix == ".py":
                compile(text, relative, "exec")
            elif suffix == ".md" and not path.name.endswith(".template.md"):
                page = verifier.Links()
                page.feed(markdown.markdown(text, extensions=["fenced_code", "tables"]))
                for target in page.targets:
                    url = urlsplit(target)
                    if url.scheme or url.netloc or not url.path:
                        continue
                    destination = (path.parent / unquote(url.path)).resolve()
                    if not destination.is_relative_to(ROOT) or not destination.exists():
                        errors.append(relative + ": missing Markdown target " + target)
            elif suffix == ".pdf":
                with pymupdf.open(path) as document:
                    if document.is_encrypted:
                        errors.append(relative + ": encrypted PDF")
                    for page in document:
                        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(1, 1), alpha=False)
                        if not pixmap.width or not pixmap.height:
                            errors.append(relative + ": empty rendered PDF page")
                        if verifier.PRIVATE_PATH.search(page.get_text()):
                            errors.append(relative + ": private path in PDF page text")
                        for link in page.get_links():
                            if verifier.PRIVATE_PATH.search(str(link)):
                                errors.append(relative + ": private path in PDF link")
                    for number in range(1, document.xref_length()):
                        if verifier.PRIVATE_PATH.search(document.xref_object(number)):
                            errors.append(relative + ": private path in PDF object")
                    if verifier.PRIVATE_PATH.search(json.dumps(document.metadata)):
                        errors.append(relative + ": private path in PDF metadata")
                    if verifier.PRIVATE_PATH.search(document.get_xml_metadata()):
                        errors.append(relative + ": private path in PDF XML metadata")
                    pdf_pages += document.page_count
            elif suffix == ".svg":
                if not path.with_suffix(".png").is_file():
                    errors.append(relative + ": matching PNG handoff image missing")
                with pymupdf.open(stream=data, filetype="svg") as document:
                    page = document[0].get_pixmap(matrix=pymupdf.Matrix(1, 1), alpha=False)
                    if not page.width or not page.height:
                        errors.append(relative + ": empty SVG render")
            elif suffix in {".png", ".jpg", ".jpeg"}:
                with Image.open(path) as image:
                    image.load()
                    if not image.width or not image.height:
                        errors.append(relative + ": empty image")
                    if suffix in {".jpg", ".jpeg"} and image.getexif():
                        errors.append(relative + ": unexpected photographic EXIF")
                    if suffix in {".jpg", ".jpeg"}:
                        photo_hashes.add(hashlib.sha256(data).hexdigest())
        except (OSError, ValueError, SyntaxError, RuntimeError) as error:
            errors.append(relative + ": " + str(error))
    if photo_hashes != approved_photos:
        errors.append("JPEG set does not equal the three approved user site photographs")
    if errors:
        raise SystemExit("\n".join("FAIL: " + error for error in errors))
    receipt = {
        "status": "PASS_local_render_decode_privacy_and_Markdown_link_checks",
        "scope": "Repository content excluding git internals, dependency/cache directories and this report. Markdown navigation checks exclude generator templates whose links resolve in generated output. Final manifest integrity is checked separately.",
        "formatCounts": dict(sorted(counts.items())),
        "pdfPagesRenderedAt72Dpi": pdf_pages,
        "distinctApprovedUserSitePhotos": len(photo_hashes),
        "largestFile": largest,
        "privacyScope": "Text source files; every PDF page text, standard/XML metadata, links and decoded object dictionaries; approved photographs checked for EXIF and exact allowlisted hashes.",
        "htmlSha256": hashlib.sha256((ROOT / "index.html").read_bytes()).hexdigest(),
        "errors": [],
        "constructionRelease": False,
    }
    OUTPUT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: {counts['.pdf']} PDFs / {pdf_pages} pages, "
          f"{counts['.svg']} SVGs, {counts['.png']} PNGs, "
          f"{counts['.jpeg'] + counts['.jpg']} JPEGs; privacy and Markdown targets")


if __name__ == "__main__":
    main()
