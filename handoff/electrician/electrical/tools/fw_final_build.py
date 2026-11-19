"""Build the source-bound electrician review package without editing the master."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "lighting" / "source"))
from validate_cct_revision import CURRENT_SHA as CCT_SHA, PRIOR_SHA, load_verified, verify
from validate_cbr_revision import CURRENT_SHA, verify as verify_cbr
FIXED = ROOT / "fixed-white"
SESSION = Path(r"not-distributed/session-state")
HOUSE = SESSION / "c40feaae-bd23-4667-9a64-9c2a607f3cd4" / "files" / "house-current"
LIGHTING = SESSION / "d7d23350-9d8c-4c65-bf59-343a3e4c6a14" / "files" / "final-lighting-fixed-white"
FILES = SESSION / "ff3336cd-ec89-4470-abbb-bd731ff9c1eb" / "files"
EXPECTED_MASTER = CURRENT_SHA
OPTION_SHA = "2fdcce1a3fdf7ff04aae045875f6a40cfd362cc58de228f70098e4fab379726a"

PDF_SOURCES = [
    ("HLG-480H-SPEC.PDF", "Mean Well HLG-480H manufacturer datasheet"),
    ("ELG-240-SPEC.PDF", "Mean Well ELG-240 manufacturer datasheet"),
    ("ELG-150-SPEC.PDF", "Mean Well ELG-150 manufacturer datasheet"),
    ("meanwell-led-driver-installation-manual-en.pdf", "Mean Well LED-driver installation manual"),
    ("skydance-t1k-t2k-manual.pdf", "Skydance T1-K/T2-K/T3-K manufacturer manual"),
    ("wipro-mollis-pro.pdf", "Wipro Mollis Pro product leaflet"),
    ("wipro-mollis-range.pdf", "Wipro Mollis product catalogue"),
    ("wipro-fokus-plus.pdf", "Wipro Fokus Plus product catalogue, image-only"),
    ("signify-greenspace-flex.pdf", "Signify GreenSpace Flex family leaflet"),
    ("orient-consumer-catalogue.pdf", "Orient Electric consumer lighting catalogue"),
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def as_cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return "; ".join(as_cell(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, separators=(",", ":"), ensure_ascii=False)
    return str(value)


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"No data for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({key: as_cell(value) for key, value in row.items()})


def table(headers: list[str], rows: list[list[object]]) -> str:
    def clean(value: object) -> str:
        return as_cell(value).replace("|", "/").replace("\n", " ")
    lines = ["| " + " | ".join(headers) + " |",
             "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(clean(value) for value in row) + " |" for row in rows)
    return "\n".join(lines)


def amount(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def prepare_floor_figure(destination: Path, master: dict) -> None:
    lighting = master["lighting"]
    rooms = lighting["design_inputs"]["rooms"]
    fixtures = lighting["fixtures"]
    curtains = lighting["curtain_pocket_s1"]["strips"]
    points = [p for room in rooms for p in room["poly_ft"]]
    points += [p for f in fixtures for p in (f["path_ft"] or [[f["x_ft"], f["z_ft"]]])]
    points += [p for strip in curtains for p in strip["polyline_ft"]]
    min_x, max_x = min(p[0] for p in points) - 1, max(p[0] for p in points) + 1
    min_z, max_z = min(p[1] for p in points) - 1, max(p[1] for p in points) + 1
    scale = min(500 / (max_x - min_x), 790 / (max_z - min_z))

    def project(p):
        return 40 + (p[0] - min_x) * scale, 115 + (p[1] - min_z) * scale

    def coords(pts):
        return " ".join(f"{x:.2f},{y:.2f}" for x, y in map(project, pts))

    colours = {2700: "#b54800", 3000: "#007450", 4000: "#005c9c"}
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="900" height="1030" viewBox="0 0 900 1030" '
        f'data-min-x="{min_x}" data-min-z="{min_z}" data-scale="{scale}">',
        '<rect width="900" height="1030" fill="white"/>',
        '<g font-family="Arial, Helvetica, sans-serif" fill="#20343b">',
        '<text x="40" y="33" font-size="21" font-weight="bold">Lighting and controls: conceptual layout</text>',
        '<text x="40" y="58" font-size="13" fill="#a13620">REVIEW ONLY - NOT FOR WIRING OR CONSTRUCTION</text>',
        '<text x="40" y="80" font-size="12">Approximate lighting zones, not surveyed walls. Lines are fittings, not cable routes.</text>',
    ]
    for room in rooms:
        poly = room["poly_ft"]
        cx, cz = project((sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly)))
        lines.append(f'<polygon points="{coords(poly)}" fill="#f3f6f5" stroke="#9aaead" stroke-width="1"/>')
        lines.append(f'<text x="{cx:.2f}" y="{cz:.2f}" text-anchor="middle" font-size="12" fill="#617878">{escape(room["id"])}</text>')

    def fitting(ident, circuit, cct, lane, pts):
        require(cct in colours and pts, f"{ident}: missing plan position or fixed CCT")
        x, y = project(pts[len(pts) // 2])
        colour = colours[cct]
        lines.append(f'<g data-fixture-id="{escape(ident)}" data-circuit="{escape(circuit)}" data-cct-k="{cct}">')
        if len(pts) > 1:
            dash = {"LINE": "9 3 2 3", "PERIM": "7 3", "CURTAIN": "2 4"}.get(lane, "")
            lines.append(f'<polyline points="{coords(pts)}" fill="none" stroke="{colour}" stroke-width="3"'
                         + (f' stroke-dasharray="{dash}"' if dash else "") + '/>')
        lines.append(f'<g data-marker="1" transform="translate({x:.2f} {y:.2f})">')
        if cct == 2700:
            lines.append(f'<circle r="4.3" fill="{colour}" stroke="#111" stroke-width="0.8"/>')
        elif cct == 3000:
            lines.append(f'<path d="M0 -5 L5 0 L0 5 L-5 0 Z" fill="{colour}" stroke="#111" stroke-width="0.8"/>')
        else:
            lines.append(f'<rect x="-4" y="-4" width="8" height="8" fill="{colour}" stroke="#111" stroke-width="0.8"/>')
        if ident in {"CBR-L1", "CBR-X1", "CBR-X2", "CBR-X3", "CBR-X4"}:
            lines.append('<circle r="7" fill="none" stroke="#111" stroke-width="1.1"/>')
        lines.append('</g></g>')

    for fixture in fixtures:
        pts = fixture["path_ft"] or [[fixture["x_ft"], fixture["z_ft"]]]
        fitting(fixture["id"], fixture["circuit"], int(fixture["cct"].removesuffix("K")), fixture["lane"], pts)
    for strip in curtains:
        fitting(strip["id"], "X-" + strip["id"], strip["cct_k"], "CURTAIN", strip["polyline_ft"])

    boards = {}
    for circuit in lighting["controls"]["circuits"]:
        board, pos = circuit["board"], circuit["board_xz_ft"]
        require(pos and len(pos) == 2, f"{circuit['circuit']}: board position missing")
        require(board not in boards or boards[board] == pos, f"{board}: inconsistent board positions")
        boards[board] = pos
    for board, pos in sorted(boards.items()):
        x, y = project(pos)
        lines.append(f'<g data-board-id="{escape(board)}" transform="translate({x:.2f} {y:.2f})">'
                     f'<path d="M0 -6 L6 5 L-6 5 Z" fill="#182c32"/>'
                     f'<text x="8" y="-4" font-size="10" font-weight="bold" '
                     f'paint-order="stroke" stroke="white" stroke-width="3">{escape(board)}</text></g>')
    lines.extend([
        '<g transform="translate(570 130)" font-size="13">',
        '<text y="0" font-size="16" font-weight="bold">Fixed CCT / symbol</text>',
        '<circle cx="7" cy="27" r="5" fill="#b54800" stroke="#111"/><text x="23" y="32">2700 K: LOW / mood / cove</text>',
        '<path d="M7 47 L13 53 L7 59 L1 53 Z" fill="#007450" stroke="#111"/><text x="23" y="58">3000 K: reading / art; lobby</text>',
        '<text x="23" y="75">and balcony HIGH</text>',
        '<rect x="2" y="89" width="10" height="10" fill="#005c9c" stroke="#111"/><text x="23" y="99">4000 K: most HIGH and task</text>',
        '<text y="136" font-size="16" font-weight="bold">Line patterns</text>',
        '<path d="M0 158 H38" stroke="#b54800" stroke-width="3"/><text x="50" y="163">Cove / other strip</text>',
        '<path d="M0 184 H38" stroke="#b54800" stroke-width="3" stroke-dasharray="9 3 2 3"/><text x="50" y="189">LINE strip</text>',
        '<path d="M0 210 H38" stroke="#b54800" stroke-width="3" stroke-dasharray="2 4"/><text x="50" y="215">Curtain strip; no lux credit</text>',
        '<path d="M0 236 H38" stroke="#b54800" stroke-width="3" stroke-dasharray="7 3"/><text x="50" y="241">Bathroom perimeter cove</text>',
        '<path d="M7 255 L14 267 L0 267 Z" fill="#182c32"/><text x="23" y="267">SB = modelled switchboard</text>',
        '<circle cx="7" cy="293" r="7" fill="none" stroke="#111" stroke-width="1.5"/><text x="23" y="298">CBR cove / LINE site hold</text>',
        '<text y="339" font-size="16" font-weight="bold">Before installation</text>',
        '<text y="363">Board positions and all dimensions</text><text y="381">are indicative, not measured.</text>',
        '<text y="407">P01 480 W class: hatch</text><text y="425">location and fit unverified.</text>',
        '<text y="451">No supply hatches or cable routes</text><text y="469">are released or plotted here.</text>',
        '<text y="495">See circuit-labelled lighting plans,</text><text y="513">the switchboard schedule and BoM.</text>',
        '<text y="547">CBR fan: room-centred 1050 mm</text><text y="565">planning sweep; no product selected.</text>',
        '<text y="591">Site, clearance, product, driver and</text><text y="609">protection checks remain open.</text>',
        '</g>',
        '<path d="M840 855 V900 M830 890 L840 900 L850 890" fill="none" stroke="#20343b" stroke-width="3"/>',
        '<text x="840" y="920" text-anchor="middle" font-size="16" font-weight="bold">N</text>',
        '</g></svg>',
    ])
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")


def prepare_curtain_figure(destination: Path, fixed: Path) -> None:
    source = (fixed / "assets" / "fw-curtain-pocket.svg").read_text(encoding="utf-8")
    old = "in the room ceiling (P01/P07/P12/P16)"
    require(source.count(old) == 1, "Expected curtain hatch annotation missing")
    source = source.replace(old, "P01/P07/P12/P16: siting unverified")
    destination.write_text(source, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--house-root", type=Path, default=HOUSE)
    ap.add_argument("--lighting-root", type=Path, default=LIGHTING)
    ap.add_argument("--fixed-root", type=Path, default=FIXED)
    ap.add_argument("--manufacturer-sources", type=Path, default=ROOT / "sources")
    ap.add_argument("--dimmer-sources", type=Path, default=FILES / "low-load-dimmer-research" / "sources")
    ap.add_argument("--master", type=Path)
    ap.add_argument("--prior-master", required=True, type=Path)
    ap.add_argument("--cct-master", required=True, type=Path)
    ap.add_argument("--expected-master-sha", default=EXPECTED_MASTER)
    ap.add_argument("--out", type=Path, default=ROOT / "final-handoff")
    args = ap.parse_args()

    house, lighting_root, fixed = args.house_root.resolve(), args.lighting_root.resolve(), args.fixed_root.resolve()
    master_path = (args.master or house / "house-design.json").resolve()
    expected = args.expected_master_sha.lower()
    require(sha(master_path) == expected, "Master hash differs from the requested basis; no output written")
    master = load(master_path)
    previous_master = load_verified(args.prior_master, PRIOR_SHA)
    cct_master = load_verified(args.cct_master, CCT_SHA)
    delta = verify(previous_master, cct_master)
    cbr_delta = verify_cbr(cct_master, load_verified(master_path, CURRENT_SHA))
    integration_path = house / "generated" / "living-supply-and-cabinet-selections-receipt.json"
    wardrobe_path = house / "generated" / "wardrobe-interiors-reference-receipt.json"
    prior_receipt_path = house / "generated" / "homeowner-final-coordination-integration.json"
    pooja_receipt_path = house / "generated" / "pooja-display-decision-receipt.json"
    option_path = fixed / "data" / "living-low-one-supply-option.json"
    prior_plan_path = fixed / "data" / "fixed-white-control-plan.json"
    prior_plan_receipt_path = fixed / "receipt.json"
    verified_path = lighting_root / "verification.json"
    fragment_path = lighting_root / "lighting-fragment-fixed-white.json"
    integration, wardrobe, prior, pooja = (
        load(integration_path), load(wardrobe_path), load(prior_receipt_path), load(pooja_receipt_path)
    )
    option, plan, verified = load(option_path), load(prior_plan_path), load(verified_path)

    require(wardrobe["after_master_sha256"] == PRIOR_SHA, "Latest wardrobe receipt is not bound to the predecessor")
    require(wardrobe["before_master_sha256"] == integration["after_master_sha256"],
            "Wardrobe and supply receipt chain mismatch")
    before_wardrobe_path = house / "archive" / "before-wardrobe-interiors-review.json"
    require(sha(before_wardrobe_path) == wardrobe["before_master_sha256"], "Prior master snapshot SHA mismatch")
    before_wardrobe = load(before_wardrobe_path)
    for section in ("lighting", "visualization_geometry", "architecture", "decisions", "bathrooms", "open_items"):
        require(previous_master[section] == before_wardrobe[section], f"Wardrobe integration changed {section}")
    old_storage = dict(previous_master["storage"])
    added_reference = old_storage.pop("wardrobe_interiors_review")
    require(old_storage == before_wardrobe["storage"] and added_reference == wardrobe["reference"],
            "Existing storage or the linked wardrobe reference changed")
    require(sha(house / added_reference["file"]) == added_reference["sha256"] == wardrobe["copied_fragment_sha256"],
            "Wardrobe reference fragment SHA mismatch")
    require(all(wardrobe["retained"][key] is False for key in
                ("homeowner_interior_approval", "construction_release", "product_approval", "exact_chain_proven")),
            "A wardrobe or technical release flag is not false")
    require(integration["before_master_sha256"] == pooja["after_master_sha256"], "Pooja and supply receipt chain mismatch")
    require(pooja["before_master_sha256"] == prior["after_master_sha256"], "Homeowner and pooja receipt chain mismatch")
    require(sha(option_path) == OPTION_SHA == integration["source_option_sha256"], "One-supply option SHA mismatch")
    require(sha(prior_plan_path) == prior["source_artifacts"]["electrical_control_plan_sha256"], "Prior control plan SHA mismatch")
    require(sha(prior_plan_receipt_path) == prior["source_artifacts"]["electrical_control_plan_receipt_sha256"], "Prior receipt SHA mismatch")
    require(sha(verified_path) == prior["source_artifacts"]["fixed_white_verification_sha256"], "Historical verification SHA mismatch")
    require(sha(fragment_path) == prior["source_artifacts"]["verified_fixed_white_fragment_sha256"], "Historical lighting fragment SHA mismatch")
    require(prior["source_artifacts"]["fixed_white_verification"] == {"PASS": 82}, "Historical verification count changed")
    require(all(integration["holds"][key] is False for key in ("construction_release", "product_approval", "exact_chain_proven")),
            "A release flag is not false")

    old_master_path = house / "archive" / "before-living-supply-and-cabinet-selections.json"
    require(sha(old_master_path) == integration["before_master_sha256"], "Previous master snapshot SHA mismatch")
    old = load(old_master_path)
    lighting = master["lighting"]
    require(previous_master["lighting"]["fixtures"] == old["lighting"]["fixtures"], "Fixtures changed during the supply integration")
    require(previous_master["lighting"]["design_inputs"] == old["lighting"]["design_inputs"], "Lighting design inputs changed during integration")
    require(previous_master["visualization_geometry"] == old["visualization_geometry"], "Geometry changed during supply integration")
    require(len(lighting["fixtures"]) == 104 and len(lighting["controls"]["circuits"]) == 47,
            "Expected 104 base fixtures and 47 base circuits")

    selected = lighting["curtain_pocket_s1"]
    curtains = selected["strips"]
    require([p["id"] for p in curtains] == ["CURT-LIV", "CURT-DIN", "CURT-MBR-S", "CURT-CBR"],
            "Unexpected selected curtain pockets")
    require(round(sum(p["indicative_strip_length_m"] for p in curtains), 2) == 8.88,
            "Curtain length does not total 8.88 m")
    require(round(sum(p["indicative_strip_length_m"] * 8 for p in curtains), 2) == 71.04,
            "Curtain power does not total 71.04 W")
    require(all(not p["fabrication_release"] and not p["photometry_credit"] and p["cct_k"] == 2700 for p in curtains),
            "Curtain hold, photometry or CCT changed")
    effective = selected["selected_S1_totals"]
    for key, expected_value in {
        "knobs": 21, "knob_outputs": 38, "amplifiers": 3, "psus": 12,
        "psu_nameplate_total_W": 1980, "circuits_including_selected_strips": 51,
        "fittings_including_selected_strips": 108,
    }.items():
        require(effective[key] == expected_value, f"Unexpected integrated total: {key}")
    require(lighting["controls"]["selected_living_low_supply"]["source_option_sha256"] == OPTION_SHA,
            "Master does not reference the chosen one-supply option")

    out = args.out.resolve()
    for subdir in ("figures", "figures/photos", "schedules", "sources", "source-evidence", "tools"):
        (out / subdir).mkdir(parents=True, exist_ok=True)
    for name in ("concept-flat.svg", "concept-living-low.svg"):
        shutil.copy2(fixed / "templates" / name, out / "figures" / name)
    prepare_floor_figure(out / "figures" / "controls-plan.svg", master)
    prepare_curtain_figure(out / "figures" / "curtain-pocket.svg", fixed)

    originals = lighting["controls"]["circuits"]
    circuit_rows, fixture_rows, curtain_rows = [], [], []
    for c in originals:
        code = c["circuit"]
        control = c["knob_group"] or (f"D-{code}" if c["control"] in ("TE", "TRK") else "INTEGRAL")
        circuit_rows.append({
            "circuit": code, "room": "; ".join(c["rooms"]), "lane": c["lane"],
            "fixture_ids": c["fixtures"], "n_fixtures": len(c["fixtures"]),
            "wall_control": control, "board": c["board"], "control_class": c["control"],
            "supply_id": c["psu"], "model_W": c["W_envelope"], "model_outputs": c["sections"],
            "CCT": c["cct"], "release_status": "PRODUCT / CHAIN HOLD",
            "note": c.get("note", ""),
        })
    for p in curtains:
        code = f"X-{p['id']}"
        watts = round(p["indicative_strip_length_m"] * 8, 2)
        circuit_rows.append({
            "circuit": code, "room": p["room"], "lane": "LOW / CURTAIN",
            "fixture_ids": [p["id"]], "n_fixtures": 1, "wall_control": p["target_knob_group"],
            "board": p["fed_from_knob_board"], "control_class": "KNOB1",
            "supply_id": [p["proposed_supply"]], "model_W": watts, "model_outputs": 1,
            "CCT": ["2700K"], "release_status": "UNMEASURED / PRODUCT / CHAIN HOLD",
            "note": "Derived length; no added knob or photometry credit.",
        })
        photo = p.get("site_photo")
        if photo:
            source_photo = house / photo["file"]
            require(source_photo.is_file() and sha(source_photo) == photo["sha256"],
                    f"Site photo missing or changed: {p['id']}")
            shutil.copy2(source_photo, out / "figures" / "photos" / source_photo.name)
        curtain_rows.append({
            "fixture_id": p["id"], "circuit": code, "room": p["room"],
            "length_m_derived": p["indicative_strip_length_m"], "power_W_per_m_assumed": 8,
            "power_W_unrounded_model": watts, "cct_K": 2700,
            "wall_control": p["target_knob_group"], "supply_id": p["proposed_supply"],
            "site_photo_in_master": photo["file"] if photo else "",
            "site_photo_sha256": photo["sha256"] if photo else "",
            "site_photo_in_pack": f"figures/photos/{Path(photo['file']).name}" if photo else "",
            "measurement_status": "OPEN - derived, not measured",
            "photometry_credit": False, "fabrication_release": False,
        })
    require(len(circuit_rows) == 51 and len({c["circuit"] for c in circuit_rows}) == 51,
            "Circuit identifiers are missing or duplicated")
    circuits_by_id = {c["circuit"]: c for c in circuit_rows}
    for code in ("C03", "C04", "C05", "X-CURT-LIV"):
        require(circuits_by_id[code]["supply_id"] == ["P01"], f"{code} is not on P01")

    for f in lighting["fixtures"]:
        fixture_rows.append({
            "id": f["id"], "room": f["room"], "lane": f["lane"], "circuit": f["circuit"],
            "fixture_class": f["type"], "description": f["desc"], "CCT": f["cct"],
            "model_W": f["W_envelope"], "model_lm": f["lm"], "model_beam_deg": f["beam_deg"],
            "IP_target": f["ip"], "CRI_min_target": f["cri_min"], "R9_min_target": f["r9_min"],
            "supply_class": f["supply"], "length_m": f["length_m"],
            "x_ft": f["x_ft"], "z_ft": f["z_ft"], "path_ft": f["path_ft"],
            "photometry_credit": True, "release_status": "REVIEW ONLY",
        })
    for p in curtains:
        fixture_rows.append({
            "id": p["id"], "room": p["room"], "lane": "LOW / CURTAIN", "circuit": f"X-{p['id']}",
            "fixture_class": "COVE_FW", "description": "Unmeasured 24 V fixed warm curtain-pocket strip",
            "CCT": "2700K", "model_W": round(p["indicative_strip_length_m"] * 8, 2),
            "model_lm": None, "model_beam_deg": None, "IP_target": "site and product check",
            "CRI_min_target": 90, "R9_min_target": 50, "supply_class": "24V",
            "length_m": p["indicative_strip_length_m"], "x_ft": None, "z_ft": None,
            "path_ft": p["polyline_ft"], "photometry_credit": False,
            "release_status": "UNMEASURED / REVIEW ONLY",
        })
    require(len(fixture_rows) == 108 and len({f["id"] for f in fixture_rows}) == 108,
            "Fixture identifiers are missing or duplicated")

    group_changes = {x["knob"]: x for x in selected["selected_S1_electrical"]["knob_groups_changed"]}
    knob_rows = []
    for k in plan["knob_groups"]:
        code = k["knob"]
        ids = k["circuits"] + [f"X-{item}" for item in k["curtain_strip"]]
        extra = group_changes.get(code)
        outputs = extra["outputs_after"] if extra else k["outputs"]
        repeaters = extra["amplifiers_after"] if extra else k["amplifiers"]
        psus = ["P01"] if code == "K-LIV-LOW" else k["psus"]
        knob_rows.append({
            "knob": code, "room": k["room"], "board": k["board"], "label": k["label"],
            "circuits": ids, "supplies": psus, "model_W": round(sum(circuits_by_id[i]["model_W"] for i in ids), 2),
            "modeled_outputs": outputs, "modeled_repeaters": repeaters,
            "status": "HOLD - exact chain / product / site",
        })
    require(len(knob_rows) == 21 and sum(k["modeled_outputs"] for k in knob_rows) == 38
            and sum(k["modeled_repeaters"] for k in knob_rows) == 3, "Knob output/repeater totals mismatch")
    knobs_by_id = {k["knob"]: k for k in knob_rows}
    require(knobs_by_id["K-LIV-LOW"]["modeled_outputs"] == 6 and
            knobs_by_id["K-LIV-LOW"]["modeled_repeaters"] == 2 and
            knobs_by_id["K-LIV-LOW"]["model_W"] == 181.52, "Living knob data mismatch")

    wall_rows = []
    for w in plan["wall_controls"]:
        ids = [f"X-{i}" if i.startswith("CURT-") else i for i in w["circuits"]]
        require(all(i in circuits_by_id for i in ids), f"Wall control contains unknown circuit {w['control']}")
        wall_rows.append({
            "control": w["control"], "board": w["board"], "room": w["room"],
            "description": w["label"], "device_class": w["device"], "circuits": ids,
            "modeled_W": round(sum(circuits_by_id[i]["model_W"] for i in ids), 2),
            "status": "PRODUCT / CHAIN HOLD",
        })
    require(len(wall_rows) == 31 and sum(w["control"].startswith("D-") for w in wall_rows) == 10,
            "Wall-control count mismatch")
    fitting_controls = [
        {"circuit": x["circuit"], "room": x["room"], "board": x["board"], "device": x["device"],
         "model_W": x["W"], "CCT": x["cct"], "status": "PRODUCT / SITE HOLD"}
        for x in plan["fitting_mounted_controls"]
    ]

    psu_changes = {x["psu"]: x for x in selected["selected_S1_electrical"]["supplies_changed"]}
    supply_rows = []
    for p in lighting["controls"]["psus"]:
        pid = p["psu"]
        change = psu_changes.get(pid)
        ids = change["circuits"] if change else p["circuits"]
        nameplate = change["nameplate_after_W"] if change else p["nameplate_W"]
        watts = round(sum(circuits_by_id[i]["model_W"] for i in ids), 2)
        supply_rows.append({
            "supply_id": pid, "circuits": ids, "modeled_load_W": watts, "planning_nameplate_W": nameplate,
            "planning_allowance_factor": 0.60, "planning_allowance_W": round(nameplate * 0.60, 2),
            "load_pct_of_planning_allowance": round(watts / (nameplate * 0.60) * 100, 1),
            "site_location_status": "OPEN; previous placeholder not sized for 480 W" if pid == "P01" else "OPEN; indicative hatch only",
            "reference_only": "HLG-480H-24" if pid == "P01" else "generic class / refer to source index",
            "release_status": "PRODUCT / THERMAL / PROTECTION HOLD",
        })
    require(len(supply_rows) == 12 and sum(s["planning_nameplate_W"] for s in supply_rows) == 1980,
            "Supply schedule does not total 12 / 1980 W")
    require("P03" not in {p["supply_id"] for p in supply_rows}, "Removed P03 still appears in supply schedule")
    supply_circuits = [i for p in supply_rows for i in p["circuits"]]
    required_supply_circuits = [c["circuit"] for c in circuit_rows if c["control_class"] == "KNOB1"]
    require(sorted(supply_circuits) == sorted(required_supply_circuits),
            "Supply schedule does not cover every 24 V circuit exactly once")
    supplies_by_id = {p["supply_id"]: p for p in supply_rows}

    distributions = []
    for lt in plan["lighting_circuits"]["with_curtain_strips"]:
        ids = [i for i in lt["members"] if i != "P03"]
        watts = sum(supplies_by_id[i]["modeled_load_W"] for i in ids) if lt["kind"] == "24 V" else sum(
            circuits_by_id[i]["model_W"] for i in ids)
        distributions.append({
            "group": lt["lt"], "description": lt["name"], "kind": lt["kind"], "members": ids,
            "modeled_lighting_W": round(watts, 2),
            "inrush_status": "HOLD - previous screen invalid" if lt["lt"] in ("LT-4", "LT-5")
                              else "OPEN - historical reference screen is not approval",
            "inverter_concept": bool(lt["inverter_default"]),
        })
    require(len(distributions) == 7, "Distribution group count changed")
    require(round(sum(d["modeled_lighting_W"] for d in distributions), 2) ==
            round(sum(c["model_W"] for c in circuit_rows), 2), "Distribution loads do not sum to circuits")

    base_drop = lighting["electrical_checks"]["voltage_drop"]
    changes = selected["selected_S1_electrical"]["voltage_drop_changed"]
    changes_by_key = {(x["circuit"], x["section"]): x for x in changes}
    drop_rows = []
    for x in base_drop:
        key = (x["circuit"], x["section"])
        change = changes_by_key.get(key)
        pct = change["dV_pct_after"] if change else x["dV_pct"]
        status = change["status_after"] if change else x["status"]
        drop_rows.append({
            "circuit": x["circuit"], "section": x["section"],
            "supply_id": "P01" if x["circuit"] in ("C03", "C04", "C05") else x["psu"],
            "modeled_dV_pct": pct, "status": status, "basis": "S1 planning model; actual design open",
            "note": "One-supply reroute / protection not calculated" if status == "HOLD"
                    else x.get("strip_feed_note", ""),
        })
    for x in changes:
        if x.get("new_section"):
            drop_rows.append({
                "circuit": x["circuit"], "section": x["section"], "supply_id": x["psu"],
                "modeled_dV_pct": x["dV_pct_after"], "status": x["status_after"],
                "basis": "S1 planning model; pocket unmeasured", "note": "No fabrication release",
            })
    require(len(drop_rows) == 37 and Counter(x["status"] for x in drop_rows) == Counter({"OK": 30, "MARGINAL": 2, "HOLD": 5}),
            "Integrated voltage-drop statuses differ from expected 30/2/5")
    for code, pct in (("C39", 3.3), ("C40", 3.9)):
        require(next(x for x in drop_rows if x["circuit"] == code)["modeled_dV_pct"] == pct,
                f"Unexpected {code} voltage drop")

    dimmer_rows = []
    for c in circuit_rows:
        if c["control_class"] not in ("TE", "TRK"):
            continue
        if c["control_class"] == "TRK":
            nominal = "NOT SCREENED - track maker must specify complete chain"
        elif c["model_W"] < 3 or c["model_W"] > 50 or c["n_fixtures"] > 8:
            nominal = "OUTSIDE listed nominal W or lamp-count limit"
        elif c["model_W"] >= 45 or c["n_fixtures"] == 8:
            nominal = "AT/NEAR LIMIT - not an approved match"
        else:
            nominal = "NOMINAL W/count only - not an approved match"
        dimmer_rows.append({
            "circuit": c["circuit"], "control": c["wall_control"], "model_W": c["model_W"],
            "fitting_count": c["n_fixtures"], "Legrand_677304_screen": nominal,
            "driver_input_VA_count_edge_and_compatibility": "UNVERIFIED",
            "procurement_status": "HOLD",
        })
    require(len(dimmer_rows) == 10, "Expected ten mains-dimmer groups")

    classes = defaultdict(list)
    for f in lighting["fixtures"]:
        classes[(f["type"], f["desc"])].append(f)
    class_rows = []
    for (code, description), members in classes.items():
        def values(key: str) -> list:
            return sorted({str(f[key]) for f in members if f.get(key) is not None})
        additional = [f for f in fixture_rows
                      if f["fixture_class"] == code and not f["photometry_credit"]]
        class_rows.append({
            "fixture_class": code, "modeled_count_per_flat": len(members) + len(additional),
            "base_count": len(members), "additional_curtain_count": len(additional),
            "description_or_design_target": description,
            "CCT": values("cct"),
            "nominal_W_per_listed_fixture": sorted(set(values("W_nominal")) |
                                                   {str(f["model_W"]) for f in additional}),
            "lumens_per_listed_fixture": values("lm"), "beam_deg": values("beam_deg"),
            "IP_target": values("ip"), "CRI_min_target": values("cri_min"), "R9_min_target": values("r9_min"),
            "supply_class": values("supply"), "actual_cutout_and_dimensions": "MEASURE / RFQ",
            "photometry_note": ("Additional curtain strips have no lumen or lux credit."
                                if additional else "Original model assumptions only."),
            "status": "GENERIC PROJECT TARGET - not a product specification",
        })
    require(sum(row["modeled_count_per_flat"] for row in class_rows) == len(fixture_rows),
            "Fixture class counts do not cover the current 108 fixtures")

    for name, rows in (
        ("circuit-schedule.csv", circuit_rows), ("fixtures.csv", fixture_rows),
        ("curtain-pockets.csv", curtain_rows), ("knob-groups.csv", knob_rows),
        ("wall-control-schedule.csv", wall_rows), ("fitting-controls.csv", fitting_controls),
        ("supplementary-switches.csv", plan["switches"]), ("supply-schedule.csv", supply_rows),
        ("lighting-distribution.csv", distributions), ("voltage-drop-review.csv", drop_rows),
        ("mains-dimmer-check.csv", dimmer_rows), ("fixture-class-specifications.csv", class_rows),
    ):
        write_csv(out / "schedules" / name, rows)

    circuit_table = table(
        ["Circuit", "Room / lane", "Fixture IDs", "Control / supply", "W"],
        [[x["circuit"], f"{x['room']} / {x['lane']}", ", ".join(x["fixture_ids"]),
          f"{x['wall_control']} / {', '.join(x['supply_id']) or 'mains / integral'}", amount(x["model_W"])]
         for x in circuit_rows],
    )
    control_table = table(
        ["Wall", "Board", "Controls these circuits", "W"],
        [[w["control"], w["board"], ", ".join(w["circuits"]), amount(w["modeled_W"])] for w in wall_rows],
    )
    fitting_table = table(
        ["Fitting control", "Board", "Device"],
        [[x["circuit"], x["board"], x["device"]] for x in fitting_controls],
    )
    supply_table = table(
        ["24 V supply", "Model W", "Nameplate W", "Circuit groups"],
        [[x["supply_id"], amount(x["modeled_load_W"]), x["planning_nameplate_W"], ", ".join(x["circuits"])]
         for x in supply_rows],
    )
    distribution_table = table(
        ["Concept group", "Members", "Model W", "Inrush / protection status"],
        [[x["group"], ", ".join(x["members"]), amount(x["modeled_lighting_W"]), x["inrush_status"]]
         for x in distributions],
    )

    source_files = []
    for name, title in PDF_SOURCES:
        source = args.manufacturer_sources / name
        require(source.is_file(), f"Missing manufacturer source {source}")
        target = out / "sources" / name
        if source.resolve() != target.resolve():
            shutil.copy2(source, target)
        source_files.append({"path": f"sources/{name}", "title": title, "sha256": sha(target)})
    for name in (
        "legrand-arteor-advance-F04600EN-00.pdf",
        "schneider-avataron-PHA1631900.pdf",
    ):
        source = args.dimmer_sources / name
        require(source.is_file(), f"Missing manufacturer source {source}")
        target = out / "sources" / name
        if source.resolve() != target.resolve():
            shutil.copy2(source, target)
        source_files.append({"path": f"sources/{name}", "title": name, "sha256": sha(target)})
    breaker_source = args.manufacturer_sources / "meanwell-led-manual-breaker-table.json"
    breaker_target = out / "sources" / breaker_source.name
    require(breaker_source.is_file(), f"Missing manufacturer lookup {breaker_source}")
    if breaker_source.resolve() != breaker_target.resolve():
        shutil.copy2(breaker_source, breaker_target)

    evidence = [
        ("wardrobe-interiors-reference-receipt.json", wardrobe_path),
        ("homeowner-coordination-receipt.json", prior_receipt_path),
        ("pooja-display-receipt.json", pooja_receipt_path),
        ("living-supply-and-cabinet-selections-receipt.json", integration_path),
        ("living-low-one-supply-option.json", option_path),
        ("prior-control-plan.json", prior_plan_path),
        ("prior-control-plan-receipt.json", prior_plan_receipt_path),
        ("verified-fixed-white-verification.json", verified_path),
    ]
    for name, path in evidence:
        shutil.copy2(path, out / "source-evidence" / name)

    replacements = {
        "{{MASTER_SHA}}": expected,
        "{{MASTER_BINDING}}": ("The verified predecessor chain includes the fixed-CCT revision and the subsequent "
                               "provisional CBR-X1-X4 relocation and route reanalysis. The cove, all other fittings, "
                               "modeled loads and lumen outputs remain unchanged; the CBR ceiling hold is not released."),
        "{{CIRCUIT_TABLE}}": circuit_table,
        "{{CONTROL_TABLE}}": control_table,
        "{{FITTING_CONTROLS_TABLE}}": fitting_table,
        "{{SUPPLY_TABLE}}": supply_table,
        "{{DISTRIBUTION_TABLE}}": distribution_table,
        "{{PDF_MANIFEST}}": table(
            ["Official local document", "SHA-256"],
            [[f"[{s['title']}]({s['path']})", f"`{s['sha256']}`"] for s in source_files],
        ),
    }
    for src, dst in (("electrical-review.template.md", "electrical-review.md"),
                     ("source-index.template.md", "source-index.md"),
                     ("wholesale-rfq.template.md", "wholesale-rfq.md"),
                     ("control-options.template.md", "control-options.md")):
        text = (Path(__file__).parent / src).read_text(encoding="utf-8")
        for key, value in replacements.items():
            text = text.replace(key, value)
        require("{{" not in text, f"Unresolved template placeholder in {src}")
        (out / dst).write_text(text, encoding="utf-8")

    ledger = {
        "schema": "electrical-handoff-ledger/1",
        "master_sha256": expected,
        "decision_receipt_sha256": sha(integration_path),
        "latest_master_receipt_sha256": sha(wardrobe_path),
        "cct_revision": delta,
        "children_ceiling_revision": cbr_delta,
        "one_supply_option_sha256": OPTION_SHA,
        "historical_photometry": {
            "source_fragment_sha256": sha(fragment_path), "verification_sha256": sha(verified_path),
            "historical_passes": 82, "rerun_on_current_master": False,
        },
        "totals_per_flat": {
            "base_fixtures": 104, "curtain_fixtures": 4, "fixtures_including_curtains": 108,
            "base_circuits": 47, "curtain_circuits": 4, "circuits_including_curtains": 51,
            "knobs": 21, "mains_dimmer_groups": 10, "modeled_outputs": 38, "modeled_repeaters": 3,
            "supplies_24V": 12, "supplies_24V_nameplate_W": 1980,
            "track_driver_48V": 1, "curtain_length_m": 8.88, "curtain_W": 71.04,
            "curtain_photometry_credit": False,
            "summed_fixture_allowance_W_including_curtains": round(sum(c["model_W"] for c in circuit_rows), 2),
        },
        "release_flags": {"construction_release": False, "product_approval": False, "exact_chain_proven": False},
        "circuits": circuit_rows, "fixtures": fixture_rows, "knob_groups": knob_rows,
        "wall_controls": wall_rows, "supplies": supply_rows, "distribution": distributions,
        "voltage_drop": drop_rows, "curtain_pockets": curtain_rows,
        "sources": source_files,
    }
    write_json(out / "schedules" / "electrical-ledger.json", ledger)
    write_json(out / "build-context.json", {
        "built_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "master_sha256": expected, "latest_master_receipt_sha256": sha(wardrobe_path),
        "living_supply_decision_receipt_sha256": sha(integration_path),
        "one_supply_option_sha256": OPTION_SHA, "prior_control_sha256": sha(prior_plan_path),
        "historic_photometry_verification_sha256": sha(verified_path),
        "release_flags": ledger["release_flags"],
        "note": "PDF/PNG export and independent validation are still required before final receipt.",
    })
    for name in ("fw_final_build.py", "fw_render.py", "export_figures_png.py"):
        shutil.copy2(Path(__file__).parent / name, out / "tools" / name)
    for name in ("electrical-review.template.md", "source-index.template.md",
                 "wholesale-rfq.template.md", "control-options.template.md"):
        shutil.copy2(Path(__file__).parent / name, out / "tools" / name)
    require(sha(master_path) == expected, "Master changed during the build; outputs are not valid")
    print(json.dumps({"master_sha256": expected, "output": str(out), "circuits": len(circuit_rows),
                      "fixtures": len(fixture_rows), "knobs": len(knob_rows), "supplies": len(supply_rows),
                      "supply_nameplate_W": 1980, "drop_status": dict(Counter(x["status"] for x in drop_rows)),
                      "modeled_fixture_W": ledger["totals_per_flat"]["summed_fixture_allowance_W_including_curtains"]},
                     indent=2))


if __name__ == "__main__":
    main()
