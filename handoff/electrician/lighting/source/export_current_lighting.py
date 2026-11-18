"""Export an explicitly review-only lighting package from the guarded house master."""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import math
import shutil
import textwrap
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon

SESSION = Path(r"not-distributed/lighting-session-inputs")
MASTER = Path(r"handoff/source-basis/house-design.json")
PACK = SESSION / "final-lighting-fixed-white"
OPT = SESSION / "final-lighting-opt1-rev1"
SOURCE = SESSION / "lighting-integrated-current"
OUT = SESSION / "lighting-current-review"
EXPECTED_MASTER = "b6f6bf1a127c7e39086deb9fd1d2c0dff79a495381e1a4b9457f6a9a468f23ac"
EXPECTED_OPTICAL_DI = "ca19a7b5cf2c0c92cf3120c95c812567fbdaa3325a7e18b3a132105e66aa604e"
EXPECTED_HEATMAP = "e81bf2fbe1819f481c12b45aba9ead3352893f00abeaf6bf3fc1bbf698910b4a"
EXPECTED_OLD_VERIFICATION = "06f44f9cb2b55d977c8c806557113ccd6edb6ce9de2fe41b391b27320e4bf3c9"
RELEASE = "REVIEW ONLY - NOT FOR CONSTRUCTION"
KIND = {"HIGH": "main", "COVE": "mood", "MOOD": "mood", "LINE": "mood", "PERIM": "mood", "LOW": "mood"}
COLORS = {2700: "#b96b27", 3000: "#356e8b", 4000: "#5475ae"}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canon(value) -> str:
    return sha(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def json_bytes(value) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def read(path: Path):
    return json.loads(path.read_bytes())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def output(name: str, raw: bytes):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return path


def write_json(name: str, value):
    return output(name, json_bytes(value))


def write_csv(name: str, columns: list[str], rows: list[dict]):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="raise", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output(name, stream.getvalue().encode("utf-8-sig"))


def clean(value):
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        return "; ".join(str(item) for item in value)
    return value


def validate_optical_provenance(data, heatmap):
    lighting = data["lighting"]
    di = lighting["design_inputs"]
    old_di = read(PACK / "lighting-design-inputs-fixed-white.json")["lighting"]["design_inputs"]
    require(canon(old_di) == EXPECTED_OPTICAL_DI, "Original photometric input fingerprint changed")
    require(lighting["calculations"]["source"]["design_inputs_sha256"] == EXPECTED_OPTICAL_DI,
            "The inherited calculations have a different source input")
    for key in set(di) | set(old_di):
        if key not in {"rooms", "pending_constraints", "provenance"}:
            require(di.get(key) == old_di.get(key), f"Numerical lighting input changed: {key}")
    old_rooms = copy.deepcopy(old_di["rooms"])
    new_rooms = copy.deepcopy(di["rooms"])
    for rooms in (old_rooms, new_rooms):
        for room in rooms:
            for fixture in room["fixtures"]:
                if fixture["id"] in {f"CBR-H{i}" for i in range(1, 7)}:
                    for field in ("constraint_refs", "homeowner_release", "position_status"):
                        fixture.pop(field, None)
    require(old_rooms == new_rooms, "Room geometry, fixture geometry, optics or non-approved fixture settings changed")
    old_fixtures = read(PACK / "fixture-ledger.json")
    current_fixtures = copy.deepcopy(lighting["fixtures"])
    for fixture in current_fixtures:
        require(fixture.pop("tunable", None) is False, f"{fixture['id']} is not fixed-white")
    require(current_fixtures == old_fixtures, "The accepted fixture ledger differs from the original optical calculation")
    original_calc = read(PACK / "calc-results.json")
    current_calc = copy.deepcopy(lighting["calculations"])
    old_calc = copy.deepcopy(original_calc)
    for calc in (old_calc, current_calc):
        calc.pop("electrical_summary", None)
        for key in ("control_totals_scope", "psu_isolators", "psu_nameplate_total_W", "psus_24V", "standby_W_est"):
            calc["totals"].pop(key, None)
        calc["hd14"]["psu"].pop("status", None)
    require(old_calc == current_calc, "An optical or unrelated calculation changed after the verified source")
    raw_heatmap = (PACK / "heatmaps.json").read_bytes()
    require(sha(raw_heatmap) == EXPECTED_HEATMAP, "Saved analytic heatmap hash changed")
    require(lighting["supporting_outputs"]["files"]["heatmaps.json"]["sha256"] == EXPECTED_HEATMAP,
            "Master does not reference the saved analytic heatmap")
    require(sha((PACK / "verification.json").read_bytes()) == EXPECTED_OLD_VERIFICATION,
            "Original verification receipt fingerprint changed")
    verification = read(PACK / "verification.json")
    require(verification["summary"] == {"PASS": 82} and all(c["result"] == "PASS" for c in verification["checks"]),
            "Original fixed-white calculation verification is not all-pass")
    require(verification["design_inputs"]["sha256"] == EXPECTED_OPTICAL_DI, "Original verification used a different DI")
    checked = 0
    missing_stats = []
    for room_id, grid in heatmap["rooms"].items():
        nx, nz = len(grid["x_m"]), len(grid["z_m"])
        require(len(grid["stats_mask"]) == nz and all(len(row) == nx for row in grid["stats_mask"]), f"{room_id} mask shape")
        for scene, rows in grid["E"].items():
            require(len(rows) == nz and all(len(row) == nx for row in rows), f"{room_id} {scene} grid shape")
            values = [value for row, mask in zip(rows, grid["stats_mask"])
                      for value, included in zip(row, mask) if included and value is not None]
            require(values and all(math.isfinite(v) and v >= 0 for v in values), f"{room_id} {scene} invalid values")
            result = lighting["calculations"]["rooms"][room_id]
            ref = result.get("combinations", {}).get(scene) or result.get("scenes", {}).get(scene)
            if ref is None:
                missing_stats.append(f"{room_id}:{scene}")
                continue
            average, minimum = sum(values) / len(values), min(values)
            require(abs(average-ref["avg"]) <= 2 and abs(minimum-ref["min"]) <= 2,
                    f"{room_id} {scene} stored grid and statistics disagree")
            if average:
                require(abs(minimum/average-ref["U0"]) <= .025, f"{room_id} {scene} uniformity disagrees")
            checked += 1
    require(checked == 71, f"Unexpected number of comparable grid statistics: {checked}")
    return {"grid_statistics_compared": checked, "grids_without_reported_statistics": missing_stats,
            "original_verification_passes": 82, "unchanged_optical_fixture_count": len(old_fixtures)}


def reconcile(data):
    lighting = data["lighting"]
    fixtures, controls = lighting["fixtures"], lighting["controls"]
    cct_map, cp = copy.deepcopy(lighting["fixed_cct_map"]), copy.deepcopy(lighting["curtain_pocket_s1"])
    ext = controls["selected_curtain_S1_extension"]
    ids = {f["id"] for f in fixtures}
    require(len(ids) == len(fixtures) == 104, "Base fixture IDs/count")
    require(len(controls["circuits"]) == 47 and len(controls["psus"]) == 12, "Base control/supply count")
    require(sum(s["nameplate_W"] for s in controls["psus"]) == 1890, "Base supply capacity")
    require({x["id"] for x in cct_map["fittings"]} == ids, "Fixed-CCT map does not match fixture IDs")
    by_id = {f["id"]: f for f in fixtures}
    for row in cct_map["fittings"]:
        fixture = by_id[row["id"]]
        require(row["room"] == fixture["room"] and row["circuit"] == fixture["circuit"]
                and f'{row["cct_k"]}K' == fixture["cct"] and row["cct_fixed"],
                f"Fixed-CCT mapping differs for {row['id']}")
    require(Counter(f["cct_k"] for f in cct_map["fittings"]) == {2700: 30, 3000: 40, 4000: 34},
            "CCT distribution changed")
    require({x["id"] for x in cp["strips"]} == {"CURT-LIV", "CURT-DIN", "CURT-MBR-S", "CURT-CBR"},
            "Selected curtain strip set changed")
    require(all(x["cct_k"] == 2700 and x["fabrication_release"] is False
                and x["photometry_credit"] is False for x in cp["strips"]), "Curtain selection holds changed")
    require(abs(sum(s["indicative_strip_length_m"] for s in cp["strips"])-8.88) < .001
            and abs(sum(s["W_envelope"] for s in cp["strips"])-71.04) <= .051
            and all(abs(s["W_envelope"]-8*s["indicative_strip_length_m"]) <= .051 for s in cp["strips"]),
            "Curtain allowance totals or per-pocket rounded loads")
    selected_totals = ext["with_S1"]
    require((selected_totals["knobs"], selected_totals["knob_outputs"], selected_totals["amplifiers"],
             selected_totals["psus"], selected_totals["psu_nameplate_total_W"]) == (21, 38, 3, 12, 1980),
            "Selected S1 totals changed")
    require(all(lighting["calculation_validity"][x] is False for x in
                ("construction_release", "product_approval", "exact_chain_proven"))
            and data["metadata"]["construction_release"] is False, "Release flags must remain false")
    hold_map = defaultdict(list)
    for hold in lighting["design_inputs"]["provenance"]["layout_basis"]["holds"]:
        for fixture_id in hold.get("fixtures", []):
            hold_map[fixture_id].append(hold["id"])
    cbr_high = {f"CBR-H{i}" for i in range(1, 7)}
    require(not any(hold_map[x] for x in cbr_high), "CBR H1-H6 unexpectedly have a placement hold")
    require(all(by_id[x]["circuit"] == "C37" for x in cbr_high), "CBR H1-H6 circuit changed")
    require(all("H-CURTAIN-POCKET" in hold_map[x["id"]] for x in cp["strips"]), "Curtain pocket hold missing")
    changes = {x["psu"]: x for x in ext["supply_changes"]}
    psu_rows = []
    for supply in controls["psus"]:
        revised = changes.get(supply["psu"])
        row = {
            "psu": supply["psu"], "circuits": clean(revised["circuits"] if revised else supply["circuits"]),
            "nameplate_W": revised["nameplate_after_W"] if revised else supply["nameplate_W"],
            "strip_load_W": revised["W_envelope_after"] if revised else supply["W_envelope"],
            "planning_pct_of_0_60": revised["pct_of_usable_after"] if revised else supply["loading_pct_of_usable"],
            "status": "HOLD: location, branch protection, inrush and exact chain" if supply["psu"] == "P01"
                      else "planning allowance only; product, temperature and protection unverified",
            "reference": "HLG-480H-24 is an example, not a selected SKU" if supply["psu"] == "P01" else "",
        }
        psu_rows.append(row)
    require(len(psu_rows) == 12 and sum(x["nameplate_W"] for x in psu_rows) == 1980
            and not any(x["psu"] == "P03" for x in psu_rows), "Effective selected PSU ledger is inconsistent")
    p01 = next(x for x in psu_rows if x["psu"] == "P01")
    require(p01["nameplate_W"] == 480 and p01["strip_load_W"] == 181.52
            and p01["circuits"] == "C03; C04; C05; X-CURT-LIV", "Selected P01 arrangement")
    p16 = next(x for x in psu_rows if x["psu"] == "P16")
    require(p16["nameplate_W"] == 240 and p16["strip_load_W"] == 121.0, "P16 selected S1 loading changed")
    vd = {(x["circuit"], x["section"]): {
        "circuit": x["circuit"], "section": x["section"], "psu": x["psu"],
        "dV_pct": x["dV_pct"], "status": x["status"], "comment": x.get("hold_reason", "")
    } for x in lighting["electrical_checks"]["voltage_drop"]}
    for change in ext["voltage_drop_changes"]:
        vd[(change["circuit"], change["section"])] = {
            "circuit": change["circuit"], "section": change["section"], "psu": change["psu"],
            "dV_pct": change["dV_pct_after"], "status": change["status_after"],
            "comment": change.get("hold_reason", "Planning screen only; route and protective design unverified"),
        }
    require(len(vd) == 37 and Counter(x["status"] for x in vd.values()) == {"OK": 30, "MARGINAL": 2, "HOLD": 5},
            "Selected voltage-drop ledger does not reproduce")
    require(vd[("C39", "all")]["dV_pct"] == 3.3 and vd[("C40", "all")]["dV_pct"] == 3.6,
            "P16 C39/C40 marginal results changed")
    require(all(x["status"] == "HOLD" and x["dV_pct"] is None for x in vd.values()
                if x["circuit"] in {"C03", "C04", "C05", "X-CURT-LIV"}),
            "An invalid P01/P03 living voltage-drop result survived")
    require(cp["strips"][0]["id"] == "CURT-LIV" and cp["strips"][0]["voltage_drop"]["status"] == "HOLD",
            "Living curtain voltage-drop screen not invalidated")
    require("INVALID" in lighting["electrical_checks"]["inrush_and_branch_protection"]["LT-4"]
            and "INVALID" in lighting["electrical_checks"]["inrush_and_branch_protection"]["LT-5"],
            "Old living inrush screens not invalidated")
    return cct_map, cp, hold_map, psu_rows, list(vd.values())


def schedule_rows(data, cct_map, cp, hold_map):
    lighting = data["lighting"]
    map_fixtures = {x["id"]: x for x in cct_map["fittings"]}
    fixtures = []
    for f in lighting["fixtures"]:
        m = map_fixtures[f["id"]]
        fixtures.append({
            "id": f["id"], "room": f["room"], "lane": f["lane"], "circuit": f["circuit"],
            "group": m["group_id"], "type": f["type"], "description": f["desc"], "cct_K": m["cct_k"],
            "nominal_W": f["W_nominal"], "generic_lm": f["lm"], "beam_deg": clean(f["beam_deg"]),
            "length_m": clean(f["length_m"]), "x_ft": clean(f["x_ft"]), "z_ft": clean(f["z_ft"]),
            "path_ft": json.dumps(f["path_ft"], separators=(",", ":")) if f["path_ft"] else "",
            "IP_target": f["ip"], "CRI_min": f["cri_min"], "R9_min": f["r9_min"],
            "placement_holds": clean(hold_map[f["id"]]),
            "status": "REVIEW; exact product and site geometry not approved",
        })
    curtain = []
    for s in cp["strips"]:
        curtain.append({
            "id": s["id"], "room": s["room"], "status": "SELECTED; H-CURTAIN-POCKET",
            "selected": "yes", "cct_K": 2700, "knob": s["target_knob_group"],
            "circuit": "X-" + s["id"], "supply": s["proposed_supply"],
            "indicative_length_m": s["indicative_strip_length_m"],
            "generic_W": round(8*s["indicative_strip_length_m"], 2), "recorded_rounded_W": s["W_envelope"],
            "path_ft": json.dumps(s["polyline_ft"], separators=(",", ":")), "photometry_credit": "no",
            "measurement": "unmeasured; 0.30 m returns and pocket width/depth are assumptions",
        })
    held = next(x for x in cct_map["curtain_pocket_candidates"]["pockets"] if x["id"] == "CURT-MBR-W03")
    curtain.append({
        "id": held["id"], "room": held["room"], "status": "EXCLUDED; W03 remains held",
        "selected": "no", "cct_K": 2700, "knob": held["group_id"], "circuit": "not assigned",
        "supply": "not assigned", "indicative_length_m": held["indicative_strip_length_m"],
        "generic_W": round(8*held["indicative_strip_length_m"], 2), "recorded_rounded_W": held["W_envelope"],
        "path_ft": json.dumps(held["polyline_ft"], separators=(",", ":")),
        "photometry_credit": "no", "measurement": "unmeasured; excluded from all selected totals",
    })
    ext = lighting["controls"]["selected_curtain_S1_extension"]
    changes = {x["knob"]: x for x in ext["group_changes"]}
    base_circuits = {x["circuit"]: x for x in lighting["controls"]["circuits"]}
    group_rows = []
    for group in cct_map["groups"]:
        extra = [s for s in cp["strips"] if s["target_knob_group"] == group["group_id"]]
        change = changes.get(group["group_id"], {})
        circuits = group["circuits"] + ["X-" + s["id"] for s in extra]
        boards = sorted({base_circuits[c]["board"] for c in group["circuits"]}
                        | {s["fed_from_knob_board"] for s in extra})
        group_rows.append({
            "board": clean(boards), "group": group["group_id"], "room": clean(group["rooms"]),
            "role": group["layer"], "control_device": group["control_device"],
            "circuits_including_selected_curtains": clean(circuits),
            "base_fittings": group["n_fittings"], "selected_curtain_strips": clean([s["id"] for s in extra]),
            "fixed_CCT_K": clean(group["cct_k"]), "supply": clean(group["supplies"]),
            "modeled_outputs": clean(change.get("outputs_after", group.get("knob_outputs"))),
            "modeled_repeaters": clean(change.get("amplifiers_after", group.get("amplifiers"))),
            "nominal_load_W": round(sum(base_circuits[c]["W_envelope"] for c in group["circuits"])
                                    + sum(s["W_envelope"] for s in extra), 2),
            "status": ("HOLD: distribution/protection/chain" if group["group_id"] == "K-LIV-LOW"
                       else "brightness only; exact products and chain unverified"),
        })
    circuit_rows = []
    for c in lighting["controls"]["circuits"]:
        circuit_rows.append({
            "circuit": c["circuit"], "board": c["board"], "rooms": clean(c["rooms"]), "lane": c["lane"],
            "fixture_ids": clean(c["fixtures"]), "group": clean(c.get("knob_group") or
                next(g["group_id"] for g in cct_map["groups"] if c["circuit"] in g["circuits"])),
            "supply": clean(c["psu"]), "cct": clean(c["cct"]), "load_W": c["W_envelope"],
            "status": ("HOLD: P01 route, voltage drop and protection" if c["circuit"] in {"C03", "C04", "C05"}
                       else "C37 fitting locations released for review; dimmer procurement held" if c["circuit"] == "C37"
                       else "review; product and site holds apply"),
        })
    for s in cp["strips"]:
        circuit_rows.append({
            "circuit": "X-" + s["id"], "board": s["fed_from_knob_board"], "rooms": s["room"],
            "lane": "LOW", "fixture_ids": s["id"], "group": s["target_knob_group"],
            "supply": s["proposed_supply"], "cct": "2700K", "load_W": s["W_envelope"],
            "status": "SELECTED FOR REVIEW; pocket measurement, mock-up and product/chain held",
        })
    require(len(fixtures) == 104 and len(curtain) == 5 and len(group_rows) == 37 and len(circuit_rows) == 51,
            "Schedule row counts")
    return fixtures, curtain, group_rows, circuit_rows


def product_rows(fixtures, cp):
    groups = {}
    for f in fixtures:
        key = (f["type"], f["cct_K"], f["IP_target"], f["CRI_min"], f["R9_min"])
        g = groups.setdefault(key, {"type": f["type"], "fixed_CCT_K": f["cct_K"], "quantity_per_flat": 0,
            "total_run_m_indicative": 0.0, "nominal_W_per_fitting": set(), "generic_lm_per_fitting": set(),
            "beam_deg": set(), "IP_target": f["IP_target"], "CRI_min": f["CRI_min"], "R9_min": f["R9_min"],
            "locations": set(), "generic_search_description": f["description"]})
        g["quantity_per_flat"] += 1
        if f["length_m"] != "":
            g["total_run_m_indicative"] += f["length_m"]
        g["nominal_W_per_fitting"].add(str(f["nominal_W"]))
        g["generic_lm_per_fitting"].add(str(f["generic_lm"]))
        if f["beam_deg"] != "":
            g["beam_deg"].add(str(f["beam_deg"]))
        g["locations"].add(f["room"])
    rows = []
    for key in sorted(groups):
        item = groups[key]
        item["total_run_m_indicative"] = round(item["total_run_m_indicative"], 2) or ""
        for field in ("nominal_W_per_fitting", "generic_lm_per_fitting", "beam_deg", "locations"):
            item[field] = clean(sorted(item[field]))
        item["status"] = "Generic search target only; documented product, chain and site fit unapproved"
        rows.append(item)
    rows.append({
        "type": "CURTAIN-COVE-STRIP", "fixed_CCT_K": 2700, "quantity_per_flat": 4,
        "total_run_m_indicative": 8.88, "nominal_W_per_fitting": "generic 8 W/m",
        "generic_lm_per_fitting": "generic 720 lm/m, unverified", "beam_deg": "",
        "IP_target": "site dependent", "CRI_min": 90, "R9_min": 50,
        "locations": "LIV; DIN; MBR; CBR", "generic_search_description": "Warm white, single-colour 24 V strip in a concealed curtain pocket",
        "status": "Selected for review; measured mock-up and all electrical/product checks open; no lux credit",
    })
    return rows


def plot_plans(data, plot_fixtures):
    rooms = data["lighting"]["design_inputs"]["rooms"]
    polygons = [r["poly_ft"] for r in rooms]
    all_points = [p for poly in polygons for p in poly] + [p for f in plot_fixtures for p in (f["path_ft"] or ([[f["x_ft"], f["z_ft"]]] if f["x_ft"] is not None else []))]
    min_x, max_x = min(p[0] for p in all_points)-.5, max(p[0] for p in all_points)+.5
    min_z, max_z = min(p[1] for p in all_points)-.5, max(p[1] for p in all_points)+.5
    legends = [
        Line2D([0], [0], color=COLORS[2700], lw=3, label="2700 K fixed"),
        Line2D([0], [0], color=COLORS[3000], lw=3, label="3000 K fixed"),
        Line2D([0], [0], color=COLORS[4000], lw=3, label="4000 K fixed"),
        Line2D([0], [0], marker="o", markersize=11, markerfacecolor="none", markeredgecolor="#a04d29",
               linestyle="none", label="Individual placement / site hold"),
        Line2D([0], [0], color="#a04d29", lw=2, ls="--", label="Dashed strip: placement or pocket held"),
    ]
    for kind, title in (("main", "Main lights"), ("mood", "Coves and mood"), ("task", "Task, accent and night")):
        fig, ax = plt.subplots(figsize=(13, 18))
        for room in rooms:
            poly = room["poly_ft"]
            ax.add_patch(Polygon(poly, closed=True, facecolor="#f5f8f8", edgecolor="#79919a", linewidth=.65, zorder=1))
            x = sum(p[0] for p in poly)/len(poly)
            z = sum(p[1] for p in poly)/len(poly)
            ax.text(x, z, room["id"], ha="center", va="center", color="#90a5ab", fontsize=9, zorder=2)
        for f in plot_fixtures:
            if KIND.get(f["lane"], "task") != kind:
                continue
            points = f["path_ft"] or ([[f["x_ft"], f["z_ft"]]] if f["x_ft"] is not None else [])
            if not points:
                continue
            color = COLORS[f["cct_k"]]
            held = bool(f["hold_ids"])
            if len(points) > 1:
                ax.plot([p[0] for p in points], [p[1] for p in points],
                        color=color, linestyle="--" if held else "-", linewidth=1.6, zorder=4)
                x, z = points[len(points)//2]
            else:
                x, z = points[0]
                ax.scatter([x], [z], s=27, c=color, edgecolors="white", linewidths=.5, zorder=5)
                if held:
                    ax.scatter([x], [z], s=95, facecolors="none", edgecolors="#a04d29", linewidths=.8, zorder=6)
            ax.annotate(f["id"], (x, z), xytext=(3, 3), textcoords="offset points", fontsize=4.8,
                        color="#213842", zorder=7)
        ax.set_xlim(min_x, max_x); ax.set_ylim(max_z, min_z); ax.set_aspect("equal")
        ax.set_xlabel("Sheet x (feet; west to right)"); ax.set_ylabel("Sheet z (feet; north downward)")
        ax.grid(color="#b4c6cc", linewidth=.3, alpha=.45)
        ax.set_title(f"{title} | typical floor\n{RELEASE}", fontsize=14, fontweight="bold", loc="left")
        ax.legend(handles=legends, loc="upper center", bbox_to_anchor=(.5, -.055), ncol=2, fontsize=8, frameon=False)
        fig.text(.09, .025, "Approximate lighting zones, not measured walls. Unringed symbols are not product or construction approval.\n"
                 "No PSU hatch location, wiring route, structural cutting or fixing detail is released. See schedules and site holds.",
                 fontsize=8, color="#744023")
        fig.tight_layout(rect=(0, .07, 1, .98))
        for suffix in ("pdf", "svg", "png"):
            fig.savefig(OUT / f"lighting-plan-{kind}.{suffix}", dpi=150,
                        metadata={"Creator": "House lighting review"} if suffix in ("pdf", "svg") else None)
        plt.close(fig)


def plot_heatmaps(data, heatmaps):
    folder = OUT / "heatmaps"
    folder.mkdir(exist_ok=True)
    lux_cmap = LinearSegmentedColormap.from_list("review_lux", [
        (0.0, "#e5eff1"), (100/750, "#82bacb"), (300/750, "#d8b561"),
        (500/750, "#cf793d"), (1.0, "#813931"),
    ])
    lux_cmap.set_bad("white")
    with PdfPages(OUT / "heatmaps-summary.pdf") as pdf:
        for room_id, grid in heatmaps["rooms"].items():
            fig, axes = plt.subplots(1, 2, figsize=(11.7, 8.3), constrained_layout=True)
            fig.suptitle(f"{room_id} | saved analytic illuminance estimates\n{RELEASE}", fontsize=15, fontweight="bold")
            result = data["lighting"]["calculations"]["rooms"][room_id]
            for ax, scenario, title in zip(axes, ("HIGH_100", "Mood"), ("Main lights - 100%", "Mood scene")):
                values = np.ma.masked_invalid(np.array(
                    [[float("nan") if x is None else x for x in row] for row in grid["E"][scenario]], dtype=float))
                half = grid["step_m"]/2
                extent = (grid["x_m"][0]-half, grid["x_m"][-1]+half, grid["z_m"][-1]+half, grid["z_m"][0]-half)
                image = ax.imshow(values, origin="upper", extent=extent, cmap=lux_cmap, vmin=0, vmax=750, interpolation="nearest")
                ref = result.get("combinations", {}).get(scenario) or result.get("scenes", {}).get(scenario)
                suffix = f" / {ref['avg']} avg, {ref['min']} min lx, U0 {ref['U0']}" if ref else ""
                ax.set_title(title + suffix, fontsize=9)
                ax.set_xlabel("sheet x (m)"); ax.set_ylabel("sheet z (m)"); ax.set_aspect("equal")
                fig.colorbar(image, ax=ax, shrink=.55, label="maintained lx (750+ clipped)")
            caveat = "Generic optics; not a measured result. 0.5 m statistics border; selected curtain strips excluded."
            if room_id == "LIV":
                caveat += " Mood retains inherited pooja allowance; revised niche held."
            if room_id == "CBR":
                caveat += " Children's geometry remains an unmeasured planned frame."
            fig.text(.05, .025, caveat, fontsize=8, color="#803f22")
            pdf.savefig(fig)
            fig.savefig(folder / f"{room_id}-analytic.png", dpi=125)
            plt.close(fig)


def table_page(pdf, title, columns, rows, widths, note):
    fig, ax = plt.subplots(figsize=(11.7, 8.3)); ax.axis("off")
    fig.text(.04, .96, title, fontsize=15, fontweight="bold", ha="left")
    fig.text(.04, .925, RELEASE + " | one typical flat; exact quantities and routes require site review", fontsize=8, color="#9d4b28")
    ax.set_position([.04, .10, .92, .78])
    table = ax.table(cellText=rows, colLabels=columns, colWidths=widths, loc="upper center", cellLoc="left")
    table.auto_set_font_size(False); table.set_fontsize(7); table.scale(1, 1.15)
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor("#d1dce0")
        if row == 0:
            cell.set_facecolor("#dce9ec"); cell.set_text_props(weight="bold", color="#1a303c")
        elif row % 2 == 0:
            cell.set_facecolor("#f4f8f8")
    fig.text(.04, .035, textwrap.fill(note, 145), fontsize=7.5, color="#4d6874")
    pdf.savefig(fig); plt.close(fig)


def schedule_pdf(data, fixtures, curtain, groups, psus, products):
    with PdfPages(OUT / "lighting-review-schedules.pdf") as pdf:
        summary = [
            ["104", "Base fittings in inherited optical calculations"],
            ["4 / 8.88 m", "Selected 2700 K curtain strips; unmeasured; excluded from lux"],
            ["47 + 4", "Base controlled groups plus four separate curtain circuit records"],
            ["21 / 38 / 3", "Brightness knobs / modeled outputs / modeled PWM repeaters"],
            ["12 / 1,980 W", "24 V supplies and selected S1 planning nameplate per flat"],
            ["P01 / 480 W", "Reference-only supply; 181.52 W strip load; branch protection open"],
            ["10", "Mains dimmer groups with product/compatibility procurement holds"],
            ["K-2", "Kitchen worktop: 518 avg / 323 min lx, U0 0.623; analytic only"],
        ]
        table_page(pdf, "Lighting review / quantities and holds", ["Quantity", "Scope"], summary, [.18, .82],
                   "No approved SKU, measured cable route, installation detail, breaker PASS or construction release. "
                   "Four curtain lengths and the CBR window remain unmeasured; W03 is excluded.")
        for start in range(0, len(fixtures), 25):
            chunk = fixtures[start:start+25]
            rows = [[f["id"], f["room"], f["group"], str(f["cct_K"]), str(f["nominal_W"]),
                     "HOLD" if f["placement_holds"] else "review"] for f in chunk]
            table_page(pdf, f"Base fitting schedule / {start+1}-{start+len(chunk)}",
                       ["Fitting", "Room", "Control group", "K", "W", "Placement"], rows,
                       [.14, .09, .32, .08, .08, .16],
                       "Fitting positions and sources are generic design allowances. See fixture-ledger.csv for coordinates, "
                       "CCT reason, IP target, detailed hold IDs and exact source descriptions.")
        for start in range(0, len(groups), 22):
            chunk = groups[start:start+22]
            rows = [[g["board"], g["group"], g["circuits_including_selected_curtains"], str(g["supply"]),
                     str(g["modeled_outputs"]), str(g["modeled_repeaters"])] for g in chunk]
            table_page(pdf, f"Switchboard and brightness groups / {start+1}-{start+len(chunk)}",
                       ["Board", "Group", "Circuits incl. selected curtains", "24 V PSU", "Outputs", "Repeaters"],
                       rows, [.10, .23, .36, .12, .09, .10],
                       "Conceptual grouping only. Group ratings, protective devices, SELV segregation, locations and wiring "
                       "must be designed by the electrician and verified against exact equipment.")
        rows = [[p["psu"], p["circuits"], str(p["nameplate_W"]), str(p["strip_load_W"]),
                 str(p["planning_pct_of_0_60"])] for p in psus]
        table_page(pdf, "Selected S1 supply schedule",
                   ["PSU", "Controlled circuits", "Nameplate W", "Strip load W", "% of assumed 0.60"],
                   rows, [.09, .47, .14, .14, .16],
                   "0.60 = 0.80 x 0.75 is an unverified project sizing allowance, not a manufacturer rating. "
                   "P01 feeder, voltage drop, 20 A-to-12.5 A distribution, LT-4/LT-5 inrush and protection are open.")
        for start in range(0, len(products), 22):
            chunk = products[start:start+22]
            rows = [[p["type"], str(p["fixed_CCT_K"]), str(p["quantity_per_flat"]), str(p["total_run_m_indicative"]),
                     p["locations"]] for p in chunk]
            table_page(pdf, f"Generic product search list / {start+1}-{start+len(chunk)}",
                       ["Generic type", "K", "Qty/flat", "Run m", "Locations"], rows, [.35, .08, .10, .10, .37],
                       "Search categories are not specified or approved makes. Check the detailed CSV for power, lumens, "
                       "beam, CRI/R9 and IP targets; strips and dimensions require field measurement.")


def make_spec(data, fixtures, cp, psus, groups):
    l = data["lighting"]
    m = {x["id"]: x for x in l["fixed_cct_map"]["fittings"]}
    room_lines = []
    for r in l["design_inputs"]["rooms"]:
        rows = [f for f in fixtures if f["room"] == r["id"]]
        bins = Counter(f["cct_K"] for f in rows)
        room_lines.append(f"| {r['name']} ({r['id']}) | {len(rows)} | " +
                          ", ".join(f"{n} x {k} K" for k, n in sorted(bins.items())) + " |")
    pockets = "\n".join(f"| {s['id']} | {s['target_knob_group']} | {s['proposed_supply']} | "
                         f"{s['indicative_strip_length_m']:.2f} | {8*s['indicative_strip_length_m']:.2f} |"
                         for s in cp["strips"])
    psu_table = "\n".join(f"| {p['psu']} | {p['circuits']} | {p['nameplate_W']} | {p['strip_load_W']} |"
                           for p in psus)
    scene_levels = l["design_inputs"]["scenes"]["levels"]
    scene_table = "\n".join(f"| {name} | " + (", ".join(
        f"{lane} {'see accent study' if level is None else str(round(level*100))+'%'}"
        for lane, level in levels.items()) or "all off") + " |"
        for name, levels in scene_levels.items())
    holds = l["design_inputs"]["provenance"]["layout_basis"]["holds"]
    hold_table = "\n".join(f"| {h['id']} | {h['item'].replace('|', '/')} | {h['needed_to_release'].replace('|', '/')} |"
                            for h in holds)
    return f"""# Lighting specification and review handoff

**{RELEASE}.** Homeowner selections establish design direction, not fabrication, product approval, electrical protection or a proven dimming chain.

| Binding | SHA-256 |
|---|---|
| Current house master | `{EXPECTED_MASTER}` |
| Current lighting design-input record (canonical JSON) | `{canon(l['design_inputs'])}` |
| Original photometry calculation input (canonical JSON) | `{EXPECTED_OPTICAL_DI}` |
| Saved analytic heatmap | `{EXPECTED_HEATMAP}` |

The photometric calculations and heatmaps were **not recalculated** for this rebind. Original optical inputs, every fixture position and every room/task result were compared with the verified fixed-white source. The recent changes are status/selection and electrical topology changes. Generic optics, maintenance factor 0.8, estimated geometry and assumed reflectance remain; no measured lux or manufacturer IES/LDT equivalence is claimed.

## Fixed CCT and fitting schedule

All coves, decorative strips and selected curtain strips are **2700 K**. Living, dining and bedroom mains/readers are generally **3000 K**; kitchen task, utility, dressing and bath face/task lights are **4000 K**. The CCT is fixed by fitting; the controls adjust brightness only. `fixture-ledger.csv` and `fixed-cct-map.json` give each fitting, rule and hold.

| Room | Base fittings | Fixed white bins |
|---|---:|---|
{chr(10).join(room_lines)}

Base: 104 fittings, 47 controlled groups. Selected extension: four additional curtain strips and four circuit records, with no lux credit. CBR-H1-H6 are shown as switchable review fittings on C37 at their existing locations; the C37 dimmer and other CBR ceiling/bed/desk/site holds remain.

## Curtain pockets: selected, not measured

| Strip | Existing LOW knob | Planned supply | Indicative m | Generic load W |
|---|---|---|---:|---:|
{pockets}

Indicative total **8.88 m / 71.04 W** assumes generic 8 W/m and 0.30 m returns. The inherited electrical scenario rounds individual strip loads to 0.1 W, so its per-supply loads differ slightly from the per-pocket figures above. No length is measured from a photo. Confirm pocket width/depth, two tracks, brackets, stack, hidden strip setback, profile, heat, access and cable route by site mock-up (**H-CURTAIN-POCKET**). CBR window is an unmeasured placeholder. MBR W03 is excluded and remains held. A shared LOW knob means the curtain strip cannot be independently off from that room's cove.

## Brightness scenes

These are illustrative settings of the already separate controls, not a claim that the house has a scene controller. Percentages are relative model settings; individual users may adjust. A dash means not specified; `None` accents use the separate accent study. Off and Night have no saved room-grid map.

| Setting | Relative levels |
|---|---|
{scene_table}

Bathroom grooming is modeled with the independent face control at 100% and the corresponding HIGH control at 30-50%; the selected face/driver/dimmer chain is unverified.

## Selected S1 controls and supply

Per flat: **21** single-colour brightness knobs, **38** modeled outputs, **3** modeled PWM repeaters, **10** mains-dimmer groups on procurement hold, **12** planned 24 V supplies totaling **1,980 W**. The 104-fitting base alone has 12 supplies / 1,890 W; the S1 overlay includes P07/P12 changes and all four strips. The 48 V track driver is separate.

K-LIV-LOW uses **P01 at 480 W class**, C03/C04/C05/X-CURT-LIV, six modeled outputs and two modeled repeaters. The strip load is **181.52 W / 7.56 A at 24 V**, excluding auxiliary and feeder loss. The reference Mean Well HLG-480H-24 is **not** a selected or approved SKU. `0.60 = 0.80 x 0.75` is only a project planning allowance, not an approved thermal rating.

| PSU | Selected S1 circuits | Planned nameplate W | Generic load W |
|---|---|---:|---:|
{psu_table}

**OPEN, no breaker PASS:** the 20 A reference exceeds the candidate T1-K's 12.5 A input nameplate. Distribution, branch and equipment protection, exact chain, low-end dimming/flicker, heat and supply location need licensed electrician and manufacturer design. Old P01/P03 living voltage-drop checks and LT-4/LT-5 inrush screens are invalid. The HLG-480H datasheet and retained installation table disagree on B16/C16 unit limits; obtain manufacturer guidance. P16 remains 121 W on 240 W; modeled S1 C39 3.3% and C40 3.6% are MARGINAL, not a cable-size instruction. `voltage-drop-selected-s1.csv` marks five living sections HOLD and unknown.

## Calculated results: limitations

Kitchen K-2 (KIT-T4 plus KIT-T1 at generic 650 lm/m) retains **518 lx average / 323 lx minimum / U0 0.623** on the modeled worktop. It becomes marginal in the documented lower-reflectance, lower-output or cabinet-offset sensitivity cases. Room grids in `heatmaps.json` and the workbench are at their stated receiver planes; they are not worktop, face or reading measurements. Living LOW and scenes using accent retain an inherited pooja allowance and are not current niche photometry. Pooja display is small idols with a framed picture behind, conceptual only; niche dimensions, light geometry, thermal/fire clearance and support remain held. No final aim or cutting instruction is authorized.

## Site, layout and product holds

| ID | Issue | Before release |
|---|---|---|
{hold_table}

Also retain the ten mains-dimmer compatibility holds, bath-zone/earthing/segregation and dry/wet protection review, P16/C39/C40, inrush, manufacturer photometry, CCT binning, supply derating and electrical surge/environment checks. Qualify construction using measured conditions and local professional approval. OPT-E (BWP carcass, laminate shutters) is selected; the split master wardrobe and the dressing/utility cabinets have unmeasured widths/clearances and are not fabrication-ready.

`generic-product-search.csv` is a generic search list, not an order or current quote. Historical cost and compliance references are clearly labelled; do not use prior P01/P03 supply, output, voltage-drop or breaker totals as current.
"""


def main():
    global OUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUT,
                        help="New empty output directory within this session's files")
    OUT = parser.parse_args().output.resolve()
    require(OUT.is_relative_to(SESSION.resolve()), "Output must remain inside this session's files")
    raw_master = MASTER.read_bytes()
    require(sha(raw_master) == EXPECTED_MASTER, f"Master changed: {sha(raw_master)}; do not rebind blindly")
    require(not OUT.exists() or not any(OUT.iterdir()),
            f"Output directory {OUT} is not empty; choose a new directory to preserve previous review evidence")
    data = json.loads(raw_master)
    heatmaps = read(PACK / "heatmaps.json")
    optical_check = validate_optical_provenance(data, heatmaps)
    cct_map, cp, hold_map, psu_rows, voltage_rows = reconcile(data)
    for strip in cp["strips"]:
        strip["proposed_supply_status"] = (
            "HOMEOWNER_SELECTED_S1_REVIEW; measured pocket, product, supply distribution and exact chain remain held"
        )
    fixtures, curtain, group_rows, circuit_rows = schedule_rows(data, cct_map, cp, hold_map)
    products = product_rows(fixtures, cp)
    OUT.mkdir(parents=True, exist_ok=True)
    lighting = data["lighting"]

    original_binding = copy.deepcopy(cct_map["binding"])
    fragment_bytes = json_bytes({"lighting": {"design_inputs": lighting["design_inputs"]}})
    cp_bytes = json_bytes(cp)
    cct_map["binding"].update({
        "master_sha256": EXPECTED_MASTER,
        "design_inputs_sha256": canon(lighting["design_inputs"]),
        "fragment_file_sha256": sha(fragment_bytes),
        "curtain_pocket_candidate_json_sha256": sha(cp_bytes),
        "photometry_source_design_inputs_sha256": EXPECTED_OPTICAL_DI,
        "original_map_binding": original_binding,
        "binding_method": "Current master/selection rebind; inherited optical results are not recalculated",
    })
    cct_map["curtain_pocket_candidates"]["source"] = "curtain-pocket-s1.json in this review package"
    cct_map["selected_curtain_S1"]["effective_totals"] = copy.deepcopy(lighting["controls"]["selected_curtain_S1_extension"]["with_S1"])
    for f in cct_map["fittings"]:
        f["placement_hold_ids"] = hold_map[f["id"]]
        if f["id"] in {f"CBR-H{i}" for i in range(1, 7)}:
            f["viewer_operability"] = "ACTIVE_FOR_REVIEW; C37 dimmer procurement remains held"
    for p in cct_map["curtain_pocket_candidates"]["pockets"]:
        p["placement_hold_ids"] = hold_map[p["id"]] or (["H-MBR-W03"] if p["id"] == "CURT-MBR-W03" else [])
        p["photometry_credit"] = False

    output("lighting-design-inputs.json", fragment_bytes)
    output("curtain-pocket-s1.json", cp_bytes)
    write_json("fixed-cct-map.json", cct_map)
    write_json("fixture-ledger.json", lighting["fixtures"])
    write_json("circuit-control-psu-ledger.json", lighting["controls"])
    write_json("electrical-checks.json", lighting["electrical_checks"])
    write_json("calc-results-current.json", lighting["calculations"])
    write_json("calculation-validity.json", lighting["calculation_validity"])
    write_json("bom-historical-estimate.json", lighting["bom"])
    output("heatmaps.json", (PACK / "heatmaps.json").read_bytes())
    output("compliance-analytic-reference.csv", (PACK / "compliance.csv").read_bytes())
    criteria = (SESSION / "lighting-criteria-and-combinations.md").read_text(encoding="utf-8")
    output("criteria-historical-reference.md", (
        "> HISTORICAL RESEARCH REFERENCE: the rev 3.3 room comparison, tunable options and prior schedules below "
        "are not the current selected layout. Use lighting-specification.md and the current schedules for design review.\n\n"
        + criteria).encode("utf-8"))
    write_csv("fixture-ledger.csv", list(fixtures[0]), fixtures)
    write_csv("curtain-strips.csv", list(curtain[0]), curtain)
    write_csv("switchboard-schedule.csv", list(group_rows[0]), group_rows)
    write_csv("circuit-ledger.csv", list(circuit_rows[0]), circuit_rows)
    write_csv("supply-ledger-selected-s1.csv", list(psu_rows[0]), psu_rows)
    write_csv("voltage-drop-selected-s1.csv", list(voltage_rows[0]), voltage_rows)
    write_csv("generic-product-search.csv", list(products[0]), products)

    plot_fixtures = []
    map_rows = {x["id"]: x for x in cct_map["fittings"]}
    for f in lighting["fixtures"]:
        m = map_rows[f["id"]]
        plot_fixtures.append({
            "id": f["id"], "room": f["room"], "lane": f["lane"], "circuit": f["circuit"],
            "group_id": m["group_id"], "cct_k": m["cct_k"], "x_ft": f["x_ft"], "z_ft": f["z_ft"],
            "path_ft": f["path_ft"], "hold_ids": hold_map[f["id"]], "supply": clean(next(
                c["psu"] for c in lighting["controls"]["circuits"] if c["circuit"] == f["circuit"])),
            "description": f["desc"], "status": "Active for review" if f["id"] in {f"CBR-H{i}" for i in range(1, 7)}
                else "Design review; product and site checks remain open",
        })
    for s in cp["strips"]:
        plot_fixtures.append({
            "id": s["id"], "room": s["room"], "lane": "LOW", "circuit": "X-" + s["id"],
            "group_id": s["target_knob_group"], "cct_k": 2700, "x_ft": None, "z_ft": None,
            "path_ft": s["polyline_ft"], "hold_ids": hold_map[s["id"]], "supply": s["proposed_supply"],
            "description": "Curtain-pocket warm strip; indicative length, unmeasured; no lux credit",
            "status": "Homeowner-selected for review; pocket mock-up and product/electrical holds remain",
        })
    require(len(plot_fixtures) == 108, "Workplan fixture count")
    payload = {
        "master_sha256": EXPECTED_MASTER, "photometry_source_design_inputs_sha256": EXPECTED_OPTICAL_DI,
        "rooms": [{"id": r["id"], "name": r["name"], "poly_ft": r["poly_ft"]} for r in lighting["design_inputs"]["rooms"]],
        "fixtures": plot_fixtures, "heatmaps": heatmaps, "room_results": lighting["calculations"]["rooms"],
    }
    template = (SOURCE / "lighting-workbench.template.html").read_text(encoding="utf-8")
    require(template.count("__DATA__") == 1, "Workbench template data placeholder")
    safe_payload = json.dumps(payload, separators=(",", ":"), ensure_ascii=False, allow_nan=False).replace("<", "\\u003c")
    output("lighting-workbench.html", template.replace("__DATA__", safe_payload).encode("utf-8"))
    output("lighting-specification.md", make_spec(data, fixtures, cp, psu_rows, group_rows).encode("utf-8"))
    output("README.md", f"""# Current lighting review package

**{RELEASE}.** One typical Hyderabad 2BHK floor; confirm conditions independently on all four floors.

Master SHA-256: `{EXPECTED_MASTER}`. The package is generated from that master; `manifest.json` binds each file. The optical calculation input remains `{EXPECTED_OPTICAL_DI}` and the saved heatmap remains `{EXPECTED_HEATMAP}`. Fixture geometry and the optical numerical dependencies were checked against the previously verified source; no new photometric run or product equivalence is claimed.

- `lighting-workbench.html`: offline plan, individual fitting inspector and saved analytic room maps. The controls select stored results, not live recalculation.
- `lighting-plan-main`, `lighting-plan-mood`, `lighting-plan-task`: PDF, SVG and PNG plan sheets. Lighting-zone outlines and the four curtain lengths remain approximate.
- `lighting-review-schedules.pdf`: review quantities, fitting/control/supply and generic product tables.
- `heatmaps-summary.pdf`, `heatmaps/*.png`, `heatmaps.json`: inherited numerical model, no curtain lux credit.
- `lighting-specification.md`, `fixture-ledger.csv`, `curtain-strips.csv`, `switchboard-schedule.csv`, `circuit-ledger.csv`, `supply-ledger-selected-s1.csv`, `voltage-drop-selected-s1.csv`, `generic-product-search.csv`: current review schedules.
- `compliance-analytic-reference.csv`, `criteria-historical-reference.md`, `bom-historical-estimate.json`: prior calculations, research and cost allowances; not current product, cost or statutory approval.

Four curtain strips are homeowner-selected but held for pocket measurement/mock-up; W03 is excluded. CBR-H1-H6 are active for review; their C37 dimmer and other site holds remain. P01 is one 480 W-class reference supply; P03 is removed. P01 distribution/protection, LT-4/LT-5 inrush and living voltage drop are OPEN. P16/C39/C40 remain MARGINAL. Product approval, exact-chain proof and construction release are false; a licensed electrician and manufacturers must resolve the electrical design.
""".encode("utf-8"))
    plot_plans(data, plot_fixtures)
    plot_heatmaps(data, heatmaps)
    schedule_pdf(data, fixtures, curtain, group_rows, psu_rows, products)
    evidence = OPT / "heatmaps" / "heatmap-KITWT-K-2.png"
    evidence_key = "heatmaps/heatmap-KITWT-K-2.png"
    require(sha(evidence.read_bytes()) == lighting["supporting_outputs"]["files"][evidence_key]["sha256"],
            "K-2 task-plane evidence changed")
    shutil.copyfile(evidence, OUT / "heatmaps" / "kitchen-worktop-K2-source.png")

    require(sha(MASTER.read_bytes()) == EXPECTED_MASTER, "Master changed during export; package is stale")
    files = {str(p.relative_to(OUT)).replace("\\", "/"): {"sha256": sha(p.read_bytes()), "bytes": p.stat().st_size}
             for p in sorted(OUT.rglob("*")) if p.is_file() and p.name not in {"manifest.json", "verification.json"}}
    manifest = {
        "schema": "house-lighting-current-review/1",
        "master_sha256": EXPECTED_MASTER, "current_design_inputs_canonical_sha256": canon(lighting["design_inputs"]),
        "original_photometry_design_inputs_canonical_sha256": EXPECTED_OPTICAL_DI,
        "original_heatmaps_sha256": EXPECTED_HEATMAP, "source_verification_sha256": EXPECTED_OLD_VERIFICATION,
        "rebind_status": "OPTICAL_SOURCE_UNCHANGED; numerical heatmaps reused, not a new photometric run",
        "site_assumptions": "approximate lighting zones, unmeasured curtain lengths, generic optics; no curtain lux credit",
        "counts": {"base_fittings": 104, "base_circuits": 47, "selected_curtain_strips": 4,
                   "selected_circuits": 51, "brightness_knobs": 21, "modeled_outputs": 38,
                   "modeled_repeaters": 3, "supplies_24V": 12, "nameplate_W": 1980},
        "retained": {"construction_release": False, "product_approval": False, "exact_chain_proven": False,
                     "P01_voltage_drop": "HOLD", "LT4_LT5_inrush": "INVALID / OPEN",
                     "P16_C39_C40": "MARGINAL / OPEN", "curtain_pockets": "H-CURTAIN-POCKET",
                     "W03": "EXCLUDED / HELD", "CBR_H1_H6": "active for review; C37 dimmer held"},
        "source_comparison": optical_check, "files": files,
        "verification_receipt": "verification.json binds this manifest and is excluded from files to avoid a circular hash",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path = write_json("manifest.json", manifest)
    print(json.dumps({"directory": str(OUT), "master_sha256": EXPECTED_MASTER,
                      "manifest_sha256": sha(manifest_path.read_bytes()), "file_count": len(files),
                      "source_comparison": optical_check}, indent=2))


if __name__ == "__main__":
    main()
