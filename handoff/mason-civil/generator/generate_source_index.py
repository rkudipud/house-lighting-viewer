"""Create a current-master room/opening index without consulting retired layouts."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import pymupdf


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


parser = argparse.ArgumentParser()
parser.add_argument("--master", required=True, type=Path)
parser.add_argument("--pack", required=True, type=Path)
parser.add_argument("--sha", required=True)
args = parser.parse_args()
master = args.master.resolve()
pack = args.pack.resolve()
master_bytes = master.read_bytes()
if hashlib.sha256(master_bytes).hexdigest() != args.sha:
    sys.exit("Master hash changed; refuse to build a stale index.")
house = json.loads(master_bytes.decode("utf-8-sig"))
r05_ceiling = house["lighting"]["design_inputs"]["ceilings"]["CBR"]
if r05_ceiling["band_h_m"] != 3.048 or r05_ceiling["tray_h_m"] != 3.2766:
    raise ValueError("Unexpected R05 reported levels; review their source before generating the index.")
register_path = pack / "site-details" / "opening-register.json"
site_receipt_path = pack / "site-details" / "site-details-verification.json"
register = read_json(register_path)
site_receipt = read_json(site_receipt_path)
if (register["source_master_sha256"] != args.sha
        or site_receipt["source_master"]["sha256"] != args.sha
        or site_receipt["opening_register"]["sha256"] != digest(register_path)
        or site_receipt["checks_passed"] != site_receipt["checks_total"]):
    sys.exit("Opening register is not verified against this master.")


def resolve_pointer(ref):
    prefix = "house-design.json#/"
    if not ref.startswith(prefix):
        raise ValueError(f"Not a canonical JSON pointer: {ref}")
    node = house
    for key in ref[len(prefix):].split("/"):
        key = key.replace("~1", "/").replace("~0", "~")
        node = node[int(key)] if isinstance(node, list) else node[key]
    return node


room_notes = {
    "R01": "Nominal label includes a lift-side cutout; not a full clear rectangle.",
    "R05": "Current children's arrangement is a proposed metric reconstruction; its return and openings require site survey.",
    "R08": "Utility / washing nominal-size scope and assembled model need site reconciliation.",
    "R08a": "Washing bay is a subdivision of the utility area, not an additional room.",
    "R10": "Lift footprint only; lift door and interior are not established.",
    "R13": "The one recorded offset is not a continuous legal setback or wall thickness.",
}
rooms = []
for ri, room in enumerate(house["architecture"]["rooms"]):
    dimensions = []
    for di, dim in enumerate(room["dimensions"]):
        if not dim.get("homeowner_confirmed_measured") or dim.get("independently_verified") is not False:
            raise ValueError(f"Unexpected room dimension evidence for {room['id']}")
        dimensions.append({
            "original_feet_inches": dim["original"],
            "value_ft": dim["value_ft"],
            "value_m": dim["value_m"],
            "confidence_in_master": dim["confidence"],
            "independently_verified": dim["independently_verified"],
            "confirmation_request": dim.get("confirmation_request"),
            "canonical_ref": f"house-design.json#/architecture/rooms/{ri}/dimensions/{di}",
            "historical_numeric_provenance_only": dim.get("source"),
        })
    rooms.append({
        "id": room["id"],
        "name": room["name"],
        "lighting_room_id": room.get("lighting_room_id"),
        "canonical_ref": f"house-design.json#/architecture/rooms/{ri}",
        "dimensions": dimensions,
        "dimension_status": ("homeowner_reported_measured_not_independently_verified"
                             if dimensions else "not_provided_measure_on_site"),
        "note": room_notes.get(room["id"]),
    })

architecture_openings = {o["id"]: i for i, o in enumerate(house["architecture"]["openings"])}
openings = []
for entry in sorted(register["openings"], key=lambda o: o["code"]):
    resolve_pointer(entry["model_geometry_ref"])
    row = dict(entry)
    if entry["code"] in architecture_openings:
        ai = architecture_openings[entry["code"]]
        row["architecture_identity_ref"] = f"house-design.json#/architecture/openings/{ai}"
        row["architecture_geometry_not_used"] = True
    if entry["code"] == "PN1":
        row["estimate_ref"] = "house-design.json#/decisions/pooja_niche/dimensions"
    if entry["code"] == "W05":
        row["active_image_relationship_ref"] = "house-design.json#/source_register/current_children_visual_layout"
        row["note"] = "Visual placeholder behind curtain; actual location and width unverified."
    if entry["code"] == "W03":
        row["note"] = "Homeowner says roughly centred; actual offsets and width unmeasured."
    if entry["code"] == "D01":
        row["note"] = "Architecture describes double-leaf; current visualization depicts single-leaf. Existing leaf count and swing unverified."
    openings.append(row)

connections = [
    {"id": c["id"], "connects": c["connects"], "width_m": None,
     "note": c["note"], "status": "carry_forward_relationship_not_site_verified",
     "canonical_ref": f"house-design.json#/architecture/open_connections/{i}"}
    for i, c in enumerate(house["architecture"]["open_connections"])
]
if len(rooms) != 14 or sum(len(r["dimensions"]) for r in rooms) != 21 or len(openings) != 21:
    raise ValueError("Unexpected room, dimension or opening count; review the master before publishing.")
if any(c["width_m"] is not None for c in house["architecture"]["open_connections"]):
    raise ValueError("Connection widths changed; review their evidence status.")
floor_instances = house["architecture"]["floor_instances"]
if len(floor_instances) != 4 or any(f["actual_storey_label"] is not None for f in floor_instances):
    raise ValueError("Floor labels changed; update the floor-specific survey guidance.")

out = pack / "source-index"
out.mkdir(parents=True, exist_ok=True)
source = {
    "schema": "civil_room_opening_source_index/1",
    "source_master": {"path": str(master), "sha256": args.sha},
    "source_opening_register": {"path": str(register_path), "sha256": digest(register_path)},
    "status": "review_only_not_for_construction",
    "scope": "14 room/area records, 21 model openings, 10 carry-forward connections and S01 stair; survey each floor separately",
    "source_policy": (
        "Current house-design.json is the active source. Historical P page references are retained only as provenance "
        "of separately homeowner-confirmed numerical labels; the retired original layout was not consulted or used as geometry."
    ),
    "orientation": {
        "source_ref": "house-design.json#/visualization_geometry/orientation",
        "sheet_top": "south", "sheet_bottom": "north", "sheet_left": "east", "sheet_right": "west",
        "bearing": "homeowner-described; not surveyed",
    },
    "storeys": [{"id": f["id"], "actual_storey_label": f["actual_storey_label"],
                 "site_variations": f["site_variations"]} for f in floor_instances],
    "rooms": rooms,
    "openings": openings,
    "connections": connections,
    "stair": {
        "id": "S01",
        "current_model_ref": "house-design.json#/visualization_geometry/stairs",
        "width_m": None, "riser_height_m": None, "tread_depth_m": None,
        "riser_count": None, "clear_headroom_m": None, "guard_height_m": None,
        "status": "assumed_model_only_all_site_dimensions_unverified",
        "note": "The drawn 7 and 15 lines are illustrative, not verified riser counts. Verify rise, going, width, landing, arrival and safety on each floor.",
    },
    "height_datum": {
        "source_ref": "house-design.json#/decisions/ceiling_heights",
        "floor_to_floor_m": house["decisions"]["ceiling_heights"]["stated_by_homeowner"]["floor_to_floor_m"],
        "band_drop_m": house["decisions"]["ceiling_heights"]["stated_by_homeowner"]["band_drop_m"],
        "status": "homeowner_stated_unmeasured",
        "note": "The older 3.188 m slab and 2.959 m band estimates depend on assumed thicknesses. R05 has separate homeowner-reported levels which conflict with the older slab estimate; its actual slab is unmeasured.",
        "children_R05": {
            "source_ref": "house-design.json#/lighting/design_inputs/ceilings/CBR",
            "band_m": r05_ceiling["band_h_m"],
            "centre_m_approx": r05_ceiling["tray_h_m"],
            "status": "homeowner_reported_approximate_not_surveyed",
            "slab_status": "unmeasured_conflict_with_older_estimate",
        },
    },
    "active_children_relationship_source": {
        "canonical_ref": "house-design.json#/source_register/current_children_visual_layout",
        "document": "MR.RAJESH_INTERIOR_RENDERS.pdf",
        "pages_1_based": house["source_register"]["current_children_visual_layout"]["selected_pages_1_based"],
        "status": "undimensioned perspectives; not a measured scale drawing",
    },
}
(out / "room-opening-index.json").write_text(json.dumps(source, indent=2), encoding="utf-8")

lines = [
    "# Room and opening source index - review only",
    "",
    f"**Canonical master SHA-256:** `{args.sha}`. Not for construction or fabrication.",
    "",
    "The 14 records include rooms, service areas, a lift footprint and a margin. The 21 openings include doors, windows, vents, niche fronts and a parapet opening. Each modeled span is an identification aid, not a measured size. Survey each actual floor separately; F1-F4 do not establish storey labels or identical built layouts.",
    "",
    "Room dimensions below are recorded by the master as homeowner-confirmed measured labels, but none is independently verified. Historical P page 1 references are numerical provenance only; the retired original layout was not consulted or used for geometry. Exact canonical pointers and evidence fields are in `room-opening-index.json`.",
    "",
    "## Rooms and areas",
    "",
    "| ID | Room / area | Homeowner-reported nominal feet / inches | Metres | Evidence |",
    "|---|---|---|---|---|",
]
for r in rooms:
    original = " x ".join(d["original_feet_inches"] for d in r["dimensions"]) or "Not supplied"
    metric = " x ".join(str(d["value_m"]) for d in r["dimensions"]) if r["dimensions"] else "-"
    evidence = "Homeowner reported; not independently surveyed" if r["dimensions"] else "Measure on site"
    lines.append(f"| {r['id']} | {r['name']} | {original} | {metric} | {evidence} |")
lines.extend(["", "R01 includes a lift-side cutout; R08/R08a are one utility/washing area whose scope needs reconciliation. R10 is a lift footprint, not an accessible room. R13 is one offset, not a confirmed continuous legal setback.", "",
              "## Openings", "",
              "| ID | Current-model identification | Model width m | Basis | Actual width / height |",
              "|---|---|---:|---|---|"])
for o in openings:
    lines.append(f"| {o['code']} | {o['name']} | {o['model_width_m']:.2f} | {o['model_width_status']} | Unmeasured |")
lines.extend([
    "",
    "D01 leaf count conflicts between architecture and visualization. W03 offsets are unmeasured; W05 is a visual placeholder. PN1 is an already-built niche with homeowner-estimated dimensions; its extension and support are unverified. No new or deeper cutting is authorised.",
    "",
    "## Connections, stair and heights",
    "",
    "The following are carry-forward model relationships, not verified site openings. Widths are not supplied:",
    "",
    "| ID | Connects | Model note |",
    "|---|---|---|",
])
for c in connections:
    links = " to ".join(x or "unknown" for x in c["connects"])
    lines.append(f"| {c['id']} | {links} | {c['note']} |")
lines.extend([
    "",
    "S01: two modeled flights and a turning area; the drawn 7 / 15 tread lines are illustrative, not verified riser counts. Measure rise, going, flight width, landing, arrival direction, headroom and guard per floor.",
    "",
    "HD-11: homeowner-stated 11 ft floor-to-floor and approximately 9 in band drop, not measured on site. The older 3.188 m slab and 2.959 m band estimates depend on assumed slab and finish thicknesses. R05 is separately homeowner-reported at a 3.048 m band and approximately 3.277 m centre; this conflicts with the older slab estimate. The R05 slab is unmeasured. Verify all levels and cavities on site.",
    "",
    "South-up: page top south, bottom north, left east, right west. The homeowner-described compass is not a surveyed true bearing.",
    "",
    "Current children's layout relationships cite MR.RAJESH_INTERIOR_RENDERS.pdf pages 16-18, which are undimensioned perspectives, not a scale survey.",
    "",
])
(out / "room-opening-index.md").write_text("\n".join(lines), encoding="utf-8")

W, H = 1191, 842
ink, muted, red, blue = (0.12, 0.23, 0.26), (0.35, 0.43, 0.45), (0.62, 0.20, 0.20), (0.20, 0.36, 0.45)
doc = pymupdf.open()


def cell(page, x, y, value, width, size=11, color=ink, bold=False):
    value = str(value)
    font = "hebo" if bold else "helv"
    while size > 8 and pymupdf.get_text_length(value, fontname=font, fontsize=size) > width:
        size -= .5
    if pymupdf.get_text_length(value, fontname=font, fontsize=size) > width:
        raise ValueError(f"Text does not fit source-index cell: {value}")
    page.insert_text((x, y), value, fontname=font, fontsize=size, color=color)


def page_header(title, number, subtitle):
    p = doc.new_page(width=W, height=H)
    cell(p, 40, 43, title, 1030, 23, bold=True)
    cell(p, 40, 69, subtitle, 1090, 11, color=muted)
    cell(p, 1130, 42, f"{number} / 3", 40, 11, color=muted)
    p.draw_line((40, 88), (W - 40, 88), color=(.78, .82, .82), width=.7)
    return p


def page_footer(page):
    page.draw_line((40, 800), (W - 40, 800), color=(.78, .82, .82), width=.7)
    cell(page, 40, 820, f"MASTER SHA256: {args.sha}", 620, 9, color=muted)
    cell(page, 730, 820, "REVIEW ONLY - NOT A CONSTRUCTION RELEASE", 425, 10, color=red, bold=True)


p = page_header("Rooms and areas - source index", 1, "14 master records; household-reported nominal dimensions require independent site verification")
cell(p, 40, 112, "Historical P page 1 is numeric provenance only; the retired original layout was not consulted.", 1100, 10, color=muted)
for x, name, width in [(40, "ID", 50), (100, "ROOM / AREA", 275), (405, "NOMINAL FEET / INCHES", 230),
                       (675, "NOMINAL METRES", 195), (915, "EVIDENCE", 220)]:
    cell(p, x, 145, name, width, 10, color=blue, bold=True)
for i, r in enumerate(rooms):
    y = 172 + i * 31
    if i % 2 == 0:
        p.draw_rect((40, y - 16, W - 40, y + 9), color=None, fill=(.96, .975, .97))
    original = " x ".join(d["original_feet_inches"] for d in r["dimensions"]) or "Not supplied"
    metric = " x ".join(str(d["value_m"]) for d in r["dimensions"]) if r["dimensions"] else "-"
    status = "Owner-reported; unverified" if r["dimensions"] else "Measure on site"
    for x, val, width in [(40, r["id"], 50), (100, r["name"], 275), (405, original, 230),
                          (675, metric, 195), (915, status, 220)]:
        cell(p, x, y, val, width, 10.5)
cell(p, 40, 635, "R01 includes a lift-side cutout. R08 / R08a form one utility/washing area; confirm its extent.", 1090, 11, color=muted)
cell(p, 40, 660, "R10 is a lift footprint with no established door. R13 is one offset, not a continuous legal setback.", 1090, 11, color=muted)
cell(p, 40, 700, "South-up: top S, bottom N, left E, right W; the bearing is not surveyed.", 1090, 11, color=muted)
cell(p, 40, 725, "F1-F4 are requested instances only: actual storey labels and differences must be surveyed.", 1090, 11, color=red)
page_footer(p)

short_names = {
    "D01": "Main entrance - leaf count unresolved", "D02": "Master bedroom door", "D03": "Children bedroom door",
    "D04": "Attached toilet door", "D05": "Common toilet door", "D06": "Kitchen / utility door",
    "W01": "Kitchen exterior window", "W02": "Kitchen / utility window", "W03": "Master south window",
    "W04": "Master west window", "W05": "Children west window - placeholder", "W06": "Living east window",
    "W07": "Dining east window", "V01": "Attached toilet vent", "V02": "Common toilet vent",
    "G01": "Entrance side panel 1", "G02": "Entrance side panel 2", "PN1": "Pooja niche front",
    "SN1": "Attached shower niche", "SN2": "Common shower niche", "UP1": "Utility parapet opening",
}
status_names = {"scaled_model_not_measured": "Model only", "assumed_not_measured": "Assumed / placeholder",
                "proposed_model_not_measured": "Proposed model", "homeowner_estimate_unverified": "Owner estimate"}
p = page_header("Openings - source index", 2, "All actual opening widths, heights, offsets and hardware remain unmeasured")
for x, name, width in [(40, "ID", 60), (110, "CURRENT MODEL IDENTIFICATION", 340), (500, "MODEL WIDTH m", 145),
                       (685, "BASIS", 190), (900, "ACTUAL / SITE", 245)]:
    cell(p, x, 120, name, width, 10, color=blue, bold=True)
for i, o in enumerate(openings):
    y = 147 + i * 25
    if i % 2 == 0:
        p.draw_rect((40, y - 15, W - 40, y + 7), color=None, fill=(.96, .975, .97))
    for x, val, width in [(40, o["code"], 60), (110, short_names[o["code"]], 340),
                          (500, f'{o["model_width_m"]:.2f}', 145),
                          (685, status_names[o["model_width_status"]], 190),
                          (900, "Not measured; each floor", 245)]:
        cell(p, x, y, val, width, 10.5)
cell(p, 40, 705, "D01: double-leaf architecture versus single-leaf visualization; verify existing leaf count and swing.", 1090, 11, color=red)
cell(p, 40, 730, "W03 offsets are unmeasured; W05 is a visual placeholder. PN1 is built, but estimates and support need review.", 1090, 11, color=muted)
cell(p, 40, 755, "Exact current-master geometry pointers, dimension statuses and floor-specific nulls are in the JSON index.", 1090, 11, color=muted)
page_footer(p)

p = page_header("Connections, stair and levels", 3, "Carry-forward relationships are not verified site openings; all connection widths are unmeasured")
for x, name, width in [(40, "ID", 75), (130, "CONNECTS", 250), (420, "MODEL NOTE - VERIFY ON EACH FLOOR", 700)]:
    cell(p, x, 120, name, width, 10, color=blue, bold=True)
for i, c in enumerate(connections):
    y = 148 + i * 29
    if i % 2 == 0:
        p.draw_rect((40, y - 15, W - 40, y + 9), color=None, fill=(.96, .975, .97))
    cell(p, 40, y, c["id"], 75, 10.5)
    cell(p, 130, y, " to ".join(x or "unknown" for x in c["connects"]), 250, 10.5)
    cell(p, 420, y, c["note"], 700, 10.5)
cell(p, 40, 470, "S01 / STAIR - MODEL ONLY", 700, 12, color=blue, bold=True)
cell(p, 40, 496, "7 and 15 drawn tread lines are illustrative, not verified riser counts.", 1090, 11)
cell(p, 40, 520, "Measure rise, tread/going, width, landings, arrival, headroom and guard on each floor.", 1090, 11)
cell(p, 40, 570, "HEIGHTS - HOMEOWNER-STATED, NOT MEASURED", 700, 12, color=blue, bold=True)
cell(p, 40, 596, "11 ft floor-to-floor; about 9 in band drop. Slab and finish thicknesses are assumed.", 1090, 11)
cell(p, 40, 620, "Older derived slab 3.188 m / band 2.959 m use assumed thicknesses; not a site survey.", 1090, 11)
cell(p, 40, 644, f"R05 only: band {r05_ceiling['band_h_m']:.3f} m / centre approx. {r05_ceiling['tray_h_m']:.3f} m, homeowner-reported.", 1090, 11)
cell(p, 40, 668, "R05 slab unmeasured; the reported centre conflicts with the older slab estimate. Survey before work.", 1090, 11, color=red)
cell(p, 40, 692, "Bath, utility, lobby and balcony levels and opening heads/sills require survey.", 1090, 11)
cell(p, 40, 742, "Children's layout reference: MR.RAJESH_INTERIOR_RENDERS.pdf pages 16-18.", 1090, 11, color=muted)
cell(p, 40, 766, "Those perspectives establish relationships only, not dimensions or whole-house masonry.", 1090, 11, color=muted)
page_footer(p)
doc.set_toc([[1, "Rooms and areas", 1], [1, "Openings", 2], [1, "Connections, stair and levels", 3]])
doc.set_metadata({"title": "Room and opening source index - review only",
                  "subject": f"Canonical house-design.json sha256 {args.sha}; not a construction release"})
pdf_path = out / "room-opening-index.pdf"
doc.save(pdf_path, garbage=4, deflate=True)
doc.close()

with pymupdf.open(pdf_path) as proof:
    if len(proof) != 3:
        raise RuntimeError("The source index must have three pages.")
    texts = [page.get_text() for page in proof]
    if any(args.sha not in t or "NOT A CONSTRUCTION RELEASE" not in t for t in texts):
        raise RuntimeError("A source-index PDF page lacks its source hash or review hold.")
    if any(r["id"] not in texts[0] for r in rooms) or any(o["code"] not in texts[1] for o in openings):
        raise RuntimeError("The source-index PDF omits a room or opening identifier.")
    if any(c["id"] not in texts[2] for c in connections) or "illustrative" not in texts[2]:
        raise RuntimeError("The source-index PDF omits a connection or stair hold.")
    if any(term not in texts[2] for term in ("3.048 m", "3.277 m", "R05 slab unmeasured", "conflicts")):
        raise RuntimeError("The source-index PDF omits the reported R05 levels or unresolved slab conflict.")
    for i, page in enumerate(proof, 1):
        (out / f"room-opening-index-{i:02}.svg").write_text(page.get_svg_image(text_as_path=False), encoding="utf-8")
        page.get_pixmap(matrix=pymupdf.Matrix(1.6, 1.6), alpha=False).save(out / f"room-opening-index-{i:02}.png")

if master.read_bytes() != master_bytes:
    raise RuntimeError("Canonical master changed during source-index generation.")
files = [{"file": p.name, "sha256": digest(p), "bytes": p.stat().st_size}
         for p in sorted(out.iterdir()) if p.is_file() and p.name != "source-index-verification.json"]
receipt = {
    "schema": "civil_source_index_receipt/1",
    "source_master": {"path": str(master), "sha256": args.sha},
    "source_register_sha256": digest(register_path),
    "construction_release": False,
    "checks": {
        "rooms": len(rooms), "homeowner_reported_dimensions": sum(len(r["dimensions"]) for r in rooms),
        "model_openings": len(openings), "connections": len(connections), "pdf_pages": len(texts),
        "all_opening_geometry_pointers_resolved": True,
        "all_actual_opening_dimensions_unmeasured": all(o["actual_width_m"] is None and o["actual_height_m"] is None for o in openings),
        "master_hash_and_construction_hold_on_every_page": True,
    },
    "sheets": [
        {"title": "Rooms and areas - source index"},
        {"title": "Openings - source index"},
        {"title": "Connections, stair and levels"},
    ],
    "files": files,
}
(out / "source-index-verification.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
print(json.dumps({"rooms": len(rooms), "dimensions": sum(len(r["dimensions"]) for r in rooms),
                  "openings": len(openings), "connections": len(connections),
                  "pdf_sha256": digest(pdf_path), "master_sha256": args.sha}, indent=2))
