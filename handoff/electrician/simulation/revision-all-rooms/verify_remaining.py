"""Recompute the reported grid statistics directly from raw JSON and verify all hashes."""

import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ROOMS = ("UTL", "DRS", "LOB", "TL1", "TL2", "BAL")
VARIANTS = (
    "base", "rho_low", "rho_high", "beam_minus10", "beam_plus10",
    "ceil_minus0.1", "ceil_plus0.1", "pocket_narrow", "pocket_wide",
)
LOW = {"COVE", "LINE", "MOOD", "PERIM"}
SCENES = ("Off", "Mood", "Relax", "Work", "Full", "Night")


def load(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def assert_stats(expected, values, label):
    mean = sum(values) / len(values)
    minimum = min(values)
    maximum = max(values)
    uniformity = minimum / mean if mean > 0 else None
    for key, actual in (("avg", mean), ("min", minimum), ("max", maximum)):
        if abs(actual - expected[key]) > 0.000051:
            raise AssertionError(f"{label} {key}: {actual} != {expected[key]}")
    if uniformity is None:
        if expected["U0"] is not None:
            raise AssertionError(f"{label} zero-lux uniformity must be null")
    elif abs(uniformity - expected["U0"]) > 0.0000051:
        raise AssertionError(f"{label} U0: {uniformity} != {expected['U0']}")


def number(value, suffix=""):
    return "-" if value is None else f"{value:.2f}{suffix}"


def main():
    receipt_path = ROOT / "simulation-receipt-remaining.json"
    report_path = ROOT / "simulation-report-remaining.md"
    receipt = load(receipt_path)
    analysis = load(ROOT / "analysis-remaining.json")
    report = report_path.read_text(encoding="utf-8")
    if receipt["new_enclosure_cases"] != 54 or analysis["failures"]:
        raise AssertionError("incorrect coverage or failed analysis checks")
    if any(receipt["approvals"].values()):
        raise AssertionError("an approval is unexpectedly true")
    if not receipt["remote_cleanup"]["all_holds_removed"] or not receipt["remote_cleanup"]["jobs_directory_absent"]:
        raise AssertionError("remote cleanup was not confirmed")
    for name, expected in receipt["files"].items():
        path = ROOT / name
        if not path.is_file() or digest(path) != expected:
            raise AssertionError(f"receipt hash mismatch: {name}")
    if digest(Path(receipt["master"]["path"])) != receipt["master"]["sha256"]:
        raise AssertionError("master hash mismatch")
    if digest(Path(receipt["delivered_review_manifest"]["path"])) != receipt["delivered_review_manifest"]["sha256"]:
        raise AssertionError("review manifest hash mismatch")
    if digest(Path(receipt["previous_receipt"]["path"])) != receipt["previous_receipt"]["sha256"]:
        raise AssertionError("previous receipt hash mismatch")
    if digest(ROOT.parent / "simulation-report.md") != receipt["previous_report_sha256"]:
        raise AssertionError("previous report hash mismatch")

    recomputed = 0
    for variant in VARIANTS:
        raw = load(ROOT / "runs" / f"sens512small-{variant}" / "sim-results.json")
        if raw["variant"] != variant or set(raw["enclosures"]) != set(ROOMS):
            raise AssertionError(f"variant or room coverage mismatch: {variant}")
        for room in ROOMS:
            enclosure = raw["enclosures"][room]
            tag = f"grid:{room}"
            meta = enclosure["meta"][tag]
            bits = [
                (bool(mask), bool(task))
                for mask_row, task_row in zip(meta["mask"], meta["task"])
                for mask, task in zip(mask_row, task_row)
            ]
            selected = [task for inside, task in bits if inside]
            indices = [i for i, task in enumerate(selected) if task]
            if len(selected) != len(enclosure["points"][tag]) or not indices:
                raise AssertionError(f"bad task mask: {variant}/{room}")
            fixtures = list(enclosure["fixtures"].values())
            expected = analysis["rooms"][room][variant]

            def calc(weights):
                result = []
                for index in indices:
                    value = 0.0
                    for fixture in fixtures:
                        level = weights.get(fixture["lane"], 0) or 0
                        value += float(level) * fixture["E"][tag][index]
                    if not math.isfinite(value) or value < -1e-6:
                        raise AssertionError(f"bad lux at {variant}/{room}/{index}")
                    result.append(value)
                return result

            for lane, lane_data in expected["lanes"].items():
                assert_stats(lane_data, calc({lane: 1.0}), f"{variant}/{room}/{lane}")
                recomputed += 1
            assert_stats(expected["HIGH"], calc({"HIGH": 1.0}), f"{variant}/{room}/HIGH")
            recomputed += 1
            if expected["LOW"] is not None:
                assert_stats(expected["LOW"], calc({lane: 1.0 for lane in LOW}), f"{variant}/{room}/LOW")
                assert_stats(expected["HIGH_LOW"], calc({**{lane: 1.0 for lane in LOW}, "HIGH": 1.0}),
                             f"{variant}/{room}/HIGH_LOW")
                recomputed += 2
            for scene in SCENES:
                assert_stats(expected["scenes"][scene], calc(analysis["scenes"][scene]),
                             f"{variant}/{room}/{scene}")
                recomputed += 1
            if room == "UTL":
                task_values = calc({"HIGH": 1.0, "TASK": 1.0})
                actual = sum(task_values) / len(task_values)
                if abs(actual - expected["utility_HIGH_TASK"]["avg"]) > 0.000051:
                    raise AssertionError(f"{variant}/UTL/HIGH+TASK mismatch")
                recomputed += 1
            if room == "LOB":
                face_points = enclosure["points"]["lobby_face"]
                if len(face_points) != 3:
                    raise AssertionError(f"{variant}/LOB face point count mismatch")
                weights = analysis["scenes"]["Work"]
                face_values = [
                    sum(float(weights.get(f["lane"], 0) or 0) * f["E"]["lobby_face"][i]
                        for f in fixtures)
                    for i in range(len(face_points))
                ]
                assert_stats(expected["lobby_face_HIGH_MIRROR"], face_values,
                             f"{variant}/LOB/HIGH+MIRROR face")
                recomputed += 1
            if variant not in ("base", "pocket_narrow", "pocket_wide"):
                base = analysis["rooms"][room]["base"]
                hi_u = f"{number(base['HIGH']['U0'])} -> {number(expected['HIGH']['U0'])}"
                low_u = (f"{number(base['LOW']['U0'])} -> {number(expected['LOW']['U0'])}"
                         if base["LOW"] is not None and expected["LOW"] is not None else "-")
                row = (f"| {room} | {variant} | {number(expected['delta_pct']['HIGH'], '%')} | "
                       f"{hi_u} | {number(expected['delta_pct']['LOW'], '%')} | {low_u} |")
                if row not in report:
                    raise AssertionError(f"report sensitivity row mismatch: {room}/{variant}")
            if variant == "base":
                expected_row = f"| {room} | " + " | ".join(
                    f"{expected['scenes'][scene]['avg']:.1f}" for scene in SCENES
                ) + " |"
                if expected_row not in report:
                    raise AssertionError(f"report scene row mismatch: {room}")
        if variant in ("pocket_narrow", "pocket_wide"):
            for room in ROOMS:
                scene = ROOT / "runs" / f"sens512small-{variant}" / "radiance" / f"{room}.rad"
                base = ROOT / "runs" / "sens512small-base" / "radiance" / f"{room}.rad"
                if digest(scene) != digest(base):
                    raise AssertionError(f"pocket control did change {room} scene")

    for variant in ("base",) + tuple(v for v in VARIANTS
                                     if v not in ("base", "pocket_narrow", "pocket_wide")):
        utility = analysis["rooms"]["UTL"][variant]["utility_HIGH_TASK"]
        face = analysis["rooms"]["LOB"][variant]["lobby_face_HIGH_MIRROR"]
        row = f"| {variant} | {utility['avg']:.1f} | {face['avg']:.1f} / {face['min']:.1f} |"
        if row not in report:
            raise AssertionError(f"report task-plane row mismatch: {variant}")

    for phrase in ("identical-scene controls", "not a physical", "open-air", "not measured",
                   "Construction release, product approval and exact-chain proof remain false"):
        if phrase not in report:
            raise AssertionError(f"important report limitation omitted: {phrase}")
    result = {
        "status": "PASS",
        "independent_statistic_recomputations": recomputed,
        "room_variant_cases": 54,
        "receipt_files_verified": len(receipt["files"]),
        "report_sha256": digest(report_path),
        "receipt_sha256": digest(receipt_path),
        "verifier_sha256": digest(Path(__file__)),
        "master_sha256": receipt["master"]["sha256"],
    }
    (ROOT / "independent-verification.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
