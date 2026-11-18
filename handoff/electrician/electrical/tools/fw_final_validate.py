"""Independently verify the review pack's source linkage and internal consistency."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

import pymupdf
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
HOUSE = Path(r"handoff/source-basis")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master", type=Path, default=HOUSE / "house-design.json")
    parser.add_argument("--out", type=Path, default=ROOT / "final-handoff")
    args = parser.parse_args()
    out, master_path = args.out.resolve(), args.master.resolve()
    ledger = load(out / "schedules" / "electrical-ledger.json")
    master_sha = ledger["master_sha256"]
    checks = []

    def check(name: str, condition: bool, detail: object) -> None:
        if not condition:
            raise ValueError(f"{name}: {detail}")
        checks.append({"check": name, "status": "PASS", "detail": detail})

    check("master hash", sha(master_path) == master_sha, master_sha)
    m = load(master_path)
    decision = load(out / "source-evidence" / "living-supply-and-cabinet-selections-receipt.json")
    wardrobe = load(out / "source-evidence" / "wardrobe-interiors-reference-receipt.json")
    previous = load(out / "source-evidence" / "homeowner-coordination-receipt.json")
    pooja = load(out / "source-evidence" / "pooja-display-receipt.json")
    option = out / "source-evidence" / "living-low-one-supply-option.json"
    check("receipt chain", wardrobe["after_master_sha256"] == master_sha
          and wardrobe["before_master_sha256"] == decision["after_master_sha256"]
          and decision["before_master_sha256"] == pooja["after_master_sha256"]
          and pooja["before_master_sha256"] == previous["after_master_sha256"], "all ancestor links")
    check("wardrobe reference linkage", wardrobe["reference"] == m["storage"]["wardrobe_interiors_review"]
          and sha(out / "source-evidence" / "wardrobe-interiors-reference-receipt.json")
          == ledger["latest_master_receipt_sha256"], "reference only; no new wardrobe lighting")
    check("one-supply decision hash", decision["source_option_sha256"] == sha(option) == ledger["one_supply_option_sha256"],
          sha(option))
    check("all release flags false",
          all(ledger["release_flags"].get(k) is False and decision["holds"].get(k) is False
              and wardrobe["retained"].get(k) is False
              and m["lighting"]["curtain_pocket_s1"][k] is False
              for k in ("construction_release", "product_approval", "exact_chain_proven")),
          ledger["release_flags"])

    master_fixtures = {f["id"]: f for f in m["lighting"]["fixtures"]}
    packed_fixtures = {f["id"]: f for f in ledger["fixtures"]}
    check("104 base fixtures", len(master_fixtures) == 104 and set(master_fixtures).issubset(packed_fixtures),
          len(master_fixtures))
    for ident, f in master_fixtures.items():
        p = packed_fixtures[ident]
        check(f"fixture {ident}",
              p["room"] == f["room"] and p["circuit"] == f["circuit"]
              and p["fixture_class"] == f["type"] and p["CCT"] == f["cct"]
              and p["model_W"] == f["W_envelope"] and p["x_ft"] == f["x_ft"]
              and p["z_ft"] == f["z_ft"] and p["path_ft"] == f["path_ft"], "matches master")
    check("108 total unique fixtures", len(packed_fixtures) == 108 == len(ledger["fixtures"]), len(packed_fixtures))
    master_circuits = {c["circuit"]: c for c in m["lighting"]["controls"]["circuits"]}
    packed_circuits = {c["circuit"]: c for c in ledger["circuits"]}
    check("51 unique circuits", len(master_circuits) == 47 and len(packed_circuits) == 51,
          {"base": len(master_circuits), "total": len(packed_circuits)})
    for ident, c in master_circuits.items():
        p = packed_circuits[ident]
        check(f"circuit {ident}",
              p["fixture_ids"] == c["fixtures"] and p["model_W"] == c["W_envelope"]
              and p["supply_id"] == c["psu"], "fixture, power and supply match master")
    curtains = m["lighting"]["curtain_pocket_s1"]["strips"]
    check("four warm curtain strips", len(curtains) == 4 and all(
        p["cct_k"] == 2700 and packed_fixtures[p["id"]]["CCT"] == "2700K"
        and not packed_fixtures[p["id"]]["photometry_credit"]
        and packed_circuits[f"X-{p['id']}"]["model_W"] == round(p["indicative_strip_length_m"] * 8, 2)
        for p in curtains), "2700 K; exact derived W; no lux credit")
    check("curtain length and load", round(sum(p["indicative_strip_length_m"] for p in curtains), 2) == 8.88
          and round(sum(packed_circuits[f"X-{p['id']}"]["model_W"] for p in curtains), 2) == 71.04,
          "8.88 m / 71.04 W, unmeasured")
    for p in curtains:
        photo = p.get("site_photo")
        if photo:
            saved = out / "figures" / "photos" / Path(photo["file"]).name
            check(f"site photo {p['id']}", saved.is_file() and sha(saved) == photo["sha256"], sha(saved))
    check("MBR photo association is not fabricated",
          next(p for p in curtains if p["id"] == "CURT-MBR-S")["site_photo"] is None,
          "not linked in canonical master; on-site check remains open")

    covered = []
    for w in ledger["wall_controls"]:
        covered.extend(w["circuits"])
    covered.extend(f["circuit"] for f in read_csv(out / "schedules" / "fitting-controls.csv"))
    check("all circuit controls exactly once", Counter(covered) == Counter(packed_circuits.keys()),
          {"covered": len(covered), "unique": len(set(covered))})
    knobs, supplies = ledger["knob_groups"], ledger["supplies"]
    check("knob and repeater totals", len(knobs) == 21
          and sum(k["modeled_outputs"] for k in knobs) == 38
          and sum(k["modeled_repeaters"] for k in knobs) == 3, "21 / 38 / 3")
    check("12 supplies at 1980 W", len(supplies) == 12 and sum(p["planning_nameplate_W"] for p in supplies) == 1980,
          "12 / 1980 W")
    p01 = next(p for p in supplies if p["supply_id"] == "P01")
    check("living one-supply load", p01["planning_nameplate_W"] == 480
          and set(p01["circuits"]) == {"C03", "C04", "C05", "X-CURT-LIV"}
          and p01["modeled_load_W"] == 181.52 and not any(p["supply_id"] == "P03" for p in supplies),
          "P01 / 480 W / 181.52 W; no P03")
    check("living sizing arithmetic", round(181.52 / .6, 2) == 302.53
          and 480 * .6 == 288 and round(181.52 / 24, 2) == 7.56, "0.60 is a planning assumption")
    assigned = [c for supply in supplies for c in supply["circuits"]]
    required = [c["circuit"] for c in ledger["circuits"] if c["control_class"] == "KNOB1"]
    check("24 V supply coverage", Counter(assigned) == Counter(required), "each modeled 24 V group exactly once")
    drops = ledger["voltage_drop"]
    check("voltage-drop hold counts", Counter(x["status"] for x in drops) == Counter({"OK": 30, "MARGINAL": 2, "HOLD": 5}),
          dict(Counter(x["status"] for x in drops)))
    check("changed living drops held", all(x["modeled_dV_pct"] is None and x["status"] == "HOLD"
          for x in drops if x["circuit"] in ("C03", "C04", "C05", "X-CURT-LIV")), "not a PASS")
    check("C39/C40 marginal", next(x for x in drops if x["circuit"] == "C39")["modeled_dV_pct"] == 3.3
          and next(x for x in drops if x["circuit"] == "C40")["modeled_dV_pct"] == 3.6, "3.3% / 3.6%")
    check("LT4/LT5 held", all("invalid" in x["inrush_status"].lower()
          for x in ledger["distribution"] if x["group"] in ("LT-4", "LT-5")), "old inrush screens invalid")

    locations = read_csv(out / "schedules" / "location-linked-bom.csv")
    kinds = Counter()
    for row in locations:
        kinds[row["item_kind"]] += float(row["quantity_per_flat"])
    check("location BOM quantities", kinds["modeled luminaire or strip fixture"] == 108
          and kinds["24 V constant-voltage supply"] == 12 and kinds["local wall dimmer/knob"] == 31
          and kinds["modeled PWM repeater"] == 3 and kinds["conceptual on/off switch module"] == 8
          and kinds["48 V track system driver"] == 1, dict(kinds))
    check("location BOM covers every fixture",
          {x["item_id"] for x in locations if x["item_kind"] == "modeled luminaire or strip fixture"} == set(packed_fixtures),
          "all 108 IDs")
    classes = read_csv(out / "schedules" / "fixture-class-specifications.csv")
    fixture_classes = Counter(f["fixture_class"] for f in ledger["fixtures"])
    check("fixture class quantities include curtains",
          {x["fixture_class"]: int(x["modeled_count_per_flat"]) for x in classes} == fixture_classes
          and sum(int(x["additional_curtain_count"]) for x in classes) == 4,
          {"classes": len(classes), "total": sum(fixture_classes.values()), "additional_curtains": 4})
    switchboards = read_csv(out / "schedules" / "switchboard-schedule.csv")
    check("switchboard quantities", sum(int(x["wall_PWM_knobs"]) for x in switchboards) == 21
          and sum(int(x["mains_dimmer_groups"]) for x in switchboards) == 10
          and sum(int(x["supplementary_switch_modules"]) for x in switchboards) == 8,
          {"boards": len(switchboards), "knobs": 21, "mains": 10, "switches": 8})
    check("historic verification not represented as a rerun",
          ledger["historical_photometry"]["historical_passes"] == 82
          and ledger["historical_photometry"]["rerun_on_current_master"] is False,
          "historical 82/82; no current-master rerun")

    for s in ledger["sources"]:
        path = out / s["path"]
        check(f"source {path.name}", path.is_file() and sha(path) == s["sha256"], s["sha256"])
        if path.suffix.lower() == ".pdf":
            with pymupdf.open(path) as doc:
                check(f"source PDF {path.name}", len(doc) > 0, f"{len(doc)} pages")
    for image_path in sorted((out / "figures").glob("*.svg")):
        tree = ElementTree.parse(image_path)
        width, height = (int(tree.getroot().attrib[k]) for k in ("width", "height"))
        image = out / "figures" / f"{image_path.stem}.png"
        with Image.open(image) as rendered:
            check(f"figure pair {image_path.stem}", rendered.size == (2 * width, 2 * height),
                  {"svg": [width, height], "png": list(rendered.size)})
    floor_text = (out / "figures" / "controls-plan.svg").read_text(encoding="utf-8")
    check("superseded living supply markers absent",
          "P01 240W" not in floor_text and "P03 150W" not in floor_text
          and "P01 480 W class: hatch" in floor_text, "P01 location intentionally unplotted")
    index = (out / "source-index.md").read_text(encoding="utf-8")
    for href in re.findall(r"\]\((sources/[^)]+)\)", index):
        check(f"source index link {href}", (out / href).is_file(), href)

    for name in ("electrical-review", "source-index", "wholesale-rfq", "control-options", "bill-of-materials"):
        md, html, pdf = (out / f"{name}.{suffix}" for suffix in ("md", "html", "pdf"))
        render = load(out / f"{name}-render.json")
        check(f"{name} render hashes", sha(md) == render["md_sha256"] and sha(html) == render["html_sha256"]
              and sha(pdf) == render["pdf_sha256"], "source, HTML and PDF")
        check(f"{name} layout", all(not render[k] for k in
              ("page_errors", "external_requests", "overflow", "out_of_bounds_text", "near_empty_pages")),
              "no browser, image, overflow or text-boundary errors")
        text = md.read_text(encoding="utf-8")
        check(f"{name} bound to master", master_sha in text, master_sha)
        with pymupdf.open(pdf) as doc:
            text = "".join(page.get_text() for page in doc)
            compact = re.sub(r"\s+", "", text)
            check(f"{name} PDF content", len(doc) == render["pages"] and master_sha in compact,
                  f"{len(doc)} pages; current master hash present")
    main_text = (out / "electrical-review.md").read_text(encoding="utf-8").lower()
    check("review and holds explicit", "not for ordering, wiring or construction" in main_text
          and "old p01/p03 living voltage-drop results are **invalid" in main_text
          and "no site photo is individually linked to `curt-mbr-s`" in main_text,
          "no construction release; living drop and MBR photo holds visible")
    check("live master still unchanged", sha(master_path) == master_sha, master_sha)
    result = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "master_sha256": master_sha,
        "status": "PASS",
        "scope": "Artifact/source linkage and arithmetic only; not a new photometric, electrical-safety or manufacturer compatibility approval.",
        "checks_passed": len(checks),
        "checks": checks,
    }
    (out / "validation.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    target_script = out / "tools" / Path(__file__).name
    if Path(__file__).resolve() != target_script.resolve():
        shutil.copy2(Path(__file__), target_script)
    print(json.dumps({k: v for k, v in result.items() if k != "checks"}, indent=2))


if __name__ == "__main__":
    main()
