"""Provisional wardrobe internals, derived from the current storage dimensions."""
from copy import deepcopy
from html import escape
from pathlib import Path

import pymupdf

PANEL_MM = 18
BACK_MM = 9
WALL_GAP_MM = 25
SHUTTER_ALLOWANCE_MM = 25
TOP_SHELF_MM = 1900
LONG_RAIL_MM = 1750
DOUBLE_RAILS_MM = (1800, 950)
DRAWERS_MM = ((300, 480), (480, 660))
PULLOUT_MM = (700, 820)
PULLOUT_UNIT_INR = (1000, 2500)


def mm(value_m):
    return round(value_m * 1000, 1)


def ft_in(value_mm):
    inches = round(value_mm / 25.4)
    return f"{inches // 12} ft {inches % 12} in"


def dimension(value_mm):
    return f"{round(value_mm):,} mm ({ft_in(value_mm)})"


def bay_width(width_mm, count):
    net = width_mm - (count + 1) * PANEL_MM
    if net <= 0:
        raise ValueError(f"{width_mm} mm is insufficient for {count} bays and their panels")
    return round(net / count, 1)


def cabinet_depth(envelope_mm, allowances_mm):
    usable = envelope_mm - sum(allowances_mm)
    if usable <= 0:
        raise ValueError(f"{envelope_mm} mm cabinet depth is insufficient for its allowances")
    return round(usable, 1)


def bay(name, kind, clear_width_mm):
    result = {
        "id": name, "kind": kind, "clear_width_mm": clear_width_mm,
        "shelf_heights_ffl_mm": [], "rail_heights_ffl_mm": [],
        "drawers_ffl_mm": [], "pullouts_ffl_mm": [], "lockable_drawer": False,
    }
    if kind == "long_hang":
        result.update(shelf_heights_ffl_mm=[TOP_SHELF_MM], rail_heights_ffl_mm=[LONG_RAIL_MM],
                      contents="Long dresses/kurtas, suits or folded sarees on smooth hangers; verify garment length.")
    elif kind == "double_short":
        result.update(shelf_heights_ffl_mm=[TOP_SHELF_MM], rail_heights_ffl_mm=list(DOUBLE_RAILS_MM),
                      contents="Two rows for child clothes or short shirts; actual lengths must be checked.")
    elif kind == "fold_drawers":
        result.update(shelf_heights_ffl_mm=[1050, 1400, 1650, TOP_SHELF_MM],
                      drawers_ffl_mm=[list(d) for d in DRAWERS_MM], pullouts_ffl_mm=[list(PULLOUT_MM)],
                      contents="Folded clothes, two drawers and one removable pull-out tray.")
    elif kind == "child_fold_drawers":
        result.update(shelf_heights_ffl_mm=[1050, 1250, 1450, 1650, TOP_SHELF_MM],
                      drawers_ffl_mm=[list(d) for d in DRAWERS_MM], pullouts_ffl_mm=[list(PULLOUT_MM)],
                      contents="Folded clothes, two drawers and one accessory pull-out tray.")
    elif kind == "child_linen":
        result.update(shelf_heights_ffl_mm=[500, 800, 1100, 1500, TOP_SHELF_MM],
                      contents="Adjustable folded clothes and light linen; bulky bedding goes to a verified loft.")
    elif kind == "shallow_locked":
        result.update(shelf_heights_ffl_mm=[400, 650, 1100, 1450, TOP_SHELF_MM],
                      drawers_ffl_mm=[[700, 880]], lockable_drawer=True,
                      contents="Small folded items and one lockable drawer; not a security safe.")
    elif kind == "shallow_shelves":
        result.update(shelf_heights_ffl_mm=[400, 700, 1000, 1300, 1600, TOP_SHELF_MM],
                      contents="Folded clothes, toiletries or accessories; no normal-depth hanging.")
    elif kind == "shallow_shelves_five":
        result.update(shelf_heights_ffl_mm=[450, 800, 1150, 1500, TOP_SHELF_MM],
                      contents="Adjustable shallow shelves for folded garments and accessories.")
    elif kind == "utility_shelf":
        result.update(shelf_heights_ffl_mm=[400],
                      contents="One adjustable shelf; leave any plumbing, leaks and service access clear.")
    elif kind == "utility_tall":
        result.update(contents="Small cleaning bin or supplies below the counter; keep plumbing accessible.")
    elif kind == "shoe_shelves":
        result.update(shelf_heights_ffl_mm=[250, 450, 650],
                      contents="Four levels including the base; adjust a shelf for taller footwear.")
    else:
        raise ValueError(f"Unknown provisional bay kind: {kind}")
    return result


