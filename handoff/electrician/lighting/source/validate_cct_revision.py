"""Verify that the current master differs from its predecessor only by the reviewed CCT proposal."""
import copy
import hashlib
import json
from pathlib import Path

PRIOR_SHA = "b6f6bf1a127c7e39086deb9fd1d2c0dff79a495381e1a4b9457f6a9a468f23ac"
CURRENT_SHA = "1fa6b0fa040d2f0c81427d9277eb9b98f23170b7f63446f287000d58fc9002a4"
IDS = {f"LIV-H{i}" for i in range(1, 11)} | {f"DIN-H{i}" for i in (1, 2, 3, 6)} | {
    f"MBR-H{i}" for i in range(1, 9)
} | {f"CBR-H{i}" for i in range(1, 7)}
CIRCUITS = {"C01", "C02", "C09", "C10", "C20", "C37"}


def load_verified(path, expected):
    raw = Path(path).read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected:
        raise ValueError(f"Unexpected master SHA-256: {actual}")
    return json.loads(raw)


def verify(prior, current):
    old, normalized = prior["lighting"], copy.deepcopy(current)
    light = normalized["lighting"]
    decision = light.pop("current_cct_review_decision")
    if set(decision["changed_fittings"]) != IDS or decision["prior_master_sha256"] != PRIOR_SHA:
        raise ValueError("Unexpected CCT decision or predecessor")
    for section in ("fixtures",):
        seen = set()
        for item in light[section]:
            if item["id"] in IDS:
                if item["room"] not in {"LIV", "DIN", "MBR", "CBR"} or item["lane"] != "HIGH" or item["cct"] != "4000K":
                    raise ValueError(f"Unexpected selected fixture {item['id']}")
                item["cct"] = "3000K"
                seen.add(item["id"])
        if seen != IDS:
            raise ValueError("Selected fixture IDs do not match")
    seen = set()
    for room in light["design_inputs"]["rooms"]:
        for item in room["fixtures"]:
            if item["id"] in IDS:
                if item["cct"] != "4000K" or item["lane"] != "HIGH":
                    raise ValueError(f"Unexpected design-input fixture {item['id']}")
                item["cct"] = "3000K"
                seen.add(item["id"])
    if seen != IDS:
        raise ValueError("Design-input fixture IDs do not match")
    seen = set()
    for circuit in light["controls"]["circuits"]:
        if circuit["circuit"] in CIRCUITS:
            if circuit["cct"] != ["4000K"] or not set(circuit["fixtures"]) <= IDS:
                raise ValueError(f"Unexpected selected circuit {circuit['circuit']}")
            circuit["cct"] = ["3000K"]
            seen.add(circuit["circuit"])
    if seen != CIRCUITS:
        raise ValueError("Selected circuit IDs do not match")

    mapping = light["fixed_cct_map"]
    original_map = old["fixed_cct_map"]
    originals = {f["id"]: f for f in original_map["fittings"]}
    for item in mapping["fittings"]:
        if item["id"] in IDS:
            if item["cct_k"] != 4000 or item["cct_rule"] != "R40-MAIN":
                raise ValueError(f"Unexpected map fixture {item['id']}")
            for key in ("cct_k", "cct_rule", "cct_reason"):
                item[key] = originals[item["id"]][key]
    original_groups = {g["group_id"]: g for g in original_map["groups"]}
    for group in mapping["groups"]:
        if set(group["fittings"]) & IDS:
            if group["cct_k"] != [4000] or group["cct_rules"] != ["R40-MAIN"] or not set(group["fittings"]) <= IDS:
                raise ValueError(f"Unexpected map group {group['group_id']}")
            for key in ("cct_k", "cct_rules"):
                group[key] = original_groups[group["group_id"]][key]
    if mapping["counts"]["by_cct_k"] != {"2700": 30, "3000": 12, "4000": 62}:
        raise ValueError("Unexpected CCT totals")
    for key in ("counts", "cct_bins_k", "cct_rules", "accepted_minor_mixes", "policy"):
        mapping[key] = copy.deepcopy(original_map[key])
    for key in ("status",):
        light["design_inputs"][key] = old["design_inputs"][key]
    for key in ("Mood", "Full"):
        light["design_inputs"]["scenes"]["cct"][key] = old["design_inputs"]["scenes"]["cct"][key]
    if normalized != prior:
        raise ValueError("Change exceeds the permitted CCT proposal and related descriptions")
    return {"prior_master_sha256": PRIOR_SHA, "current_master_sha256": CURRENT_SHA,
            "changed_fixture_ids": sorted(IDS), "changed_circuits": sorted(CIRCUITS),
            "note": "CCT proposal only; fixtures, circuits, lumens, watts and geometry otherwise unchanged. Prior optical outputs are inherited, not recalculated."}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prior")
    parser.add_argument("current")
    args = parser.parse_args()
    print(json.dumps(verify(load_verified(args.prior, PRIOR_SHA),
                            load_verified(args.current, CURRENT_SHA))))
