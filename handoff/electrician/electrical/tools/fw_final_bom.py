"""Build a location-linked modeled bill and switchboard schedule from the review ledger."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HOUSE = Path(r"handoff/source-basis")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def flatten(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "; ".join(flatten(v) for v in value)
    if isinstance(value, dict):
        return json.dumps(value, separators=(",", ":"), ensure_ascii=False)
    return str(value)


def save_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"No data for {path}")
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows({key: flatten(value) for key, value in row.items()} for row in rows)


def table(headers: list[str], rows: list[list[object]]) -> str:
    def cell(value: object) -> str:
        return flatten(value).replace("|", "/").replace("\n", " ")
    output = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    output.extend("| " + " | ".join(cell(v) for v in row) + " |" for row in rows)
    return "\n".join(output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master", type=Path, default=HOUSE / "house-design.json")
    parser.add_argument("--out", type=Path, default=ROOT / "final-handoff")
    args = parser.parse_args()
    out = args.out.resolve()
    master_path = args.master.resolve()
    ledger = load(out / "schedules" / "electrical-ledger.json")
    master_hash = ledger["master_sha256"]
    if sha(master_path) != master_hash:
        raise ValueError("The live master no longer matches the electrical ledger")
    master = load(master_path)
    plan = load(out / "source-evidence" / "prior-control-plan.json")
    circuits = {c["circuit"]: c for c in ledger["circuits"]}
    boards = {b["board"]: b for b in master["lighting"]["electrical_checks"]["board_devices"]}
    supplies = {p["psu"]: p for p in master["lighting"]["controls"]["psus"]}
    controls_by_board = defaultdict(list)
    switches_by_board = defaultdict(list)
    fitting_by_board = defaultdict(list)
    for w in ledger["wall_controls"]:
        controls_by_board[w["board"]].append(w)
    for sw in plan["switches"]:
        if sw["switch_modules"] != len(sw["positions"]):
            raise ValueError(f"Switch positions do not match count for {sw['circuit']}")
        for position in sw["positions"]:
            switches_by_board[position].append(sw)
    for f in plan["fitting_mounted_controls"]:
        fitting_by_board[f["board"]].append(f)
    all_boards = set(controls_by_board) | set(switches_by_board) | set(fitting_by_board)
    if not all_boards.issubset(boards):
        raise ValueError(f"Missing board geometry: {all_boards - set(boards)}")

    switchboard_rows = []
    for board_id in sorted(all_boards):
        board = boards[board_id]
        controls = controls_by_board[board_id]
        switches = switches_by_board[board_id]
        integral = fitting_by_board[board_id]
        switchboard_rows.append({
            "board": board_id,
            "x_ft_indicative": board["xz_ft"][0],
            "z_ft_indicative": board["xz_ft"][1],
            "wall_PWM_knobs": sum(w["control"].startswith("K-") for w in controls),
            "mains_dimmer_groups": sum(w["control"].startswith("D-") for w in controls),
            "wall_control_ids": [w["control"] for w in controls],
            "supplementary_switch_modules": len(switches),
            "supplementary_switch_circuits": [s["circuit"] for s in switches],
            "integral_fitting_controls_near_board_not_wall_modules": [f["circuit"] for f in integral],
            "status": "UNSURVEYED; exact plate, module fit and wiring OPEN",
        })
    if sum(b["wall_PWM_knobs"] for b in switchboard_rows) != 21:
        raise ValueError("Switchboard knob count is not 21")
    if sum(b["mains_dimmer_groups"] for b in switchboard_rows) != 10:
        raise ValueError("Switchboard mains-dimmer count is not 10")
    if sum(b["supplementary_switch_modules"] for b in switchboard_rows) != 8:
        raise ValueError("Switchboard supplementary switch count is not 8")

    rows = []

    def item(**values: object) -> None:
        keys = (
            "item_id", "item_kind", "quantity_per_flat", "unit", "room", "board", "circuit_or_control",
            "fixture_class", "model_description_or_spec", "CCT", "model_W", "model_lm", "beam_deg",
            "CRI_min_target", "R9_min_target", "IP_target", "strip_length_m_modeled",
            "x_ft_indicative", "z_ft_indicative", "path_ft_indicative",
            "pricing", "status",
        )
        rows.append({key: values.get(key) for key in keys})

    for f in ledger["fixtures"]:
        item(
            item_id=f["id"], item_kind="modeled luminaire or strip fixture", quantity_per_flat=1,
            unit="fixture", room=f["room"], circuit_or_control=f["circuit"],
            fixture_class=f["fixture_class"], model_description_or_spec=f["description"],
            CCT=f["CCT"], model_W=f["model_W"], model_lm=f["model_lm"], beam_deg=f["model_beam_deg"],
            CRI_min_target=f["CRI_min_target"], R9_min_target=f["R9_min_target"], IP_target=f["IP_target"],
            strip_length_m_modeled=f["length_m"], x_ft_indicative=f["x_ft"], z_ft_indicative=f["z_ft"],
            path_ft_indicative=f["path_ft"], pricing="NO VERIFIED QUOTE",
            status="MODEL ONLY; actual product, dimensions and site held",
        )
        if f["length_m"] is not None:
            item(
                item_id=f"PROFILE-{f['id']}", item_kind="profile and diffuser allowance",
                quantity_per_flat=f["length_m"], unit="m modeled installed run", room=f["room"],
                circuit_or_control=f["circuit"], fixture_class=f["fixture_class"],
                model_description_or_spec="Profile/diffuser allowance; omit if supplied integrated with manufacturer-approved heat-sinking; section and wet-zone suitability open",
                CCT=f["CCT"], IP_target=f["IP_target"], strip_length_m_modeled=f["length_m"],
                x_ft_indicative=f["x_ft"], z_ft_indicative=f["z_ft"], path_ft_indicative=f["path_ft"],
                pricing="NO VERIFIED QUOTE", status="MODEL LENGTH ONLY; measure, allow cuts/waste and approve product",
            )
    for p in ledger["supplies"]:
        source = supplies[p["supply_id"]]
        location = None if p["supply_id"] == "P01" else source.get("hatch_xz_ft")
        rooms = sorted({circuits[code]["room"] for code in p["circuits"]})
        item(
            item_id=p["supply_id"], item_kind="24 V constant-voltage supply", quantity_per_flat=1,
            unit="supply", room=rooms, circuit_or_control=p["circuits"],
            model_description_or_spec=f"{p['planning_nameplate_W']} W planning nameplate; {p['modeled_load_W']} W modeled load; manufacturer reference only",
            model_W=p["modeled_load_W"], x_ft_indicative=location[0] if location else None,
            z_ft_indicative=location[1] if location else None, pricing="NO VERIFIED QUOTE",
            status="HATCH / PRODUCT / INPUT / THERMAL / PROTECTION HOLD",
        )
    for w in ledger["wall_controls"]:
        board = boards[w["board"]]
        item(
            item_id=w["control"], item_kind="local wall dimmer/knob", quantity_per_flat=1,
            unit="control", room=w["room"], board=w["board"], circuit_or_control=w["circuits"],
            model_description_or_spec=w["device_class"], model_W=w["modeled_W"],
            x_ft_indicative=board["xz_ft"][0], z_ft_indicative=board["xz_ft"][1],
            pricing="NO VERIFIED QUOTE", status="MODEL ONLY; exact driver/control chain and board fit HOLD",
        )
    for k in ledger["knob_groups"]:
        if k["modeled_repeaters"]:
            item(
                item_id=f"AMP-{k['knob']}", item_kind="modeled PWM repeater",
                quantity_per_flat=k["modeled_repeaters"], unit="repeater", room=k["room"],
                board=k["board"], circuit_or_control=k["knob"],
                model_description_or_spec="Exact input/output, PWM tracking, current, fault protection and location unverified",
                pricing="NO VERIFIED QUOTE", status="MODELED COUNT ONLY; exact product and location HOLD",
            )
    for sw in plan["switches"]:
        for number, board_id in enumerate(sw["positions"], 1):
            board = boards[board_id]
            item(
                item_id=f"SW-{sw['circuit']}-{number}", item_kind="conceptual on/off switch module",
                quantity_per_flat=1, unit="module", room=sw["room"], board=board_id,
                circuit_or_control=sw["circuit"], model_description_or_spec=sw["note"],
                x_ft_indicative=board["xz_ft"][0], z_ft_indicative=board["xz_ft"][1],
                pricing="NO VERIFIED QUOTE", status="MODEL ONLY; exact switch arrangement and board fit HOLD",
            )
    item(
        item_id="TRACK-48V-DRIVER-C13", item_kind="48 V track system driver", quantity_per_flat=1,
        unit="driver", room=circuits["C13"]["room"], board=circuits["C13"]["board"],
        circuit_or_control="C13", model_description_or_spec="48 V track driver and listed wall control; model LED load 26 W, actual AC input unknown",
        model_W=26, pricing="NO VERIFIED QUOTE", status="TRACK SYSTEM / DIMMER / LOCATION HOLD",
    )
    categories = Counter()
    for row in rows:
        categories[row["item_kind"]] += row["quantity_per_flat"]
    if categories["modeled luminaire or strip fixture"] != 108:
        raise ValueError("Location BOM does not contain 108 distinct modeled fixtures")
    if categories["24 V constant-voltage supply"] != 12:
        raise ValueError("Location BOM does not contain twelve 24 V supplies")
    if categories["local wall dimmer/knob"] != 31:
        raise ValueError("Location BOM does not contain 31 local wall controls")
    if categories["modeled PWM repeater"] != 3 or categories["conceptual on/off switch module"] != 8:
        raise ValueError("Location BOM repeater/switch counts mismatch")

    save_csv(out / "schedules" / "switchboard-schedule.csv", switchboard_rows)
    save_csv(out / "schedules" / "location-linked-bom.csv", rows)
    groups = defaultdict(list)
    for f in ledger["fixtures"]:
        groups[(f["room"], f["fixture_class"])].append(f)
    room_rows = []
    for (room, fixture_class), members in sorted(groups.items()):
        lengths = [x["length_m"] for x in members if x["length_m"] is not None]
        room_rows.append([
            room, fixture_class, len(members), ", ".join(sorted({x["CCT"] for x in members})),
            round(sum(lengths), 2) if lengths else "-", ", ".join(x["id"] for x in members),
        ])
    board_table = table(
        ["Board", "Knobs / mains dimmers", "On/off modules", "Integral fitting IDs"],
        [[x["board"], f"{x['wall_PWM_knobs']} / {x['mains_dimmer_groups']}",
          x["supplementary_switch_modules"], ", ".join(x["integral_fitting_controls_near_board_not_wall_modules"]) or "-"]
         for x in switchboard_rows],
    )
    group_table = table(["Room", "Class", "Qty", "Fixed CCT", "Strip m", "Fixture IDs"], room_rows)
    text = f"""# Location-linked lighting bill of materials

