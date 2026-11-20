"""Render supplied simulation grids; never launch Radiance or recalculate lighting."""

import csv
import hashlib
import html
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import markdown
import pymupdf

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "handoff" / "electrician" / "simulation"
ROOMS = {
    "LIV": "Living", "DIN": "Dining", "KIT": "Kitchen", "MBR": "Master bedroom",
    "CBR": "Children's room", "UTL": "Utility", "DRS": "Dressing", "LOB": "Lobby",
    "TL1": "Toilet 1", "TL2": "Toilet 2", "BAL": "Balcony (enclosed assumption)",
}
STYLE = """
body{font:1rem/1.6 system-ui,sans-serif;max-width:74rem;margin:auto;padding:2rem 1.25rem;color:#172a35;background:#f5f4ef}
a{color:#075975;overflow-wrap:anywhere} .hold{border-left:.35rem solid #98610d;padding:1rem;background:white}
.maps{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:1rem}
figure{margin:0 0 1rem}img{width:100%;height:auto}table{border-collapse:collapse;display:block;overflow-x:auto;background:white}
th,td{border:1px solid #c9d1d3;padding:.5rem}code{overflow-wrap:anywhere}
"""


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def colour(value):
    stops = [(0, (23, 61, 82)), (250, (32, 143, 138)), (500, (245, 191, 95)), (750, (161, 58, 43))]
    value = min(750, max(0, value))
    for (lo, a), (hi, b) in zip(stops, stops[1:]):
        if value <= hi:
            mix = (value - lo) / (hi - lo)
            return "#" + "".join(f"{round(x + (y - x) * mix):02x}" for x, y in zip(a, b))
    raise ValueError("Invalid colour scale")


def page(title, body):
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f"<title>{html.escape(title)}</title><style>{STYLE}</style></head>"
            f"<body>{body}</body></html>\n")


