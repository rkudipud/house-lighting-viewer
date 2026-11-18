"""Capture three captioned review renders from a verified offline viewer."""
import argparse
import hashlib
import json
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright


ap = argparse.ArgumentParser()
ap.add_argument("--html", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--master", required=True)
args = ap.parse_args()
html = Path(args.html).resolve()
out = Path(args.out).resolve()
out.mkdir(parents=True, exist_ok=True)
info = json.loads((html.parent / "build-info.json").read_text(encoding="utf-8"))
html_sha = hashlib.sha256(html.read_bytes()).hexdigest()
if info["htmlSha256"] != html_sha or info["masterSha256"] != args.master:
    raise ValueError("Viewer bytes or master do not match the build receipt")

captures = [
    {
        "file": "01-whole-flat-dollhouse.png",
        "room": "living",
        "mode": "doll",
        "interiors": False,
        "pose": "walkthrough.setMode('doll');walkthrough.setOrbit(.22,1.12,19)",
        "caption": "WHOLE FLAT / ROOF-OFF  |  REVIEW DRAFT - SITE MEASUREMENTS AND PROFESSIONAL APPROVALS REQUIRED",
    },
    {
        "file": "02-living-light-and-curtains.png",
        "room": "living",
        "mode": "first",
        "interiors": False,
        "light": {"high": 70, "low": 55},
        "pose": "walkthrough.setMode('first');walkthrough.setPose(12,36,1.5708,.38,76)",
        "caption": "LIVING / HIGH 70% + LOW 55%  |  VISUAL LIGHTING ONLY - NO MEASURED LUX OR CONSTRUCTION RELEASE",
    },
    {
        "file": "03-master-proposed-interiors.png",
        "room": "master",
        "mode": "first",
        "interiors": True,
        "light": {"high": 70, "low": 55},
        "pose": "walkthrough.setMode('first');walkthrough.setPose(22.9,12.5,0,.05,75)",
        "caption": "MASTER / PROPOSED INTERIORS  |  UNMEASURED, UNAPPROVED APPROXIMATIONS - NOT FOR FABRICATION",
    },
]
errors, requests, results = [], [], []
with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True, args=["--enable-webgl", "--ignore-gpu-blocklist"])
    context = browser.new_context(viewport={"width": 1600, "height": 1000}, device_scale_factor=1, accept_downloads=True)
    page = context.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("request", lambda r: requests.append(r.url))
    page.on("requestfailed", lambda r: errors.append("request failed: " + r.url))
    page.goto(html.as_uri(), wait_until="networkidle", timeout=180000)
    page.wait_for_function("window.walkthrough?.ready", timeout=180000)
    if page.evaluate("walkthrough.PLAN.master.sha256") != args.master:
        raise ValueError("Running viewer does not contain the expected master")
    page.evaluate("walkthrough.setAllRooms(true)")
    for spec in captures:
        page.evaluate("(room)=>walkthrough.selectRoom(room)", spec["room"])
        page.evaluate("(on)=>walkthrough.setInteriors(on)", spec["interiors"])
        if "light" in spec:
            page.evaluate("([room,levels])=>walkthrough.setRoomLight(room,levels)", [spec["room"], spec["light"]])
        page.evaluate(spec["pose"])
        page.wait_for_timeout(2500)
        state = page.evaluate("walkthrough.getState()")
        if state["mode"] != spec["mode"] or state["selectedRoom"] != spec["room"] or state["interiors"] != spec["interiors"]:
            raise RuntimeError(f"Unexpected viewer state before {spec['file']}: {state}")
        with page.expect_download(timeout=120000) as dl:
            page.evaluate("walkthrough.exportPng()")
        path = out / spec["file"]
        dl.value.save_as(str(path))
        with Image.open(path) as raw:
            im = raw.convert("RGB")
        footer = max(60, round(im.width / 32))
        captioned = Image.new("RGB", (im.width, im.height + footer), "#16343c")
        captioned.paste(im, (0, 0))
        draw = ImageDraw.Draw(captioned)
        font_size = 30
        font_name = str(Path(os.environ["WINDIR"]) / "Fonts" / "segoeui.ttf") if "WINDIR" in os.environ else "DejaVuSans.ttf"
        while True:
            font = ImageFont.truetype(font_name, font_size)
            if draw.textbbox((0, 0), spec["caption"], font=font)[2] <= im.width - 40 or font_size <= 16:
                break
            font_size -= 1
        draw.text((20, im.height + (footer - font_size) // 2 - 2), spec["caption"], fill="#f3f5ef", font=font)
        captioned.save(path, format="PNG", optimize=True)
        data = path.read_bytes()
        results.append({"file": spec["file"], "caption": spec["caption"], "mode": spec["mode"],
                        "room": spec["room"], "proposed_interiors": spec["interiors"], "pose": spec["pose"],
                        "visual_brightness": spec.get("light", {"high": 100, "low": 100}),
                        "width": captioned.width, "height": captioned.height, "bytes": len(data),
                        "sha256": hashlib.sha256(data).hexdigest()})
    external = [r for r in requests if not (r.startswith("file://") or r.startswith("blob:") or r.startswith("data:"))]
    browser.close()
if errors or external:
    raise RuntimeError(f"Capture browser errors: {errors}; external requests: {external}")
receipt = {"status": "REVIEW DRAFT - not a construction release", "master_sha256": args.master,
           "viewer_html_sha256": html_sha, "current_fixed_cct_map_sha256": info["currentFixedCctMapSha256"],
           "frozen_heatmaps_sha256": info["heatmapsSha256"], "renders": results,
           "browser_errors": errors, "external_requests": external}
(out / "render-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
print(json.dumps(receipt, indent=2))
