"""Build, render and verify the read-only "current layout views" drawing set.

Usage:
  python render_layout_views.py --master <house-design.json> --out <folder> --sha <expected master sha256> [--live <live master>]

Pipeline (re-runnable, offline, no master edits):
  1. hash-guard the master, run layout_views.mjs (SVG per sheet + sheets.json)
  2. render each SVG in headless Edge: PNG at 2x, vector PDF page, DOM checks
  3. merge one searchable PDF (plan -> RCP -> elevations by room)
  4. reconcile drawn ids against the raw master JSON
  5. write README.md and layout-views-verification.json (receipt)
"""
import argparse
import hashlib
import json
import platform
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pymupdf
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
SCALE = 2


def sha(path_or_bytes):
    data = path_or_bytes if isinstance(path_or_bytes, (bytes, bytearray)) else Path(path_or_bytes).read_bytes()
    return hashlib.sha256(data).hexdigest()


def artifact(path):
    path = Path(path)
    data = path.read_bytes()
    return {"file": path.name, "sha256": sha(data), "bytes": len(data)}


ap = argparse.ArgumentParser()
ap.add_argument("--master", required=True, type=Path)
ap.add_argument("--out", required=True, type=Path)
ap.add_argument("--sha", required=True)
ap.add_argument("--live", type=Path, help="current live master, only to report whether it has moved past the bound master")
ap.add_argument("--staging", action="store_true", help="validate non-final outputs in a separate folder while lighting integration is pending")
ap.add_argument("--review-draft", action="store_true", dest="review_draft", help="mark every sheet REVIEW DRAFT (integrated master, not construction-released)")
args = ap.parse_args()
out = args.out.resolve()
args.master = args.master.resolve()

master_bytes = args.master.read_bytes()
master_sha = sha(master_bytes)
if master_sha != args.sha:
    sys.exit(f"Master SHA {master_sha} does not match expected {args.sha}; refusing to draw.")
house = json.loads(master_bytes.decode("utf-8-sig"))
lighting = house["lighting"]
pending = bool(re.search("pending|stale", lighting["status"] + " " + lighting["calculation_validity"].get("niche_notation_update", {}).get("status", ""), re.I))
assert args.staging or not pending, "Lighting integration is pending; use --staging in a separate folder, not final outputs."
assert not args.staging or not {"current-layout-views", "current-floorplan"} & {p.lower() for p in out.parts}, "Staging must not replace current drawing folders."
out.mkdir(parents=True, exist_ok=True)
assert lighting["calculation_validity"]["construction_release"] is False, "This drawing set is not a construction release."
fixture_count = len(lighting["fixtures"])
circuit_ids = sorted({f["circuit"] for f in lighting["fixtures"]})
circuit_count = len(circuit_ids)
cbr_count = sum(f["room"] == "CBR" for f in lighting["fixtures"])
lighting_summary = f"{fixture_count} base fittings, {circuit_count} controlled groups"
fixed_white = lighting["status"] == "FIXED_WHITE_HOMEOWNER_SIGNED_REVIEW_CANDIDATE_NOT_CONSTRUCTION_RELEASED"
opt1 = lighting["status"].startswith("OPT1") or fixed_white
selected_strips = lighting["curtain_pocket_s1"]["strips"] if fixed_white else []
k2 = lighting["calculation_validity"].get("homeowner_selections", {}).get("kitchen_worktop", {})
if opt1:
    assert k2.get("option") == "K-2", "OPT-1 master must record the homeowner-selected kitchen option K-2"
    lighting_note = (f"OPT-1 calculated review candidate from the bound master ({lighting_summary}). Four selected 2700 K curtain strips bring the review schedule to 108 fittings / 51 circuits; no new knobs or photometry credit. Kitchen task option K-2 is homeowner-selected for review: "
                     "it adds the sink-end linear KIT-T4 and lowers KIT-T1 output. Generic-optics analytic estimates, not measured or manufacturer-validated; "
                     "no photometry is shown on this sheet. Not construction-released; product, driver, dimmer and site-fit holds remain open. "
                     "Each bathroom face-light pair has its own knob (HD-17). "
                     "Pooja fittings remain count/load allowances only, with inherited positions held (H-POOJA-GEOMETRY); "
                     "no corrected placement is implied.")
else:
    lighting_note = (("STAGING: prior lighting is stale pending HD-18 recoordination. " if pending else "") +
                     f"HD-14 lighting proposal ({lighting_summary}) from the bound master, including HD-16 and HD-17. "
                     "Not construction-released; no photometry is shown. Each bathroom face-light pair has its own knob (HD-17). "
                     "LIV-P1/P2 remain count/load allowances only, with inherited positions held (H-POOJA-GEOMETRY); "
                     "no corrected placement is implied. Site and product-fit holds remain open.")

for stale in list(out.glob("*.svg")) + list(out.glob("*.png")) + list(out.glob("*.pdf")):
    stale.unlink()
gen = subprocess.run(["node", str(HERE / "layout_views.mjs"), str(args.master), str(out), args.sha] + (["--staging"] if args.staging else (["--review-draft"] if args.review_draft else [])),
                     capture_output=True, text=True, cwd=HERE)
if gen.returncode != 0:
    sys.exit("layout_views.mjs failed:\n" + gen.stderr + gen.stdout)
manifest = json.loads((out / "sheets.json").read_text(encoding="utf-8"))
assert manifest["master_sha256"] == master_sha
drawing_source = manifest["drawing_source"]

JS_DOM = """() => {
  const svg = document.querySelector('svg');
  const box = svg.getBoundingClientRect();
  const W = box.width, H = box.height;
  const texts = [...svg.querySelectorAll('text')].filter(t => (t.textContent || '').trim()).map(t => {
    const b = t.getBoundingClientRect();
    return {t: t.textContent.trim().slice(0, 60), x: b.x - box.x, y: b.y - box.y, r: b.right - box.x, b: b.bottom - box.y};
  });
  const outside = texts.filter(o => o.x < -0.5 || o.y < -0.5 || o.r > W + 0.5 || o.b > H + 0.5);
  const overlaps = [];
  for (let i = 0; i < texts.length; i++) for (let j = i + 1; j < texts.length; j++) {
    const a = texts[i], c = texts[j];
    const w = Math.min(a.r, c.r) - Math.max(a.x, c.x), h = Math.min(a.b, c.b) - Math.max(a.y, c.y);
    if (w > 3 && h > 4) overlaps.push([a.t, c.t, Math.round(w), Math.round(h), Math.round(a.x), Math.round(a.y)]);
  }
  const ids = a => [...new Set([...svg.querySelectorAll('[data-' + a + ']')].map(e => e.getAttribute('data-' + a)))].sort();
  return {W, H, texts: texts.length, outside, overlaps,
    ids: Object.fromEntries(['room-id','wall-id','opening-id','storage-id','item-id','panel-id','fixture-id','fan-room','curtain-pocket','curtain-strip',
      'groove','bath-id','stair-part','bed','suppressed-storage','inactive','fixture-room','hold-mark','hold-fixture','pooja-callout','detail','niche-representation'].map(a => [a, ids(a)])),
    trayHeights: Object.fromEntries([...svg.querySelectorAll('[data-ceiling^="tray-"]')].map(e => [e.getAttribute('data-ceiling'), {height: Number(e.getAttribute('data-tray-height')), basis: e.getAttribute('data-height-basis')}])),
    inactiveFixtureIds: [...svg.querySelectorAll('[data-fixture-id][data-inactive]')].map(e => e.getAttribute('data-fixture-id')).sort(),
    allowanceFixtureIds: [...svg.querySelectorAll('[data-fixture-id][data-held-allowance]')].map(e => e.getAttribute('data-fixture-id')).sort(),
    elements: svg.querySelectorAll('*').length,
    text: svg.textContent.replace(/\\s+/g, ' ')};
}"""

