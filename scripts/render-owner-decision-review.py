"""Create separate owner-choice overlays without editing historical wardrobe drawings."""

import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "handoff/contractor/wardrobe/final"
OUTPUT = ROOT / "handoff/decisions/wardrobe-review"
NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", NS)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def element(parent, tag, **attrs):
    return ET.SubElement(parent, f"{{{NS}}}{tag}", {key: str(value) for key, value in attrs.items()})


def text(parent, x, y, value, size=20, **attrs):
    node = element(parent, "text", x=x, y=y, **{"font-size": size, **attrs})
    node.text = value
    return node


def build():
    manifest = json.loads((ROOT / "handoff/manifest.json").read_bytes())
    pins = {row["path"]: row["sha256"] for row in manifest["files"]}
    inputs = ["wardrobe-interiors.json", "R04-interior-elevation.svg", "R05-interior-elevation.svg"]
    for name in inputs:
        path = SOURCE / name
        if digest(path) != pins[path.relative_to(ROOT).as_posix()]:
            raise ValueError(f"Historical source does not match inventory: {name}")
    model = json.loads((SOURCE / inputs[0]).read_bytes())
    retained = {}
    for room_id in ("R04", "R05"):
        retained[room_id] = [
            bay["id"] for section in model["rooms"][room_id]["sections"]
            for bay in section["bays"] if bay["pullouts_ffl_mm"]
        ]
    if retained != {"R04": ["A3", "B3"], "R05": ["C3"]}:
        raise ValueError("The source proposal no longer matches the three retained tray bays")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    combined = pymupdf.open()
    files = []
    for room_id, label, name in (
        ("R04", "Master: retain trays A3 + B3", "master-interiors-decision-review"),
        ("R05", "Children: six loft doors + tray C3", "children-interiors-decision-review"),
    ):
        original = ET.parse(SOURCE / f"{room_id}-interior-elevation.svg").getroot()
        document = ET.Element(f"{{{NS}}}svg", {
            "width": "1400", "height": "1240", "viewBox": "0 0 1400 1240",
            "role": "img", "aria-labelledby": "decision-title",
        })
        title = element(document, "title", id="decision-title")
        title.text = label + " - dated owner-choice overlay; not for fabrication"
        element(document, "rect", width=1400, height=1240, fill="white")
        style = element(document, "style")
        style.text = "text{font-family:Arial,sans-serif;fill:#172b39}"
        text(document, 50, 36, "OWNER DECISION REVIEW | 18 NOVEMBER 2026", 24, **{"font-weight": "bold"})
        text(document, 50, 68, label, 23)
        element(document, "rect", x=50, y=88, width=30, height=20, fill="#202020", id="matte-black-finish-swatch")
        text(document, 95, 105, "MATTE BLACK HANDLES: finish only; shape, position and product not approved", 19)
        group = element(document, "g", transform="translate(0 125)")
        for node in list(original):
            group.append(node)
        tray_labels = [node for node in group.iter(f"{{{NS}}}text") if node.text == "PULL-OUT"]
        if len(tray_labels) != len(retained[room_id]):
            raise ValueError("Unexpected tray count in historical SVG")
        for bay_id, node in zip(retained[room_id], tray_labels):
            node.text = "RETAIN TRAY"
            node.set("font-weight", "bold")
            node.set("id", "retained-tray-" + bay_id)
            center = float(node.get("x"))
            width = 158.09 if room_id == "R05" else 150.4
            element(group, "rect", x=center - width / 2, y=565.6, width=width, height=20.4,
                    fill="none", stroke="#976000", **{"stroke-width": 4})
        if room_id == "R05":
            loft_label = next(node for node in group.iter(f"{{{NS}}}text")
                              if (node.text or "").startswith("LOFT:"))
            loft_label.set("y", "204")
            loft_label.text = "SIX DOOR FRONTS ONLY - JOINTS ARE NOT INTERNAL PARTITIONS"
            loft_label.set("font-size", "17")
            for number in range(6):
                x = 75 + number * (1250 / 6)
                element(group, "rect", x=x + 2, y=218, width=1250 / 6 - 4, height=116,
                        fill="#edf0f0", stroke="#264d60", id=f"children-loft-door-{number + 1}")
                text(group, x + 1250 / 12, 267, f"DOOR {number + 1}", 19, **{"text-anchor": "middle"})
                text(group, x + 1250 / 12, 298, "width TBD", 15, **{"text-anchor": "middle"})
                element(group, "rect", x=x + 1250 / 6 - 22, y=263, width=6, height=34,
                        rx=2, fill="#202020", id=f"matte-black-handle-marker-{number + 1}")
        text(document, 50, 1114, "DECISION OVERLAY ONLY: all source dimensions, bays and other details remain provisional.", 20)
        text(document, 50, 1146, "Grey is a drafting tone, not a shutter finish; soft-close and shutter mechanism remain unconfirmed.", 18)
        if room_id == "R05":
            text(document, 50, 1176, "Six doors do NOT prove suitcase fit. Measure the unobstructed opening, supports, hardware and route.", 18)
        else:
            text(document, 50, 1176, "Two master trays retained; heights, widths, runners, loads, access and the rest of the interior need review.", 18)
        text(document, 50, 1210, "NO CONSTRUCTION / PRODUCT / PROCUREMENT / FABRICATION RELEASE", 21, **{"font-weight": "bold"})
        svg = OUTPUT / f"{name}.svg"
        ET.ElementTree(document).write(svg, encoding="utf-8", xml_declaration=True)
        source_doc = pymupdf.open(stream=svg.read_bytes(), filetype="svg")
        page_doc = pymupdf.open("pdf", source_doc.convert_to_pdf())
        png = OUTPUT / f"{name}.png"
        page_doc[0].get_pixmap(matrix=pymupdf.Matrix(1, 1), alpha=False).save(png)
        combined.insert_pdf(page_doc)
        source_doc.close()
        page_doc.close()
        files.extend([svg, png])
    pdf = OUTPUT / "wardrobe-owner-review.pdf"
    combined.set_metadata({
        "title": "18 November 2026 - wardrobe owner decision overlays",
        "subject": "Six children's loft doors, matte-black handle finish, three retained trays; all site and fabrication holds remain",
    })
    combined.save(pdf, garbage=4, deflate=True, no_new_id=True)
    combined.close()
    files.append(pdf)
    receipt = {
        "schema": "wardrobe-owner-review-derivation/1", "date": "2026-11-18",
        "status": "separate-decision-overlays-not-full-regeneration",
        "sourceMasterSha256": manifest["masterSha256"],
        "sourceInputs": [{"repositoryPath": (SOURCE / name).relative_to(ROOT).as_posix(),
                          "sha256": digest(SOURCE / name)} for name in inputs],
        "sourceArtifactsModified": False, "sourceDimensionsRevalidated": False,
        "coordinateUnits": "SVG layout coordinates, not new site measurements",
        "retainedTrayBays": retained, "childrenLoftDoorFronts": 6,
        "doorJointsAreNotApprovedInternalPartitions": True,
        "handleFinish": "matte black; swatch only, no product/profile/location approval",
        "shutterFinishAndMechanism": "unconfirmed; grey drafting tone is not a finish selection",
        "softClose": "unconfirmed proposal",
        "suitecaseAccess": "site-measured unobstructed opening, internals, supports, open-door hardware and approach required",
        "constructionRelease": False, "productRelease": False,
        "fabricationRelease": False, "procurementRelease": False,
        "rendering": "PyMuPDF; SVG/PNG geometry is repeatable, PDF serialization is not an archival byte-reproduction promise",
        "files": [{"path": path.name, "bytes": path.stat().st_size, "sha256": digest(path)} for path in files],
    }
    (OUTPUT / "review-source-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print("Created two SVG/PNG decision overlays, a two-page PDF and source/hash receipt; historical files untouched")


if __name__ == "__main__":
    build()
