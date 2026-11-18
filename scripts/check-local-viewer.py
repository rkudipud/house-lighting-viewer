"""Check the integrated static viewer offline and under a Pages-style URL prefix."""

import csv
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib.request import urlopen

from PIL import Image
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "/house-lighting-viewer/"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        if not self.path.startswith(PREFIX):
            self.send_error(404)
            return
        self.path = self.path[len(PREFIX) - 1:]
        super().do_GET()

    def log_message(self, *_):
        pass


def main():
    checks = []
    errors = []
    external = []
    exports = {}

    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        checks.append(name)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    base = origin + PREFIX
    build = json.loads((ROOT / "build-info.json").read_text())
    try:
        for item in build["downloads"]:
            with urlopen(base + item["href"]) as response:
                data = response.read()
                check(item["href"] + " HTTP/hash", response.status == 200 and
                      hashlib.sha256(data).hexdigest() == item["sha256"])
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                channel="msedge", headless=True, args=["--enable-unsafe-swiftshader"]
            )
            try:
                context = browser.new_context(
                    viewport={"width": 1365, "height": 900}, reduced_motion="reduce",
                    accept_downloads=True,
                )
                context.on("page", lambda page: page.on("pageerror", lambda error: errors.append(str(error))))
                context.on("request", lambda request: external.append(request.url)
                           if request.url.startswith(("http://", "https://"))
                           and not request.url.startswith(origin + "/") else None)
                page = context.new_page()
                page.set_default_timeout(60000)
                page.goto(base, wait_until="networkidle")
                page.wait_for_function("window.walkthrough?.ready")
                check("current canonical binding", page.evaluate(
                    "walkthrough.PLAN.master.sha256") == build["masterSha256"])
                check("two brightness sliders, no colour input",
                      page.locator('input[type="range"]').count() == 2 and
                      page.locator('input[type="color"]').count() == 0)
                check("four current PDF links", page.locator("#pdf-links a").count() == 4)
                for mode in ("first", "third", "doll", "heat", "rcp"):
                    page.locator(f'[data-view="{mode}"]').click()
                    check("view mode " + mode, page.evaluate("walkthrough.getState().mode") == mode)
                room_ids = page.locator("#room option").evaluate_all("(nodes)=>nodes.map(n=>n.value)")
                for room in room_ids:
                    page.locator("#room").select_option(room)
                    check("room navigation " + room,
                          page.evaluate("walkthrough.getState().selectedRoom") == room)
                page.locator("#room").select_option("living")
                for lane, value in (("high", 70), ("low", 55)):
                    page.locator("#" + lane + "-dim").evaluate(
                        "(input,value)=>{input.value=value;input.dispatchEvent(new Event('input',{bubbles:true}));}",
                        value,
                    )
                    check(lane + " visual brightness", page.evaluate(
                        f"walkthrough.getRoomLight('living').{lane}") == value)
                page.locator("#all-off").click()
                check("all-off control", not page.evaluate("walkthrough.getRoomLight('living').on"))
                page.locator("#all-on").click()
                check("all-on control", page.evaluate("walkthrough.getRoomLight('living').on"))
                page.locator("#room").select_option("master")
                page.locator("#interiors").click()
                check("provisional interior illustration", page.evaluate("walkthrough.getState().interiors"))
                page.locator('[data-view="heat"]').click()
                check("older CBR map withheld", "withheld" in page.locator("#map-flags").inner_text())
                page.locator('[data-view="doll"]').click()
                for button, rows in (("#dl-schedule", "scheduleRows"), ("#dl-groups", "groupRows")):
                    expected = page.evaluate(
                        f"walkthrough.{rows}().map(row=>row.map(value=>String(value??'')))"
                    )
                    with page.expect_download() as downloaded:
                        page.locator(button).click()
                    with open(downloaded.value.path(), encoding="utf-8-sig", newline="") as stream:
                        actual = list(csv.reader(stream))
                    check(button + " complete CSV content", actual == expected)
                    exports[rows] = len(actual) - 1
                with page.expect_download() as downloaded:
                    page.locator("#dl-png").click()
                with Image.open(downloaded.value.path()) as image:
                    image.load()
                    check("view PNG export", image.width >= 1365 and image.height >= 900)
                page.set_viewport_size({"width": 390, "height": 844})
                check("mobile page width", page.evaluate(
                    "document.documentElement.scrollWidth <= innerWidth"))
                page.locator("#collapse").click()
                check("mobile hide panel", page.locator("body").evaluate(
                    "body=>body.classList.contains('collapsed')"))
                page.locator("#restore").click()
                check("mobile restore panel", not page.locator("body").evaluate(
                    "body=>body.classList.contains('collapsed')"))
                workbench = context.new_page()
                workbench.goto(base + "handoff/electrician/lighting/lighting-workbench.html",
                               wait_until="networkidle")
                check("integrated workbench master", workbench.locator("#master-hash").inner_text()
                      .startswith(build["masterSha256"][:8]))
                before = workbench.locator("#fixture-info").inner_text()
                fitting = workbench.locator("#fixture option").last.get_attribute("value")
                workbench.locator("#fixture").select_option(fitting)
                check("integrated workbench fixture interaction",
                      workbench.locator("#fixture-info").inner_text() != before)
                simulation = context.new_page()
                simulation.goto(base + "handoff/electrician/simulation/index.html", wait_until="networkidle")
                simulation.locator("img").evaluate_all("(nodes)=>nodes.forEach(node=>node.loading='eager')")
                simulation.wait_for_function(
                    "[...document.images].every(image=>image.complete&&image.naturalWidth===1100&&image.naturalHeight===1030)"
                )
                check("separate simulation gallery loads all 33 maps", simulation.locator("img").count() == 33)
                text = simulation.locator("body").inner_text().lower()
                check("simulation caveats and revision status", all(
                    phrase in text for phrase in ("not measured", "small-room sensitivity", "glare/ugr",
                                                  "daylight", "0.4 ft", "revision", "awaits coordinator review")
                ))
                simulation.locator('a[href="simulation-report.html"]').click()
                simulation.wait_for_load_state("networkidle")
                check("readable simulation report", simulation.locator("table").count() >= 6 and
                      "20/20" in simulation.locator("body").inner_text())
                simulation.set_viewport_size({"width": 390, "height": 844})
                check("mobile simulation report", simulation.evaluate(
                    "document.documentElement.scrollWidth <= innerWidth"))
                simulation.locator('a[href="revision-all-rooms/index.html"]').click()
                simulation.wait_for_load_state("networkidle")
                text = simulation.locator("body").inner_text().lower()
                check("remaining-room revision scope and controls", all(
                    phrase in text for phrase in ("54", "identical-scene controls, not physical pocket sensitivity",
                                                  "12/8", "floor plane", "enclosed", "not measured")
                ))
                check("all revision numerical and editable scene links", simulation.locator('a[href$=".rad"]').count() == 54
                      and simulation.locator('a[href$="/sim-results.json"]').count() == 9)
                simulation.locator('a[href="simulation-report-remaining.html"]').click()
                simulation.wait_for_load_state("networkidle")
                check("full remaining-room report tables", simulation.locator("table").count() >= 5
                      and "identical-scene controls" in simulation.locator("body").inner_text().lower())
                check("mobile remaining-room report", simulation.evaluate(
                    "document.documentElement.scrollWidth <= innerWidth"))
                offline = context.new_page()
                offline.goto((ROOT / "index.html").as_uri(), wait_until="networkidle")
                offline.wait_for_function("window.walkthrough?.ready")
                check("offline file viewer", offline.evaluate("walkthrough.ready"))
                check("no browser exceptions", not errors)
                check("no external runtime requests", not external)
                context.close()
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
    receipt = {
        "status": "PASS_local_integrated_browser_checks",
        "masterSha256": build["masterSha256"],
        "htmlSha256": hashlib.sha256((ROOT / "index.html").read_bytes()).hexdigest(),
        "profiles": ["desktop", "mobile-width", "offline-file", "Pages-style repository prefix"],
        "checksPassed": len(checks),
        "checks": checks,
        "browserErrors": errors,
        "externalRequests": external,
        "exportDataRows": exports,
        "constructionRelease": False,
        "publicationAuthorized": False,
    }
    (ROOT / "handoff" / "viewer" / "local-browser-verification.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    print(f"PASS: {len(checks)} integrated browser/export/download checks")


if __name__ == "__main__":
    main()