console_errors, page_errors, http_requests, sheet_results = [], [], [], []
pdf_parts = []
with sync_playwright() as pw:
    browser = pw.chromium.launch(channel="msedge", headless=True)
    edge_version = browser.version
    for s in manifest["sheets"]:
        svg_path = out / s["file"]
        svg_text = svg_path.read_text(encoding="utf-8")
        m = re.search(r'width="([\d.]+)" height="([\d.]+)" viewBox', svg_text)
        w, h = float(m.group(1)), float(m.group(2))
        page = browser.new_page(viewport={"width": int(w), "height": int(h) + 1}, device_scale_factor=SCALE)
        page.on("pageerror", lambda e: page_errors.append(str(e)))
        page.on("console", lambda c: console_errors.append(c.text) if c.type == "error" else None)
        page.on("request", lambda r: http_requests.append(r.url) if r.url.startswith(("http:", "https:")) else None)
        page.route("http://**", lambda r: r.abort())
        page.route("https://**", lambda r: r.abort())
        page.set_content('<html><head><style>html,body{margin:0;background:#fff}svg{display:block}</style></head><body>' + svg_text + '</body></html>',
                         wait_until="networkidle")
        dom = page.evaluate(JS_DOM)
        png = out / (s["id"] + ".png")
        page.locator("svg").first.screenshot(path=str(png))
        page.set_content(f'<html><head><style>@page{{size:{w}px {h + 1}px;margin:0}}html,body{{margin:0}}svg{{display:block}}</style></head><body>' + svg_text + '</body></html>',
                         wait_until="networkidle")
        part = out / ("_part_" + s["id"] + ".pdf")
        page.pdf(path=str(part), prefer_css_page_size=True, print_background=True)
        pdf_parts.append((s, part))
        page.close()
        sheet_results.append({"sheet": s, "dom": dom, "svg": svg_text, "png": png, "w": w, "h": h})
    browser.close()

# merged, searchable PDF: plan -> RCP -> elevations
doc = pymupdf.open()
toc = []
for s, part in pdf_parts:
    with pymupdf.open(part) as p:
        assert len(p) == 1, f"{s['id']} printed on {len(p)} pages"
        doc.insert_pdf(p)
    toc.append([1, s["title"], len(doc)])
    part.unlink()
doc.set_toc(toc)
doc.set_metadata({"title": "Current layout views - top-down plan, reflected ceiling plan, interior elevations",
                  "subject": f"Read-only drawing set from canonical master sha256 {master_sha}",
                  "author": "Architectural/BIM coordinator (generated)", "keywords": "layout, RCP, elevations, south-up, north arrow, HD-11"})
pdf_path = out / "current-layout-views.pdf"
doc.save(pdf_path, garbage=4, deflate=True)
doc.close()

# ---------------------------------------------------------------- checks
checks, failures = [], []


def check(name, ok, detail=None):
    checks.append({"check": name, "ok": bool(ok), **({"detail": detail} if detail is not None else {})})
    if not ok:
        failures.append(name + (": " + json.dumps(detail)[:400] if detail is not None else ""))


V = house["visualization_geometry"]
by_id = {r["sheet"]["id"]: r for r in sheet_results}
plan = by_id["01-plan-furnished"]["dom"]
rcp = by_id["02-rcp"]["dom"]
elev = [r for r in sheet_results if "-elev-" in r["sheet"]["id"]]

check("zero page errors", not page_errors, page_errors)
check("zero console errors", not console_errors, console_errors)
check("no network requests", not http_requests, http_requests)
check("expected sheet count 13 (plan, RCP, 11 room elevations)", len(sheet_results) == 13 and len(elev) == 11)
check("every SVG text sits inside its page", all(not r["dom"]["outside"] for r in sheet_results),
      {r["sheet"]["id"]: r["dom"]["outside"] for r in sheet_results if r["dom"]["outside"]})
overlaps = {r["sheet"]["id"]: r["dom"]["overlaps"] for r in sheet_results if r["dom"]["overlaps"]}
check("no text-on-text overlaps (bounding boxes)", not overlaps, overlaps)
check("generated SVG final bytes match the sheet manifest",
      all(sha(out / s["file"]) == s["sha256"] for s in manifest["sheets"]))
check("R05 tray metadata uses the reported approximate level, not the older slab reference",
      rcp["trayHeights"].get("tray-CBR") == {
          "height": house["lighting"]["design_inputs"]["ceilings"]["CBR"]["tray_h_m"],
          "basis": "homeowner-reported-approximate-unsurveyed",
      }, rcp["trayHeights"])

# plan vs raw master
fx_ids = sorted(f["id"] for f in house["lighting"]["fixtures"])
sup = sorted(V["master_layout"]["superseded_storage_ids"])
storage = house["storage"]["items"]
kept = [i for i in storage if i["id"] not in sup]
built_bed_kinds = {"queen_storage_bed", "bedside_unit"}
WR = house["decisions"]["warning_resolution"]
RC = house["decisions"]["r05_clearance"]
hd14_omitted = set(WR["answers"]["bedside_joinery"]["excluded_item_ids"])
not_drawn_storage = sorted(i["id"] for i in kept if i["kind"] in built_bed_kinds or i["id"] in hd14_omitted)
want_storage = sorted(i["id"] for i in kept if i["kind"] not in built_bed_kinds and i["id"] not in hd14_omitted)
n_bath = len(house["bathrooms"]["rooms"])
check("plan: every master room drawn once (10 visualization rooms + 2 bathrooms)", len(plan["ids"]["room-id"]) == len(V["rooms"]) + n_bath == 12, [len(plan["ids"]["room-id"]), len(V["rooms"]), n_bath])
check("plan: wall ids match master", sorted(w["id"] for w in V["walls"]) == plan["ids"]["wall-id"])
v_open = {o["id"] for o in V["openings"]}
bath_open = set(plan["ids"]["opening-id"]) - v_open
check("plan: all 15 master openings drawn plus the 3 openings (door, niche, vent) of each bathroom record", v_open <= set(plan["ids"]["opening-id"]) and len(v_open) == 15 and len(bath_open) == 3 * n_bath and all(re.fullmatch(r"bath[12]-(door|niche|vent)", i) for i in bath_open), sorted(bath_open))
check("plan: drawn storage = master storage minus 5 superseded R04 records minus built beds and the 3 HD-14 omitted bedside units", want_storage == plan["ids"]["storage-id"],
      {"want": want_storage, "got": plan["ids"]["storage-id"]})
