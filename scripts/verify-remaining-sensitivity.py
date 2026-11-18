"""Verify the public six-room revision without private inputs or simulation execution."""

import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "handoff" / "electrician" / "simulation" / "revision-all-rooms"
LOW = {"COVE", "LINE", "MOOD", "PERIM"}


def load(name):
    return json.loads((PACK / name).read_bytes())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_stats(expected, values, label):
    if not values or any(not math.isfinite(value) or value < -1e-6 for value in values):
        raise ValueError("Invalid illuminance vector: " + label)
    mean = math.fsum(values) / len(values)
    actual = {"avg": mean, "min": min(values), "max": max(values),
              "U0": min(values) / mean if mean > 0 else None}
    for key, value in actual.items():
        target = expected[key]
        if value is None or target is None:
            if value != target:
                raise ValueError(label + ": null uniformity mismatch")
        elif abs(value - target) > (0.0000051 if key == "U0" else 0.000051):
            raise ValueError(label + ": rounded " + key + " mismatch")


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def main():
    receipt = load("repository-copy-receipt.json")
    analysis = load("analysis-remaining.json")
    source_receipt = load("simulation-receipt-remaining.json")
    producer_verification = load("independent-verification.json")
    if (source_receipt["approvals"] != {"construction_release": False, "product_approval": False,
                                      "exact_chain_proven": False}
            or analysis["failures"] or source_receipt["fixtures_moved"]
            or source_receipt["master_modified"] or source_receipt["pushed"]
            or source_receipt["published"] or "remote_cleanup" in source_receipt):
        raise ValueError("Unexpected release, fixture, audit or operational metadata")
    if producer_verification["receipt_sha256"] != receipt["sourceManifestSha256"]:
        raise ValueError("Independent producer receipt pin mismatch")
    for item in receipt["files"]:
        if digest(PACK / item["path"]) != item["sha256"]:
            raise ValueError("Delivered hash mismatch: " + item["path"])
        if item.get("modelPayloadSha256"):
            value = load(item["path"])
            payload = ({key: value[key] for key in
                        ("master_sha256", "variant", "V", "MF", "assumptions", "params", "units", "enclosures")}
                       if "enclosures" in value else
                       {key: data for key, data in value.items() if key != "engines"})
            if canonical(payload) != item["modelPayloadSha256"]:
                raise ValueError("Model payload changed: " + item["path"])
    with (PACK / "sensitivity-summary.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 54 or len({(row["room"], row["variant"]) for row in rows}) != 54:
        raise ValueError("CSV case coverage mismatch")
    report = (PACK / "simulation-report-remaining.md").read_text()
    computations = 0
    controls = 0
    for row in rows:
        room, variant = row["room"], row["variant"]
        raw = load(f"runs/sens512small-{variant}/sim-results.json")
        if raw["variant"] != variant or set(raw["enclosures"]) != set(analysis["rooms"]):
            raise ValueError("Raw room/variant coverage mismatch")
        enclosure = raw["enclosures"][room]
        tag = "grid:" + room
        meta = enclosure["meta"][tag]
        selection = [bool(task) for masks, tasks in zip(meta["mask"], meta["task"])
                     for inside, task in zip(masks, tasks) if inside]
        indices = [i for i, selected in enumerate(selection) if selected]
        if (len(selection) != len(enclosure["points"][tag])
                or len(indices) != analysis["grid_shapes"][room]["task_points"]):
            raise ValueError("Task mask/point mismatch")
        fixtures = list(enclosure["fixtures"].values())
        expected = analysis["rooms"][room][variant]

        def values(weights, plane=tag, selected=indices):
            return [math.fsum(float(weights.get(fixture["lane"], 0) or 0) *
                              fixture["E"][plane][i] for fixture in fixtures) for i in selected]

        groups = [(stats, values({lane: 1})) for lane, stats in expected["lanes"].items()]
        groups.append((expected["HIGH"], values({"HIGH": 1})))
        if expected["LOW"] is not None:
            groups += [(expected["LOW"], values(dict.fromkeys(LOW, 1))),
                       (expected["HIGH_LOW"], values({**dict.fromkeys(LOW, 1), "HIGH": 1}))]
        groups += [(stats, values(analysis["scenes"][scene])) for scene, stats in expected["scenes"].items()]
        if room == "LOB":
            groups.append((expected["lobby_face_HIGH_MIRROR"],
                           values(analysis["scenes"]["Work"], "lobby_face", range(3))))
        for stats, vector in groups:
            check_stats(stats, vector, room + "/" + variant)
            computations += 1
        if room == "UTL":
            vector = values({"HIGH": 1, "TASK": 1})
            if abs(math.fsum(vector) / len(vector) - expected["utility_HIGH_TASK"]["avg"]) > 0.000051:
                raise ValueError("Utility HIGH+TASK mean mismatch")
            computations += 1
        for key in ("HIGH", "LOW"):
            stats = expected[key] or {}
            for column, field in (("avg_lx", "avg"), ("min_lx", "min"), ("U0", "U0")):
                cell = row[key + "_" + column]
                if (None if cell == "" else float(cell)) != stats.get(field):
                    raise ValueError("CSV statistic mismatch")
            cell = row[key + "_change_pct"]
            delta = expected["delta_pct"][key]
            if (None if cell == "" else float(cell)) != delta:
                raise ValueError("CSV sensitivity delta mismatch")
            base = analysis["rooms"][room]["base"][key]
            if delta is not None and abs((stats["avg"] / base["avg"] - 1) * 100 - delta) > 0.0006:
                raise ValueError("Paired sensitivity calculation mismatch")
        if variant.startswith("pocket_"):
            if "not physical pocket sensitivity" not in row["interpretation"]:
                raise ValueError("Pocket control mislabelled")
            scene = f"runs/sens512small-{variant}/radiance/{room}.rad"
            baseline = f"runs/sens512small-base/radiance/{room}.rad"
            if digest(PACK / scene) != digest(PACK / baseline):
                raise ValueError("Identical-scene control changed")
            controls += 1
        if variant not in {"base", "pocket_narrow", "pocket_wide"}:
            def number(value, suffix=""):
                return "-" if value is None else f"{value:.2f}{suffix}"
            base = analysis["rooms"][room]["base"]
            hi_u = f"{number(base['HIGH']['U0'])} -> {number(expected['HIGH']['U0'])}"
            low_u = (f"{number(base['LOW']['U0'])} -> {number(expected['LOW']['U0'])}"
                     if base["LOW"] is not None and expected["LOW"] is not None else "-")
            table_row = (f"| {room} | {variant} | {number(expected['delta_pct']['HIGH'], '%')} | "
                         f"{hi_u} | {number(expected['delta_pct']['LOW'], '%')} | {low_u} |")
            if table_row not in report:
                raise ValueError("Report sensitivity table mismatch")
    if computations != 612 or controls != 12:
        raise ValueError("Incomplete statistics/control coverage")
    result = {
        "status": "PASS_public_revision_fidelity_not_a_simulation_rerun",
        "upstreamReceiptEntriesVerifiedDuringImport": 128,
        "publicCopiesHashVerified": len(receipt["files"]),
        "modelPayloadDigestsVerified": 10,
        "roomVariantCases": len(rows), "rawStatisticSetsRecomputed": computations,
        "identicalSceneControlComparisons": controls,
        "pairedPhysicalSensitivityReportRowsChecked": 36,
        "csvRowsChecked": len(rows), "editableScenesIncluded": 54,
        "sourcePublicReceiptSha256": digest(PACK / "repository-copy-receipt.json"),
        "publicReportSha256": digest(PACK / "simulation-report-remaining.md"),
        "publicSourceReceiptSha256": digest(PACK / "simulation-receipt-remaining.json"),
        "analysisSha256": digest(PACK / "analysis-remaining.json"),
        "csvSha256": digest(PACK / "sensitivity-summary.csv"),
        "radianceExecuted": False, "masterApprovalChainVerifiedInPublicMode": False,
        "constructionRelease": False, "publicationAuthorized": False,
    }
    (PACK / "local-revision-verification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: {computations} raw statistic sets, 54 CSV cases, 36 physical-sensitivity table rows, {controls} identical-scene controls")


if __name__ == "__main__":
    main()
