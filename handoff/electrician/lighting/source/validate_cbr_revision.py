"""Verify the bounded, provisional children-ceiling successor to the CCT master."""
import copy
import hashlib
import json
import math
from pathlib import Path

PRIOR_SHA = "1fa6b0fa040d2f0c81427d9277eb9b98f23170b7f63446f287000d58fc9002a4"
E7D2_SHA = "e7d2e6c7cdeedd72abb3dd236304646eb01174a2df65b5401be8c53b907853e7"
E7D2_HEATMAP_SHA = "a94b370c0f3b9572c104b93fce96cdc3e110b5b2062f2c426d8cb6c95811b408"
# R05 successor: room-centre 1050 mm planning fan, reported band heights, CBR-only re-analysis.
CURRENT_SHA = "79ece2aef1acd63ee401702149a91e29a6ed660123c4d9d3640ab5304ed89822"
HEATMAP_SHA = "e935075c00174584056d8f4fb5aaac799146341c7d5923d1d45bd714a9a0e7c6"
R05_PATCH = Path(__file__).with_name("cbr-r05-revision.json")
R05_FAN_XZ_M = [7.0104, 10.8983376]
R05_SWEEP_MM = 1050
IDS = [f"CBR-X{i}" for i in range(1, 5)]
PATHS = [
    [[22.8698, 32.1], [20.4198, 32.1], [20.4198, 34.05]],
    [[25.0659, 32.1], [27.5159, 32.1], [27.5159, 34.05]],
    [[27.5159, 38.4991], [27.5159, 40.4491], [25.0659, 40.4491]],
    [[22.8698, 40.4491], [20.4198, 40.4491], [20.4198, 38.4991]],
]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_verified(path, expected):
    raw = Path(path).read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    require(actual == expected, f"Unexpected master SHA-256: {actual}")
    return json.loads(raw)


