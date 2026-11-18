"""Export packaged SVG figures to PNG without accessing the network."""

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("assets", type=Path, help="directory containing SVG figures")
    parser.add_argument("output", type=Path, help="directory for exported PNGs")
    args = parser.parse_args()

    sources = sorted(args.assets.glob("*.svg"))
    if not sources:
        raise SystemExit(f"No SVG figures found in {args.assets}")
    args.output.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(device_scale_factor=2)
        context.route("**/*", lambda route: route.abort())
        page = context.new_page()
        for source in sources:
            page.set_content(
                '<!doctype html><html><body style="margin:0;background:white"></body></html>'
            )
            page.evaluate(
                """svg => {
                    document.body.innerHTML = svg;
                    if (document.body.children.length !== 1 ||
                        document.body.firstElementChild.tagName.toLowerCase() !== 'svg')
                        throw new Error('Expected exactly one SVG figure');
                }""",
                source.read_text(encoding="utf-8"),
            )
            figure = page.locator("svg")
            bounds = figure.bounding_box()
            if not bounds or bounds["width"] < 1 or bounds["height"] < 1:
                raise ValueError(f"SVG has no visible size: {source}")
            output = args.output / f"{source.stem}.png"
            figure.screenshot(path=str(output))
            print(f"{source.name} -> {output.name}: {bounds['width']} x {bounds['height']} CSS pixels at 2x")
        context.close()
        browser.close()


if __name__ == "__main__":
    main()
