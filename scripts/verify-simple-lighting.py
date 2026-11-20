"""Check simplified viewer controls and rendered HIGH/LOW separation."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


PIXELS = """() => {
    const w=walkthrough,r=w.renderer;
    w.lighting.update(2);r.render(w.scene,w.camera);
    const gl=r.getContext(),width=r.domElement.width,height=r.domElement.height;
    const x=Math.floor(width*.35),y=Math.floor(height*.15);
    const nx=Math.floor(width*.5),ny=Math.floor(height*.65);
    const pixels=new Uint8Array(nx*ny*4);
    gl.readPixels(x,y,nx,ny,gl.RGBA,gl.UNSIGNED_BYTE,pixels);
    let sum=0,white=0,black=0;
    for(let i=0;i<pixels.length;i+=4){
        const [r,g,b]=pixels.subarray(i,i+3);
        sum+=.2126*r+.7152*g+.0722*b;
        if(Math.min(r,g,b)>=250)white++;
        if(Math.max(r,g,b)<=10)black++;
    }
    return {mean:sum/(nx*ny),clipped:white/(nx*ny),dark:black/(nx*ny)};
}"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    errors, report = [], {}
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True, args=["--enable-webgl", "--ignore-gpu-blocklist", "--use-angle=swiftshader"]
        )
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 800}, reduced_motion="reduce")
            page.set_default_timeout(10000)
            page.on("pageerror", lambda error: errors.append(str(error)))
            # Render settled frames explicitly instead of competing with the viewer's render loop.
            page.add_init_script("window.requestAnimationFrame = () => 0")
            page.goto(args.url, wait_until="networkidle", timeout=180000)
            assert page.evaluate("window.walkthrough?.ready"), page.locator("#fatal-detail").text_content()
            assert page.locator("input[type=range], #about, #h-storage").count() == 0
            assert page.locator("#desk p, #help-dialog p").count() == 0
            def click(selector):
                page.locator(selector).first.evaluate("(element) => element.click()")

            def select_room(room):
                page.locator("#room").evaluate("""(select, room) => {
                    select.value=room;select.dispatchEvent(new Event('change'));
                }""", room)

            select_room("living")
            click("#high-on")
            assert page.evaluate("walkthrough.getRoomLight('living').high") == 0
            click("#high-on")
            assert page.evaluate("walkthrough.getRoomLight('living').high") == 100
            click("#low-on")
            select_room("dining")
            assert page.locator("#low-on").is_checked(), "Other room LOW lights must stay on"
            assert not page.evaluate("walkthrough.lighting.groupStates.C05.on"), "Held shared LINE must stay off"
            select_room("living")
            click("#low-on")
            page.locator("#fixture-list").locator("..").locator("summary").evaluate("(el) => el.click()")
            click("#fixture-list button")
            fields = page.locator("#inspector dt").all_text_contents()
            assert fields == ["Name", "Type", "Wattage", "Lumens", "Spec", "Beam angle", "Color", "Location", "Code"]
            assert page.locator("#inspector dd").all_text_contents()[0].startswith("Living ")
            click("#close-inspector")
            for room in ("living", "master", "children", "kitchen", "bath1"):
                page.evaluate("""room => {
                    walkthrough.setMode('first');walkthrough.selectRoom(room);
                    walkthrough.setAllRooms(true);
                    const s=walkthrough.getState();
                    walkthrough.setPose(s.position[0]/.3048,s.position[2]/.3048,s.yaw,s.pitch);
                }""", room)
                scenes = {}
                for scene, high, low in (("off", False, False), ("low", False, True), ("high", True, False), ("both", True, True)):
                    page.evaluate("""([high,low]) => {
                        walkthrough.setMasterLight('high',{on:high});
                        walkthrough.setMasterLight('low',{on:low});
                    }""", [high, low])
                    scenes[scene] = page.evaluate(PIXELS)
                report[room] = scenes
                assert scenes["high"]["mean"] > scenes["low"]["mean"] + 5, (room, scenes)
                assert scenes["low"]["mean"] > scenes["off"]["mean"] + 5, (room, scenes)
                assert scenes["both"]["mean"] >= scenes["high"]["mean"], (room, scenes)
                assert scenes["both"]["clipped"] < .1, (room, scenes)
                assert scenes["off"]["dark"] < .35, (room, scenes)
            for mode in ("first", "third", "doll", "heat", "rcp"):
                state = page.evaluate("""mode => {
                    document.querySelector(`[data-view="${mode}"]`).click();
                    return {mode:walkthrough.getState().mode,map:!document.querySelector('#sec-map').hidden};
                }""", mode)
                assert state == {"mode": mode, "map": mode == "heat"}
            print("PASS desktop controls, views and rendered lighting", flush=True)
            mobile = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
            mobile.on("pageerror", lambda error: errors.append(str(error)))
            mobile.add_init_script("window.requestAnimationFrame = () => 0")
            mobile.goto(args.url, wait_until="networkidle", timeout=180000)
            assert mobile.evaluate("window.walkthrough?.ready"), mobile.locator("#fatal-detail").text_content()
            mobile.locator("#room").evaluate("""select => {
                select.value='master';select.dispatchEvent(new Event('change'));
            }""")
            mobile.locator("#fixture-list").locator("..").locator("summary").evaluate("(el) => el.click()")
            mobile.locator("#fixture-list button").first.evaluate("(button) => button.click()")
            assert mobile.evaluate("""() => {
                const panel=document.querySelector('#inspector'),box=panel.getBoundingClientRect();
                return !panel.hidden && box.width>0 && box.height>0 &&
                    box.left>=0 && box.right<=innerWidth && box.top>=0 && box.bottom<=innerHeight &&
                    document.documentElement.scrollWidth<=innerWidth;
            }""")
            assert not errors, errors
            print("PASS mobile fitting inspector", flush=True)
        finally:
            browser.close()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("PASS simple switches, room isolation, held circuits, fitting details, five views, mobile layout and HIGH/LOW rendering")


if __name__ == "__main__":
    main()
