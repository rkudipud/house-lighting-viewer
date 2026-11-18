"""Generate and validate a master-bound, schematic curtain-pocket review sheet."""
import argparse
import hashlib
import html
import json
from datetime import datetime, timezone
from pathlib import Path

import pymupdf
from playwright.sync_api import sync_playwright


def digest(data):
    return hashlib.sha256(data).hexdigest()


def artifact(path):
    data = path.read_bytes()
    return {"file": path.name, "bytes": len(data), "sha256": digest(data)}


ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--master", required=True, type=Path)
ap.add_argument("--sha", required=True)
ap.add_argument("--out", required=True, type=Path)
args = ap.parse_args()
source = args.master.read_bytes()
master_sha = digest(source)
if master_sha != args.sha:
    raise ValueError(f"Master SHA {master_sha} differs from the authorized SHA")
house = json.loads(source.decode("utf-8-sig"))
lighting = house["lighting"]
selected = lighting["curtain_pocket_s1"]
pockets = lighting["fixed_cct_map"]["curtain_pocket_candidates"]["pockets"]
strips = {s["id"]: s for s in selected["strips"]}
by_id = {p["id"]: p for p in pockets}
expected = ["CURT-LIV", "CURT-DIN", "CURT-MBR-S", "CURT-CBR"]
if (set(strips) != set(expected) or set(by_id) != set(expected + ["CURT-MBR-W03"])
        or selected["construction_release"] is not False
        or selected["product_approval"] is not False
        or selected["selected_S1_totals"]["photometry_credit_for_selected_strips"] is not False):
    raise ValueError("Selected curtain strip set or review holds differ from the expected master")
for ident, s in strips.items():
    p = by_id[ident]
    if (s["cct_k"] != 2700 or s["lane"] != "LOW" or s["new_knob"] is not False
            or s["photometry_credit"] is not False or s["fabrication_release"] is not False
            or p["held"] is not False or p["group_id"] != s["target_knob_group"]):
        raise ValueError(f"Curtain strip {ident} does not match the fixed-white review conditions")
if by_id["CURT-MBR-W03"]["held"] is not True:
    raise ValueError("CURT-MBR-W03 must remain held")

out = args.out.resolve()
out.mkdir(parents=True, exist_ok=True)
esc = html.escape
rows = []
for n, ident in enumerate(expected + ["CURT-MBR-W03"]):
    p = by_id[ident]
    s = strips.get(ident)
    state = ("SELECTED FOR REVIEW" if s else "HELD / UNLIT")
    note = ("Window and pocket unmeasured" if ident == "CURT-CBR" else
            "W03 pocket and window coordination held" if not s else "Pocket and returns unmeasured")
    y = 890 + n * 48
    color = "#8b5d19" if s else "#a3403b"
    rows.append(
        f'<path d="M75 {y + 13}H1605" stroke="#d8e0de"/>'
        f'<text x="84" y="{y}" class="mono" font-size="16">{esc(ident)}</text>'
        f'<text x="315" y="{y}" font-size="16">{esc(p["room"])}</text>'
        f'<text x="425" y="{y}" class="mono" font-size="15">{esc(p["group_id"])}</text>'
        f'<text x="665" y="{y}" fill="{color}" font-size="15" font-weight="700">{state}</text>'
        f'<text x="975" y="{y}" font-size="15" class="muted">{esc(note)}</text>'
    )

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1680" height="1280" viewBox="0 0 1680 1280" role="img" aria-labelledby="title description">
<title id="title">Curtain pocket section - review diagram</title>
<desc id="description">Schematic only: two recessed curtain tracks and a selected warm strip, with all dimensions and detailing unmeasured. W03 is held and unlit.</desc>
<metadata>Master SHA256: {master_sha}; review draft; no photometry credit</metadata>
<defs>
 <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10Z" fill="#9b641c"/></marker>
 <linearGradient id="warm" x1="0" x2="0" y1="0" y2="1"><stop stop-color="#f8cb7c" stop-opacity=".55"/><stop offset="1" stop-color="#f8cb7c" stop-opacity="0"/></linearGradient>
