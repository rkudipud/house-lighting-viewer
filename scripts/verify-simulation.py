"""Verify imported/derived simulation fidelity without importing simulator code."""

import csv
import hashlib
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "handoff" / "electrician" / "simulation"


def main():
    copy = json.loads((PACK / "repository-copy-receipt.json").read_text())
    numeric_files = 0
    for record in copy["files"]:
        data = (PACK / record["path"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != record["sha256"]:
            raise ValueError("Public copy hash mismatch: " + record["path"])
        if record["path"].startswith(("analysis/", "runs/")):
            if record["sha256"] != record["sourceSha256"]:
                raise ValueError("Numerical source evidence was modified")
            numeric_files += 1
    grids = json.loads((PACK / "analysis" / "sim-heatmaps.json").read_text())
    images = json.loads((PACK / "derived-evidence-receipt.json").read_text())
    for record in images["files"]:
        if hashlib.sha256((PACK / record["path"]).read_bytes()).hexdigest() != record["sha256"]:
            raise ValueError("Derived image hash mismatch")
    total_cells = 0
    rows_verified = 0
    with (PACK / "heatmap-cells.csv").open(encoding="utf-8", newline="") as stream:
        reader = csv.reader(stream)
        if next(reader) != ["room", "scene", "x_ft", "z_ft", "maintained_lux", "inside_grid_mask"]:
            raise ValueError("CSV header mismatch")
        for room, grid in grids.items():
            for scene, values in grid["layers"].items():
                svg = PACK / "heatmaps" / f"{room}-{scene}.svg"
                tree = ET.fromstring(svg.read_bytes())
                actual = {
                    (int(node.attrib["data-row"]), int(node.attrib["data-col"])): node.attrib
                    for node in tree.iter() if "data-lux" in node.attrib
                }
                expected_count = 0
                for j, row in enumerate(values):
                    for i, value in enumerate(row):
                        expected_csv = [room, scene, str(grid["x_ft"][i]), str(grid["z_ft"][j]),
                                        "" if value is None else str(value), str(int(value is not None))]
                        if next(reader) != expected_csv:
                            raise ValueError("CSV data/coordinate/mask mismatch")
                        rows_verified += 1
                        if value is None:
                            if (j, i) in actual:
                                raise ValueError("Outside-mask SVG cell was filled")
                            continue
                        if not math.isfinite(value) or float(actual[j, i]["data-lux"]) != value:
                            raise ValueError("SVG value mismatch")
                        expected_count += 1
                if len(actual) != expected_count:
                    raise ValueError("SVG cell count mismatch")
                total_cells += expected_count
                with Image.open(svg.with_suffix(".png")) as png:
                    png.load()
                    if png.size != (1100, 1030):
                        raise ValueError("Unexpected PNG dimensions")
                    probes = list(actual.items())
                    probes = [probes[0], max(probes, key=lambda item: float(item[1]["data-lux"]))]
                    for _, node in probes:
                        x = int(float(node["x"]) + float(node["width"]) / 2)
                        y = int(float(node["y"]) + float(node["height"]) / 2)
                        expected_rgb = tuple(bytes.fromhex(node["fill"][1:]))
                        rgb = png.convert("RGB").getpixel((x, y))
                        if any(abs(a - b) > 2 for a, b in zip(rgb, expected_rgb)):
                            raise ValueError("PNG/SVG pixel mismatch")
        if next(reader, None) is not None:
            raise ValueError("Unexpected extra CSV data")
    if images["svgNumericalCellsAndMaskVerified"] != total_cells or images["mapPairs"] != 33:
        raise ValueError("Derived receipt counts differ from independently checked files")
    for path in PACK.rglob("*"):
        if path.suffix in {".json", ".md", ".py", ".html", ".cal", ".svg", ".csv"}:
            text = path.read_text(encoding="utf-8-sig").lower()
            if "/nfs/" in text or "/home/" in text or (
                "@" in text and re.search(r"\b[\w.-]+@[\w.-]+\.[a-z]{2,}", text)
            ):
                raise ValueError("Private compute detail in " + path.relative_to(PACK).as_posix())
    receipt = {
        "status": "PASS_public_simulation_fidelity_without_Radiance",
        "radianceExecuted": False, "sourceNumericalFilesByteIdentical": numeric_files,
        "heatmapPairs": images["mapPairs"], "nonNullSvgCellsVerified": total_cells,
        "csvRowsIncludingMaskedCellsVerified": rows_verified,
        "pngPixelChecks": "First and peak-value source cells in every map match SVG colours within 2 RGB levels.",
        "privateComputeDetails": "No private network domain, shared-host path or job-system markers in public addendum.",
        "constructionRelease": False, "publicationAuthorized": False,
    }
    (PACK / "local-simulation-verification.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: {numeric_files} unchanged numeric files, 33 map pairs, {total_cells} SVG cells, {rows_verified} CSV rows")


if __name__ == "__main__":
    main()