def section(name, width_mm, depth_mm, kinds, *, back_allowances, item_id):
    count = len(kinds)
    clear_width = bay_width(width_mm, count)
    result = {
        "id": name, "item_id": item_id, "width_mm": round(width_mm, 1),
        "depth_envelope_mm": round(depth_mm, 1),
        "estimated_clear_depth_mm": cabinet_depth(depth_mm, back_allowances),
        "clear_width_formula": "(external width - (bay count + 1) x 18 mm) / bay count",
        "width_status": "proposed_placeholder_not_site_measured",
        "bays": [bay(f"{name}{i + 1}", kind, clear_width) for i, kind in enumerate(kinds)],
        "checks": [],
    }
    if any(k in ("long_hang", "double_short") for k in kinds):
        if clear_width < 480:
            result["checks"].append("Bay under the 480 mm working hanger-width target; test actual adult hangers and revise if tight.")
        if result["estimated_clear_depth_mm"] < 560:
            result["checks"].append("Clear depth under the 560 mm working hanging-depth target; verify hangers and shutters.")
    return result


def interiors(data):
    """Derive a fresh schematic whenever master dimensions change; no master writes."""
    items = {item["id"]: item for item in data["items"]}
    zones = data["R04"]["south_wardrobe_zones_m"]
    window = data["R04"]["window_bay_m"]
    r04 = []
    for zone, name in zip(zones, ("A", "B")):
        sec = section(name, mm(zone[2] - zone[0]), mm(zone[3] - zone[1]),
                      ("long_hang", "double_short", "fold_drawers"),
                      back_allowances=(WALL_GAP_MM, SHUTTER_ALLOWANCE_MM, BACK_MM),
                      item_id="R04 split placeholder")
        sec["bays"][1]["contents"] = "Two rows for short shirts, blouses or kurtas; verify actual lengths."
        r04.append(sec)
    r04[0]["bays"][2]["lockable_drawer"] = True
    r04[1]["bays"][2]["lockable_drawer"] = True
    child = items["ST-R05-WR01"]
    cu = child["bounds_uv_m"]
    r05 = section("C", mm(cu[3] - cu[1]), mm(cu[2] - cu[0]),
                  ("long_hang", "double_short", "child_fold_drawers", "child_linen"),
                  back_allowances=(WALL_GAP_MM, SHUTTER_ALLOWANCE_MM, BACK_MM),
                  item_id=child["id"])
    r05["bays"][0]["contents"] = "Long uniforms, dresses or coats; adjust the rail as the child grows."
    r05["bays"][2]["lockable_drawer"] = True
    dressing = items["ST-R04a-WR01"]
    db = dressing["bounds_m"]
    r04a = section("D", mm(db[3] - db[1]), mm(db[2] - db[0]),
                   ("shallow_locked", "shallow_shelves", "shallow_shelves", "shallow_shelves_five"),
                   back_allowances=(20, BACK_MM), item_id=dressing["id"])
    utility = items["ST-R08-UC01"]
    ub = utility["bounds_m"]
    r08 = section("U", mm(ub[3] - ub[1]), mm(ub[2] - ub[0]),
                  ("utility_shelf", "utility_tall"),
                  back_allowances=(BACK_MM, PANEL_MM), item_id=utility["id"])
    shoe = items["ST-R09-SH01"]
    sb = shoe["bounds_m"]
    r09 = section("S", mm(sb[2] - sb[0]), mm(sb[3] - sb[1]),
                  ("shoe_shelves", "shoe_shelves"), back_allowances=(BACK_MM, PANEL_MM), item_id=shoe["id"])

    rooms = {
        "R04": {
            "name": "Master split wardrobe", "sections": r04, "height_mm": 2100,
            "plinth_top_mm": 100, "window_gap_mm": mm(window[2] - window[0]),
            "loft_height_range_mm": [2130, 3080],
            "loft": "Concept above the split and W03; actual section, support and curtain pocket unmeasured.",
            "holds": ["Split widths are placeholders; W03 and curtain pocket require site measurement.",
                      "Adult hangers must fit the computed clear bay/depth; long-hang clearance is before hanger allowance."],
        },
        "R05": {
            "name": "Children's wardrobe", "sections": [r05], "height_mm": mm(child["height_range_m"][1]),
            "plinth_top_mm": mm(child["plinth_m"][1]), "door_segment_mm": mm(cu[1]),
            "door_opening_mm": [mm(v) for v in data["R05"]["door_opening_v_m"]],
            "loft_height_range_mm": [mm(v) for v in items["ST-R05-LF01"]["height_range_m"]],
            "loft": "One continuous door-to-wardrobe loft; dimensions/support unmeasured and six vs eight leaves unresolved.",
            "holds": ["Keep existing room layout; the bed/study 387.6 mm corner gap is a site hold.",
                      "Use the short double-hang for short items only; adjust for a growing child."],
        },
        "R04a": {
            "name": "Dressing cabinet", "sections": [r04a], "height_mm": mm(dressing["height_range_m"][1]),
            "plinth_top_mm": mm(dressing["height_range_m"][0]),
            "loft_height_range_mm": [mm(v) for v in items["ST-R04a-LF01"]["height_range_m"]],
            "loft": "Existing/proposed loft envelope unmeasured; support and clearance require checking.",
            "holds": ["Selected in scope, but clear dressing width and opening/door operation remain unmeasured.",
                      "Shallow cabinet: shelves and a drawer only; normal full-depth hanging is not provided."],
        },
        "R08": {
            "name": "Utility under-counter", "sections": [r08], "height_mm": mm(utility["height_range_m"][1]),
            "plinth_top_mm": mm(utility["height_range_m"][0]),
            "loft_height_range_mm": [mm(v) for v in items["ST-R08-LF01"]["height_range_m"]],
            "loft": "Utility loft shutters are separately allowed; shelf support and dimensions unmeasured.",
            "holds": ["Selected in scope; plumbing and service access may alter the shelf layout.",
                      "Keep the kitchen-to-south wall straight; no enclosing return is proposed."],
        },
        "R09": {
            "name": "Entry shoe cabinet", "sections": [r09], "height_mm": mm(shoe["height_range_m"][1]),
            "plinth_top_mm": mm(shoe["height_range_m"][0]),
            "loft": "No entry loft is assumed or costed.",
            "holds": ["Confirm shoe length, egress, rain exposure and anti-tip restraint.",
                      "Four levels in each of two bays: up to about 16 pairs only if pairs fit; not guaranteed."],
        },
    }
    result = {
        "schema": "wardrobe-interiors/1",
        "source_master_sha256": data.get("interior_generation_basis_sha256", data["source_master_sha256"]),
        "status": "provisional_design_not_homeowner_approved_or_fabrication_released",
        "parameter_basis": {
            "widths_and_depths": "Recomputed from current storage section/item bounds on each generation; all are placeholders until surveyed.",
            "panel_mm": PANEL_MM, "back_mm": BACK_MM,
            "top_shelf_ffl_mm": TOP_SHELF_MM, "long_rail_ffl_mm": LONG_RAIL_MM,
            "long_rail_to_base_mm": LONG_RAIL_MM - 100,
            "double_rail_ffl_mm": list(DOUBLE_RAILS_MM),
            "double_upper_rail_to_lower_mm": DOUBLE_RAILS_MM[0] - DOUBLE_RAILS_MM[1],
            "double_lower_rail_to_base_mm": DOUBLE_RAILS_MM[1] - 100,
            "drawer_fronts_ffl_mm": [list(d) for d in DRAWERS_MM],
            "accessory_pullout_ffl_mm": list(PULLOUT_MM),
            "short_hang_caveat": ("Two 1000 mm drops do not fit below a 1900 mm shelf over a 100 mm plinth; "
                                  "the 850/850 mm rail-to-obstruction distances are for short items only, "
                                  "before hanger and clearance deductions. The upper rail has 82 mm to the assumed "
                                  "18 mm shelf underside; verify the hanger hook and hardware. Adjust after measurement."),
            "reach_and_load_caveat": ("Rail and shelf heights are working ergonomic targets, not a code requirement. "
                                      "Confirm user reach, hanger/garment sizes, shutter swing, support and load on site."),
        },
        "rooms": rooms,
        "hardware_delta": {
            "reference_allowances": {
                "wardrobe_and_loft_hinges_each_per_flat": 92,
                "drawer_channel_pairs_per_flat": 7,
                "locks_each_per_flat": 4,
                "note": ("Reference counts from the previous single-run R04 and eight-leaf R05-loft cost model; "
                         "not final quantities. Runner low-end evidence is not soft-close."),
            },
            "additional_pullout_trays_per_flat": 3,
            "tray_allocation": {"R04": 2, "R05": 1},
            "tray_unit_inr": list(PULLOUT_UNIT_INR),
            "per_flat_inr": [3 * n for n in PULLOUT_UNIT_INR],
            "four_flats_inr": [12 * n for n in PULLOUT_UNIT_INR],
            "status": "UNVERIFIED allowance; provisional interior choice, not a quote or approved purchase",
            "includes": "One tray/basket and compatible slide pair per proposed pull-out, in addition to the reference drawers.",
            "unpriced": ("R04 split panel/shutter/rail changes; utility carcass, partition, base and shelf; "
                         "shoe carcass, shelf supports and fitments not demonstrably included in the front/top allowances; "
                         "upgrading baseline runners to soft-close, locks/anchors/lighting and final installation. "
                         "Re-quantity and quote; do not add items already included by a supplier."),
            "wardrobe_lighting": "None newly selected or costed; coordinate any later switched light with the electrical plan.",
        },
    }
    for room_id, room in rooms.items():
        for sec in room["sections"]:
            for b in sec["bays"]:
                for level in b["shelf_heights_ffl_mm"] + b["rail_heights_ffl_mm"]:
                    if not room["plinth_top_mm"] < level < room["height_mm"]:
                        raise ValueError(f"{room_id}/{b['id']} level {level} mm is outside its usable height")
                for low, high in b["drawers_ffl_mm"] + b["pullouts_ffl_mm"]:
                    if not room["plinth_top_mm"] <= low < high <= room["height_mm"]:
                        raise ValueError(f"{room_id}/{b['id']} drawer or tray is outside its usable height")
                    if any(low < shelf < high for shelf in b["shelf_heights_ffl_mm"]):
                        raise ValueError(f"{room_id}/{b['id']} shelf crosses a drawer or tray")
                for rail in b["rail_heights_ffl_mm"]:
                    upper = [shelf for shelf in b["shelf_heights_ffl_mm"] if shelf > rail]
                    if upper and min(upper) - PANEL_MM - rail < 70:
                        raise ValueError(f"{room_id}/{b['id']} has insufficient working hanger-hook space above the rail")
    return result