**Master SHA-256:** `{master_hash}`. These are **modeled quantities for one flat**, not purchase quantities or approved construction dimensions. Four floors are intended to repeat the scheme, but site geometry, returns, cuts, product lead lengths and wastage must be measured independently. No verified current installed quote exists.

The complete `schedules/location-linked-bom.csv` lists **108 fixture records**, the separate profile allowances, **12 24 V supply classes**, **31 wall controls**, **three modeled PWM repeaters**, **eight conceptual switch modules**, and one 48 V track driver. It includes circuit/board, model specification, CCT, CRI/R9/IP targets and available indicative solver coordinates or strip paths. A supply, dimmer, switch, profile or repeater appears separately from its fixture; omit a separate profile where an approved integrated product already includes the required diffuser and heat-sinking. Do not treat these entries as certified matched products.

**Cautions:** P01's 480 W-class hatch location is unknown. Other positions are design placeholders, not field measurements. Strip lengths are installed-run model lengths, **not** reel or cut-order quantities. The four curtain strips are 8.88 m / 71.04 W combined, unmeasured and excluded from lux calculations. Prices, GST, delivery, labour, mounting hardware, spare stock, electrical cabling, connectors, boxes, DB/protection, accessories and waste need itemised quotes and professional survey.

## Fixture groups by location