def main():
    source = PACK / "analysis" / "sim-heatmaps.json"
    grids = json.loads(source.read_text())
    if set(grids) != set(ROOMS):
        raise ValueError("Unexpected room coverage")
    output = PACK / "heatmaps"
    output.mkdir(exist_ok=True)
    derived = []
    cards = []
    cells_verified = 0
    with (PACK / "heatmap-cells.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["room", "scene", "x_ft", "z_ft", "maintained_lux", "inside_grid_mask"])
        for room, grid in grids.items():
            if room == "CBR":
                continue
            cards.append(f'<section id="{room}"><h2>{html.escape(ROOMS[room])}</h2><div class="maps">')
            xs, zs = grid["x_ft"], grid["z_ft"]
            step = grid["step_ft"]
            if xs != sorted(xs) or zs != sorted(zs) or step != 0.25:
                raise ValueError("Unexpected coordinate orientation or sampling")
            scale = min(700 / (len(xs) * step), 650 / (len(zs) * step))
            cell = scale * step
            for scene, values in grid["layers"].items():
                if len(values) != len(zs) or any(len(row) != len(xs) for row in values):
                    raise ValueError("Grid shape mismatch")
                title = room + " / " + scene + " / exploratory Radiance estimate"
                lines = [
                    '<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="1030" viewBox="0 0 1100 1030">',
                    f"<title>{html.escape(title)}</title>",
                    '<rect width="1100" height="1030" fill="#ffffff"/>',
                    '<g font-family="sans-serif" fill="#172a35">',
                    f'<text x="50" y="40" font-size="24">{html.escape(title)}</text>',
                    '<text x="50" y="72" font-size="18">GENERIC / PROVISIONAL / NOT MEASURED / NOT PRODUCT VALIDATION</text>',
                    f'<text x="50" y="102" font-size="17">Workplane {grid["plane_m"]} m; MF 0.8; 100% stored output; 0.25 ft source grid</text>',
                    '<text x="80" y="815" font-size="17">Plan x / ft; plan z increases down the page. Blank cells are outside the source mask.</text>',
                    '<text x="50" y="860" font-size="17">P1 excluded; pooja strip/spot and KIT-L1 cove remain HELD. No fixtures moved.</text>',
                    '<text x="50" y="888" font-size="17">Curtain strips have no lux credit. UTL/BAL assume enclosure, not real open-air conditions.</text>',
                    '<text x="50" y="916" font-size="17">Base-run map; see separate six-room revision. Glare/UGR and daylight not computed; holds remain.</text>',
                    '<text x="50" y="944" font-size="17">Viewer/workbench maps remain separate frozen analytic estimates, not this ray-tracing result.</text>',
                    '<text x="50" y="982" font-size="14">Source: analysis/sim-heatmaps.json. Values are supplied rounded lux; no lighting recalculated.</text>',
                    "</g>", '<g id="cells">',
                ]
                expected = {}
                for j, row in enumerate(values):
                    for i, value in enumerate(row):
                        writer.writerow([room, scene, xs[i], zs[j], "" if value is None else value, int(value is not None)])
                        if value is None:
                            continue
                        if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                            raise ValueError("Nonfinite or negative source value")
                        expected[j, i] = value
                        lines.append(f'<rect data-row="{j}" data-col="{i}" data-lux="{value}" '
                                     f'x="{80 + i * cell:.6f}" y="{130 + j * cell:.6f}" '
                                     f'width="{cell:.6f}" height="{cell:.6f}" fill="{colour(value)}"/>')
                lines.append('</g><g font-family="sans-serif" font-size="16" fill="#172a35">')
                for i in range(0, len(xs), 8):
                    lines.append(f'<text x="{80 + i * cell:.3f}" y="790">{xs[i]:.2f}</text>')
                for j in range(0, len(zs), 8):
                    lines.append(f'<text x="8" y="{140 + j * cell:.3f}">{zs[j]:.2f}</text>')
                lines.append('<text x="855" y="140">Maintained lux</text>')
                for tick in range(501):
                    value = 750 * (500 - tick) / 500
                    lines.append(f'<rect x="860" y="{160 + tick}" width="35" height="1" fill="{colour(value)}"/>')
                for value in (0, 150, 300, 450, 600, 750):
                    y = 160 + (750 - value) * 500 / 750
                    label = "750+ (clipped)" if value == 750 else str(value)
                    lines.append(f'<text x="905" y="{y + 6:.2f}">{label}</text>')
                lines.append("</g></svg>")
                svg = output / f"{room}-{scene}.svg"
                svg.write_text("\n".join(lines) + "\n", encoding="utf-8")
                root = ET.fromstring(svg.read_bytes())
                actual = {
                    (int(node.attrib["data-row"]), int(node.attrib["data-col"])): float(node.attrib["data-lux"])
                    for node in root.iter() if "data-lux" in node.attrib
                }
                if actual != expected:
                    raise ValueError("SVG numerical values or mask differ from supplied grid")
                cells_verified += len(actual)
                png = svg.with_suffix(".png")
                with pymupdf.open(stream=svg.read_bytes(), filetype="svg") as document:
                    document[0].get_pixmap(alpha=False).save(png)
                for path in (svg, png):
                    derived.append({"path": path.relative_to(PACK).as_posix(), "sha256": digest(path),
                                    "sourcePath": "analysis/sim-heatmaps.json", "sourceSha256": digest(source)})
                stem = svg.stem
                cards.append(
                    f'<figure><a href="heatmaps/{stem}.png"><img loading="lazy" src="heatmaps/{stem}.png" '
                    f'alt="{html.escape(title)}; generic unmeasured estimate; all holds remain"></a>'
                    f'<figcaption>{html.escape(scene)}: <a href="heatmaps/{stem}.png">PNG</a> / '
                    f'<a href="heatmaps/{stem}.svg">editable SVG</a>. '
                    'Fixed 0-750 lux colour scale; higher colours clipped, numerical values retained. '
                    'A zero LOW grid means no modelled LOW contribution, not a missing mask.</figcaption></figure>'
                )
            cards.append("</div></section>")
    report_body = markdown.markdown((PACK / "simulation-report.md").read_text(),
                                    extensions=["tables", "fenced_code"])
    (PACK / "simulation-report.html").write_text(
        page("Exploratory simulation report", '<a href="index.html">Simulation evidence and heatmaps</a>'
             '<p class="hold">Historical report: CBR geometry and LOW state predate the current design; use the '
             '<a href="../lighting/heatmaps-summary.pdf">current review heatmaps</a>. Its small-room '
             'sensitivity not-run statement is superseded by the '
             '<a href="revision-all-rooms/index.html">six-room revision</a>. Limitations and holds remain.</p>' + report_body),
        encoding="utf-8",
    )
    intro = """
<a href="../index.html">Electrician handoff</a>
<h1>Historical exploratory Radiance evidence</h1>
<p class="hold"><strong>Historical baseline, not the current children's-room design.</strong>
The superseded CBR image derivatives and CSV rows have been removed.
Use the <a href="../lighting/heatmaps-summary.pdf">current review heatmaps</a> for CBR.
The original multi-room numerical source is retained unchanged for provenance, not as the current CBR result.
The <a href="revision-all-rooms/index.html">verified six-room small-room sensitivity revision</a>
is now included. It supersedes only the historical report's not-run statement.
This page preserves the earlier report and base grids; it is not a construction release.</p>
<p class="hold"><strong>GENERIC, PROVISIONAL, NOT MEASURED, NOT PRODUCT-SPECIFIC.
No construction, product, procurement or fabrication approval.</strong>
No fixtures or canonical data were changed. These static ray-tracing estimates do not replace
the viewer/workbench's frozen analytic maps and do not respond to their sliders.</p>
<p>Radiance rcontrib 6.0a: backward Monte-Carlo ray tracing with inter-reflection,
generic cos^m/Lambertian sources, assumed diffuse reflectances, MF 0.8.
103 of 104 base fittings simulated; LIV-P1 excluded because its strip record is outside the canonical niche.
Selected curtain strips are excluded with no lux credit.</p>
<p class="hold">Living and kitchen main-light evenness are marginal under the stated model.
KIT-L1 overruns its polygon by 0.4 ft and its unmeasured cove/slot remains held.
Pooja P1 is excluded; P2 aim misses the canonical niche and remains held. No re-aim or relocation was made.
Utility/balcony remain enclosed approximations. The separate six-room revision covers
UTL, DRS, LOB, TL1, TL2 and BAL, with pocket narrow/wide as identical-scene controls,
not physical pocket sensitivity. Bathroom results are floor-plane; DRS/LOB task U0 uses
only 12/8 points. Glare/UGR, daylight, flicker and thermal behaviour are not included.</p>
<p><a href="simulation-report.html">Full readable report and sensitivity tables</a> /
<a href="simulation-report.md">Markdown report</a> /
<a href="analysis/sim-summary.json">Model and sensitivity summary</a> /
<a href="analysis/checks.json">Producer's 20 checks</a> /
<a href="runs/base/sim-results.json">Base per-fitting results</a> /
<a href="analysis/sim-heatmaps.json">Original numerical grids</a> /
<a href="heatmap-cells.csv">Every grid cell as CSV, including outside-mask blanks</a> /
<a href="README.md">Editable sources, omissions and reproduction limits</a> /
<a href="repository-copy-receipt.json">Original/public hashes</a> /
<a href="derived-evidence-receipt.json">Derived rendering fidelity</a>.</p>
<p>All source-receipt-listed base/sensitivity/convergence result JSON is retained.
The low-sampling KIT sensitivity is superseded by sens512kit; the room-specific pairing and
excluded parity diagnostic are explained in the report. Source checks are producer evidence,
not independent product or site validation.</p>
<p>Source grids retain their delivered rounding and masks. Grid-cell colours must not be read
as task-area minimum/uniformity figures: use the report's defined task areas and scene accounting.</p>
"""
    anchors = " / ".join(f'<a href="#{room}">{html.escape(name)}</a>' for room, name in ROOMS.items() if room != "CBR")
    raw_links = "".join(
        f'<li><a href="{path.relative_to(PACK).as_posix()}">{path.relative_to(PACK).as_posix()}</a></li>'
        for path in sorted((PACK / "runs").rglob("sim-results.json"))
    )
    raw_links = "<details><summary>All raw base, sensitivity and convergence results</summary><ul>" + raw_links + "</ul></details>"
    (PACK / "index.html").write_text(page("Exploratory Radiance evidence", intro + raw_links + anchors + "".join(cards)), encoding="utf-8")
    summary = {
        "status": "PASS_supplied_grid_fidelity_not_a_simulation_rerun",
        "radianceExecuted": False, "constructionRelease": False, "publicationAuthorized": False,
        "sourceHeatmapsSha256": digest(source), "sourceRooms": len(grids), "rooms": len(grids) - 1,
        "omittedDerivedRooms": {"CBR": "Superseded geometry; current CBR results are in the lighting review pack."},
        "mapPairs": len(derived) // 2, "svgNumericalCellsAndMaskVerified": cells_verified,
        "csv": "heatmap-cells.csv", "csvSha256": digest(PACK / "heatmap-cells.csv"),
        "rendering": "SVG rectangles preserve every supplied non-null value and mask; PNGs rasterize those SVGs at 1100x1030. Fixed scale 0-750 lux clips colour only, never numerical exports.",
        "files": derived,
    }
    (PACK / "derived-evidence-receipt.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"Rendered {len(derived) // 2} SVG/PNG pairs; {cells_verified} supplied cells/masks verified")


if __name__ == "__main__":
    main()
