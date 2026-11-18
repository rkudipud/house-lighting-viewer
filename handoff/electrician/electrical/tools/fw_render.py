"""Render the current lighting handover (Markdown -> self-contained HTML -> A4 PDF) and report checks.

Usage: python render_current_lighting_handover.py <handover.md> [--final] [--json out.json]
--final refuses any remaining PENDING marker.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import mimetypes
import re
from datetime import datetime, timezone
from pathlib import Path

import markdown
import pymupdf
from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

PREVIEW = Path(__file__).resolve().parents[2] / "work" / "preview" / "fw-contact"

CSS = """
@page { size: A4; }
* { box-sizing: border-box; }
html { color: #233138; background: #e8eceb; font-family: Arial, sans-serif; }
body { margin: 0 auto; max-width: 1000px; background: white; padding: 48px; }
main { font-size: 15px; line-height: 1.48; }
h1 { font-size: 30px; line-height: 1.18; margin: 0 0 14px; }
h2 { color: #1c4d51; font-size: 23px; margin: 30px 0 12px; border-top: 2px solid #87a7a4; padding-top: 12px; }
h3 { font-size: 18px; margin: 20px 0 9px; }
p { margin: 0 0 11px; }
strong { color: #102e37; }
table { width: 100%; border-collapse: collapse; margin: 12px 0 16px; font-size: 13px; line-height: 1.36; }
th { background: #e9f1ef; text-align: left; color: #173c43; }
td, th { border: 1px solid #c7d3d2; padding: 6px 8px; vertical-align: top; }
tbody tr:nth-child(even) { background: #f7f9f8; }
img { display: block; max-width: 100%; height: auto; margin: 14px auto; }
img.photo { max-height: 430px; object-fit: contain; }
a { color: #245f69; overflow-wrap: anywhere; }
code, pre { font-size: 12.5px; }
pre { background: #f3f6f4; border: 1px solid #d5dedc; padding: 10px 12px; white-space: pre-wrap; }
blockquote { border-left: 4px solid #b5522f; margin: 14px 0; padding: 8px 14px; background: #fbf1ec; }
.toc { padding: 12px 18px; background: #f1f5f3; font-size: 13px; columns: 2; column-gap: 22px; }
.toc ul { padding-left: 16px; margin: 0; }
@media print {
  html, body { background: white; max-width: none; padding: 0; margin: 0; }
  main { font-size: 10.2pt; line-height: 1.34; }
  h1 { font-size: 22pt; }
  h2 { font-size: 15.5pt; margin-top: 0; padding-top: 6pt; break-before: page; }
  h2#contents { break-before: auto; margin-top: 14pt; }
  h3 { font-size: 12pt; margin-top: 12pt; }
  h1, h2, h3 { break-after: avoid; }
  p, li { widows: 3; orphans: 3; }
  table { font-size: 8.9pt; line-height: 1.3; margin: 7pt 0 10pt; }
  td, th { padding: 4pt 5pt; }
  thead { display: table-header-group; }
  tr { break-inside: avoid; }
  pre { font-size: 8.3pt; break-inside: avoid; }
  img { width: 100%; max-height: 215mm; object-fit: contain; break-inside: avoid; margin: 9pt auto; }
  img.photo { width: auto; height: 76mm; }
  p:has(> img) { break-inside: avoid; }
  a { color: #233138; text-decoration: none; }
  * { print-color-adjust: exact; -webkit-print-color-adjust: exact; }
}
"""


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def slug(title: str) -> str:
    return re.sub(r"[\s]+", "-", re.sub(r"[^\w\- ]", "", title.lower()).strip())


def contents(text: str) -> str:
    items = [f'<li><a href="#{slug(l[3:].strip())}">{html.escape(l[3:].strip())}</a></li>'
             for l in text.splitlines() if l.startswith("## ")]
    return '<h2 id="contents">Contents</h2>\n<div class="toc"><ul>' + "".join(items) + "</ul></div>"


def embed(body: str, root: Path) -> tuple[str, list[str]]:
    used: list[str] = []

    def repl(m: re.Match[str]) -> str:
        tag, src = m.group(0), html.unescape(m.group(1))
        if src.startswith(("http:", "https:", "data:")):
            raise ValueError(f"Only packaged images allowed: {src}")
        f = (root / src).resolve()
        if not f.is_relative_to(root.resolve()) or not f.is_file():
            raise ValueError(f"Missing image: {f}")
        used.append(src)
        mime = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        tag = tag.replace(m.group(1), f"data:{mime};base64,{base64.b64encode(f.read_bytes()).decode()}")
        if "/photos/" in src:
            tag = tag.replace("<img ", '<img class="photo" ')
        return tag

    return re.sub(r'<img\b[^>]*src="([^"]+)"[^>]*>', repl, body), used


def render(source: Path, final: bool, no_pdf: bool = False) -> dict:
    root = source.parent
    text = source.read_text(encoding="utf-8")
    publication_hold = "**Publication hold.**" in text
    pending = re.findall(r"\[PENDING-[A-Z]+[^\]]*\]", text)
    if final and pending:
        raise ValueError(f"{len(pending)} pending markers remain")
    dali = [l for l in text.splitlines() if re.search(r"\bDALI\b", l)]
    if len(dali) > 1:
        raise ValueError(f"DALI on {len(dali)} lines; only the single exclusion note is allowed")
    for stale in (r"\brev(ision)?[ .-]?\d", r"\bOption A\b", r"\bDT8\b", r"\b[01]-10 ?V\b"):
        if re.search(stale, text, flags=re.I):
            raise ValueError(f"Stale/excluded content matched {stale}")
    md_text = text.replace("{{CONTENTS}}", contents(text))
    body = markdown.markdown(md_text, extensions=["tables", "toc", "fenced_code", "sane_lists"],
                             extension_configs={"toc": {"toc_depth": "2-3", "slugify": lambda v, s: slug(v)}})
    body, images = embed(body, root)
    title = html.escape(text.splitlines()[0].removeprefix("# "))
    html_path = source.with_suffix(".html")
    html_path.write_text(
        f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width, initial-scale=1"><title>{title}</title>'
        f"<style>{CSS}</style></head><body><main>{body}</main></body></html>", encoding="utf-8")
    pdf_path = source.with_suffix(".pdf")
    errors: list[str] = []
    requests: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1200, "height": 900})
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("request", lambda r: requests.append(r.url) if r.url.startswith(("http:", "https:")) else None)
        page.goto(html_path.as_uri(), wait_until="networkidle")
        imgs = page.locator("img").evaluate_all("(els)=>els.map(e=>({alt:e.alt,ok:e.complete&&e.naturalWidth>0}))")
        assert all(i["ok"] for i in imgs), imgs
        broken = page.locator('a[href^="#"]').evaluate_all(
            "(els)=>els.map(e=>e.getAttribute('href')).filter(h=>!document.getElementById(h.slice(1)))")
        assert not broken, f"Broken contents links: {broken}"
        page.emulate_media(media="print")
        page.set_viewport_size({"width": 695, "height": 1000})
        overflow = page.locator("table, pre").evaluate_all(
            "(els)=>els.map((e,i)=>({i,tag:e.tagName,excess:e.scrollWidth-e.clientWidth})).filter(x=>x.excess>2)")
        if no_pdf:
            browser.close()
            assert not errors, errors
            assert not requests, requests
            result = {
                "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "mode": "html-only (PDF withheld)", "pending_markers": len(pending),
                "dali_mentions": len(dali), "pages": None, "images": images,
                "page_errors": errors, "external_requests": requests, "overflow": overflow,
                "out_of_bounds_text": None, "near_empty_pages": None,
                "publication_hold": publication_hold,
                "md_sha256": sha(source), "html_sha256": sha(html_path), "pdf_sha256": None,
            }
            print(json.dumps({k: v for k, v in result.items() if k != "images"}, indent=1))
            return result
        page.pdf(path=str(pdf_path), format="A4", print_background=True, prefer_css_page_size=True,
                 margin={"top": "15mm", "right": "13mm", "bottom": "16mm", "left": "13mm"},
                 display_header_footer=True,
                 header_template='<div style="width:100%;margin:0 13mm;font:8px Arial;color:#637275;">'
                                 'HYDERABAD 2BHK / FIXED-WHITE CONTROL PLAN / '
                                 + ('PUBLICATION HELD' if publication_hold else 'CURRENT DRAFT') + '</div>',
                 footer_template='<div style="width:100%;margin:0 13mm;font:8px Arial;color:#637275;'
                                 'display:flex;justify-content:space-between;"><span>'
                                 + ('Held working copy' if publication_hold else 'Review and quotation only') +
                                 ' - not for ordering or construction</span><span><span class="pageNumber">'
                                 '</span> / <span class="totalPages"></span></span></div>')
        browser.close()
    assert not errors, errors
    assert not requests, requests
    doc = pymupdf.open(pdf_path)
    oob, thin = [], []
    for i, pg in enumerate(doc):
        for b in pg.get_text("dict")["blocks"]:
            for ln in b.get("lines", []):
                for s in ln["spans"]:
                    x0, _, x1, _ = s["bbox"]
                    if s["text"].strip() and (x0 < 20 or x1 > pg.rect.width - 20):
                        oob.append({"page": i + 1, "text": s["text"][:40]})
        if len(pg.get_text().strip()) < 160 and not pg.get_images():
            thin.append(i + 1)
    PREVIEW.mkdir(parents=True, exist_ok=True)
    for start in range(0, len(doc), 12):
        sheet = Image.new("RGB", (4 * 310, 3 * 457), "#d8dfe0")
        draw = ImageDraw.Draw(sheet)
        for j in range(start, min(start + 12, len(doc))):
            pix = doc[j].get_pixmap(matrix=pymupdf.Matrix(.5, .5))
            im = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            im.thumbnail((294, 420))
            x, y = ((j - start) % 4) * 310 + 8, ((j - start) // 4) * 457 + 25
            sheet.paste(im, (x, y))
            draw.text((x, y - 18), f"Page {j + 1}", fill="#20343b")
        sheet.save(PREVIEW / f"contact-{start // 12 + 1}.png")
    result = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "complete review, publication held" if final and publication_hold else ("final" if final else "draft"),
        "publication_hold": publication_hold, "pending_markers": len(pending),
        "dali_mentions": len(dali), "pages": len(doc), "images": images,
        "page_errors": errors, "external_requests": requests, "overflow": overflow,
        "out_of_bounds_text": oob, "near_empty_pages": thin,
        "md_sha256": sha(source), "html_sha256": sha(html_path), "pdf_sha256": sha(pdf_path),
    }
    print(json.dumps({k: v for k, v in result.items() if k != "images"}, indent=1))
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", type=Path)
    ap.add_argument("--final", action="store_true")
    ap.add_argument("--json", type=Path)
    ap.add_argument("--no-pdf", action="store_true", help="validate and write HTML only; do not print the PDF")
    a = ap.parse_args()
    if a.final and a.no_pdf:
        ap.error("--final requires the PDF")
    r = render(a.source.resolve(), a.final, a.no_pdf)
    if a.json:
        a.json.write_text(json.dumps(r, indent=2), encoding="utf-8")