def canonical_sha(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def unique(rows, key, value):
    found = [row for row in rows if row[key] == value]
    require(len(found) == 1, f"Expected exactly one {key}={value}")
    return found[0]


def restore_fields(current, prior, fields):
    for field in fields:
        if field in prior:
            current[field] = copy.deepcopy(prior[field])
        else:
            current.pop(field, None)


def verify_e7d2(prior, current):
    normalized = copy.deepcopy(current)
    old, lighting = prior["lighting"], normalized["lighting"]
    di, old_di = lighting["design_inputs"], old["design_inputs"]
    room, old_room = unique(di["rooms"], "id", "CBR"), unique(old_di["rooms"], "id", "CBR")
    fixtures = {f["id"]: f for f in lighting["fixtures"]}
    old_fixtures = {f["id"]: f for f in old["fixtures"]}
    inputs = {f["id"]: f for f in room["fixtures"]}
    old_inputs = {f["id"]: f for f in old_room["fixtures"]}
    ceiling, old_ceiling = di["ceilings"]["CBR"], old_di["ceilings"]["CBR"]

    require(ceiling["lines_lit_ft"] == PATHS, "Proposed CBR LINE paths changed")
    require(ceiling["tray_corners_ft"] == old_ceiling["tray_corners_ft"], "The existing cove was moved")
    for fixture_id, path in zip(IDS, PATHS):
        fixture, previous = fixtures[fixture_id], old_fixtures[fixture_id]
        source, old_source = inputs[fixture_id], old_inputs[fixture_id]
        require(fixture["path_ft"] == source["path"]["pts_ft"] == path, f"{fixture_id}: path representations differ")
        length = lambda pts: sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
        require(abs(length(path) - length(previous["path_ft"])) < 1e-8, f"{fixture_id}: strip length changed")
        restore_fields(fixture, previous, ("path_ft", "note"))
        restore_fields(source, old_source, ("path", "note", "position_status"))
    require(fixtures["CBR-L1"] == old_fixtures["CBR-L1"], "The existing CBR cove fitting was changed")
    restore_fields(ceiling, old_ceiling, ("lines_lit_ft", "frame_ft", "lines_black", "lines_note", "status", "position_status"))
    restore_fields(room, old_room, ("status",))
    restore_fields(room["frame"]["fan_proposal"], old_room["frame"]["fan_proposal"], ("status",))
    restore_fields(di["calc_geometry"]["children"], old_di["calc_geometry"]["children"], ("status",))
    restore_fields(di["calc_geometry"]["children"]["fan"], old_di["calc_geometry"]["children"]["fan"], ("status",))
    restore_fields(di["pending_constraints"], old_di["pending_constraints"], ("_",))
    hold = unique(di["provenance"]["layout_basis"]["holds"], "id", "H-CBR-CEIL")
    old_hold = unique(old_di["provenance"]["layout_basis"]["holds"], "id", "H-CBR-CEIL")
    require(set(hold["fixtures"]) == {"CBR-L1", *IDS}, "The original ceiling hold was broadened or released")
    restore_fields(hold, old_hold, ("basis", "needed_to_release"))

    fan = unique(normalized["visualization_geometry"]["fans"], "room", "children")
    old_fan = unique(prior["visualization_geometry"]["fans"], "room", "children")
    require(fan["at_m"] == old_fan["proposal"]["global_xz_m"] == [7.3054, 11.0123376],
            "The fan is not at the existing provisional cove-centre position")
    restore_fields(fan, old_fan, ("at_m", "src", "status"))
    restore_fields(fan["proposal"], old_fan["proposal"], ("decision_status",))
    decision = normalized["decisions"].pop("children_ceiling_review")
    require(decision["construction_release"] is False and decision["moved_fittings"] == IDS
            and decision["retained_cove"] == "CBR-L1", "Proposal decision or release status changed")
    risks = decision["modelled_risks"]
    require((risks["wardrobe_vertical_lux_high_plus_low"], risks["wardrobe_target_lux"],
             risks["supine_nearest_degrees_from_zenith"]) == (149, 150, 3.2),
            "The modelled wardrobe or glare caveat changed")

    validity = lighting["calculation_validity"]
    revision = validity.pop("children_ceiling_revision")
    require(revision["predecessor_master_sha256"] == PRIOR_SHA and revision["retained_hold"] == "H-CBR-CEIL"
            and revision["construction_release"] is False and revision["fixture_ids"] == IDS
            and revision["reanalysed_heatmaps_sha256"] == E7D2_HEATMAP_SHA
            and revision["design_inputs_canonical_sha256"] == canonical_sha(current["lighting"]["design_inputs"]),
            "CBR analysis binding or site holds changed")
    require(validity["compliance_summary"] == {"PASS": 59, "MARGINAL": 10, "HOLD": 2},
            "Unexpected post-proposal calculation status counts")
    validity["compliance_summary"] = copy.deepcopy(old["calculation_validity"]["compliance_summary"])
    heat = lighting["supporting_outputs"]["files"]["heatmaps.json"]
    require(heat["sha256"] == E7D2_HEATMAP_SHA, "Current CBR heat-map is not bound")
    lighting["supporting_outputs"]["files"]["heatmaps.json"] = copy.deepcopy(
        old["supporting_outputs"]["files"]["heatmaps.json"])

    calc, old_calc = lighting["calculations"], old["calculations"]
    cbr = calc["rooms"]["CBR"]
    require((cbr["combinations"]["HIGH_100"]["avg"], cbr["combinations"]["LOW_100"]["avg"],
             cbr["combinations"]["HIGH+LOW_100"]["avg"]) == (127, 133, 261),
            "CBR generic-optics estimates changed")
    require(calc["children"]["wardrobe_face"]["HIGH_LOW_100"]["avg"] == 149,
            "CBR wardrobe estimate changed")
    for section in ("rooms", "sensitivity"):
        calc[section]["CBR"] = copy.deepcopy(old_calc[section]["CBR"])
    calc["hd14"]["highs_finish"]["LOR_sensitivity"]["CBR"] = copy.deepcopy(
        old_calc["hd14"]["highs_finish"]["LOR_sensitivity"]["CBR"])
    calc["children"] = copy.deepcopy(old_calc["children"])
    for key in calc["reading_settings"]:
        if key.startswith("CBR-"):
            calc["reading_settings"][key] = copy.deepcopy(old_calc["reading_settings"][key])
    for pocket in ("0.20m", "0.25m"):
        before, after = old_calc["curtains"][pocket]["rows"], calc["curtains"][pocket]["rows"]
        require(after[:-1] == before and after[-1]["window"] == "CBR"
                and after[-1]["fixture"] == "CBR-X3", f"{pocket}: unexpected curtain diagnostic")
        calc["curtains"][pocket] = copy.deepcopy(old_calc["curtains"][pocket])
    require(len(calc["compliance"]) == len(old_calc["compliance"]), "Compliance row count changed")
    for i, row in enumerate(calc["compliance"]):
        before = old_calc["compliance"][i]
        require((row["room"], row["check"]) == (before["room"], before["check"]), "Compliance row order changed")
        if row["room"] == "CBR":
            calc["compliance"][i] = copy.deepcopy(before)
    rb, previous_rb = calc["ceiling_rebase"], old_calc["ceiling_rebase"]
    rb["cove"]["CBR"] = copy.deepcopy(previous_rb["cove"]["CBR"])
    for name in ("room_lux", "compliance_changes"):
        require(len(rb["deltas"][name]) == len(previous_rb["deltas"][name]), f"{name}: row count changed")
        for i, row in enumerate(rb["deltas"][name]):
            before = previous_rb["deltas"][name][i]
            require(row["room"] == before["room"], f"{name}: row order changed")
            if row["room"] == "CBR":
                rb["deltas"][name][i] = copy.deepcopy(before)
    changes, previous_changes = rb["deltas"]["status_changes"], previous_rb["deltas"]["status_changes"]
    require(changes[:-1] == previous_changes and changes[-1]["room"] == "CBR"
            and changes[-1]["status_new"] == "MARGINAL", "Unexpected rebase status changes")
    rb["deltas"]["status_changes"] = copy.deepcopy(previous_changes)
    rb["deltas"]["status_counts_new"] = copy.deepcopy(previous_rb["deltas"]["status_counts_new"])
    require(rb["deltas"]["electrical_changes"]["worst_dV_pct"]["new"] == 3.6,
            "CBR base voltage-drop comparison changed")
    rb["deltas"]["electrical_changes"]["worst_dV_pct"]["new"] = \
        previous_rb["deltas"]["electrical_changes"]["worst_dV_pct"]["new"]
    require(calc["electrical_summary"]["worst_known_dV_pct"] == 3.6, "Unexpected worst known drop")
    calc["electrical_summary"]["worst_known_dV_pct"] = old_calc["electrical_summary"]["worst_known_dV_pct"]

    checks, old_checks = lighting["electrical_checks"], old["electrical_checks"]
    c40 = unique(checks["voltage_drop"], "circuit", "C40")
    old_c40 = unique(old_checks["voltage_drop"], "circuit", "C40")
    require((c40["branch_m"], c40["dV_pct"], c40["dV_branch_V"], c40["status"])
            == (6.87, 3.6, .32, "MARGINAL"), "Unexpected base C40 route or drop")
    restore_fields(c40, old_c40, ("branch_m", "dV_pct", "dV_branch_V"))
    require(checks["summary"]["worst_known_dV_pct"] == 3.6, "Unexpected electrical summary")
    checks["summary"]["worst_known_dV_pct"] = old_checks["summary"]["worst_known_dV_pct"]
    scenario_pairs = [
        (lighting["controls"]["selected_curtain_S1_extension"]["voltage_drop_changes"],
         old["controls"]["selected_curtain_S1_extension"]["voltage_drop_changes"]),
        (checks["selected_curtain_S1_extension"]["voltage_drop_changes"],
         old_checks["selected_curtain_S1_extension"]["voltage_drop_changes"]),
        (lighting["curtain_pocket_s1"]["selected_S1_electrical"]["voltage_drop_changed"],
         old["curtain_pocket_s1"]["selected_S1_electrical"]["voltage_drop_changed"]),
    ]
    for rows, before in scenario_pairs:
        row, old_row = unique(rows, "circuit", "C40"), unique(before, "circuit", "C40")
        require((row["branch_m"], row["dV_pct_before"], row["dV_pct_after"], row["status_after"])
                == (6.87, 3.6, 3.9, "MARGINAL"), "Unexpected selected-curtain C40 estimate")
        restore_fields(row, old_row, ("branch_m", "dV_pct_before", "dV_pct_after"))
    require(normalized == prior, "Changes exceed the reviewed CBR geometry and recalculation scope")
    return {
        "prior_master_sha256": PRIOR_SHA,
        "current_master_sha256": E7D2_SHA,
        "changed_fixture_ids": IDS,
        "heatmaps_sha256": E7D2_HEATMAP_SHA,
        "note": "Only the proposed CBR LINE paths and directly dependent calculations changed; "
                "the existing cove, all CCTs, loads and other fixture positions are retained. "
                "H-CBR-CEIL and construction holds remain.",
    }


ABSENT = {"$absent": True}
_CBR_KEYS = {"CBR", "children", "children_ceiling_review", "children_ceiling_revision"}


def _cbr_node(node):
    return isinstance(node, dict) and (
        str(node.get("room", "")).startswith("CBR") or node.get("room") == "children"
        or str(node.get("id", "")).startswith("CBR") or node.get("id") == "H-CBR-CEIL"
        or node.get("window") == "CBR")


def _scoped(doc, path):
    if any(str(k) in _CBR_KEYS for k in path):
        return True
    node = doc
    for k in path:
        if _cbr_node(node):
            return True
        if isinstance(node, dict) and k in node or isinstance(node, list) and isinstance(k, int) and k < len(node):
            node = node[k]
        else:
            return False
    return _cbr_node(node)


def r05_scope_violations(before, after, ops):
    """Return changed paths that are not confined to the children's room (CBR/R05)."""
    bad = []
    heat = ["lighting", "supporting_outputs", "files", "heatmaps.json"]
    for op in ops:
        path = op["path"]
        if path[:4] == heat and path[4:] in (["sha256"], ["bytes"]):
            continue
        if path[:4] == ["lighting", "calculations", "ceiling_rebase", "deltas"] and len(path) == 5:
            rows = [op["before"], op["after"]]
            if all(isinstance(r, list) for r in rows) and [x for x in rows[0] if x.get("room") != "CBR"] \
                    == [x for x in rows[1] if x.get("room") != "CBR"]:
                continue
        if not (_scoped(before, path) and _scoped(after, path)):
            bad.append(path)
    return bad


def _apply_reverse(doc, ops):
    for op in ops:
        *parents, leaf = op["path"]
        node = doc
        for k in parents:
            node = node[k]
        found = node.get(leaf, ABSENT) if isinstance(node, dict) else node[leaf]
        require(found == op["after"], f"R05 record does not match the current master at {op['path']}")
        if op["before"] == ABSENT:
            del node[leaf]
        else:
            node[leaf] = copy.deepcopy(op["before"])


def verify(prior, current):
    """Verify the R05 successor by rebuilding the e7d2 predecessor, then apply the e7d2 checks unchanged."""
    record = json.loads(R05_PATCH.read_text(encoding="utf-8"))
    require(record["predecessor_master_sha256"] == E7D2_SHA and record["successor_master_sha256"] == CURRENT_SHA,
            "R05 revision record is not bound to the expected masters")
    require(canonical_sha(current) == record["successor_canonical_sha256"], "Current master is not the R05 successor")
    rebuilt = copy.deepcopy(current)
    _apply_reverse(rebuilt, record["operations"])
    require(canonical_sha(rebuilt) == record["predecessor_canonical_sha256"],
            "R05 changes do not reconstruct the verified e7d2 predecessor")
    require(not r05_scope_violations(rebuilt, current, record["operations"]), "R05 changes exceed the children's room")

    fan = unique(current["visualization_geometry"]["fans"], "room", "children")
    require(fan["at_m"] == R05_FAN_XZ_M and fan["proposal"]["sweep_mm"] == R05_SWEEP_MM,
            "Children's fan is not the provisional room-centre 1050 mm planning sweep")
    lighting = current["lighting"]
    old_fixtures = {f["id"]: f for f in rebuilt["lighting"]["fixtures"]}
    for f in lighting["fixtures"]:
        if f["id"] in IDS:
            require({k: v for k, v in f.items() if k not in ("mount_h_m", "note")}
                    == {k: v for k, v in old_fixtures[f["id"]].items() if k not in ("mount_h_m", "note")},
                    f"{f['id']}: only the reported mounting height and status note may change")
            require("modelled ON" in f["note"] and "H-CBR-CEIL" in f["note"] and "unlit" not in f["note"],
                    f"{f['id']}: note must state modelled-ON design simulation and retain the physical hold")
        else:
            require(f == old_fixtures[f["id"]], f"{f['id']}: fixture changed outside the R05 heights")
    require(lighting["design_inputs"]["ceilings"]["CBR"]["tray_corners_ft"]
            == rebuilt["lighting"]["design_inputs"]["ceilings"]["CBR"]["tray_corners_ft"], "The existing cove was moved")
    hold = unique(lighting["design_inputs"]["provenance"]["layout_basis"]["holds"], "id", "H-CBR-CEIL")
    require(set(hold["fixtures"]) == {"CBR-L1", *IDS}, "The ceiling hold was broadened or released")
    decision = current["decisions"]["children_ceiling_review"]
    revision = lighting["calculation_validity"]["children_ceiling_revision"]
    require(decision["construction_release"] is False and revision["construction_release"] is False
            and revision["retained_hold"] == "H-CBR-CEIL" and revision["predecessor_master_sha256"] == E7D2_SHA
            and revision["reanalysed_heatmaps_sha256"] == HEATMAP_SHA
            and lighting["supporting_outputs"]["files"]["heatmaps.json"]["sha256"] == HEATMAP_SHA,
            "R05 analysis binding or release status changed")
    predecessor = verify_e7d2(prior, rebuilt)
    return {
        "prior_master_sha256": PRIOR_SHA,
        "current_master_sha256": CURRENT_SHA,
        "predecessor_master_sha256": E7D2_SHA,
        "changed_fixture_ids": IDS,
        "heatmaps_sha256": HEATMAP_SHA,
        "r05_operations": len(record["operations"]),
        "predecessor_check": predecessor["note"],
        "note": "R05 successor: fan at nominal room centre (1050 mm planning sweep, product not selected), "
                "homeowner-reported band heights (slab unmeasured) and CBR-only re-analysis with the retained "
                "cove and LINE modelled ON. H-CBR-CEIL, site, procurement and construction holds remain.",
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prior")
    parser.add_argument("current")
    args = parser.parse_args()
    print(json.dumps(verify(load_verified(args.prior, PRIOR_SHA), load_verified(args.current, CURRENT_SHA))))