</defs>
<style>text{{font-family:"Segoe UI",Arial,sans-serif;fill:#203b43}} .muted{{fill:#5d7174}} .mono{{font-family:Consolas,monospace}} .label{{font-size:15px;fill:#45636a}}</style>
<rect width="1680" height="1280" fill="#fcfdfc"/>
<text x="60" y="58" font-size="34" font-weight="600">Curtain pocket - indicative section</text>
<text x="60" y="90" font-size="18" class="muted">REVIEW DRAFT / schematic only / not a construction or fabrication detail</text>
<text x="1620" y="58" text-anchor="end" font-size="14" class="mono">house-design.json</text>
<path d="M60 116H1620" stroke="#c8d2d3"/>
<rect x="60" y="146" width="960" height="615" rx="8" fill="#fff" stroke="#d2dcda"/>
<text x="88" y="180" font-size="20" font-weight="650">SECTION THROUGH WINDOW AND CEILING</text>
<text x="88" y="207" font-size="14" class="muted">Illustrative arrangement only; track order and mounting must be checked on site.</text>
<rect x="118" y="245" width="830" height="42" fill="#b9c9cc" stroke="#6b8083"/>
<text x="533" y="272" text-anchor="middle" font-size="15">Existing slab reference - no cutting or chasing authorised</text>
<rect x="118" y="287" width="88" height="393" fill="#d9e0db" stroke="#80938e"/>
<rect x="137" y="335" width="52" height="276" fill="#d9edf1" stroke="#76949c" stroke-width="2"/>
<path d="M163 336V611M137 470H189" stroke="#9bb5b8" stroke-width="2"/>
<rect x="635" y="357" width="313" height="62" fill="#e1e4dc" stroke="#899a95"/>
<rect x="614" y="335" width="21" height="84" fill="#e1e4dc" stroke="#899a95"/>
<text x="794" y="396" text-anchor="middle" font-size="15">False-ceiling band</text>
<path d="M229 310H610" stroke="#9b641c" stroke-width="1.5" stroke-dasharray="5 4" marker-start="url(#arrow)" marker-end="url(#arrow)"/>
<text x="420" y="304" text-anchor="middle" font-size="14" fill="#9b641c">CLEAR POCKET WIDTH UNMEASURED</text>
<path d="M592 318V350" stroke="#9b641c" stroke-width="1.5" stroke-dasharray="4 3" marker-start="url(#arrow)" marker-end="url(#arrow)"/>
<text x="574" y="335" text-anchor="end" font-size="13" fill="#9b641c">depth unmeasured</text>
<g data-track="sheer">
 <rect x="303" y="331" width="40" height="15" rx="3" fill="#607b82"/>
 <path d="M323 346V670" stroke="#bdced0" stroke-width="16" opacity=".7"/>
 <path d="M315 348Q326 360 315 372T315 396T315 420T315 444T315 468T315 492T315 516T315 540T315 564T315 588T315 612T315 636T315 660" fill="none" stroke="#94adb0" stroke-width="2"/>
 <text x="323" y="700" text-anchor="middle" class="label">Sheer track</text>
</g>
<g data-track="blackout">
 <rect x="421" y="331" width="40" height="15" rx="3" fill="#607b82"/>
 <path d="M441 346V670" stroke="#b09b82" stroke-width="22" opacity=".75"/>
 <path d="M433 348Q444 360 433 372T433 396T433 420T433 444T433 468T433 492T433 516T433 540T433 564T433 588T433 612T433 636T433 660" fill="none" stroke="#8f7960" stroke-width="2"/>
 <text x="441" y="700" text-anchor="middle" class="label">Blackout track</text>
</g>
<path d="M552 343L580 343L570 587L440 587Z" fill="url(#warm)"/>
<rect x="558" y="334" width="24" height="9" rx="3" fill="#e3a442" data-strip="selected-2700K"/>
<path d="M570 329V310H785" fill="none" stroke="#b47e2c"/>
<text x="790" y="314" font-size="14" fill="#9b641c">2700 K strip / seat to verify</text>
<text x="163" y="735" text-anchor="middle" font-size="14" class="muted">WINDOW SIDE</text>
<text x="810" y="735" text-anchor="middle" font-size="14" class="muted">ROOM SIDE</text>
<rect x="1045" y="146" width="575" height="615" rx="8" fill="#f3f6f2" stroke="#d2dcda"/>
<text x="1073" y="183" font-size="19" font-weight="650">BEFORE SITE WORK</text>
<text x="1073" y="225" font-size="16" font-weight="650">01 / Measure the built pocket</text>
<text x="1073" y="252" font-size="15" class="muted">Verify width, depth, return, window opening and</text>
<text x="1073" y="274" font-size="15" class="muted">curtain stack. The drawing is not to scale.</text>
<text x="1073" y="322" font-size="16" font-weight="650">02 / Check both tracks and fabric</text>
<text x="1073" y="349" font-size="15" class="muted">Confirm bracket spacing, fixing substrate, cleaning</text>
<text x="1073" y="371" font-size="15" class="muted">access and free travel for sheer and blackout.</text>
<text x="1073" y="419" font-size="16" font-weight="650">03 / Mock up the strip</text>
<text x="1073" y="446" font-size="15" class="muted">Confirm clearance, heat, feed and service access;</text>
<text x="1073" y="468" font-size="15" class="muted">hide the source from seated and standing sightlines.</text>
<text x="1073" y="516" font-size="16" font-weight="650">04 / Keep controls simple</text>
<text x="1073" y="543" font-size="15" class="muted">Selected strips follow the room's existing LOW</text>
<text x="1073" y="565" font-size="15" class="muted">dimmer. No new knob and no adjustable CCT.</text>
<text x="1073" y="613" font-size="16" font-weight="650" fill="#9b641c">No lux credit</text>
<text x="1073" y="640" font-size="15" class="muted">Strip light is illustrative and excluded from frozen</text>
<text x="1073" y="662" font-size="15" class="muted">photometric estimates. Products are not approved.</text>
<text x="1073" y="706" font-size="14" class="muted">MBR-S and CBR assumed returns exceed modeled</text>
<text x="1073" y="728" font-size="14" class="muted">corners by about 0.30 m; verify actual ends on site.</text>
<text x="60" y="815" font-size="20" font-weight="650">CURTAIN STRIP STATUS / FIXED 2700 K</text>
<text x="84" y="852" font-size="13" font-weight="700" class="muted">RECORD</text>
<text x="315" y="852" font-size="13" font-weight="700" class="muted">ROOM</text>
<text x="425" y="852" font-size="13" font-weight="700" class="muted">EXISTING LOW CONTROL</text>
<text x="665" y="852" font-size="13" font-weight="700" class="muted">STATUS</text>
<text x="975" y="852" font-size="13" font-weight="700" class="muted">MEASUREMENT / HOLD</text>
{''.join(rows)}
<text x="60" y="1180" font-size="15" class="muted">All selected strip positions, sizes, returns and feed access remain unmeasured. Site mock-up and qualified coordination required.</text>
<path d="M60 1212H1620" stroke="#c8d2d3"/>
<text x="60" y="1242" font-size="12" class="mono muted">Master SHA256: {master_sha}</text>
<text x="1620" y="1242" text-anchor="end" font-size="14" fill="#9b641c">REVIEW ONLY - not for construction</text>
</svg>'''

svg_path = out / "curtain-pocket-section-review.svg"
png_path = out / "curtain-pocket-section-review.png"
pdf_path = out / "curtain-pocket-section-review.pdf"
svg_path.write_text(svg, encoding="utf-8")
errors, requests = [], []
with sync_playwright() as pw:
    browser = pw.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1680, "height": 1281}, device_scale_factor=2)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("request", lambda r: requests.append(r.url) if r.url.startswith(("http:", "https:")) else None)
    page.route("http://**", lambda r: r.abort())
    page.route("https://**", lambda r: r.abort())
    page.set_content('<html><head><style>html,body{margin:0}svg{display:block}</style></head><body>' + svg + '</body></html>', wait_until="networkidle")
    dom = page.evaluate("""() => {
      const svg=document.querySelector('svg'),texts=[...svg.querySelectorAll('text')].map(e=>{
        const b=e.getBoundingClientRect();return {text:e.textContent,x:b.x,y:b.y,r:b.right,b:b.bottom};
      });
      const outside=texts.filter(b=>b.x<0||b.y<0||b.r>1680||b.b>1280);
      const overlap=[];
      for(let i=0;i<texts.length;i++)for(let j=i+1;j<texts.length;j++){
        const a=texts[i],b=texts[j];
        if(Math.min(a.r,b.r)-Math.max(a.x,b.x)>3&&Math.min(a.b,b.b)-Math.max(a.y,b.y)>4)overlap.push([a.text,b.text]);
      }
      return {outside,overlap,tracks:[...svg.querySelectorAll('[data-track]')].map(e=>e.getAttribute('data-track')),
        strips:svg.querySelectorAll('[data-strip="selected-2700K"]').length,text:svg.textContent};
    }""")
    page.locator("svg").screenshot(path=str(png_path))
    page.set_content('<html><head><style>@page{size:1680px 1281px;margin:0}html,body{margin:0}svg{display:block}</style></head><body>' + svg + '</body></html>', wait_until="networkidle")
    page.pdf(path=str(pdf_path), prefer_css_page_size=True, print_background=True)
    browser.close()

if errors or requests or dom["outside"] or dom["overlap"]:
    raise ValueError(f"Render problems: errors={errors}, requests={requests}, outside={dom['outside']}, overlap={dom['overlap']}")
if dom["tracks"] != ["sheer", "blackout"] or dom["strips"] != 1:
    raise ValueError("The diagram must show exactly two tracks and one schematic strip")
required = expected + ["CURT-MBR-W03", "HELD / UNLIT", "No lux credit", "unmeasured", master_sha]
if any(text not in dom["text"] for text in required):
    raise ValueError("The diagram is missing a required status or source label")
with pymupdf.open(pdf_path) as document:
    if len(document) != 1 or any(text not in document[0].get_text() for text in required):
        raise ValueError("The PDF must have one searchable page with all status and source labels")
if args.master.read_bytes() != source:
    raise ValueError("Master changed during rendering; regenerate")

readme = out / "README.md"
readme.write_text(
    "# Curtain pocket review section\n\n"
    "Schematic only, not to scale and not a construction or fabrication release. "
    "Two concealed tracks and four selected warm strips require site measurement and a mock-up. "
    "CBR window/pocket is unmeasured; W03 remains held and unlit. No strip lux credit is included. "
    "The strip seat, brackets, feed, service access and product selection are not approved.\n\n"
    f"Master SHA-256: `{master_sha}`.\n",
    encoding="utf-8",
)
receipt = {
    "verified_utc": datetime.now(timezone.utc).isoformat(),
    "master_sha256": master_sha,
    "status": "REVIEW_DRAFT_NOT_CONSTRUCTION_RELEASED",
    "selected_strips": {i: {"group": strips[i]["target_knob_group"], "cct_k": strips[i]["cct_k"],
                             "photometry_credit": strips[i]["photometry_credit"]} for i in expected},
    "held": ["CURT-MBR-W03"], "cbr_window": "placeholder; unmeasured",
    "model_clash": "Assumed MBR-S and CBR returns each exceed a modeled room corner by about 0.30 m; actual ends unmeasured.",
    "checks": {"tracks": dom["tracks"], "schematic_strip_symbols": dom["strips"], "pdf_pages": 1,
               "searchable_status_labels": True, "out_of_page_text": dom["outside"],
               "text_overlap": dom["overlap"], "browser_errors": errors, "http_requests": requests},
    "artifacts": [artifact(p) for p in (svg_path, png_path, pdf_path, readme)],
    "generator_sha256": digest(Path(__file__).read_bytes()),
}
(out / "curtain-section-verification.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
print(json.dumps({"master_sha256": master_sha, "selected": expected, "held": receipt["held"],
                  "pdf_sha256": artifact(pdf_path)["sha256"], "errors": errors}))
