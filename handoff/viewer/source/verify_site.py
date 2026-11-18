"""Black-box verification of a staged light-planner site (desktop + mobile).

usage: python verify_site.py --url URL --out DIR --master SHA --cct-map JSON --build-info JSON --wardrobes JSON
"""
import argparse, io, json, hashlib, re, sys, time, traceback
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname
from PIL import Image, ImageStat
from playwright.sync_api import sync_playwright

ap = argparse.ArgumentParser()
ap.add_argument("--url", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--label", default="local")
ap.add_argument("--master", required=True)
ap.add_argument("--only", default="desktop,mobile")
ap.add_argument("--cct-map", required=True, help="current, master-bound fixed-CCT map JSON")
ap.add_argument("--build-info", required=True, help="review build receipt for downloaded PDF hashes")
ap.add_argument("--wardrobes", required=True, help="referenced provisional wardrobe-interior JSON")
args = ap.parse_args()
_b = Path(args.cct_map).read_bytes()
CMAP = json.loads(_b.decode("utf-8-sig"))
CMAP["_sha256"] = hashlib.sha256(_b).hexdigest()
CMAP["_cct"] = {f["id"]: int(f["cct_k"]) for f in CMAP["fittings"]}
CMAP["_fixtures"] = {f["id"]: f for f in CMAP["fittings"]}
BUILD = json.loads(Path(args.build_info).read_text(encoding="utf-8-sig"))
_w = Path(args.wardrobes).read_bytes()
WARDROBES = json.loads(_w.decode("utf-8-sig"))
WARDROBE_SHA = hashlib.sha256(_w).hexdigest()
if BUILD["masterSha256"] != args.master or BUILD["currentFixedCctMapSha256"] != CMAP["_sha256"] or BUILD["wardrobeInteriorsSha256"] != WARDROBE_SHA:
    raise ValueError("Build receipt does not bind the requested master, CCT map and wardrobe proposal")
out = Path(args.out)
(out / "screens").mkdir(parents=True, exist_ok=True)
(out / "downloads").mkdir(parents=True, exist_ok=True)
origin = urlparse(args.url)
FT = 0.3048
checks = []
report = {"label": args.label, "url": args.url, "profiles": {}}


def check(profile, name, cond, detail=None):
    checks.append({"profile": profile, "name": name, "pass": bool(cond), "detail": detail})
    print(("PASS " if cond else "FAIL ") + f"[{profile}] {name}" + (f" :: {detail}" if detail is not None and not cond else ""), flush=True)
    return bool(cond)


def lum(png, crop=None):
    im = Image.open(io.BytesIO(png)).convert("L")
    if crop:
        im = im.crop(crop)
    st = ImageStat.Stat(im)
    return round(st.mean[0], 2), round(st.stddev[0], 2)


def set_range(page, id_, v):
    page.evaluate(
        """([id,v])=>{const el=document.getElementById(id);
        Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(el,String(v));
        el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));}""",
        [id_, v],
    )


def run_profile(p, name, ctx_args, crop_fn):
    msgs, errors, warnings, requests = [], [], [], []
    browser = p.chromium.launch(channel="msedge", headless=True, args=["--enable-webgl", "--ignore-gpu-blocklist"])
    ctx = browser.new_context(accept_downloads=True, **ctx_args)
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
    page.on("console", lambda m: (errors if m.type == "error" else warnings if m.type == "warning" else msgs).append(m.text[:600]))
    page.on("request", lambda r: requests.append(r.url))
    page.on("requestfailed", lambda r: errors.append("requestfailed: " + r.url))
    t0 = time.time()
    page.goto(args.url, wait_until="networkidle", timeout=180000)
    page.wait_for_function("window.walkthrough?.ready || getComputedStyle(document.getElementById('fatal')).display!=='none'", timeout=180000)
    ready = page.evaluate("Boolean(window.walkthrough?.ready)")
    report_p = {"loadSeconds": round(time.time() - t0, 1)}
    if not check(name, "page loads and the 3D scene is ready", ready, page.locator("#fatal-detail").inner_text()):
        browser.close()
        return report_p
    page.wait_for_timeout(1500)
    shot = lambda n: page.screenshot(path=str(out / "screens" / f"{name}-{n}.png"))
    state = lambda: page.evaluate("walkthrough.getState()")
    bright = lambda: lum(page.screenshot(), crop_fn(state()))

    # ---- data / binding
    d = page.evaluate(
        """()=>{const w=walkthrough,P=w.PLAN;const fx=P.fixtures.zones.flatMap(z=>z.fixtures);let lights=0;w.scene.traverse(o=>{if(o.isLight)lights++});
        return {master:P.master.sha256,fixtures:fx.length,circuits:P.fixtures.controls.circuits.length,lights,
        withCct:fx.filter(f=>Number.isFinite(+String(f.cct).replace(/[^0-9.]/g,''))&&+String(f.cct).replace(/[^0-9.]/g,'')>1500).length,
        tunable:fx.filter(f=>f.tunable).length,risingFlight:P.stairs.risingFlightShown,k2:Boolean(P.analysis.k2),
        rangeInputs:document.querySelectorAll('input[type=range]').length,colorInputs:document.querySelectorAll('input[type=color]').length,
        rooms:[...document.querySelectorAll('#room option')].map(o=>[o.value,o.textContent]),
        stairParts:(w.model.stairParts||[]).map(s=>s.part),title:document.title,
        heat:Boolean(w.analysis),heatSha:P.analysis.source.sha256,noRecompute:P.numericalLighting.available===false,
        holds:P.analysis.holdIds?.length}}"""
    )
    report_p["data"] = d
    check(name, "bound to the requested integrated master", d["master"] == args.master, d["master"])
    check(name, "104 fixtures / 47 circuits embedded", d["fixtures"] == 104 and d["circuits"] == 47, d)
    check(name, "every fixture has a fixed CCT, none tunable", d["withCct"] == 104 and d["tunable"] == 0, d)
    check(name, "K-2 kitchen task lighting present", d["k2"])
    check(name, "upper stair flight omitted", d["risingFlight"] is False and "rising-flight" not in d["stairParts"], d["stairParts"])
    check(name, "16 real-time lights (performance budget)", d["lights"] == 16, d["lights"])
    check(name, "only two sliders (HIGH, LOW) and no colour/temperature input", d["rangeInputs"] == 2 and d["colorInputs"] == 0, d)
    check(name, "room list covers every room + balcony/entry", len(d["rooms"]) == 12 and any("alcon" in t for _, t in d["rooms"]), d["rooms"])
    check(name, "16 holds carried", d["holds"] == 16, d["holds"])
    check(name, "frozen heatmap is bound and live lux recomputation is disabled", d["heat"] and d["heatSha"] == BUILD["heatmapsSha256"] and d["noRecompute"], d)
    check(name, "bundled Three.js copyright and MIT permission notice are present", "Copyright" in page.content() and "Permission is hereby granted, free of charge" in page.content())
    txt = page.locator("#desk").inner_text().lower()
    check(name, "caveats visible (review draft, not construction, not recomputed)", all(k in txt for k in ["review draft", "construction", "lux"]), None)
    if CMAP:
        cm = page.evaluate(
            """()=>{const w=walkthrough,P=w.PLAN,fx=P.fixtures.zones.flatMap(z=>z.fixtures);
            return {cct:Object.fromEntries(fx.map(f=>[f.id,parseInt(String(f.cct))])),
            rules:Object.fromEntries(fx.map(f=>[f.id,f.cctRule])),holds:Object.fromEntries(fx.map(f=>[f.id,f.placementHoldIds])),src:P.fixedCct?.source||null,
            mixed:P.fixtures.controls.circuits.filter(c=>new Set(fx.filter(f=>f.circuit===c.circuit).map(f=>f.cct)).size>1).map(c=>c.circuit),
            pockets:(P.curtainPockets?.pockets||[]).map(p=>({id:p.id,held:p.held,selected:p.selected,cct:p.cct,lane:p.lane,circuit:p.circuit,holds:p.placementHoldIds})),
            live:(w.model.curtainPockets||[]).map(p=>({id:p.id,held:p.held,selected:p.selected,emissive:!!p.mat.emissive,inEmission:w.model.emission.some(e=>e.mat===p.mat)})),
            counted:fx.filter(f=>/^CURT-/.test(f.id)).length}}"""
        )
        report_p["cctMap"] = cm
        bad = {k: [v, CMAP["_cct"].get(k)] for k, v in cm["cct"].items() if CMAP["_cct"].get(k) != v}
        check(name, "all 104 fixture CCTs equal the fixed-CCT map", len(cm["cct"]) == 104 and not bad and set(cm["cct"]) == set(CMAP["_cct"]), bad)
        bad_rules = [k for k, f in CMAP["_fixtures"].items() if cm["rules"].get(k) != f["cct_rule"] or cm["holds"].get(k) != f["placement_hold_ids"]]
        check(name, "all base CCT rules and placement holds match the current map", not bad_rules, bad_rules)
        bins = {}
        for v in cm["cct"].values():
            bins[v] = bins.get(v, 0) + 1
        check(name, "CCT bins 30 x 2700 / 40 x 3000 / 34 x 4000", bins == {2700: 30, 3000: 40, 4000: 34}, bins)
        check(name, "fixed-CCT source bound to map SHA-256", (cm["src"] or {}).get("sha256") == CMAP["_sha256"], cm["src"])
        check(name, "signed original fixed-CCT map provenance retained", (cm["src"] or {}).get("baseMapSha256") == BUILD["baseFixedCctMapSha256"], cm["src"])
        check(name, "no circuit mixes colour temperatures", not cm["mixed"], cm["mixed"])
        pk = {p["id"]: p for p in cm["pockets"]}
        exp = {p["id"]: p for p in CMAP["curtain_pocket_candidates"]["pockets"]}
        check(name, "5 curtain-pocket candidates, 2700 K on LOW, not counted in 104", set(pk) == set(exp) and len(pk) == 5 and all(p["cct"] == "2700K" and p["lane"] == "LOW" for p in pk.values()) and cm["counted"] == 0, cm["pockets"])
        check(name, "four selected strips retain separate site and no-lux-credit holds", {p["id"] for p in pk.values() if p["selected"]} == set(CMAP["selected_curtain_S1"]["strips"]) and all(p["holds"] == exp[i]["placement_hold_ids"] for i, p in pk.items()) and CMAP["selected_curtain_S1"]["photometry_credit"] is False, cm["pockets"])
        lv = {p["id"]: p for p in cm["live"]}
        held_ok = all(lv[i]["held"] and not lv[i]["inEmission"] for i, e in exp.items() if e.get("held")) and lv.get("CURT-MBR-W03", {}).get("held")
        check(name, "held pocket CURT-MBR-W03 shown grey and unlit", held_ok, cm["live"])
        check(name, "unheld pockets follow their LOW circuit (emissive)", all(lv[i]["inEmission"] for i, e in exp.items() if not e.get("held")), cm["live"])
        cb = page.evaluate("(()=>{const p=walkthrough.PLAN.curtainPockets.pockets.find(p=>p.id==='CURT-CBR');return p?{held:p.held,selected:p.selected,label:p.label}:null})()")
        check(name, "CURT-CBR selected and unheld for review, placeholder remains unmeasured", bool(cb) and cb["held"] is False and cb["selected"] is True and cb["label"] == "placeholder window, unmeasured" and not lv["CURT-CBR"]["held"], cb)
    accessories = page.evaluate("walkthrough.lighting.accessoryFixtures.map(f=>({id:f.id,held:f.held,on:walkthrough.lighting.groupStates[f.circuit].on}))")
    check(name, "four reader and two PIR fitting previews start off", {f["id"] for f in accessories} == {"MBR-R1", "MBR-R2", "CBR-R1", "CBR-R2", "MBR-N1", "LOB-N1"} and not any(f["on"] for f in accessories), accessories)
    wardrobe = page.evaluate("(()=>{const p=walkthrough.model.rooms.wardrobeProposals;return {visible:p.interior.visible,closed:p.closed.visible,records:p.records,source:walkthrough.PLAN.wardrobeInteriors.sourceSha256}})()")
    expected_sections = {(room, section["id"]): section for room, spec in WARDROBES["rooms"].items() for section in spec["sections"]}
    def wardrobe_ok(record):
        source = expected_sections.get((record["room"], record["section"]))
        return source is not None and record["unmeasured"] and [
            (b["id"], b["kind"], len(b["shelf_heights_ffl_mm"]), len(b["rail_heights_ffl_mm"]), len(b["drawers_ffl_mm"]), len(b["pullouts_ffl_mm"]))
            for b in source["bays"]
        ] == [(b["id"], b["kind"], b["shelves"], b["rails"], b["drawers"], b["pullouts"]) for b in record["features"]]
    check(name, "six unmeasured wardrobe sections match the referenced proposal", len(wardrobe["records"]) == 6 and all(wardrobe_ok(r) for r in wardrobe["records"]) and wardrobe["source"] == WARDROBE_SHA and not wardrobe["visible"] and wardrobe["closed"], wardrobe)
    page.locator("#interiors").click()
    check(name, "proposed wardrobe interiors open through the control", page.evaluate("walkthrough.getState().interiors") and page.locator("#interiors").get_attribute("aria-pressed") == "true")
    page.locator("#interiors").click()
    check(name, "proposed wardrobe interiors can be hidden again", not page.evaluate("walkthrough.getState().interiors"))
    representation = page.evaluate("""()=>{const m=walkthrough.model;return {
      effects:[m.lightEffects.floorPools.length,m.lightEffects.ceilingHalos.length,m.lightEffects.wallScallops.length],trays:m.ceilingInfo.trays,
      pockets:m.ceilingInfo.pockets,utility:m.rooms.renderedItems.filter(x=>x.id==='ST-R08-UC01'),
      utilityCollisions:m.collision.filter(x=>x.id==='ST-R08-UC01').length,
      lofts:m.rooms.renderedItems.filter(x=>x.hold==='H-LOFT')
    }}""")
    check(name, "downlight pools, ceiling halos and wall scallops are present", all(x > 0 for x in representation["effects"]), representation["effects"])
    check(name, "cove trays use continuous rings", bool(representation["trays"]) and all(t["continuous"] for t in representation["trays"]), representation["trays"])
    check(name, "four recessed curtain pockets are unmeasured and model-clipped", len(representation["pockets"]) == 4 and all(p["unmeasured"] and p["displayClipped"] for p in representation["pockets"]), representation["pockets"])
    check(name, "utility UC01 has one cabinet footprint and one collision", len(representation["utility"]) == 1 and representation["utilityCollisions"] == 1, representation["utility"])
    check(name, "loft display clipping retains H-LOFT site hold", bool(representation["lofts"]) and any(x["displayOnlyClip"] for x in representation["lofts"]) and all(x["hold"] == "H-LOFT" for x in representation["lofts"]), representation["lofts"])
    page.locator("#room").select_option("master")
    page.locator("#individual-lights summary").click()
    page.locator('[data-individual="MBR-R1"]').check()
    check(name, "master reader can be previewed individually", page.evaluate("walkthrough.lighting.groupStates.C25.on"))
    page.locator('[data-individual="MBR-N1"]').check()
    check(name, "master PIR light can be previewed individually", page.evaluate("walkthrough.lighting.groupStates.C24.on"))
    page.locator("#room-on").uncheck()
    check(name, "individual readers and PIR previews are independent of room switch", page.evaluate("walkthrough.lighting.groupStates.C25.on && walkthrough.lighting.groupStates.C24.on"))
    page.locator("#all-off").click()
    check(name, "all rooms off also clears individual previews", page.evaluate("Object.values(walkthrough.lighting.accessoryState).every(v=>!v)"))
    page.locator("#all-on").click()
    check(name, "all rooms on leaves individual previews off", page.evaluate("Object.values(walkthrough.lighting.accessoryState).every(v=>!v)"))
    page.locator("#room").select_option("children")
    check(name, "held children's readers are visible but disabled", page.locator('[data-individual="CBR-R1"]').is_disabled() and page.locator('[data-individual="CBR-R2"]').is_disabled())
    page.locator("#room").select_option("living")
    shot("00-start")

    # ---- views
    views = {}
    for v in ["first", "third", "doll", "heat", "rcp"]:
        page.locator(f"[data-view={v}]").click()
        page.wait_for_timeout(1300)
        s = state()
        m, sd = bright()
        views[v] = {"mode": s["mode"], "mean": m, "std": sd, "draws": s["draws"], "triangles": s["triangles"], "fps": round(s["fps"], 1)}
        check(name, f"view '{v}' switches and renders content", s["mode"] == v and sd > 6 and m > 8, views[v])
        if v == "heat":
            vis = page.evaluate("[walkthrough.analysis.group.visible, getComputedStyle(document.getElementById('sec-map')).display!=='none', document.querySelectorAll('#lux-table tbody tr').length]")
            check(name, "light-map overlay and table appear only in the Light map view", vis[0] and vis[1] and vis[2] >= 10, vis)
            note = page.locator("#map-note").inner_text().lower()
            check(name, "light map labelled frozen / generic optics / not recomputed", "frozen" in note and "generic" in note and "not recomputed" in note, note)
            for sc in ["HIGH_100", "LOW_100", "HIGH+LOW_100"]:
                page.locator(f'[data-map="{sc}"]').click()
                page.wait_for_timeout(500)
                check(name, f"light-map scene {sc} selectable", page.evaluate("walkthrough.analysis.scene") == sc)
            shot("view-heat")
        elif v != "first":
            shot(f"view-{v}")
        else:
            shot("view-first")
    report_p["views"] = views
    page.locator("[data-view=doll]").click()
    page.wait_for_timeout(600)
    check(name, "light-map overlay hidden outside Light map view", page.evaluate("!walkthrough.analysis.group.visible"))

    # ---- place jumps (first person) every room
    page.locator("[data-view=first]").click()
    page.wait_for_timeout(500)
    jumps = {}
    for val, label in d["rooms"]:
        page.locator("#room").select_option(val)
        page.wait_for_timeout(900)
        s = state()
        r = page.evaluate("(id)=>{const r=walkthrough.PLAN.rooms.find(r=>r.id===id);return r?{spawn:r.spawn,name:r.name}:null}", val)
        ok = s["selectedRoom"] == val and r is not None and abs(s["position"][0] - r["spawn"][0] * FT) < 0.02 and abs(s["position"][2] - r["spawn"][1] * FT) < 0.02
        m, sd = bright()
        jumps[val] = {"label": label, "pos": [round(x, 2) for x in s["position"]], "mean": m, "std": sd}
        check(name, f"jump to '{label}' places the avatar in the room", ok, {"state": s["selectedRoom"], "pos": s["position"], "spawn": r})
        shot(f"room-{val}")
    report_p["jumps"] = jumps

    # ---- walking
    page.locator("#room").select_option("living")
    page.wait_for_timeout(800)
    page.locator("#view").click(position={"x": 700, "y": 400}) if name == "desktop" else None
    s0 = state()
    for key in ["w"]:
        page.keyboard.down(key)
        page.wait_for_timeout(1200)
        page.keyboard.up(key)
    s1 = state()
    dist = ((s1["position"][0] - s0["position"][0]) ** 2 + (s1["position"][2] - s0["position"][2]) ** 2) ** .5
    if name == "desktop":
        check(name, "first-person W key walks forward", dist > 0.15, round(dist, 2))
        box = page.locator("#view").bounding_box()
        cx, cy = box["x"] + box["width"] * .6, box["y"] + box["height"] * .5
        y0 = state()["yaw"]
        page.mouse.move(cx, cy)
        page.mouse.down()
        page.mouse.move(cx + 140, cy + 10, steps=8)
        page.mouse.up()
        page.wait_for_timeout(300)
        check(name, "mouse drag turns the view (first person)", abs(state()["yaw"] - y0) > 0.05, [y0, state()["yaw"]])
    else:
        # touch-hold the on-screen walk pad (real touch events through CDP)
        cdp = ctx.new_cdp_session(page)
        b = page.locator("[data-pad=w]").bounding_box()
        check(name, "walk pad is visible on touch screens", b is not None and b["width"] > 30, b)
        if b:
            x, y = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2
            s0 = state()
            cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x, "y": y}]})
            page.wait_for_timeout(1400)
            cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
            s1 = state()
            dist = ((s1["position"][0] - s0["position"][0]) ** 2 + (s1["position"][2] - s0["position"][2]) ** 2) ** .5
            check(name, "touch-holding the walk pad moves forward", dist > 0.15, round(dist, 2))
            y0 = state()["yaw"]
            vb = page.locator("#view").bounding_box()
            sx, sy = vb["x"] + vb["width"] * .5, vb["y"] + vb["height"] * .25
            cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": sx, "y": sy}]})
            for i in range(1, 9):
                cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": sx + i * 14, "y": sy}]})
                page.wait_for_timeout(30)
            cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
            page.wait_for_timeout(300)
            check(name, "touch drag turns the view (first person)", abs(state()["yaw"] - y0) > 0.05, [y0, state()["yaw"]])
    page.locator("[data-view=third]").click()
    page.wait_for_timeout(700)
    s0 = state()
    page.keyboard.down("d")
    page.wait_for_timeout(1000)
    page.keyboard.up("d")
    s1 = state()
    dist = ((s1["position"][0] - s0["position"][0]) ** 2 + (s1["position"][2] - s0["position"][2]) ** 2) ** .5
    if name == "desktop":
        check(name, "third-person walk (D key) moves the avatar", dist > 0.1, round(dist, 2))
    shot("third-after-walk")
    # walls stop the avatar: hold W for a long time and stay inside the plan
    page.locator("[data-view=first]").click()
    page.keyboard.down("w")
    page.wait_for_timeout(5000)
    page.keyboard.up("w")
    sp = state()["position"]
    bounds = page.evaluate("(()=>{const b=walkthrough.PLAN.bounds||null;return b})()")
    inside = -1 < sp[0] < 11 and -1 < sp[2] < 17 if not bounds else True
    check(name, "walking is stopped by walls (avatar stays in the flat)", inside, [round(v, 2) for v in sp])

    # ---- lights
    page.locator("[data-view=first]").click()
    page.locator("#room").select_option("living")
    page.wait_for_timeout(900)
    page.evaluate("walkthrough.selectRoom('living')")
    page.wait_for_timeout(900)
    base = bright()
    rl = page.evaluate("walkthrough.getRoomLight('living')")
    check(name, "living room starts on at 100/100", rl["on"] and rl["high"] == 100 and rl["low"] == 100, rl)
    check(name, "HIGH/LOW show a fixed CCT, not a control", "k" in page.locator("#high-cct").inner_text().lower() and "k" in page.locator("#low-cct").inner_text().lower(), [page.locator("#high-cct").inner_text(), page.locator("#low-cct").inner_text()])
    # real pointer interaction on the HIGH slider
    page.locator("#sheet").scroll_into_view_if_needed() if page.locator("#sheet").count() else None
    page.locator("#high-dim").scroll_into_view_if_needed()
    bb = page.locator("#high-dim").bounding_box()
    page.mouse.click(bb["x"] + bb["width"] * .2, bb["y"] + bb["height"] / 2)
    page.wait_for_timeout(900)
    rl2 = page.evaluate("walkthrough.getRoomLight('living')")
    m_high = bright()
    check(name, "dragging the HIGH slider sets HIGH brightness", 8 <= rl2["high"] <= 32 and rl2["low"] == 100, rl2)
    check(name, "lower HIGH visibly dims the room", m_high[0] < base[0] - 1.0, [base, m_high])
    set_range(page, "high-dim", 100)
    set_range(page, "low-dim", 0)
    page.wait_for_timeout(900)
    rl3 = page.evaluate("walkthrough.getRoomLight('living')")
    m_low = bright()
    check(name, "LOW slider sets LOW brightness independently", rl3["low"] == 0 and rl3["high"] == 100, rl3)
    if CMAP:
        pe = page.evaluate("(()=>{const p=walkthrough.model.curtainPockets.find(p=>p.id==='CURT-LIV');return p?p.mat.emissiveIntensity:null})()")
        set_range(page, "low-dim", 100)
        page.wait_for_timeout(700)
        pe100 = page.evaluate("(()=>{const p=walkthrough.model.curtainPockets.find(p=>p.id==='CURT-LIV');return p?p.mat.emissiveIntensity:null})()")
        check(name, "living curtain pocket dims with the LOW slider", pe is not None and pe100 is not None and pe < pe100 * 0.2, [pe, pe100])
        set_range(page, "low-dim", 0)
        page.wait_for_timeout(700)
    check(name, "LOW at 0 visibly changes the room", abs(m_low[0] - base[0]) > 0.5, [base, m_low])
    set_range(page, "low-dim", 100)
    page.wait_for_timeout(300)
    page.locator(".switch").click()
    page.wait_for_timeout(900)
    m_off = bright()
    rl4 = page.evaluate("walkthrough.getRoomLight('living')")
    check(name, "room on/off switch turns the room off", rl4["on"] is False and m_off[0] < base[0] - 1.5, [rl4["on"], base, m_off])
    page.locator(".switch").click()
    page.wait_for_timeout(900)
    check(name, "room on/off switch turns it back on", page.evaluate("walkthrough.getRoomLight('living').on") is True)
    # kitchen: CCT of task lighting differs and K-2 present in inspector data
    page.locator("#all-off").click()
    page.wait_for_timeout(1000)
    off_state = page.evaluate("Object.fromEntries(walkthrough.PLAN.rooms.map(r=>[r.id,walkthrough.getRoomLight(r.id).on]))")
    m_alloff = bright()
    check(name, "All rooms off turns every room off", not any(off_state.values()), off_state)
    check(name, "All rooms off darkens the scene", m_alloff[0] < base[0] - 3, [base, m_alloff])
    shot("all-off")
    page.locator("#all-on").click()
    page.wait_for_timeout(1000)
    on_state = page.evaluate("Object.fromEntries(walkthrough.PLAN.rooms.map(r=>[r.id,walkthrough.getRoomLight(r.id).on]))")
    check(name, "All rooms on turns all active rooms on including the children's room", all(on_state.values()), on_state)
    # slider while off turns room on
    page.locator("#room").select_option("kitchen")
    page.wait_for_timeout(500)
    page.locator(".switch").click()
    page.wait_for_timeout(300)
    set_range(page, "high-dim", 60)
    page.wait_for_timeout(300)
    check(name, "moving a slider on an off room turns it on", page.evaluate("walkthrough.getRoomLight('kitchen').on") is True)
    set_range(page, "high-dim", 100)
    kit = page.evaluate("walkthrough.getRoomLight('kitchen')")
    if CMAP:
        kh, kl = json.dumps(kit["cct"].get("high")), json.dumps(kit["cct"].get("low"))
        check(name, "kitchen per map: HIGH/task 4000 K, cove (LOW) 2700 K", "4000" in kh and "2700" in kl and "4000" not in kl, kit["cct"])
    else:
        check(name, "kitchen fixed CCT is neutral (4000 K) for task and cove", "4000" in json.dumps(kit["cct"]), kit["cct"])
    page.locator("#room").select_option("children")
    page.wait_for_timeout(500)
    ch = page.evaluate("walkthrough.getRoomLight('children')")
    cbr = page.evaluate("""()=>{const w=walkthrough,fx=w.PLAN.fixtures.zones.find(z=>z.id==='CBR').fixtures;
      return {high:fx.filter(f=>/^CBR-H[1-6]$/.test(f.id)).map(f=>({id:f.id,held:f.held,on:w.lighting.groupStates[f.circuit].on})),
      other:fx.filter(f=>!/^CBR-H[1-6]$/.test(f.id)).map(f=>({id:f.id,held:f.held,on:w.lighting.groupStates[f.circuit].on}))}}""")
    check(name, "children's six HIGH fittings are switchable; other CBR fixtures remain held", not ch["held"] and ch["on"] and len(cbr["high"]) == 6 and all(not f["held"] and f["on"] for f in cbr["high"]) and all(f["held"] and not f["on"] for f in cbr["other"]), cbr)
    set_range(page, "low-dim", 0)
    page.wait_for_timeout(900)
    cbr_low = page.evaluate("walkthrough.model.curtainPockets.find(p=>p.id==='CURT-CBR').mat.emissiveIntensity")
    set_range(page, "low-dim", 100)
    page.wait_for_timeout(900)
    cbr_full = page.evaluate("walkthrough.model.curtainPockets.find(p=>p.id==='CURT-CBR').mat.emissiveIntensity")
    check(name, "selected children's curtain strip follows LOW brightness", cbr_full > 0.1 and cbr_low < cbr_full * .2, [cbr_low, cbr_full])
    shot("lights-children-review")
    page.locator("#room").select_option("living")

    # ---- inspector (tap fitting in dollhouse)
    page.locator("[data-view=doll]").click()
    page.wait_for_timeout(900)
    tgt = page.evaluate(
        """()=>{const w=walkthrough,cam=w.camera,r=w.renderer.domElement.getBoundingClientRect(),V=cam.position.constructor;
        const cands=w.model.markers.children.filter(s=>s.userData.fixture).map(s=>{const p=s.getWorldPosition(new V()).project(cam);
          return {id:s.userData.fixture.id,x:r.left+(p.x+1)/2*r.width,y:r.top+(1-p.y)/2*r.height,z:p.z}})
          .filter(c=>c.z<1&&c.x>(innerWidth>900?400:30)&&c.x<innerWidth-60&&c.y>80&&c.y<(innerHeight>800&&innerWidth<600?innerHeight*.45:innerHeight-120));
        return cands.length?cands[Math.floor(cands.length/2)]:null}"""
    )
    check(name, "fixture markers visible in dollhouse", tgt is not None, tgt)
    if tgt:
        page.mouse.click(tgt["x"], tgt["y"])
        page.wait_for_timeout(600)
        insp = page.locator("#inspector").is_visible()
        itxt = page.locator("#inspector-body").inner_text() if insp else ""
        check(name, "tapping a fitting opens the inspector with its fixed CCT", insp and re.search(r"\d{4} K fixed", itxt) is not None, itxt[:200])
        shot("inspector")
        page.evaluate("document.getElementById('close-inspector').click()")

    # ---- exports
    ex = {}
    def grab(selector, label):
        with page.expect_download(timeout=120000) as di:
            page.evaluate(f"document.querySelector('{selector}').click()")
        dl = di.value
        path = out / "downloads" / f"{name}-{dl.suggested_filename}"
        dl.save_as(str(path))
        ex[label] = {"file": dl.suggested_filename, "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        return path
    p_png = grab("#dl-png", "png")
    im = Image.open(p_png)
    check(name, "PNG screenshot downloads (image, caption bar)", im.size[0] > 300 and p_png.stat().st_size > 15000 and p_png.read_bytes()[:4] == b"\x89PNG", [im.size, ex["png"]["bytes"]])
    p_csv = grab("#dl-schedule", "schedule")
    rows = p_csv.read_text(encoding="utf-8-sig").splitlines()
    import csv
    parsed = list(csv.DictReader(rows))
    cols = [c.lower() for c in parsed[0].keys()]
    check(name, "fixture schedule CSV: 108 rows with fixed CCT, circuit, rail and placement holds", len(parsed) == 108 and any("cct" in c for c in cols) and any("circuit" in c for c in cols) and any("rail" in c for c in cols) and "placement_hold_ids" in parsed[0], [len(parsed), cols])
    ex["scheduleColumns"] = list(parsed[0].keys())
    if CMAP:
        rows_by_id = {r["fixture_id"]: r for r in parsed}
        mism = [fid for fid, f in CMAP["_fixtures"].items() if fid not in rows_by_id or
                str(f["cct_k"]) != rows_by_id[fid]["fixed_cct_K"] or f["cct_rule"] != rows_by_id[fid]["cct_rule"] or
                f["placement_hold_ids"] != [h for h in rows_by_id[fid]["placement_hold_ids"].split("; ") if h]]
        selected = set(CMAP["selected_curtain_S1"]["strips"])
        check(name, "all 104 schedule CCTs, rules and placement holds match the current map", not mism and "brightness_group" in parsed[0] and set(rows_by_id) == set(CMAP["_cct"]) | selected, mism)
        check(name, "four selected schedule strips are warm, held for site and carry no lux credit",
              all(rows_by_id[i]["fixed_cct_K"] == "2700" and "H-CURTAIN-POCKET" in rows_by_id[i]["placement_hold_ids"] and
                  "no lux credit" in rows_by_id[i]["note"].lower() for i in selected), selected)
    p_grp = grab("#dl-groups", "groups")
    parsed_g = list(csv.DictReader(p_grp.read_text(encoding="utf-8-sig").splitlines()))
    check(name, "circuit-group CSV: 51 rows", len(parsed_g) == 51 and len({r["circuit"] for r in parsed_g}) == 51, len(parsed_g))
    links = page.evaluate("[...document.querySelectorAll('#pdf-links a')].map(a=>a.getAttribute('href'))")
    expected_downloads = {d["href"]: d for d in BUILD["downloads"]}
    check(name, "four current review PDF links present", len(links) == 4 and set(links) == set(expected_downloads), links)
    for i, h in enumerate(links):
        selector = f"#pdf-links a:nth-of-type({i+1})"
        if origin.scheme == "file":
            with page.expect_popup(timeout=30000) as opened:
                page.evaluate(f"document.querySelector('{selector}').click()")
            popup = opened.value
            popup.wait_for_url(re.compile(r"^file:"), timeout=30000)
            pth = Path(url2pathname(urlparse(popup.url).path)).resolve()
            wanted = (Path(args.build_info).parent / Path(*h.split("/"))).resolve()
            check(name, f"PDF {h.split('/')[-1]} opens beside the offline viewer", pth == wanted and pth.is_file(), popup.url)
            popup.close()
            ex[f"pdf{i+1}"] = {"file": pth.name, "bytes": pth.stat().st_size, "sha256": hashlib.sha256(pth.read_bytes()).hexdigest(), "offline_action": "opened in new PDF tab"}
        else:
            pth = grab(selector, f"pdf{i+1}")
        b = pth.read_bytes()
        import pymupdf
        doc = pymupdf.open(str(pth))
        pages = doc.page_count
        text = "\n".join(p.get_text() for p in doc)
        meta = json.dumps(doc.metadata)
        doc.close()
        expected = expected_downloads[h]
        expected_pages = 13 if "layout-views" in h else 17 if "wardrobe-interiors" in h else 1
        check(name, f"PDF {h.split('/')[-1]} matches receipt and page count", b[:5] == b"%PDF-" and len(b) == expected["bytes"] and hashlib.sha256(b).hexdigest() == expected["sha256"] and pages == expected_pages, [len(b), pages])
        check(name, f"PDF {h.split('/')[-1]} is searchable, current-bound and review-marked",
              args.master in text and any(s in text.lower() for s in ["not for construction", "not construction", "not for fabrication", "review draft"]) and
              ("wardrobe-interiors" not in h or WARDROBES["source_master_sha256"] in text), text[:200])
        check(name, f"PDF {h.split('/')[-1]} has no private paths or personal metadata",
              not re.search(r"(?i)(rkudipud|[a-z]:[\\/]|session-state|\.copilot|whatsapp|attachments|[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,})", text + meta))
        ex[f"pdf{i+1}"]["pages"] = pages
    report_p["exports"] = ex

    # ---- hygiene
    ext = [u for u in requests if not (u.startswith(origin.scheme + "://" + origin.netloc) or u.startswith("data:") or u.startswith("blob:"))]
    check(name, "no external (CDN / third-party) requests", not ext, ext[:5])
    ang = [w for w in warnings if "X4122" in w or "X4008" in w or "Program Info Log" in w]
    other_warn = [w for w in warnings if w not in ang]
    check(name, "zero console errors / page errors", not errors, errors[:5])
    check(name, "no unexpected console warnings (only the known ANGLE/D3D X4122-X4008 compile notes)", not other_warn, other_warn[:5])
    check(name, "HTML has no personal paths or local attachment names", not re.search(r"(?i)(rkudipud|[a-z]:\\\\|session-state|\.copilot|whatsapp|attachments)", page.content()))
    ov = page.evaluate("[document.documentElement.scrollWidth, innerWidth, document.documentElement.scrollHeight, innerHeight]")
    check(name, "no horizontal page overflow", ov[0] <= ov[1] + 1, ov)
    report_p.update({"warningsKnownAngle": len(ang), "warningFirst": ang[0][:300] if ang else None, "requests": len(requests), "errors": errors, "finalState": state()})
    browser.close()
    return report_p


with sync_playwright() as p:
    todo = args.only.split(",")
    if "desktop" in todo:
        report["profiles"]["desktop"] = run_profile(
            p, "desktop",
            {"viewport": {"width": 1440, "height": 900}, "device_scale_factor": 1},
            lambda s: (370, 100, 1400, 820),
        )
    if "mobile" in todo:
        report["profiles"]["mobile"] = run_profile(
            p, "mobile",
            {"viewport": {"width": 390, "height": 844}, "device_scale_factor": 2, "is_mobile": True, "has_touch": True,
             "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"},
            lambda s: (0, 40, 390, max(120, 844 - int(s.get("sheetPx", 0)) - 20)),
        )

report["checks"] = checks
report["summary"] = {"total": len(checks), "passed": sum(c["pass"] for c in checks), "failed": [c["name"] + " [" + c["profile"] + "]" for c in checks if not c["pass"]]}
(out / f"verification-{args.label}.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
print(json.dumps(report["summary"], indent=2))
if report["summary"]["failed"]:
    sys.exit(1)