check("plan: no superseded R04 footprint drawn as storage", not set(sup) & set(plan["ids"]["storage-id"] + plan["ids"]["item-id"]))
check("HD-14: omitted bedside units are not drawn as an item, storage record or optional outline on any sheet",
      not hd14_omitted & set(sum((r["dom"]["ids"]["storage-id"] + r["dom"]["ids"]["item-id"] for r in sheet_results), [])))
check("plan: both tenant bed envelopes drawn, none labelled joinery", plan["ids"]["bed"] == ["tenant-supplied"] and len(
    [1 for i in plan["ids"]["item-id"] if i.startswith("TENANT-BED")]) == 2, plan["ids"]["item-id"])
check("plan: 3 stair parts, lift shaft and 2 bath blocks", len(plan["ids"]["stair-part"]) == 3 and plan["ids"]["bath-id"] == ["BATH-TL1", "BATH-TL2"])
check("plan: north arrow present", "sheet-bottom" in by_id["01-plan-furnished"]["svg"])
pn = house["decisions"]["pooja_niche"]
check("plan: pooja shown only as an estimated front outline with the PN1 callout",
      plan["ids"]["pooja-callout"] == ["PN1"] and plan["ids"]["niche-representation"] == ["front-outline-only"]
      and all(s in plan["text"] for s in ["POOJA NICHE PN1", "built", "HD-16", "OI-POOJA-01"]))
check("master: pooja already built and reinforcement homeowner-reported (decisions.pooja_niche)",
      pn["built_status"].startswith("Already built") and pn["existing_construction"]["new_cutting_requested"] is False
      and pn["existing_construction"]["evidence_status"] == "homeowner_report_not_independent_structural_verification")
check("master: niche extension is reported, not a surveyed structural design",
      pn["existing_construction"]["outside_wall_extension"]["reported"] is True
      and pn["existing_construction"]["outside_wall_extension"]["measured_geometry"] is None
      and pn["geometry_hold"]["new_or_deeper_cutting_authorized"] is False)

# RCP vs raw master (CBR H1-H6, cove and LINE modelled ON for review; other CBR fixtures held)
check("rcp: all master lighting fixtures drawn, ids equal", rcp["ids"]["fixture-id"] == fx_ids and len(fx_ids) == len(set(fx_ids)), len(fx_ids))
cbr = sorted(f["id"] for f in house["lighting"]["fixtures"] if f["room"] == "CBR")
modelled_on = {f"CBR-H{n}" for n in range(1, 7)} | {"CBR-L1"} | {f"CBR-X{n}" for n in range(1, 5)}
held_cbr = sorted(i for i in cbr if i not in modelled_on)
check("rcp: CBR H1-H6, cove and LINE drawn as modelled ON; remaining CBR fittings faded and held", rcp["inactiveFixtureIds"] == held_cbr and len(cbr) > len(held_cbr), rcp["inactiveFixtureIds"])
rcp_sheet = by_id["02-rcp"]["sheet"]
check("rcp: circuit ids reconcile with canonical controls",
      rcp_sheet["drawn"]["circuitIds"] == circuit_ids == sorted(c["circuit"] for c in lighting["controls"]["circuits"]))
check("rcp: fixture type and room counts reconcile with canonical records",
      rcp_sheet["drawn"]["fixtureTypes"] == dict(Counter(f["type"] for f in lighting["fixtures"]))
      and rcp_sheet["drawn"]["fixtureRooms"] == dict(Counter(f["room"] for f in lighting["fixtures"])))
check("rcp: path and point counts reconcile with canonical records",
      rcp_sheet["counts"]["paths"] == sum(bool(f["path_ft"]) for f in lighting["fixtures"])
      and rcp_sheet["counts"]["paths"] + rcp_sheet["counts"]["points"] == fixture_count)
check("rcp: 3 fan points", sorted(f["room"] for f in V["fans"]) == rcp["ids"]["fan-room"])
check("rcp: 5 curtain pockets (4 windows + held W03)", len(rcp["ids"]["curtain-pocket"]) == 5)
check("rcp: four selected strips drawn without new knobs or photometry credit",
      rcp["ids"]["curtain-strip"] == sorted(s["id"] for s in selected_strips)
      and len(selected_strips) == 4 and all(s["cct_k"] == 2700 and not s["new_knob"] and not s["photometry_credit"] for s in selected_strips)
      and rcp_sheet["counts"]["reviewFixtures"] == 108 and rcp_sheet["counts"]["reviewCircuits"] == 51)
check("rcp: hold marks drawn for centre, hall beam, dressing sweep and pooja allowances",
      sorted(set(rcp["ids"]["hold-mark"])) == ["H-CENTRE-RECESS", "H-DRS-SWEEP", "H-HALL-BEAM", "H-POOJA-GEOMETRY"]
      and len(rcp["ids"]["hold-fixture"]) == 11, rcp["ids"]["hold-fixture"])
check("rcp: LIV-P1/P2 retained only as held count/load allowances",
      rcp["allowanceFixtureIds"] == ["LIV-P1", "LIV-P2"] and "count/load allowances only" in rcp["text"])
face_ids = sorted(f["id"] for f in lighting["fixtures"] if f["type"] == "FACEV")
check("rcp: four bathroom face bars retain their separate HD-17 groups",
      face_ids == ["TL1-F1", "TL1-F2", "TL2-F1", "TL2-F2"]
      and all(f["circuit"] == {"TL1": "C29B", "TL2": "C35B"}[f["room"]]
              for f in lighting["fixtures"] if f["type"] == "FACEV")
      and "Each bathroom face-light pair has its own knob (HD-17)" in rcp["text"])
check("rcp: master holds named (H-MBR-BED, H-MBR-W03) and children held (H-CBR-*)", all(k in rcp["text"] for k in ["H-MBR-BED", "H-MBR-W03", "H-CBR-"]))
check("rcp: current R05 fan and modelled-on ceiling remain distinct from installation holds",
      all(k in rcp["text"] for k in ["nominal room centre", "1050 mm planning sweep", "modelled ON for review", "H-CBR-CEIL"])
      and not re.search(r"remain held and unlit|proposed cove centre", rcp["text"], re.I))
child_elevation = by_id["08-elev-R05-children"]["dom"]["text"]
check("R05 elevation: reported band and unsurveyed centre are shown without the old band",
      all(k in child_elevation for k in ["band 3.048", "centre approximately 3.277", "slab estimate", "unsurveyed"])
      and "false-ceiling band 2.96" not in child_elevation)
