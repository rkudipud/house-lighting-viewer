"""Independently audit and summarise the six-room Radiance sensitivity runs."""

import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
PREVIOUS = ROOT.parent
ROOMS = ("UTL", "DRS", "LOB", "TL1", "TL2", "BAL")
VARIANTS = (
    "base", "rho_low", "rho_high", "beam_minus10", "beam_plus10",
    "ceil_minus0.1", "ceil_plus0.1", "pocket_narrow", "pocket_wide",
)
LOW = ("COVE", "LINE", "MOOD", "PERIM")
SCENES = ("Off", "Mood", "Relax", "Work", "Full", "Night")
MASTER = "b6f6bf1a127c7e39086deb9fd1d2c0dff79a495381e1a4b9457f6a9a468f23ac"
RECEIPT_SHA = "504395aadbff043b1e5d2e4fad7ed9356b974ec44e8f3d4dc4a8a6446b6f0960"
REMOTE_RCONTRIB = "db374fe9c78d9e49c43f5df488bec666253d96be21da6d49f09bb5a994eb6c69"
REMOTE_OCONV = "9033617bb079df6e5dafcb0b1758ac5ba630d86bc3eb191725e7bffff2209dc5"


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def load(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def stats(values):
    values = np.asarray(values, dtype=float)
    if not values.size or not np.isfinite(values).all():
        raise ValueError("empty or non-finite statistics input")
    avg = float(values.mean())
    return {
        "avg": round(avg, 4),
        "min": round(float(values.min()), 4),
        "max": round(float(values.max()), 4),
        "U0": round(float(values.min()) / avg, 5) if avg > 0 else None,
    }


def vectors(enclosure, tag, mask, scenes):
    size = len(enclosure["points"][tag])
    by_lane = {}
    for fixture in enclosure["fixtures"].values():
        lane = fixture["lane"]
        by_lane.setdefault(lane, np.zeros(size))
        by_lane[lane] += np.asarray(fixture["E"][tag], dtype=float)

    def combine(levels):
        total = np.zeros(size)
        for lane, level in levels.items():
            if lane in by_lane and level is not None:
                total += float(level) * by_lane[lane]
        return stats(total[mask])

    has_low = any(lane in by_lane for lane in LOW)
    return {
        "lanes": {lane: stats(values[mask]) for lane, values in sorted(by_lane.items())},
        "HIGH": combine({"HIGH": 1.0}) if "HIGH" in by_lane else None,
        "LOW": combine({lane: 1.0 for lane in LOW}) if has_low else None,
        "HIGH_LOW": combine({**{lane: 1.0 for lane in LOW}, "HIGH": 1.0})
        if has_low and "HIGH" in by_lane else None,
        "scenes": {name: combine(scenes[name]) for name in SCENES},
    }


def expected_parameters(old, variant):
    expected = json.loads(json.dumps(old["V"]))
    changes = {
        "rho_low": {"rho": {"ceiling": 0.70, "wall": 0.35, "floor": 0.15,
                            "furniture": 0.25, "pocket": 0.70}},
        "rho_high": {"rho": {"ceiling": 0.85, "wall": 0.70, "floor": 0.40,
                             "furniture": 0.55, "pocket": 0.85}},
        "beam_minus10": {"beam_delta": -10.0},
        "beam_plus10": {"beam_delta": 10.0},
        "ceil_minus0.1": {"ceil_delta": -0.1},
        "ceil_plus0.1": {"ceil_delta": 0.1},
        "pocket_narrow": {"pocket_w": 0.08, "lip": 0.08},
        "pocket_wide": {"pocket_w": 0.25, "lip": 0.03},
    }
    expected.update(changes.get(variant, {}))
    return expected


def within_parity(reference, candidate):
    difference = abs(candidate - reference)
    limit = max(0.30, abs(reference) * 0.06)
    return difference <= limit, difference, limit


def main():
    failures = []
    checks = []

    def check(name, problems, details=None):
        checks.append({"check": name, "status": "PASS" if not problems else "FAIL",
                       "problems": problems, "details": details})
        if problems:
            failures.append(name)

    receipt_path = PREVIOUS / "simulation-receipt.json"
    prior = load(receipt_path)
    old = load(PREVIOUS / "runs" / "base" / "sim-results.json")
    master_path = Path(prior["master"]["path"])
    master = load(master_path)
    scenes = master["lighting"]["design_inputs"]["scenes"]["levels"]
    if set(SCENES) - set(scenes):
        raise ValueError("one or more canonical scene definitions are missing")

    prior_errors = []
    if digest(receipt_path) != RECEIPT_SHA:
        prior_errors.append("prior receipt hash changed")
    if digest(master_path) != MASTER:
        prior_errors.append("master hash changed")
    if digest(Path(prior["delivered_review_manifest"]["path"])) != prior["delivered_review_manifest"]["sha256"]:
        prior_errors.append("delivered review manifest changed")
    for name, expected in prior["files"].items():
        path = PREVIOUS.joinpath(*name.split("/"))
        if not path.is_file() or digest(path) != expected:
            prior_errors.append(name)
    check("Previous receipt, source files, outputs, master and delivered review unchanged", prior_errors)

    runs = {}
    for variant in VARIANTS:
        path = ROOT / "runs" / f"sens512small-{variant}" / "sim-results.json"
        runs[variant] = load(path)

    meta_errors = []
    shape_errors = []
    scene_errors = []
    fixture_errors = []
    grid_shapes = {}
    engines = {}
    values = {room: {} for room in ROOMS}

    for variant, run in runs.items():
        meta = []
        engine = run["engine"]
        remote = engine.get("remote", {})
        if run["master_sha256"] != MASTER or run["variant"] != variant:
            meta.append("master or variant mismatch")
        if set(run["enclosures"]) != set(ROOMS):
            meta.append("room coverage mismatch")
        if run["params"] != old["params"] or run["MF"] != old["MF"] or run["units"] != old["units"]:
            meta.append("sampling, MF or units mismatch")
        if run["V"] != expected_parameters(old, variant):
            meta.append("variant parameters mismatch")
        if (remote.get("rcontrib_sha256") != REMOTE_RCONTRIB
                or remote.get("oconv_sha256") != REMOTE_OCONV
                or remote.get("procs") != 16
                or engine.get("cosm_cal_sha256") != prior["engine"]["cosm_cal_sha256"]):
            meta.append("remote engine, process count or generic optics hash mismatch")
        if meta:
            meta_errors.append({"variant": variant, "errors": meta})
        engines[variant] = remote

        for room in ROOMS:
            ref = old["enclosures"][room]
            enc = run["enclosures"][room]
            tag = f"grid:{room}"
            if enc["rooms"] != ref["rooms"] or enc["poly_ft"] != ref["poly_ft"]:
                fixture_errors.append(f"{variant}/{room}: rooms or plan polygon changed")
            if set(enc["fixtures"]) != set(ref["fixtures"]) or enc["skipped"] != ref["skipped"]:
                fixture_errors.append(f"{variant}/{room}: fixture set changed")
            if set(enc["points"]) != set(ref["points"]) or enc["meta"] != ref["meta"]:
                shape_errors.append(f"{variant}/{room}: sample planes or metadata changed")
            for name in ref["points"]:
                if name not in enc["points"] or enc["points"][name] != ref["points"][name]:
                    shape_errors.append(f"{variant}/{room}/{name}: sample points changed")

            info = enc["info"]
            if info["tray_h_m"] is not None or info["flat_slot"]:
                scene_errors.append(f"{variant}/{room}: an unmodelled tray or slot appeared")
            expected_height = round(ref["info"]["ceil_m"] + run["V"]["ceil_delta"], 4)
            if abs(info["ceil_m"] - expected_height) > 0.0001:
                scene_errors.append(f"{variant}/{room}: ceiling-height shift mismatch")

            grid = enc["meta"][tag]
            mask2d = np.asarray(grid["mask"], dtype=bool)
            task2d = np.asarray(grid["task"], dtype=bool)
            points = np.asarray(enc["points"][tag], dtype=float)
            mask = task2d[mask2d]
            if (mask2d.shape != tuple(grid["grid_shape"])
                    or task2d.shape != mask2d.shape
                    or len(points) != int(mask2d.sum())
                    or not mask.any()
                    or points.shape != (len(points), 6)
                    or not np.isfinite(points).all()
                    or not np.allclose(points[:, 2], grid["plane_m"] + 0.0005, atol=1e-5)
                    or not np.allclose(points[:, 3:6], [0, 0, 1])):
                shape_errors.append(f"{variant}/{room}: invalid room grid or workplane")
            grid_shapes[room] = {
                "grid_shape": grid["grid_shape"], "sampled_points": len(points),
                "task_points": int(mask.sum()), "plane_m": grid["plane_m"],
                "other_planes": {k: len(v) for k, v in enc["points"].items() if k != tag},
            }

            for fid, fixture in enc["fixtures"].items():
                if fid not in ref["fixtures"]:
                    continue
                if any(fixture[key] != ref["fixtures"][fid][key] for key in ("room", "lane", "type", "lm")):
                    fixture_errors.append(f"{variant}/{room}/{fid}: fixture metadata changed")
                if set(fixture["E"]) != set(enc["points"]):
                    shape_errors.append(f"{variant}/{room}/{fid}: result plane mismatch")
                for plane, point_set in enc["points"].items():
                    if plane not in fixture["E"]:
                        continue
                    v = np.asarray(fixture["E"][plane], dtype=float)
                    if v.shape != (len(point_set),) or not np.isfinite(v).all() or np.any(v < -1e-6):
                        shape_errors.append(f"{variant}/{room}/{fid}/{plane}: invalid lux vector")
            values[room][variant] = vectors(enc, tag, mask, scenes)
            if room == "UTL":
                values[room][variant]["utility_HIGH_TASK"] = {
                    "avg": values[room][variant]["scenes"]["Full"]["avg"],
                    "note": "All modelled utility fixtures at 100%; 0.9 m room grid, not a counter patch",
                }
            if room == "LOB":
                all_face = np.ones(len(enc["points"]["lobby_face"]), dtype=bool)
                face = vectors(enc, "lobby_face", all_face, scenes)
                values[room][variant]["lobby_face_HIGH_MIRROR"] = face["scenes"]["Work"]

    check("All nine variants, units, optical parameters and remote engine hashes", meta_errors,
          {"variants": len(runs), "enclosures": len(ROOMS) * len(runs)})
    check("All result vectors finite, non-negative and aligned with original grids and workplanes",
          shape_errors, grid_shapes)
    check("Unchanged fixture identities and plan polygons", fixture_errors)
    check("Ceiling perturbations and flat/no-tray scene construction", scene_errors)

    null_errors = []
    for room in ROOMS:
        ref_scene = PREVIOUS / "runs" / "base" / "radiance" / f"{room}.rad"
        base_scene = ROOT / "runs" / "sens512small-base" / "radiance" / f"{room}.rad"
        if digest(ref_scene) != digest(base_scene):
            null_errors.append(f"{room}: remote baseline differs from previous local scene")
        for variant in ("pocket_narrow", "pocket_wide"):
            candidate = ROOT / "runs" / f"sens512small-{variant}" / "radiance" / f"{room}.rad"
            if digest(candidate) != digest(base_scene):
                null_errors.append(f"{room}/{variant}: scene was not a no-op")
    check("Baseline scene matches previous local scene; pocket cases are identical-scene controls",
          null_errors)

    parity_errors = []
    parity = {}
    for room in ROOMS:
        baseline = runs["base"]["enclosures"][room]
        ref = old["enclosures"][room]
        tag = f"grid:{room}"
        mm = np.asarray(ref["meta"][tag]["mask"], dtype=bool)
        task = np.asarray(ref["meta"][tag]["task"], dtype=bool)[mm]
        ref_stats = vectors(ref, tag, task, scenes)
        row = {}
        for lane in ("HIGH", "LOW"):
            original = ref_stats[lane]
            candidate = values[room]["base"][lane]
            if original is None:
                continue
            ok, delta, limit = within_parity(original["avg"], candidate["avg"])
            row[lane] = {"local_avg": original["avg"], "remote_avg": candidate["avg"],
                         "difference_pct": round(100 * (candidate["avg"] / original["avg"] - 1), 3),
                         "absolute_lx": round(delta, 4), "limit_lx": round(limit, 4)}
            if not ok:
                parity_errors.append(f"{room}/{lane}: {delta:.3f} lx exceeds {limit:.3f} lx")

        worst = []
        for fid, f in ref["fixtures"].items():
            for plane, v in f["E"].items():
                a = float(np.mean(v))
                b = float(np.mean(baseline["fixtures"][fid]["E"][plane]))
                ok, delta, limit = within_parity(a, b)
                worst.append({"fixture": fid, "plane": plane, "local_avg": round(a, 4),
                              "remote_avg": round(b, 4), "difference_lx": round(delta, 4),
                              "limit_lx": round(limit, 4),
                              "difference_pct": round(100 * (b / a - 1), 3) if a > 0 else None})
                if not ok:
                    parity_errors.append(f"{room}/{fid}/{plane}: {delta:.3f} lx exceeds {limit:.3f} lx")
        row["per_fixture"] = worst
        parity[room] = row
    check("Identical-settings local/remote parity on room lanes and every fixture/plane",
          parity_errors, {"threshold": "6% of mean, with 0.30 lx absolute floor"})

    for room in ROOMS:
        base = values[room]["base"]
        for variant in VARIANTS:
            row = values[room][variant]
            row["delta_pct"] = {}
            for lane in ("HIGH", "LOW", "HIGH_LOW"):
                old_stat, new_stat = base[lane], row[lane]
                row["delta_pct"][lane] = (
                    round(100 * (new_stat["avg"] / old_stat["avg"] - 1), 3)
                    if old_stat and new_stat and old_stat["avg"] else None
                )
        for lane in ("HIGH", "LOW"):
            vals = [values[room][variant][lane] for variant in ("base", "pocket_narrow", "pocket_wide")]
            if vals[0] is not None:
                avgs = [v["avg"] for v in vals]
                values[room]["base"].setdefault("identical_scene_range_pct", {})[lane] = round(
                    100 * (max(avgs) - min(avgs)) / avgs[0], 3
                )

    result = {
        "schema": "lighting.simulation.remaining-rooms/1",
        "status": "EXPLORATORY - not measured or product-specific, not a release",
        "master_sha256": MASTER,
        "prior_receipt_sha256": RECEIPT_SHA,
        "parameters": old["params"],
        "MF": old["MF"],
        "units": old["units"],
        "scenes": {name: scenes[name] for name in SCENES},
        "rooms": values,
        "grid_shapes": grid_shapes,
        "parity": parity,
        "engines": engines,
        "checks": checks,
        "failures": failures,
    }
    output = ROOT / "analysis-remaining.json"
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"{len(checks) - len(failures)}/{len(checks)} checks passed")
    for item in checks:
        print(item["status"], item["check"], *(item["problems"][:8]))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
