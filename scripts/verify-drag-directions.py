"""Verify horizontal mouse inversion and unchanged vertical/touch controls in a real browser."""

import argparse
import hashlib
import json
import math
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--record-baseline", action="store_true")
    args = parser.parse_args()
    if args.baseline and args.record_baseline:
        parser.error("Choose either baseline recording or comparison")
    with urlopen(args.url, timeout=90) as response:
        html_sha = hashlib.sha256(response.read()).hexdigest()
    report = {"htmlSha256": html_sha, "profiles": {}, "browserErrors": []}
    modes = ("rcp", "doll", "heat", "first", "third")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--enable-webgl", "--ignore-gpu-blocklist"])
        try:
            for kind in ("mouse", "touch"):
                context = browser.new_context(
                    viewport={"width": 1280, "height": 800} if kind == "mouse" else {"width": 390, "height": 844},
                    is_mobile=kind == "touch", has_touch=kind == "touch", reduced_motion="reduce",
                )
                try:
                    page = context.new_page()
                    page.on("pageerror", lambda error: report["browserErrors"].append(str(error)))
                    page.goto(args.url, wait_until="networkidle", timeout=180000)
                    page.wait_for_function("window.walkthrough?.ready", timeout=180000)
                    master = page.evaluate("walkthrough.PLAN.master.sha256")
                    if "masterSha256" in report and report["masterSha256"] != master:
                        raise AssertionError("Mouse and touch loaded different masters")
                    report["masterSha256"] = master
                    page.evaluate("document.getElementById('collapse').click()")
                    cdp = context.new_cdp_session(page) if kind == "touch" else None
                    results = {}
                    for mode in modes:
                        page.evaluate("""mode => {
                            const w=walkthrough;w.setMode(mode);
                            if(mode==='rcp')w.setRcp(23,35,10);
                            else if(mode==='doll'||mode==='heat')w.setOrbit(.2,1.1,20);
                            else w.setPose(23,35,0,.1,76);
                        }""", mode)
                        state = """() => {
                            const s=walkthrough.getState();
                            return s.mode==='rcp'?[s.rcp.x,s.rcp.z]:
                                s.mode==='doll'||s.mode==='heat'?[s.orbit.yaw,s.orbit.pitch]:[s.yaw,s.pitch];
                        }"""
                        before = page.evaluate(state)
                        if kind == "mouse":
                            page.mouse.move(900, 600)
                            page.mouse.down()
                            page.mouse.move(940, 630)
                            page.mouse.up()
                        else:
                            cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": 180, "y": 350}]})
                            cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": 220, "y": 380}]})
                            cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
                        after = page.evaluate(state)
                        delta = [after[i] - before[i] for i in range(2)]
                        if not all(math.isfinite(value) and abs(value) > 1e-6 for value in delta):
                            raise AssertionError(f"{kind}/{mode}: drag did not change both axes: {delta}")
                        if not args.record_baseline:
                            vertical_sign = 1 if mode in {"first", "third"} else -1
                            if mode == "rcp":
                                vertical_sign = 1
                            if kind == "touch":
                                vertical_sign *= -1
                            if delta[0] >= 0 or delta[1] * vertical_sign <= 0:
                                raise AssertionError(f"{kind}/{mode}: incorrect drag directions: {delta}")
                        results[mode] = delta
                        print(f"PASS {kind}/{mode}: delta={delta}", flush=True)
                    report["profiles"][kind] = results
                finally:
                    context.close()
        finally:
            browser.close()
    if report["browserErrors"]:
        raise AssertionError(report["browserErrors"])
    if args.baseline:
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        if baseline["htmlSha256"] == html_sha or baseline["masterSha256"] != report["masterSha256"]:
            raise AssertionError("Comparison must use different viewer builds with the same master")
        for kind, results in report["profiles"].items():
            for mode, current in results.items():
                previous = baseline["profiles"][kind][mode]
                expected_x = -previous[0] if kind == "mouse" else previous[0]
                if not math.isclose(current[0], expected_x, abs_tol=1e-8) or not math.isclose(current[1], previous[1], abs_tol=1e-8):
                    raise AssertionError(f"{kind}/{mode}: unrelated axis behaviour changed")
        print("PASS all five modes: mouse horizontal reversed; vertical and touch unchanged", flush=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