check("rcp: integrated proposal wording, not released, and no photometry words", ("OPT-1" if opt1 else "HD-14") in rcp["text"] and "not released" in rcp["text"]
      and not re.search(r"\b(lux|lumen|lm|cd/m|UGR)\b", rcp["text"], re.I))
check("rcp: same openings and walls as the plan", rcp["ids"]["opening-id"] == plan["ids"]["opening-id"] and rcp["ids"]["wall-id"] == plan["ids"]["wall-id"])
STALE = ["hypothetical", "ALL HEIGHTS ASSUMED", "position along the wall is real", "OLD W03", "Phase D", "bed head now", "inactive placeholder",
         "finalized_floorplan", "plan-reference", "2.88", "beam band: single step", "homeowner-confirmed measured numbers",
         "no recess void", "no cavity", "0.25 m pocket is an assumption", "slab underside = raised centre panel", "NS01 optional",
         "proposed to be dropped", "dropped bedsides", "centre recess", "at or near the slab", "retired plan trace",
         "baseline CPL-1", "LIGHTING LAYER IS INTERIM", "centre \u22483.19", "115 mm depth", "recess 115",
         "11.37\u201312.28", "914.4 \u00d7 1475"]
for r in sheet_results:
    hits = [s for s in STALE if s.lower() in r["dom"]["text"].lower()]
    check(f"{r['sheet']['id']}: no stale or retired wording", not hits, hits)
    check(f"{r['sheet']['id']}: master SHA and HD-11 datum wording", master_sha in r["dom"]["text"] and "HD-11" in r["dom"]["text"])
    check(f"{r['sheet']['id']}: no 1.68 x 2.13 tenant frame drawn or quoted", not re.search(r"1\.68\s*[x\u00d7]\s*2\.13|1680\s*[x\u00d7]\s*2130", r["dom"]["text"]))

# HD-14 warning batch (decisions.warning_resolution): quiet content checks
check("master: HD-14 recorded, not a construction release", WR["decision"] == "HD-14" and WR["construction_release"] is False)
check("master: HD-15 retains geometry and records a site-clearance hold",
      RC["decision"] == "HD-15" and RC["geometry_changed"] is False and RC["status"] == "layout_retained_site_clearance_hold")
check("plan and children elevation: HD-15 pinch is labelled, not a comfortable walking route",
      all(all(k in txt for k in ["HD-15", str(RC["estimated_clearance_mm"]) + " mm", "not a comfortable walking route",
                                 "Keep room and furniture positions unchanged", "OI-R05-03"])
          for txt in [plan["text"], by_id["08-elev-R05-children"]["dom"]["text"]]))
for r in [by_id["02-rcp"], *elev]:
    t = r["dom"]["text"].lower()
    check(f"{r['sheet']['id']}: HD-14 curtain wording (two tracks, sheer + blackout)", "sheer" in t and "blackout" in t and "two tracks" in t)
check("rcp: integrated lighting totals and conditional status shown",
      lighting_summary in rcp["text"] and ("OPT-1 calculated review candidate" if opt1 else "HD-14 lighting proposal") in rcp["text"]
      and "holds remain open" in rcp["text"]
      and ("stale pending HD-18 recoordination" in rcp["text"] if pending else "stale pending" not in rcp["text"]))
if opt1:
    kit_t4 = next(f for f in lighting["fixtures"] if f["id"] == "KIT-T4")
    kit_t1 = next(f for f in lighting["fixtures"] if f["id"] == "KIT-T1")
    check("OPT-1: 104 fittings in 47 groups, status not construction-released, K-2 selected",
          fixture_count == 104 and circuit_count == 47 and lighting["status"] in ["OPT1_calculated_review_candidate_not_construction_released", "FIXED_WHITE_HOMEOWNER_SIGNED_REVIEW_CANDIDATE_NOT_CONSTRUCTION_RELEASED"]
          and lighting["calculation_validity"]["construction_release"] is False and lighting["calculation_validity"]["product_approval"] is False
          and k2.get("option") == "K-2" and k2.get("status") == "selected_for_review_not_construction_release")
    check("OPT-1 rcp: K-2 kitchen fittings KIT-T4 (new sink-end linear) and lower-output KIT-T1 are drawn as lit paths",
          {"KIT-T4", "KIT-T1"} <= set(rcp["ids"]["fixture-id"]) and kit_t4["path_ft"] and kit_t1["path_ft"] and kit_t1["type"] == "TASK_LO"
          and "K-2" in rcp["text"] and "KIT-T4" in rcp["text"])
    check("OPT-1 rcp: generic-optics estimate label shown; no heat map or numerical lighting results drawn",
          "Generic-optics analytic estimates" in rcp["text"] and "not measured or manufacturer-validated" in rcp["text"]
          and "heat map" not in rcp["text"].lower() and "no photometry is shown" in rcp["text"])
check("rcp: conditional details drawn (raised-centre product fit/access, curtain pocket two tracks)",
      all(k in rcp["text"] for k in ["CONDITIONAL DETAILS", "separate gypsum/POP panel", "product fit", "access", "track 1: sheer", "track 2: blackout"]))
check("rcp and living elevation: raised centre is a separate gypsum/POP panel; depth and level unmeasured; cutting not authorised",
      all(k in txt for txt in [rcp["text"], by_id["03-elev-R01-living"]["dom"]["text"]]
          for k in ["separate gypsum/POP panel", "unmeasured", "No slab chase or structural cutting is authorised"]))

# elevations
elev_open, elev_items, elev_storage = set(), set(), set()
for r in elev:
    d, drawn = r["dom"], r["sheet"]["drawn"]
    check(f"{r['sheet']['id']}: DOM panels = generator panels", d["ids"]["panel-id"] == sorted(set(drawn["panels"])), [d["ids"]["panel-id"], drawn["panels"]])
    elev_open |= set(d["ids"]["opening-id"])
    elev_items |= set(d["ids"]["item-id"])
    elev_storage |= set(d["ids"]["storage-id"])
all_open = {o["id"] for o in V["openings"]}
check("elevations: every master opening appears on at least one elevation", all_open <= elev_open, sorted(all_open - elev_open))
plan_items = set(plan["ids"]["item-id"]) - {i for i in plan["ids"]["item-id"] if i.startswith("TENANT-BED")}
plan_only = sorted((plan_items | set(plan["ids"]["storage-id"])) - elev_items - elev_storage)
check("elevations: every drawn storage record appears on an elevation", set(plan["ids"]["storage-id"]) <= elev_storage, sorted(set(plan["ids"]["storage-id"]) - elev_storage))
check("elevations: no superseded R04 record", not set(sup) & (elev_items | elev_storage))
check("elevations: tenant beds appear as envelopes on the bedroom elevations", {"TENANT-BED-R04", "TENANT-BED-R05"} <= elev_items)
for r in sheet_results:
    t = r["dom"]["text"]
    check(f"{r['sheet']['id']}: 'unmeasured' and 'assumed' wording present", "unmeasured" in t.lower() and "assumed" in t.lower())
