import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
import pymupdf
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser(description="Render the master-derived SVG as a readable PNG and PDF, offline.")
parser.add_argument("folder", type=Path)
args = parser.parse_args()
svg = args.folder / "house-working-floorplan.svg"
receipt = args.folder / "floorplan-verification.json"
data = json.loads(receipt.read_text(encoding="utf-8"))
if data.get("drawing_source", {}).get("staging"):
    assert not {"current-floorplan", "current-layout-views"} & {p.lower() for p in args.folder.resolve().parts}, "Staging must not replace current drawing folders."
master = Path(data["source_master"]["file"])
master_bytes = master.read_bytes()
house = json.loads(master_bytes.decode("utf-8-sig"))
pending = re.search("pending|stale", house["lighting"]["status"] + " " + house["lighting"]["calculation_validity"].get("niche_notation_update", {}).get("status", ""), re.I)
assert not pending or data.get("drawing_source", {}).get("staging"), "Lighting pending: regenerate explicitly as staging."
svg_bytes = svg.read_bytes()
assert hashlib.sha256(master_bytes).hexdigest() == data["source_master"]["sha256"], "Master differs from the generated SVG; regenerate before rendering."
assert len(master_bytes) == data["source_master"]["bytes"], "Master byte count differs from the generated SVG."
assert hashlib.sha256(svg_bytes).hexdigest() == data["artifacts"]["svg"]["sha256"], "SVG differs from its receipt; regenerate before rendering."
assert len(svg_bytes) == data["artifacts"]["svg"]["bytes"], "SVG byte count differs from its receipt."
readme_text = (args.folder / "README.md").read_text(encoding="utf-8")
assert data["source_master"]["sha256"] in readme_text, "README must name the bound master SHA; update it before rendering."
assert not {sha for sha in re.findall(r"\b[0-9a-f]{64}\b", readme_text)} - {data["source_master"]["sha256"]}, "README names another SHA256; it is stale."
errors, console_errors, requests = [], [], []
page_w = data.get("page", {}).get("width_px", 1800)
page_h = data.get("page", {}).get("height_px", 1910)
pdf_h_mm = round(594 * page_h / page_w + 16, 1)
with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": page_w, "height": page_h}, device_scale_factor=1)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda c: console_errors.append(c.text) if c.type == "error" else None)
    page.on("request", lambda r: requests.append(r.url) if r.url.startswith("http") else None)
    page.route("http://**", lambda r: r.abort())
    page.route("https://**", lambda r: r.abort())
    content = svg_bytes.decode("utf-8")
    page.set_content('<html><head><style>html,body{margin:0}svg{display:block}</style></head><body>' + content + "</body></html>", wait_until="networkidle")
    page.screenshot(path=str(args.folder / "house-working-floorplan.png"), full_page=True, timeout=60000)
    text_bounds = page.evaluate("""() => [...document.querySelectorAll('text')].map(e=>{
      const b=e.getBoundingClientRect();return {text:e.textContent,x:b.x,y:b.y,right:b.right,bottom:b.bottom};
    }).filter(b=>b.x<0||b.y<0||b.right>%d||b.bottom>%d)""" % (page_w + 1, page_h + 1))
    symbols = page.evaluate("""() => ({
      house_storage: document.querySelectorAll('#house-plan [data-storage-id]').length,
      children_lofts: document.querySelectorAll('#children-plan [data-storage-id="ST-R05-LF01"]').length,
      house_beds: document.querySelectorAll('#house-plan [data-storage-kind="queen_storage_bed"]').length,
      children_beds: document.querySelectorAll('#children-plan [data-storage-kind="queen_storage_bed"]').length,
      master_overlay: document.querySelectorAll('#house-plan #master-relationship-overlay').length,
      bed_envelopes: document.querySelectorAll('[data-bed-envelope]').length,
      pooja_niche: document.querySelectorAll('#house-plan g#pooja-niche[data-pooja-niche="HD-16"][data-niche-representation="front-outline-only"]').length,
      north_arrows: document.querySelectorAll('[data-north-arrow="sheet-bottom"]').length
    })""")
    visible = page.evaluate("() => [...document.querySelectorAll('text')].map(e=>e.textContent).join(' ')")
    page.set_content('<html><head><style>@page{size:594mm %smm;margin:8mm}html,body{margin:0}svg{display:block;width:578mm;height:auto}</style></head><body>' % pdf_h_mm +
                     content + "</body></html>", wait_until="networkidle")
    page.pdf(path=str(args.folder / "house-working-floorplan.pdf"), prefer_css_page_size=True, print_background=True)
    browser.close()
