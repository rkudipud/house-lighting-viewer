"""Independently verify the bound lighting review package and its offline workbench."""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pymupdf as fitz
from PIL import Image
from playwright.sync_api import sync_playwright
from validate_cct_revision import CURRENT_SHA as CCT_SHA, PRIOR_SHA, IDS, load_verified, verify
from validate_cbr_revision import CURRENT_SHA, HEATMAP_SHA, IDS as CBR_IDS, verify as verify_cbr

BASE = Path(r"not-distributed/lighting-session-inputs")
OUT = BASE / "lighting-current-review"
EVIDENCE = BASE / "lighting-integrated-current" / "verification"
MASTER = Path(r"handoff/source-basis/house-design.json")
PACK = BASE / "final-lighting-fixed-white"
EXPECTED_MASTER = CURRENT_SHA
EXPECTED_DI = "ca19a7b5cf2c0c92cf3120c95c812567fbdaa3325a7e18b3a132105e66aa604e"
EXPECTED_HEATMAP = HEATMAP_SHA
ORIGINAL_HEATMAP = "e81bf2fbe1819f481c12b45aba9ead3352893f00abeaf6bf3fc1bbf698910b4a"
checks = []


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def read(name: str):
    return json.loads((OUT / name).read_bytes())


def rows(name: str):
    with (OUT / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def check(condition, name: str):
    if not condition:
        raise AssertionError(name)
    checks.append(name)


def pdf_text(name: str, pages: int):
    doc = fitz.open(OUT / name)
    try:
        check(len(doc) == pages, f"{name}: page count {pages}")
        text = "\n".join(page.get_text() for page in doc)
        check("REVIEW" in text and "NOT FOR CONSTRUCTION" in text, f"{name}: review-only marking")
        return text
    finally:
        doc.close()


def browser_checks(calculations):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    errors, requests = [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
            page.on("request", lambda request: requests.append(request.url) if request.url.startswith(("http://", "https://")) else None)
            page.goto((OUT / "lighting-workbench.html").as_uri(), wait_until="load")
            page.wait_for_load_state("networkidle")
            check(page.title() == "Lighting workbench | House design review", "Workbench opens offline")
            check(page.locator("#fixture option").count() == 109, "Workbench exposes 104 base fittings and 4 curtain strips")
            check(page.locator("#master-hash").inner_text() == EXPECTED_MASTER, "Workbench master binding")
            check(page.locator("#photometry-hash").inner_text() == EXPECTED_DI, "Workbench photometry provenance")

            page.select_option("#room", "CBR")
            page.select_option("#scene", "HIGH_100")
            check(page.locator("#fixture option").count() == 16, "CBR shows 14 base fittings and one curtain strip")
            expected = calculations["rooms"]["CBR"]["combinations"]["HIGH_100"]
            check(page.locator("#avg").inner_text() == str(expected["avg"])
                  and page.locator("#min").inner_text() == str(expected["min"])
                  and page.locator("#u0").inner_text() == str(expected["U0"]),
                  "CBR stored HIGH statistics match the source calculation")
            for fixture in ("CBR-H1", "CBR-H6"):
                page.select_option("#fixture", fixture)
                text = page.locator("#fixture-info").inner_text()
                check(fixture in text and "Active for review" in text and "HOLD:" not in text,
                      f"{fixture} is active for review without a blanket hold")
            page.select_option("#fixture", "CURT-CBR")
            text = page.locator("#fixture-info").inner_text()
            check("H-CURTAIN-POCKET" in text and "K-CBR-LOW" in text and "P16" in text,
                  "CBR curtain shows its existing LOW group and retained pocket hold")
            page.select_option("#room", "LIV")
            page.select_option("#scene", "Mood")
            page.select_option("#fixture", "CURT-LIV")
            check("P01" in page.locator("#fixture-info").inner_text()
                  and "H-CURTAIN-POCKET" in page.locator("#fixture-info").inner_text(),
                  "Living curtain shows selected P01 and site hold")
            check("pooja" in page.locator("#calc-warning").inner_text().lower(),
                  "Living mood displays the inherited pooja caveat")
            page.screenshot(path=str(EVIDENCE / "workbench-desktop.png"), full_page=True)
            page.select_option("#room", "UTL")
            page.select_option("#scene", "LOW_100")
            check("No saved statistics" in page.locator("#calc-context").inner_text(),
                  "A grid without reported statistics is not given invented numbers")
            page.select_option("#scene", "Night")
            check("no stored night" in page.locator("#calc-context").inner_text().lower()
                  and page.locator("#avg").inner_text() == "--", "Night has no fabricated lux map")
            page.select_option("#room", "all")
            page.select_option("#layer", "main")
            check(page.locator("#fixture option").count() == 52, "Main-light filter exposes the 51 HIGH fittings")
            page.set_viewport_size({"width": 390, "height": 844})
            page.select_option("#room", "CBR")
            page.select_option("#layer", "all")
            page.select_option("#scene", "HIGH_100")
            page.select_option("#fixture", "CBR-H1")
            check(page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"),
                  "Mobile layout does not overflow horizontally")
            check(page.locator("#plan").evaluate("element => element.width > 0 && element.height > 0"),
                  "Mobile plan is rendered")
            page.screenshot(path=str(EVIDENCE / "workbench-mobile.png"), full_page=True)
            check(not errors, f"Workbench has no browser errors: {errors}")
            check(not requests, f"Workbench has no external network requests: {requests}")
        finally:
            browser.close()
    return {"desktop_screenshot": str(EVIDENCE / "workbench-desktop.png"),
            "mobile_screenshot": str(EVIDENCE / "workbench-mobile.png"),
            "browser_errors": errors, "external_requests": requests}


def main():
    global EVIDENCE, OUT, MASTER, PACK
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master", required=True, type=Path)
    parser.add_argument("--prior-master", required=True, type=Path)
    parser.add_argument("--cct-master", required=True, type=Path)
    parser.add_argument("--pack", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    args = parser.parse_args()
    MASTER, PACK, OUT = args.master.resolve(), args.pack.resolve(), args.out.resolve()
    receipt, EVIDENCE = args.receipt.resolve(), args.evidence_dir.resolve()
    cct_master = load_verified(args.cct_master, CCT_SHA)
    verify(load_verified(args.prior_master, PRIOR_SHA), cct_master)
    verify_cbr(cct_master, load_verified(MASTER, EXPECTED_MASTER))
    if (receipt.is_relative_to(OUT.resolve()) and receipt != (OUT / "verification.json").resolve()
            or EVIDENCE.is_relative_to(OUT.resolve())):
        raise ValueError("Additional verification artifacts must be outside the delivered package")
    if receipt.exists():
        raise FileExistsError(f"Verification receipt already exists; preserve it and select a new receipt path: {receipt}")
    if any((EVIDENCE / name).exists() for name in ("workbench-desktop.png", "workbench-mobile.png")):
        raise FileExistsError(f"Verification screenshots already exist; select a new evidence directory: {EVIDENCE}")
    check(digest(MASTER) == EXPECTED_MASTER, "Current master hash is guarded")
    master = json.loads(MASTER.read_bytes())
    manifest = read("manifest.json")
    check(manifest["master_sha256"] == EXPECTED_MASTER, "Package manifest is bound to the current master")
    expected_names = set(manifest["files"])
    present_names = {str(p.relative_to(OUT)).replace("\\", "/") for p in OUT.rglob("*")
                     if p.is_file() and p.name not in {"manifest.json", "verification.json"}}
    check(expected_names == present_names, "Manifest enumerates every package file")
    check(all(digest(OUT / name) == info["sha256"] and (OUT / name).stat().st_size == info["bytes"]
              for name, info in manifest["files"].items()), "All package file hashes and sizes match")
    check(manifest["original_photometry_design_inputs_canonical_sha256"] == EXPECTED_DI
          and manifest["original_heatmaps_sha256"] == ORIGINAL_HEATMAP
          and manifest["heatmaps_sha256"] == EXPECTED_HEATMAP, "Historical and CBR-reanalysed heatmap bases retained")
    check(manifest["source_comparison"]["grid_statistics_compared"] == 71
          and len(manifest["source_comparison"]["grids_without_reported_statistics"]) == 6,
          "Comparable heatmap statistics were checked; missing source statistics recorded")
    check(all(value is False for value in (manifest["retained"]["construction_release"],
              manifest["retained"]["product_approval"], manifest["retained"]["exact_chain_proven"])),
          "Construction, product and exact-chain approval remain false")

    fixture_json = read("fixture-ledger.json")
    fixture_csv, curtain_csv = rows("fixture-ledger.csv"), rows("curtain-strips.csv")
    circuit_csv, group_csv = rows("circuit-ledger.csv"), rows("switchboard-schedule.csv")
    supply_csv, vd_csv = rows("supply-ledger-selected-s1.csv"), rows("voltage-drop-selected-s1.csv")
    products = rows("generic-product-search.csv")
    cmap, curtain = read("fixed-cct-map.json"), read("curtain-pocket-s1.json")
    check(len(fixture_json) == len(fixture_csv) == len({x["id"] for x in fixture_csv}) == 104,
          "Base fixture CSV/JSON have 104 unique fittings")
    original = json.loads((PACK / "fixture-ledger.json").read_bytes())
    normalized_fixtures = copy.deepcopy(fixture_json)
    previous_fixtures = {f["id"]: f for f in cct_master["lighting"]["fixtures"]}
    for f in normalized_fixtures:
        if f["id"] in CBR_IDS:
            # R05 also sets the LINE strips to the homeowner-reported band height.
            for key in ("path_ft", "note", "mount_h_m"):
                f[key] = copy.deepcopy(previous_fixtures[f["id"]][key])
    normalized = [{k: ("3000K" if k == "cct" and f["id"] in IDS else v)
                   for k, v in f.items() if k != "tunable"} for f in normalized_fixtures]
    check(normalized == original and all(f["tunable"] is False for f in fixture_json),
          "Only the reviewed CBR LINE paths and R05 heights changed; other optical fixture values remain fixed-white")
    check(Counter(x["cct_K"] for x in fixture_csv) == {"2700": 30, "3000": 12, "4000": 62},
          "Fixed-CCT fixture distribution is 30/12/62")
    check(cmap["binding"]["master_sha256"] == EXPECTED_MASTER
          and cmap["binding"]["design_inputs_sha256"] == canonical(master["lighting"]["design_inputs"])
          and cmap["binding"]["photometry_source_design_inputs_sha256"] == EXPECTED_DI,
          "Exported CCT map distinguishes current record from original optical input")
    check(cmap["binding"]["fragment_file_sha256"] == digest(OUT / "lighting-design-inputs.json")
          and cmap["binding"]["curtain_pocket_candidate_json_sha256"] == digest(OUT / "curtain-pocket-s1.json"),
          "CCT map references the exact exported input and curtain files")
    fmap = {f["id"]: f for f in cmap["fittings"]}
    check(all(fmap[f"CBR-H{i}"]["circuit"] == "C37"
              and not fmap[f"CBR-H{i}"]["placement_hold_ids"]
              and fmap[f"CBR-H{i}"]["viewer_operability"].startswith("ACTIVE") for i in range(1, 7)),
          "CBR H1-H6 remain active on C37 without a blanket placement hold")
    active_curtains = [x for x in curtain_csv if x["selected"] == "yes"]
    check(len(active_curtains) == 4 and len(curtain_csv) == 5
          and {x["id"] for x in active_curtains} == {"CURT-LIV", "CURT-DIN", "CURT-MBR-S", "CURT-CBR"},
          "Four selected curtain strips and excluded W03 are distinct")
    check(abs(sum(float(x["indicative_length_m"]) for x in active_curtains)-8.88) < .001
          and abs(sum(float(x["generic_W"]) for x in active_curtains)-71.04) < .001
          and all(x["cct_K"] == "2700" and x["photometry_credit"] == "no" for x in active_curtains),
          "Curtain length, load, fixed CCT and no-lux-credit totals")
    check(all(s["fabrication_release"] is False and s["photometry_credit"] is False for s in curtain["strips"]),
          "Curtain strips retain fabrication and photometry holds")
    check(len(circuit_csv) == 51 and len(group_csv) == 37 and len(supply_csv) == 12,
          "Effective circuit, brightness-group and supply schedules have expected row counts")
    liv = next(x for x in group_csv if x["group"] == "K-LIV-LOW")
    check(liv["supply"] == "P01" and liv["modeled_outputs"] == "6" and liv["modeled_repeaters"] == "2"
          and float(liv["nominal_load_W"]) == 181.52, "Living LOW uses one P01, six outputs and two modeled repeaters")
    check(sum(int(x["nameplate_W"]) for x in supply_csv) == 1980 and all(x["psu"] != "P03" for x in supply_csv),
          "Selected S1 has twelve supplies totaling 1,980 W and no P03")
    p01 = next(x for x in supply_csv if x["psu"] == "P01")
    p16 = next(x for x in supply_csv if x["psu"] == "P16")
    check(p01["nameplate_W"] == "480" and p01["strip_load_W"] == "181.52"
          and p01["circuits"] == "C03; C04; C05; X-CURT-LIV" and p01["status"].startswith("HOLD"),
          "Selected P01 arrangement and open protection")
    check(p16["nameplate_W"] == "240" and float(p16["strip_load_W"]) == 121,
          "P16 selected S1 loading remains 121 W on 240 W")
    check(len(vd_csv) == 37 and Counter(x["status"] for x in vd_csv) == {"OK": 30, "MARGINAL": 2, "HOLD": 5},
          "Selected voltage-drop rows retain five holds and two marginal cases")
    check(all(x["status"] == "HOLD" and not x["dV_pct"] for x in vd_csv
              if x["circuit"] in {"C03", "C04", "C05", "X-CURT-LIV"}),
          "Old P01/P03 living voltage-drop results are not carried forward")
    check(next(x for x in vd_csv if x["circuit"] == "C39")["dV_pct"] == "3.3"
          and next(x for x in vd_csv if x["circuit"] == "C40")["dV_pct"] == "3.9",
          "C39/C40 marginal S1 voltage-drop values use the updated provisional route")
    check(sum(int(x["quantity_per_flat"]) for x in products) == 108,
          "Generic search list covers 104 base fittings and four selected strips")
    calculations = read("calc-results-current.json")
    k2 = calculations["kitchen_worktop"]["final_HIGH+TASK_100"]
    check((k2["avg"], k2["min"], k2["U0"]) == (518, 323, .623), "K-2 nominal worktop values preserved")
    check(digest(OUT / "heatmaps.json") == EXPECTED_HEATMAP, "CBR-reanalysed heatmap byte fingerprint matches")

    main_text = pdf_text("lighting-plan-main.pdf", 7)
    mood_text = pdf_text("lighting-plan-mood.pdf", 7)
    task_text = pdf_text("lighting-plan-task.pdf", 7)
    for name, text, types in (("main", main_text, ("Recessed downlight",)),
                              ("mood", mood_text, ("Cove strip", "LINE strip", "Curtain-pocket strip")),
                              ("task", task_text, ("Reading light",))):
        doc = fitz.open(OUT / f"lighting-plan-{name}.pdf")
        try:
            check(all(abs(p.rect.width - 595.4) < 2 and abs(p.rect.height - 841.7) < 2 for p in doc),
                  f"{name} plan PDF pages are A4 portrait")
            sizes = [s["size"] for p in list(doc)[1:] for b in p.get_text("dict")["blocks"]
                     for l in b.get("lines", []) for s in l["spans"] if "-" in s["text"] and "K" in s["text"]]
            check(sizes and min(sizes) >= 7, f"{name} zoom-page fitting IDs print at >= 7 pt on A4")
        finally:
            doc.close()
        check(all(t in text for t in types) and "Label suffix = fixed CCT" in text and "site hold" in text,
              f"{name} plan legend shows fitting types, fixed CCT and hold marking")
    pdf_text("heatmaps-summary.pdf", 11)
    schedule_text = pdf_text("lighting-review-schedules.pdf", 11)
    check(all(f"CBR-H{i}" in main_text for i in range(1, 7)), "Main plan labels all six CBR HIGH fittings")
    check(all(x in mood_text for x in ("CURT-LIV", "CURT-DIN", "CURT-MBR-S", "CURT-CBR", "CBR-L1", "CBR-X1")),
          "Mood plan labels all four selected curtain strips and the CBR cove/LINE")
    check("P01" in schedule_text and "CURT-CBR" in schedule_text, "Schedule PDF includes selected supply and curtain records")
    for kind in ("main", "mood", "task"):
        svg = (OUT / f"lighting-plan-{kind}.svg").read_text(encoding="utf-8")
        check("<svg" in svg and "NOT FOR CONSTRUCTION" in svg, f"{kind} SVG is present and review-marked")
        for png in [f"lighting-plan-{kind}.png"] + [f"lighting-plan-{kind}-zoom-{i}.png" for i in range(1, 7)]:
            with Image.open(OUT / png) as image:
                check(image.width >= 1000 and image.height >= 1000, f"{png} has usable resolution")
    browser = browser_checks(calculations)
    check(digest(MASTER) == EXPECTED_MASTER, "Master remained unchanged during package verification")
    result = {
        "status": "PASS", "master_sha256": EXPECTED_MASTER,
        "manifest_sha256": digest(OUT / "manifest.json"),
        "checks_passed": len(checks), "checks": checks, "browser": browser,
        "limits": [
            "CBR has a targeted analytic reanalysis; other heatmaps are inherited. All are estimates, not measurements or physically validated simulation.",
            "CBR cove (C39) and LINE (C40) are modelled ON with scheduled lumens in the provisional design/review simulation and viewer; this is not a measurement, installation, procurement or operation approval, and their physical install/site checks remain held (H-CBR-CEIL).",
            "Four selected curtain strips have no heatmap/lux credit and remain subject to site mock-up.",
            "Living feeder, branch protection and LT-4/LT-5 inrush are open; P16/C39/C40 remain marginal.",
            "All construction, product and exact-chain approvals remain false.",
        ],
        "verified_utc": datetime.now(timezone.utc).isoformat(),
    }
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks_passed": len(checks), "receipt": str(receipt),
                      "receipt_sha256": digest(receipt), "manifest_sha256": result["manifest_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