for r in elev:
    check(f"{r['sheet']['id']}: master SHA in footer", master_sha in r["dom"]["text"])
    check(f"{r['sheet']['id']}: north arrow present", "sheet-bottom" in r["svg"])
liv = by_id["03-elev-R01-living"]
check("living elevation: titled as the east-wall pooja niche at the NE corner beside the main door",
      "Living \u2013 east wall: pooja niche at NE corner beside main door" in liv["dom"]["text"] and liv["dom"]["ids"]["detail"] == ["pooja-niche"])
check("living elevation: pooja-niche opening drawn and H-CENTRE-RECESS noted", "pooja-niche" in liv["dom"]["ids"]["opening-id"] and "H-CENTRE-RECESS" in liv["dom"]["text"])
check("living elevation: HD-16 estimates and reported extension, without a structural section",
      all(k in liv["dom"]["text"] for k in ["HD-16", "homeowner estimates", "No surveyed extension section",
          f'{V["pooja"]["depthMm"]:g}' + " mm", "OI-POOJA-01"]) and "plan section" not in liv["dom"]["text"])
master_sheet = by_id["06-elev-R04-master"]["dom"]["text"]
check("master elevation: W03 wording", "centred (homeowner-confirmed); offsets unmeasured" in master_sheet and "H-MBR-W03" in master_sheet)
check("master elevation: tenant bed wording", "tenant's bed" in master_sheet and "queen to king envelope" in master_sheet)
check("children elevation: only recorded switch zone drawn", by_id["08-elev-R05-children"]["sheet"]["drawn"]["switchStrip"] is not None)
cbr_text = by_id["08-elev-R05-children"]["dom"]["text"]
check("children elevation: curtain top is the assumed HD-11 drawing level; the retired 2.64 m appears only as retired",
      "assumed HD-11 drawing top" in cbr_text and "2.94 assumed" in cbr_text and cbr_text.count("2.64") == cbr_text.count("legacy 2.64 m retired"))

with pymupdf.open(pdf_path) as pdf:
    pdf_text = [p.get_text() for p in pdf]
    expected_headings = [
        "Furnished floor plan \u2014 top-down",
        "Reflected ceiling plan \u2014 bottoms-up",
        *[s["title"].replace("Elevations \u2014 ", "Interior elevations \u2014 ", 1)
          for s in manifest["sheets"][2:]]]
    check("pdf: 13 pages in plan -> RCP -> elevation order", len(pdf) == 13 and all(
        t.startswith(heading + "\n") and f"SHEET {i + 1} / 13" in t
        for i, (t, heading) in enumerate(zip(pdf_text, expected_headings))))
    check("pdf: master SHA is searchable on every page", all(master_sha in t for t in pdf_text))
    check("pdf: sheet titles searchable", all(any(k in t for t in [pdf_text[i]]) for i, k in enumerate(
        ["Furnished floor plan", "Reflected ceiling plan"] + [f"Interior elevations" for _ in range(11)])))
    pdf_pages = [[round(c, 1) for c in p.rect] for p in pdf]

with pymupdf.open(pdf_path) as pdf:
    room_titles = [s["title"] for s in manifest["sheets"][2:]]
    check("pdf: bookmarks list every sheet", pdf.get_toc() == [
        [1, s["title"], i + 1] for i, s in enumerate(manifest["sheets"])])

live = None
live_diff = None
if args.live and args.live.exists():
    live = sha(args.live)
    live_house = json.loads(args.live.read_bytes().decode("utf-8-sig"))
    # sections that drive the drawings, compared as parsed JSON (key order and whitespace ignored)
    drawn_from = {"architecture": lambda h: h["architecture"], "visualization_geometry": lambda h: h["visualization_geometry"],
                  "bathrooms": lambda h: h["bathrooms"], "lighting": lambda h: h["lighting"],
                  "storage.items": lambda h: h["storage"]["items"], "decisions.bedrooms": lambda h: h["decisions"]["bedrooms"],
                  "storage.item_applicability": lambda h: h["storage"].get("item_applicability"),
                  "decisions.warning_resolution": lambda h: h["decisions"].get("warning_resolution"),
                  "decisions.r05_clearance": lambda h: h["decisions"].get("r05_clearance"),
                  "open_items": lambda h: h["open_items"]}
    live_diff = {k: ("unchanged" if f(house) == f(live_house) else "CHANGED") for k, f in drawn_from.items()}

live_note = ""
if live and live != master_sha:
    live_note = (f"- The live master has since moved to `{live}`. Compared as parsed JSON against the bound master: "
                 + "; ".join(f"{k} {v}" for k, v in live_diff.items())
                 + ". This set is deliberately **not** re-bound; rerun the generator with the new SHA to rebind.\n")

# ---------------------------------------------------------------- README
corr_path = args.master.parent / "generated" / "open-item-compass-correction-receipt.json"
corr = json.loads(corr_path.read_text(encoding="utf-8-sig")) if corr_path.exists() else None
corr_note = ("- This master is a text-only open-item correction: compass wall names in OI-MBR-01/03/04 and OI-UTL-01, "
             "fixed bedside cabinets confirmed omitted (HD-14), and the unsupported loft-load figure removed from OI-R05-04. "
             "Geometry and lighting are unchanged, so these sheets differ only in the bound source hash; see `open_item_compass_correction` in the receipt.\n"
             ) if corr and corr.get("after_master_sha256") == master_sha else ""