assert not errors, errors
assert not console_errors, console_errors
assert not requests, requests
assert not text_bounds, text_bounds
expected = data.get("expected_symbols") or {"house_storage": data["storage_items"], "children_lofts": 1, "house_beds": 2, "children_beds": 1, "master_overlay": 0, "bed_envelopes": 0, "pooja_niche": 0, "north_arrows": 0}
assert expected["house_storage"] == data["storage_items"], expected
assert symbols == expected, (symbols, expected)
norm = lambda s: re.sub(r"\s+", " ", s).strip()
load_figure = re.compile(r"\d\s*kg\b|\bkg/m\b", re.I)
obsolete = data.get("obsolete_wording_checked", [])
if data.get("drawing_source", {}).get("hd18"):
    obsolete += ["TRUE NORTH", "Decimal-foot interpretation also needs confirmation", "master 41.1 mm west interface"]
assert obsolete, "Generator must record the superseded open-item phrases it excluded."
dom_hits = [p for p in obsolete if p in norm(visible)] + load_figure.findall(visible)
assert not dom_hits, f"Superseded open-item wording rendered: {dom_hits}"
missing = [q["id"] for q in data["register_quoted_in_full"] if norm(q["text"]) not in norm(visible)]
assert not missing, f"Open-item register text not rendered in full: {missing}"
if data.get("drawing_source", {}).get("staging"):
    assert "STAGING - NOT FINAL" in visible, "Staging status must be visible on the drawing."
if data.get("drawing_source", {}).get("review_draft"):
    assert "REVIEW DRAFT" in visible and "not an as-built or construction release" in visible, "Review-draft status must be visible on the drawing."
if data.get("drawing_source", {}).get("hd18"):
    assert all(t in visible for t in ["HD-18", "0.4318", "1701.8", "381", "0.4064", "approximate homeowner north"]), "HD-18 estimate and orientation notes must be visible."
with pymupdf.open(args.folder / "house-working-floorplan.pdf") as document:
    assert len(document) == 1, f"Expected one PDF sheet, received {len(document)}"
    assert data["source_master"]["sha256"] in document[0].get_text(), "PDF must contain a searchable source hash"
    pdf_text = norm(document[0].get_text())
    pdf_hits = [p for p in obsolete if p in pdf_text] + load_figure.findall(pdf_text)
    assert not pdf_hits, f"Superseded open-item wording in PDF text: {pdf_hits}"
    pdf_size = list(document[0].rect)
assert master.read_bytes() == master_bytes, "Master changed during rendering; regenerate before publishing."
assert svg.read_bytes() == svg_bytes, "SVG changed during rendering; regenerate before publishing."
data["verified_utc"] = datetime.now(timezone.utc).isoformat()
data["render"] = {"browser": "headless Edge", "errors": errors, "console_errors": console_errors, "http_requests": requests, "out_of_page_text": text_bounds,
                  "symbols": symbols, "pdf_pages": 1, "pdf_page_points": pdf_size,
                  "open_item_wording": {"phrases_checked": len(obsolete), "dom_hits": dom_hits, "pdf_hits": pdf_hits,
                                        "register_items_quoted_in_full": len(data["register_quoted_in_full"])}}
for key in ["png", "pdf"]:
    file = args.folder / f"house-working-floorplan.{key}"
    content = file.read_bytes()
    data["artifacts"][key] = {"file": file.name, "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}
readme = args.folder / "README.md"
data["readme"] = {"file": readme.name, "sha256": hashlib.sha256(readme.read_bytes()).hexdigest(), "bytes": readme.stat().st_size}
here = Path(__file__).resolve().parent
data["generators"] = {name: hashlib.sha256((here / name).read_bytes()).hexdigest()
                      for name in ["floorplan.mjs", "render_floorplan.py", "drawing-source.mjs", "src/master-adapter.js"]}
receipt.write_text(json.dumps(data, indent=2), encoding="utf-8")
print("Rendered PNG + PDF; no errors, network requests or text outside the page.")