Descriptions, individual modeled watts/lumens/beams, minimum CRI/R9, IP targets, CCT and design notes are in `schedules/fixture-class-specifications.csv` and `schedules/fixtures.csv`; a class is a search target, not a manufacturer SKU. The fixture IDs below point to their individual coordinates or paths in the location bill.

{group_table}

## Switchboards and other equipment

{board_table}

Wall controls in the table are **21 single-colour knobs and ten mains-dimmer groups**. The six integral reader/PIR controls are inside fittings, not six more wall modules. Supplementary modules are conceptual two-way/intermediate switch points; exact plate layouts and back-box sizes remain open. Board and fixture placement requires site measurement.

The supply, circuit and control mappings are in `supply-schedule.csv`, `circuit-schedule.csv` and `wall-control-schedule.csv`; P01 is one 480 W-class reference supply, P03 is removed, and the 48 V track driver is separate. All source/driver/dimmer/repeater compatibility, distribution protection, thermal checks, wet-zone suitability, C39/C40 and curtain-pocket holds remain open.

For generic/imported or branded procurement search use `wholesale-rfq.md`; for exact manufacturer evidence use `source-index.md`. **No product or construction approval is implied.**
"""
    (out / "bill-of-materials.md").write_text(text, encoding="utf-8")
    target_script = out / "tools" / Path(__file__).name
    if Path(__file__).resolve() != target_script.resolve():
        shutil.copy2(Path(__file__), target_script)
    if sha(master_path) != master_hash:
        raise ValueError("The live master changed during BOM generation")
    print(json.dumps({"master_sha256": master_hash, "location_bom_rows": len(rows),
                      "switchboards": len(switchboard_rows), "component_counts": dict(categories),
                      "fixture_groups": len(room_rows)}, indent=2))


if __name__ == "__main__":
    main()