sheets_md = "\n".join(f"| {i + 1} | {s['title']} | `{s['id']}.svg` / `.png` |" for i, s in enumerate(manifest["sheets"]))
readme = f"""# {"Layout views (read-only) - REVIEW DRAFT, not construction released" if args.review_draft else "Current layout views (read-only)"}

Drawn only from the canonical master `house-design.json`, sha256 `{master_sha}`.
{drawing_source["publication_status"]}
{"This is a new review edition on the integrated OPT-1 lighting master; the earlier published set (bound to master 124ef698) is a separate folder and is not overwritten or superseded by it." + chr(10) if args.review_draft else ""}Nothing here edits the master, adds a design decision or replaces a drawing in it. Not a construction release.
Sheet drawings are south-up: the page is **not rotated**, and the north arrow on every sheet points to the bottom of the page.

**Look and feel.** This is the original sheet style (the same 13 sheets, "Sheet n / 13" headers, pastel room fills, right-hand schedule/legend/notes). The later "drafter" redesign was rejected by the homeowner and is archived, not used. The roll-back is style only: the data underneath is the current finalised layout (HD-11 levels, current lighting, compass names). The original layout is retired (HD-13) and is not used as a source.

## Sheets (also merged, in this order, into `current-layout-views.pdf`)

| # | Sheet | Files |
|---|---|---|
{sheets_md}

1. **Top-down** = a colour-filled furnished plan with room names, recorded nominal sizes, walls, door swings, windows, the parapet opening, stairs, lift and essential furniture/storage.
2. **Bottoms-up** = the reflected ceiling plan: the ~9 in perimeter band, unmeasured raised centre and pocket details, lofts, fan points and all {fixture_count} base fixtures in {circuit_count} groups. Four selected 2700 K curtain strips bring the review count to 108 fittings / 51 circuits; the paths are indicative and clipped to the shown room, with no added knob or photometry credit. K-2 is selected for review; product, fit and construction holds remain. Hold marks (CR, HB, DS, PG) indicate conditional fittings.
3. **All walls** = interior elevations of every wall of every room, each with a key plan and a view arrow. The living east-wall sheet carries the pooja niche PN1 and an enlarged niche detail.

## How to read the compass
- Source: `visualization_geometry.orientation`: approximate homeowner north, not a surveyed true bearing. The entrance/balcony/stairs side faces **NORTH**.
- Sheet-top = South, sheet-bottom = North, sheet-left = East, sheet-right = West. Only the four cardinal directions are recorded; true bearing and magnetic declination are not surveyed.
- Walls are named by compass ("Master bedroom - south wall (wardrobes, W03 bay)"). The small grey tags such as `master-s` are only drawing IDs.

## What is real, what is assumed
- Room sizes come from the finalised master layout. **Most opening offsets are inherited or placeholder** values: every window/door is drawn at a "modelled plan position; not site verified", and a dagger (†) marks openings that are assumed, placeholder or centred-but-unmeasured.
- **Every level remains unsurveyed.** The homeowner reports the R05 band at 3.048 m and the centre approximately 3.277 m; the actual slab height and cavity are unmeasured, and the reported centre conflicts with the older slab estimate. Elsewhere, the homeowner-stated 11 ft floor-to-floor and ~9 in band drop, with assumed slab and finish thicknesses, yield older references of about 3.19 m slab underside and 2.959 m band (HD-11); the raised-panel level and cavity depth are unmeasured (HD-14). Bathrooms, utility, lobby and balcony levels and opening heads/sills are placeholders. The hall cross-beam soffit is unmeasured (H-HALL-BEAM). Verify all levels on site.
- The **loft** top of 3.08 m is an unmeasured legacy placeholder and is not raised to the slab (H-LOFT). The old 2.64 m curtain top is retired; 2.939 m is used only as an assumed HD-11 drawing top for the children's curtain, not measured hardware.
- Items whose height is not in the master (sofa, TV unit, tenant beds and so on) are drawn only as footprints below the floor line. No height was invented. Wall cabinets show a bottom of 1.45 m and no top.
- **Pooja niche PN1 (HD-16 / HD-18)** is already built at the north end of the living east wall. Its relationship is homeowner-confirmed, but the {V["pooja"]["widthMm"]} mm width, {V["pooja"]["heightMm"]} mm opening height, {V["pooja"]["sillM"]} m sill, {V["pooja"]["depthMm"]} mm depth and modeled position are **homeowner estimates, not site measurements**. {drawing_source["note"]} The homeowner reports a reinforced slab extension beyond the 9-inch wall, top to bottom through the building; its geometry and capacity are unverified. The model does not contain this extension. Only the estimated front outline and dimensions are shown: **no physical back or structural cross-section is drawn**. This model mismatch does not establish that the existing niche is unsafe or impossible. Confirm dimensions, support/capacity and balcony-edge relation on site (OI-POOJA-01). No cutting or deepening is requested or approved; no finishes or frame construction are newly selected.
- **W03** (master south window) is "centred (homeowner-confirmed); offsets unmeasured"; its curtain pocket is held (H-MBR-W03). **W05** (children's west window) is still a visual placeholder, concealed behind its curtain.
- Tenants bring their own beds: beds are dashed "tenant's bed - queen to king envelope" (1524-1829 x 1981 mm mattress), not joinery and not a tested frame (the 1.68 x 2.13 frame is not drawn). **Fixed bedside cabinets are omitted by the homeowner (HD-14: ST-R04-NS01, ST-R04-NS02, ST-R05-NS01)**; no optional outline is drawn and tenants may use movable tables. Room and bed positions are unchanged. The master's built queen bed is not drawn; the master bed position is a held test centreline (H-MBR-BED).
- **R05 clearance (HD-15):** keep the finalized room and furniture positions. The approximately {RC["estimated_clearance_mm"]} mm bed-foot/study-return clearance is a **site-check pinch, not a comfortable walking route**. Measure the actual tenant bed frame, fixed return and unobstructed route on site (OI-R05-03); no furniture relocation is authorised.
- The only switch zone in the master is the children's latch-side switch board (1.06-1.785 m along the south wall). No other switch plates are drawn because none are recorded.
- Retired wardrobe/joinery footprints are excluded: five superseded ST-R04 records are suppressed. The split wardrobe is approved in principle, but the hatched zones and interiors are unmeasured. Dressing and utility cabinets are selected conditionally, subject to FH-ST-03 / FH-ST-12 checks.
- **Lighting:** {lighting_note} CBR-H1 to H6 and its curtain strip are selected for review; the remaining CBR fittings are held and faded. C37 procurement remains held. Other holds include H-CENTRE-RECESS, H-HALL-BEAM, H-DRS-SWEEP, H-MBR-W03, H-MBR-BED and H-LOFT.
- **Raised centre (HD-14):** a separate gypsum/POP panel below the concrete slab. The homeowner confirms space will be provided for the aluminium profile/track and wiring; clear cavity depth, panel level, profile recess/fixing dimensions, wiring access and driver location are unmeasured. No categorical "no void / no space" claim is made.
- **Curtains (HD-14):** the living, master and children's rooms have two layers (sheer + blackout) on ceiling-mounted tracks concealed in recessed pockets, so each pocket needs two tracks. Pocket outlines on the RCP and elevations are indicative only; clear width, depth, track spacing and stack are unverified and no enlarged pocket is assumed.
- Curtain pockets are recessed two-track pockets, not rods. Four selected strips are shown at 2700 K on the existing LOW controls; W03 remains held. Pocket sizes, returns and feed access are unmeasured and need a site mock-up.
- Assumed MBR-S and CBR strip returns each extend about 0.30 m beyond the model room corner; paths are clipped for display only. Measure actual pocket ends and coordinate a site-fit solution; do not extend or cut from the model.
- D01 is a single leaf in the model while the architectural description says double leaf. Confirm the existing entrance and swing on site.

## Source status
- Bound master: `{master_sha}` (the file was only read).
{corr_note}{live_note}
## Not elevated (and why)
- Open edges have no wall record, so no wall is invented: living-south, dining-north (open to each other), the lobby's east edge, and the balcony's west/north/east edges. Each is noted on its sheet.
- The lift shaft is not elevated (no interior finish data).
- Plan-only items (no elevation face): {', '.join(plan_only) if plan_only else 'none'}.
- Not drawn on the plan: {', '.join(not_drawn_storage)} (tenant-supplied beds; bedside units omitted by the homeowner, HD-14).

## Re-running
```
python walkthrough\\render_layout_views.py --master <house-design.json> --out <this folder> --sha <expected master sha256> [--live <live master>] [--staging | --review-draft]
```
It refuses to draw if the master hash is not the expected one, then rebuilds every SVG, PNG and the PDF and rewrites the receipt.
PNGs are 2x; the PDF is vector and text-searchable (PDF timestamps differ between runs, SVG and PNG are reproducible).

`layout-views-verification.json` is the receipt: source hash, artifact hashes, sheet list, render checks (zero errors, no text outside the page, no network requests, drawn ids reconciled against the master) and the generator hashes.
`sheets.json` is the generator's per-sheet manifest of what was drawn.
"""
(out / "README.md").write_text(readme, encoding="utf-8")