class Drawing:
    def __init__(self, title, subtitle, master_sha):
        self.svg = [
            '<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="950" viewBox="0 0 1400 950">',
            '<rect width="1400" height="950" fill="white"/>',
            '<style>text{font-family:Arial,sans-serif;fill:#172b39}</style>',
        ]
        self.text(50, 42, title, 26, bold=True)
        self.text(50, 72, subtitle, 16)
        self.line(50, 90, 1350, 90)
        self.text(50, 920, "PROVISIONAL INTERIORS | APPROXIMATE SIZES | NOT FOR FABRICATION", 17, color="#a13e2c")
        self.text(50, 942, "Master " + master_sha, 12)

    def text(self, x, y, value, size=15, *, anchor="start", bold=False, color="#172b39"):
        self.svg.append(
            f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" text-anchor="{anchor}" '
            f'style="fill:{color};font-weight:{"bold" if bold else "normal"}">{escape(str(value))}</text>')

    def line(self, x1, y1, x2, y2, color="#264d60", dash=False):
        self.svg.append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="{color}" stroke-width="2"' + (' stroke-dasharray="7 5"' if dash else "") + "/>")

    def rect(self, x, y, w, h, fill="none", stroke="#264d60", dash=False):
        self.svg.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="2"' +
            (' stroke-dasharray="7 5"' if dash else "") + "/>")

    def save(self, output, name):
        svg = "\n".join(self.svg + ["</svg>"])
        (output / (name + ".svg")).write_text(svg, encoding="utf-8")
        with pymupdf.open(stream=svg.encode("utf-8"), filetype="svg") as doc:
            doc[0].get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5)).save(output / (name + ".png"))


