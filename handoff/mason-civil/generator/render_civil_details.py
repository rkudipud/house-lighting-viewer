"""Render and check the hash-bound civil coordination details, without network access."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pymupdf
from playwright.sync_api import sync_playwright


HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def artifact(path):
    path = Path(path)
    return {"file": path.name, "sha256": sha(path), "bytes": path.stat().st_size}


parser = argparse.ArgumentParser()
parser.add_argument("--master", required=True, type=Path)
parser.add_argument("--out", required=True, type=Path)
parser.add_argument("--sha", required=True)
args = parser.parse_args()
master = args.master.resolve()
out = args.out.resolve()
master_bytes = master.read_bytes()
if hashlib.sha256(master_bytes).hexdigest() != args.sha:
    sys.exit("Master hash differs from the requested source; refusing to render.")
result = subprocess.run(
    ["node", str(HERE / "civil_details.mjs"), str(master), str(out), args.sha],
    cwd=HERE, capture_output=True, text=True,
)
if result.returncode:
    sys.exit(result.stdout + result.stderr)

source = json.loads((out / "details-source.json").read_text(encoding="utf-8"))
register = json.loads((out / "opening-register.json").read_text(encoding="utf-8"))
assert source["source_master_sha256"] == args.sha == register["source_master_sha256"]
assert len(source["sheets"]) == 4 and len(register["openings"]) == 21
assert all(o["actual_width_m"] is None and o["actual_height_m"] is None
           for o in register["openings"])
assert all(o["model_geometry_ref"].startswith("house-design.json#/") for o in register["openings"])
assert all(abs(o["model_width_m"] - round(o["model_width_m"], 2)) < 1e-9
           for o in register["openings"])

dom_script = """() => {
  const svg = document.querySelector('svg'), b = svg.getBoundingClientRect();
  const texts = [...svg.querySelectorAll('text')].filter(t => (t.textContent || '').trim()).map(t => {
    const r = t.getBoundingClientRect();
    return {t:t.textContent.trim(),x:r.x-b.x,y:r.y-b.y,r:r.right-b.x,d:r.bottom-b.y};
  });
  const outside = texts.filter(t => t.x < -.5 || t.y < -.5 || t.r > b.width+.5 || t.d > b.height+.5);
  const overlaps = [];
  for (let i=0;i<texts.length;i++) for (let j=i+1;j<texts.length;j++) {
    const a=texts[i], c=texts[j], w=Math.min(a.r,c.r)-Math.max(a.x,c.x), h=Math.min(a.d,c.d)-Math.max(a.y,c.y);
    if (w>3 && h>4) overlaps.push([a.t,c.t,Math.round(w),Math.round(h)]);
  }
  return {outside,overlaps,text:svg.textContent.replace(/\\s+/g,' '),texts:texts.length};
}"""

page_errors = []
console_errors = []
requests = []
rows = []
pdf_parts = []
with sync_playwright() as pw:
    browser = pw.chromium.launch(channel="msedge", headless=True)
    browser_version = browser.version
    for s in source["sheets"]:
        svg_path = out / s["file"]
        if sha(svg_path) != s["sha256"]:
            raise RuntimeError(f"SVG differs from its manifest: {s['id']}")
        svg = svg_path.read_text(encoding="utf-8")
        dims = re.search(r'width="([\d.]+)" height="([\d.]+)" viewBox', svg)
        if not dims:
            raise RuntimeError(f"Missing SVG dimensions: {s['id']}")
        width, height = (float(dims.group(1)), float(dims.group(2)))
        page = browser.new_page(viewport={"width": int(width), "height": int(height) + 1}, device_scale_factor=2)
        page.on("pageerror", lambda e: page_errors.append(str(e)))
        page.on("console", lambda c: console_errors.append(c.text) if c.type == "error" else None)
        page.on("request", lambda r: requests.append(r.url) if r.url.startswith(("http:", "https:")) else None)
        page.route("http://**", lambda r: r.abort())
        page.route("https://**", lambda r: r.abort())
        page.set_content('<html><head><style>html,body{margin:0;background:#fff}svg{display:block}</style></head><body>'
                         + svg + '</body></html>', wait_until="networkidle")
        dom = page.evaluate(dom_script)
        png = out / (s["id"] + ".png")
        page.locator("svg").screenshot(path=str(png))
        page.set_content(f'<html><head><style>@page{{size:{width}px {height+1}px;margin:0}}'
                         'html,body{margin:0}svg{display:block}</style></head><body>' + svg + '</body></html>',
                         wait_until="networkidle")
        part = out / ("_part_" + s["id"] + ".pdf")
        page.pdf(path=str(part), prefer_css_page_size=True, print_background=True)
        page.close()
        pdf_parts.append(part)
        rows.append({"id": s["id"], "title": s["title"], "svg": artifact(svg_path), "png": artifact(png),
                     "text_count": dom["texts"], "outside_text": dom["outside"], "text_overlaps": dom["overlaps"],
                     "visible_text": dom["text"]})
    browser.close()

pdf_path = out / "site-coordination-details.pdf"
pdf = pymupdf.open()
for part in pdf_parts:
    with pymupdf.open(part) as p:
        if len(p) != 1:
            raise RuntimeError(f"Unexpected page count in {part.name}")
        pdf.insert_pdf(p)
    part.unlink()
pdf.set_toc([[1, s["title"], i + 1] for i, s in enumerate(source["sheets"])])
pdf.set_metadata({"title": "Civil site coordination details - review only",
                  "subject": f"Not construction released; source master sha256 {args.sha}"})
pdf.save(pdf_path, garbage=4, deflate=True)
pdf.close()

checks = []


def check(name, ok, detail=None):
    checks.append({"check": name, "ok": bool(ok), **({"detail": detail} if detail is not None else {})})


check("no browser errors or network requests", not page_errors and not console_errors and not requests,
      {"page_errors": page_errors, "console_errors": console_errors, "requests": requests})
check("all text is inside the page", all(not r["outside_text"] for r in rows),
      {r["id"]: r["outside_text"] for r in rows if r["outside_text"]})
check("no text-on-text overlaps", all(not r["text_overlaps"] for r in rows),
      {r["id"]: r["text_overlaps"] for r in rows if r["text_overlaps"]})
check("all pages carry source hash and construction hold",
      all(args.sha in r["visible_text"] and "not a construction release" in r["visible_text"] for r in rows))
check("all opening identifiers present in schedule",
      all(o["code"] in rows[1]["visible_text"] for o in register["openings"]))
check("unverified dimensions and floor labels remain explicitly unmeasured",
      all(k in rows[1]["visible_text"] for k in ["NOT measured", "unmeasured", "F1-F4", "not confirmed"])
      if "not confirmed" in rows[1]["visible_text"] else
      all(k in rows[1]["visible_text"] for k in ["NOT measured", "unmeasured", "F1-F4", "unknown"]))
check("site-selected strips and W03 exclusion represented",
      all(k in rows[0]["visible_text"] for k in ["CURT-LIV", "CURT-DIN", "CURT-MBR-S", "CURT-CBR", "CURT-MBR-W03", "held and excluded"]))
check("return clash is identified without construction set-out",
      all(k in rows[0]["visible_text"] for k in ["0.30 m", "model clash", "not a site measurement"]))
check("pooja choice and structural holds represented",
      all(k in rows[2]["visible_text"] for k in ["small idols", "framed picture", "not independently verified", "No niche deepening"]))
check("CBR accepted layout and site pinch represented",
      all(k in rows[3]["visible_text"] for k in ["CBR-H1-H6", "active/switchable", "C37", "387.6 mm", "Keep selected layout"]))
check("conditional cabinets and single-supply engineering holds represented",
      all(k in rows[3]["visible_text"] for k in ["ST-R04a-WR01", "ST-R08-UC01", "FH-ST-03", "FH-ST-12",
                                                "one selected P01", "480 W", "20 A", "12.5 A", "branch protection"]))
with pymupdf.open(pdf_path) as p:
    pdf_texts = [page.get_text() for page in p]
    check("four searchable PDF pages in sheet order",
          len(p) == 4 and all(args.sha in t for t in pdf_texts)
          and p.get_toc() == [[1, s["title"], i + 1] for i, s in enumerate(source["sheets"])])

if master.read_bytes() != master_bytes:
    raise RuntimeError("Canonical master changed during rendering; regenerate against the new hash.")
failures = [c for c in checks if not c["ok"]]
receipt = {"schema": "civil_details_receipt/1", "verified_utc": datetime.now(timezone.utc).isoformat(),
           "source_master": {"path": str(master), "sha256": args.sha, "bytes": len(master_bytes)},
           "construction_release": False, "source_manifest": artifact(out / "details-source.json"),
           "opening_register": artifact(out / "opening-register.json"), "pdf": artifact(pdf_path),
           "sheets": [{k: v for k, v in r.items() if k != "visible_text"} for r in rows],
           "checks": checks, "checks_passed": len(checks) - len(failures), "checks_total": len(checks),
           "render": {"browser": "headless Edge " + browser_version, "network_requests": requests},
           "generators": {p.name: sha(p) for p in [HERE / "civil_details.mjs", HERE / "render_civil_details.py"]}}
receipt_path = out / "site-details-verification.json"
receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
print(json.dumps({"checks": f"{len(checks)-len(failures)}/{len(checks)}",
                  "receipt_sha256": sha(receipt_path), "pdf_sha256": sha(pdf_path),
                  "failures": failures}, indent=2))
sys.exit(1 if failures else 0)