# ---------------------------------------------------------------- open-item compass correction
# Superseded OI wording (OI-MBR-01/03/04, OI-UTL-01, OI-R05-04) and sheet-letter wall labels must not reappear.
OBSOLETE_OI = ["Door v 0.16-1.01", "prefer >= 2.20", "Wardrobe wall N with W03", "headboard E with W04", "TV/door W;",
               "Topology-derived", "west-upper is the continuous wall", "north-utility return", "Compass not established",
               "re-place to N wardrobe", "N wardrobe / E headboard", "bedside and bay base are later holds",
               "MBR-rear pocket must follow", "bed head now E", "(sheet N)", "(sheet E)", "(sheet W)", "(sheet S)",
               "pre-compass wording"]
LOAD_FIGURE = re.compile(r"\d\s*kg\b|\bkg/m\b", re.I)
set_texts = {r["sheet"]["id"]: r["dom"]["text"] for r in sheet_results}
set_texts.update({f"pdf-page-{i + 1}": t for i, t in enumerate(pdf_text)})
set_texts["README.md"] = readme
if drawing_source["hd18"]:
    OBSOLETE_OI += ["TRUE NORTH", "Decimal-foot interpretation also needs confirmation", "Confirm the decimal-foot interpretation", "master 41.1 mm west interface"]
    check("HD-18: fragment-bound dimensions and derived height are shown with estimate qualifiers",
          all(t in liv["dom"]["text"] for t in ["HD-18", "0.4318", "1701.8", "381", "0.4064", "derived", "homeowner estimates"]),
          drawing_source["hd18"])
    check("HD-18: approximate homeowner north, not a surveyed true bearing, on every sheet",
          all("approximate homeowner north" in r["dom"]["text"] for r in sheet_results))
if args.staging:
    check("staging: every sheet marked NOT FINAL and lighting remains pending",
          all("STAGING - NOT FINAL" in r["dom"]["text"] for r in sheet_results)
          and drawing_source["staging"] and ("stale pending HD-18" in rcp["text"] if pending else True))
if args.review_draft:
    check("review draft: every sheet and the README marked REVIEW DRAFT, not construction released, on the OPT-1 integrated master",
          all("REVIEW DRAFT" in r["dom"]["text"] and "not a construction release" in r["dom"]["text"] for r in sheet_results)
          and drawing_source["review_draft"] and not drawing_source["staging"] and not pending and opt1
          and "REVIEW DRAFT" in (out / "README.md").read_text(encoding="utf-8"))
obsolete_hits = {k: [p for p in OBSOLETE_OI if p in t] + LOAD_FIGURE.findall(t) for k, t in set_texts.items()}
obsolete_hits = {k: v for k, v in obsolete_hits.items() if v}
check("open-item correction: superseded OI compass wording and loft-load figure absent from every sheet, PDF page and README",
      not obsolete_hits, obsolete_hits)
corr_block = None
if corr and corr.get("after_master_sha256") == master_sha:
    OI = {i["id"]: i for i in house["open_items"]["items"]}
    before_path = args.master.parent / "archive" / "before-open-item-compass-correction.json"
    before_ok = before_path.exists() and sha(before_path) == corr["before_master_sha256"]
    same = {}
    if before_ok:
        before = json.loads(before_path.read_bytes().decode("utf-8-sig"))
        for k in ["architecture", "visualization_geometry", "bathrooms", "lighting", "storage", "decisions"]:
            same[k] = before.get(k) == house.get(k)
        b_oi = {i["id"]: i for i in before["open_items"]["items"]}
        same["open_items_outside_corrected_ids"] = all(b_oi[k] == OI[k] for k in OI if k not in corr["corrected_open_items"]) and set(b_oi) == set(OI)
    r504, mbr03 = OI["OI-R05-04"]["issue"], OI["OI-MBR-03"]["issue"]
    texts_ok = (not LOAD_FIGURE.search(r504) and "allowable load are unmeasured" in r504 and "not a verified statutory minimum" in r504
                and "Fixed bedside cabinets are omitted by the homeowner (HD-14), not to be re-placed" in mbr03
                and all(not any(p in (OI[k].get("issue") or "") + (OI[k].get("resolution") or "") for p in OBSOLETE_OI)
                        for k in corr["corrected_open_items"]))
    check("open-item correction: receipt binds this master; drawn sections and other OIs byte-identical to the before-master; corrected texts confirmed",
          before_ok and all(same.values()) and texts_ok and corr["geometry_and_lighting_unchanged"] is True
          and corr["construction_release"] is False and sorted(corr["corrected_open_items"]) == sorted(
              ["OI-MBR-01", "OI-UTL-01", "OI-MBR-03", "OI-MBR-04", "OI-R05-04"]),
          {"before_found": before_ok, "unchanged": same, "texts_ok": texts_ok})
    corr_block = {"receipt": artifact(corr_path), "before_master_sha256": corr["before_master_sha256"],
                  "corrected_open_items": corr["corrected_open_items"], "sections_identical_to_before_master": same,
                  "obsolete_wording_absent": not obsolete_hits,
                  "note": "Text-only correction. These sheets do not quote the open-item register; geometry and lighting are unchanged, so drawn content is unchanged apart from the bound source hash."}

# ---------------------------------------------------------------- receipt
gens = {}
for f in [HERE / "layout_views.mjs", HERE / "drawing-source.mjs", *sorted((HERE / "layout_views").glob("*.mjs")),
          HERE / "src" / "master-adapter.js", HERE / "render_layout_views.py"]:
    gens[str(f.relative_to(HERE)).replace("\\", "/")] = sha(f)