def draw_section(d, sec, x, floor, sx, sy, height, bottom):
    width = sec["width_mm"]
    d.rect(x, floor - height * sy, width * sx, height * sy, "#f7fbfa")
    bay_count = len(sec["bays"])
    outer_bay_width = width / bay_count
    for n, b in enumerate(sec["bays"]):
        bx = x + n * outer_bay_width * sx
        bw = outer_bay_width * sx
        if n:
            d.line(bx, floor - height * sy, bx, floor)
        for shelf in b["shelf_heights_ffl_mm"]:
            d.line(bx + 3, floor - shelf * sy, bx + bw - 3, floor - shelf * sy, "#537d7c")
        for rail in b["rail_heights_ffl_mm"]:
            yy = floor - rail * sy
            d.line(bx + 8, yy, bx + bw - 8, yy, "#a46e35")
        for lo, hi in b["drawers_ffl_mm"]:
            d.rect(bx + 4, floor - hi * sy, bw - 8, (hi - lo) * sy, "#e6eef1")
            d.text(bx + bw / 2, floor - ((lo + hi) / 2) * sy + 4,
                   "LOCKED DRAWER" if b["lockable_drawer"] and lo == b["drawers_ffl_mm"][0][0] else "DRAWER",
                   12, anchor="middle")
        for lo, hi in b["pullouts_ffl_mm"]:
            d.rect(bx + 4, floor - hi * sy, bw - 8, (hi - lo) * sy, "#fff2d6")
            d.text(bx + bw / 2, floor - ((lo + hi) / 2) * sy + 4, "PULL-OUT", 12, anchor="middle")
        label = {
            "long_hang": ("LONG", "HANG"), "double_short": ("SHORT", "HANG x2"),
            "fold_drawers": ("FOLDED", "CLOTHES"), "child_fold_drawers": ("FOLDED", "CLOTHES"),
            "child_linen": ("LINEN", "SHELVES"), "shallow_locked": ("SMALL", "ITEMS"),
            "shallow_shelves": ("FOLDED", "ITEMS"), "shallow_shelves_five": ("FOLDED", "ITEMS"),
            "utility_shelf": ("SHELF", "CHECK PIPES"), "utility_tall": ("BIN / SUPPLIES", "CHECK PIPES"),
            "shoe_shelves": ("SHOES", "4 LEVELS"),
        }[b["kind"]]
        if b["kind"] == "shoe_shelves":
            yy = floor - height * sy + 15
        elif b["kind"] in ("utility_shelf", "utility_tall"):
            yy = floor - height * sy + 23
        elif b["kind"] == "double_short":
            yy = floor - 1500 * sy
        elif b["kind"] == "long_hang":
            yy = floor - 1550 * sy
        else:
            yy = floor - 1800 * sy
        d.text(bx + bw / 2, yy, label[0], 13, anchor="middle", bold=True)
        d.text(bx + bw / 2, yy + 17, label[1], 13, anchor="middle")
        d.text(bx + bw / 2, floor + 22, b["id"], 15, anchor="middle", bold=True)
        d.text(bx + bw / 2, floor + 41, f'{round(b["clear_width_mm"])} clear', 12, anchor="middle")
    if bottom > 0:
        d.rect(x, floor - bottom * sy, width * sx, bottom * sy, "#dce3e3")