node_v = subprocess.run(["node", "--version"], capture_output=True, text=True).stdout.strip()
sheet_rows = []
for r in sheet_results:
    s = r["sheet"]
    sheet_rows.append({
        "id": s["id"], "title": s["title"], "page_px": [r["w"], r["h"]], "png_scale": SCALE,
        "svg": artifact(out / s["file"]), "png": artifact(r["png"]),
        "counts": s["counts"], "svg_elements": r["dom"]["elements"], "svg_text_elements": r["dom"]["texts"],
        "pdf_page": next(i for i, (x, _) in enumerate(pdf_parts, 1) if x["id"] == s["id"])})
receipt = {
    "schema": "layout_views_receipt/1",
    "verified_utc": datetime.now(timezone.utc).isoformat(),
    "purpose": "Read-only current layout views (top-down plan, reflected ceiling plan, interior elevations) from the canonical master; not a construction release.",
    "drawing_source": drawing_source,
    "source_master": {"path": str(args.master), "sha256": master_sha, "bytes": len(master_bytes), "expected_sha256_matched": True},
    "live_master": ({"sha256": live, "same_as_bound": live == master_sha,
                     "drawn_sections_vs_bound_master": live_diff,
                     "note": ("Live master has moved past the bound master; this set is truthfully bound to the byte-identical archive above. "
                              "Sections compared in drawn_sections_vs_bound_master are unchanged unless marked CHANGED; rerun with the new SHA to rebind.") if live != master_sha else "identical"}
                    if live else None),
    "compass": {"read_from": "visualization_geometry.orientation", "evidence_status": V["orientation"]["evidence_status"],
                "sheet_to_compass": V["orientation"]["sheet_to_compass"], "true_north_vector_xz": V["orientation"]["true_north_vector_xz"],
                "scope": "cardinal directions only; true bearing and magnetic declination are not surveyed"},
    "heights": "HD-11: homeowner-stated or derived, all unmeasured (decisions.ceiling_heights); bath/utility/lobby/balcony not provided; heads and sills assumed",
    "hd14": {"decision": WR["decision"], "construction_release": WR["construction_release"],
             "bedside_units_omitted_not_drawn": sorted(hd14_omitted),
             "curtains": "two tracks (sheer + blackout) in LIV, MBR, CBR; pocket sizes unverified, none invented",
             "raised_centre": "separate gypsum/POP panel below the slab; clear cavity depth and panel level unmeasured; conditional product-fit/access detail only; no slab chasing or structural cutting authorised"},
    "hd15": {"decision": RC["decision"], "geometry_changed": RC["geometry_changed"],
             "estimated_clearance_mm": RC["estimated_clearance_mm"], "status": RC["status"], "recheck": RC["recheck"]},
    "open_item_compass_correction": corr_block,
    "lighting_status": lighting_note,
    "canonical_lighting_status": lighting["status"],
    "lighting_design_inputs_sha256": lighting["calculation_validity"]["design_inputs_sha256"],
    "lighting_selection": {"kitchen_worktop": k2, "fixtures": fixture_count, "controlled_groups": circuit_count,
                           "construction_release": lighting["calculation_validity"]["construction_release"],
                           "product_approval": lighting["calculation_validity"]["product_approval"],
                           "photometry_basis": lighting["calculation_validity"]["basis"]},
    "style": "original sheet theme restored (HD-12 style-only rollback); layout data is the current finalised master; original layout retired (HD-13), not used",
    "pooja_niche": {"built_status": pn["built_status"], "location": V["pooja"]["location_src"],
                    "dimensions": pn["dimensions"], "geometry_hold": pn["geometry_hold"],
                    "outside_wall_extension": pn["existing_construction"]["outside_wall_extension"],
                    "representation": "estimated front outline only; no physical back or structural section drawn",
                    "reinforcement": "homeowner-reported, not structurally certified", "new_cutting_requested": pn["existing_construction"]["new_cutting_requested"]},
    "sheets": sheet_rows,
    "combined_pdf": {**artifact(pdf_path), "pages": 13, "page_points": pdf_pages, "searchable": True, "order": "plan, RCP, elevations by room"},
    "readme": artifact(out / "README.md"),
    "manifest": artifact(out / "sheets.json"),
    "reconciliation": {
        "plan": {"rooms": len(plan["ids"]["room-id"]), "walls": len(plan["ids"]["wall-id"]), "openings": len(plan["ids"]["opening-id"]),
                 "storage_drawn": len(plan["ids"]["storage-id"]), "storage_superseded_suppressed": sup,
                 "storage_not_drawn_tenant_beds": not_drawn_storage, "tenant_bed_envelopes": 2,
                 "furniture_items_drawn": len([i for i in plan["ids"]["item-id"] if not i.startswith(("TENANT", "BATH"))])},
        "rcp": {"fixtures": len(rcp["ids"]["fixture-id"]), "circuits": circuit_count, "circuit_ids": circuit_ids,
                "held_CBR_fixtures_drawn_faded": len(rcp["inactiveFixtureIds"]),
                "selected_curtain_strips": rcp["ids"]["curtain-strip"], "review_fittings": 108, "review_circuits": 51,
                "count_load_only_allowances": rcp["allowanceFixtureIds"], "bathroom_face_bar_ids": face_ids,
                "hold_marks": rcp["ids"]["hold-fixture"],
                "fans": rcp["ids"]["fan-room"], "curtain_pockets": rcp["ids"]["curtain-pocket"]},
        "elevations": {"sheets": len(elev), "panels": sum(len(r["sheet"]["drawn"]["panels"]) for r in elev),
                       "open_edges_not_elevated": sum(len(r["sheet"]["drawn"]["openPanels"]) for r in elev),
                       "openings_covered": len(all_open & elev_open), "master_openings": len(all_open),
                       "plan_only_items_with_no_elevation_face": plan_only},
        "master_counts": {"rooms": len(V["rooms"]), "walls": len(V["walls"]), "openings": len(V["openings"]),
                          "storage_records": len(storage), "lighting_fixtures": len(fx_ids), "fans": len(V["fans"])}},
    "render": {"browser": "headless Edge " + edge_version, "python": platform.python_version(), "node": node_v,
               "page_errors": page_errors, "console_errors": console_errors, "http_requests": http_requests,
               "out_of_page_text": {r["sheet"]["id"]: r["dom"]["outside"] for r in sheet_results if r["dom"]["outside"]},
               "text_overlaps": overlaps},
    "checks": checks,
    "checks_passed": sum(c["ok"] for c in checks), "checks_total": len(checks),
    "generators": gens,
    "pdf_note": "PDF carries creation timestamps; SVG/PNG are reproducible from the same master and generators."}
receipt_path = out / "layout-views-verification.json"
assert args.master.read_bytes() == master_bytes, "Bound master changed during rendering; regenerate with the new SHA."
receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
print(json.dumps({"checks": f"{receipt['checks_passed']}/{receipt['checks_total']}", "receipt_sha256": sha(receipt_path),
                  "pdf_sha256": receipt["combined_pdf"]["sha256"], "failures": failures}, indent=1))
sys.exit(1 if failures else 0)