def draw_interior_sheets(model, output, current_master_sha=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    names = []
    for room_id in ("R04", "R05", "R04a", "R08", "R09"):
        room = model["rooms"][room_id]
        d = Drawing(f'{room_id} | {room["name"].upper()} | INTERIOR ELEVATION',
                    "Widths are placeholders. Heights are FFL working targets; shelves and supports remain adjustable.",
                    current_master_sha or model["source_master_sha256"])
        if current_master_sha and current_master_sha != model["source_master_sha256"]:
            d.text(50, 895, "Original interior-generation basis " + model["source_master_sha256"], 12)
        floor, sy, left, available = 705, 0.17, 75, 1250
        sections = room["sections"]
        if room_id == "R04":
            span = sections[0]["width_mm"] + room["window_gap_mm"] + sections[1]["width_mm"]
        elif room_id == "R05":
            span = room["door_segment_mm"] + sections[0]["width_mm"]
        else:
            span = sections[0]["width_mm"]
        sx = min(available / span, 0.85)
        xpos = left + (available - span * sx) / 2
        d.text(xpos, 125, f"Reference frontage {dimension(span)}; section sizes below are not cut sizes.", 16, bold=True)
        if room_id in ("R04", "R05", "R04a", "R08"):
            loft_low, loft_high = room["loft_height_range_mm"]
            d.rect(xpos, floor - loft_high * sy, span * sx, (loft_high - loft_low) * sy, "#fbf7fb", "#a172a5", True)
            d.text(xpos + span * sx / 2, floor - (loft_low + loft_high) / 2 * sy,
                   "LOFT: HEIGHT / DEPTH / SUPPORT UNMEASURED", 16, anchor="middle", color="#6f5276")
        if room_id == "R04":
            draw_section(d, sections[0], xpos, floor, sx, sy, room["height_mm"], room["plinth_top_mm"])
            gap_x = xpos + sections[0]["width_mm"] * sx
            gap_w = room["window_gap_mm"] * sx
            d.rect(gap_x, floor - 2100 * sy, gap_w, 2100 * sy, "#f2f8ff", "#6f9aad", True)
            d.text(gap_x + gap_w / 2, floor - 1100 * sy, "W03 BAY", 18, anchor="middle")
            d.text(gap_x + gap_w / 2, floor - 980 * sy, "HEAD / SILL UNKNOWN", 13, anchor="middle")
            draw_section(d, sections[1], gap_x + gap_w, floor, sx, sy, room["height_mm"], room["plinth_top_mm"])
        elif room_id == "R05":
            door = room["door_segment_mm"]
            opening_start, opening_end = room["door_opening_mm"]
            if not (0 <= opening_start < opening_end <= door):
                raise ValueError("R05 door opening does not fit its loft-door segment")
            d.rect(xpos, floor - 2130 * sy, door * sx, 2130 * sy, "#fffdf9")
            door_x, door_width = xpos + opening_start * sx, (opening_end - opening_start) * sx
            d.rect(door_x, floor - 2130 * sy, door_width, 2130 * sy, "#fff8ec", "#b98462", True)
            d.text(door_x + door_width / 2, floor - 900 * sy, "D03 ENTRY", 16, anchor="middle")
            d.text(door_x + door_width / 2, floor - 760 * sy, f'{round(opening_end - opening_start)} mm approx.', 13, anchor="middle")
            draw_section(d, sections[0], xpos + door * sx, floor, sx, sy, room["height_mm"], room["plinth_top_mm"])
        else:
            draw_section(d, sections[0], xpos, floor, sx, sy, room["height_mm"], room["plinth_top_mm"])
        d.text(50, 154, f'Unit height {dimension(room["height_mm"])} FFL; reference loft (if shown) is not a measured section.', 15)
        if room_id in ("R04", "R05"):
            notes = [
                f'Long rail {dimension(LONG_RAIL_MM)} FFL; nominal rail-to-base {dimension(LONG_RAIL_MM - 100)} BEFORE hanger clearance.',
                f'Double rails {dimension(DOUBLE_RAILS_MM[0])} / {dimension(DOUBLE_RAILS_MM[1])} FFL; upper/lower drops only 850 / 850 mm.',
                f'Top shelf {dimension(TOP_SHELF_MM)} FFL; drawers {dimension(DRAWERS_MM[0][0])} to {dimension(DRAWERS_MM[-1][1])} FFL.',
                "Use double hanging for short items only; two 1,000 mm drops do not fit. Confirm hangers, reach and support.",
            ]
        elif room_id == "R04a":
            notes = [
                f'Estimated clear depth {dimension(sections[0]["estimated_clear_depth_mm"])}; NO normal full-depth hanging.',
                f'Lockable drawer {dimension(700)} to {dimension(880)} FFL; top shelf {dimension(TOP_SHELF_MM)} FFL.',
                "Selected cabinet: field-check dressing width, door and shutter swing before proceeding.",
                "The lockable drawer is not a security safe. Loft load and curtain/light access remain unverified.",
            ]
        elif room_id == "R08":
            notes = [
                f'One shelf at {dimension(400)} FFL is a concept only; relocate/remove if plumbing or services require it.',
                "Selected under-counter shutters are allowed; any carcass, base, partition and shelf need a separate quote.",
                "Measure counter, drainage and door swing; keep chemicals safely stored away from children.",
                "The loft above is a separate assumed envelope; no new corner-enclosing utility wall is proposed.",
            ]
        else:
            notes = [
                f'Three adjustable intermediate shelves near {dimension(250)}, {dimension(450)} and {dimension(650)} FFL.',
                "Two bays x four levels: up to approximately 16 pairs only if the actual pairs fit.",
                "No entry loft is assumed. Carcass/shelf support not confirmed in front/top allowance; request a quote.",
                "Confirm rain exposure and egress; qualify anti-tip restraints against the actual substrate.",
            ]
        for n, note in enumerate(notes):
            d.text(50, 790 + n * 24, note, 15)
        name = f"{room_id}-interior-elevation"
        d.save(output, name)
        names.append(name)
    return names
