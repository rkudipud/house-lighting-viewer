"""Public-safe wardrobe reproduction check: snapshot-only, no master snapshots or canonical receipts.

It verifies that the published review package is reproducible from the redistributable snapshot and
immutable interior source. It does NOT re-verify master/receipt provenance; that requires verify_rollup.py
with the private pinned master chain.
"""
import argparse
import copy
import csv
import hashlib
import json
import re
import struct
from pathlib import Path
from xml.etree import ElementTree

import pymupdf

from cost_model import verify as verify_costs
from interiors_model import interiors

HERE = Path(__file__).resolve().parent
OUT = HERE / "final"
EXPECTED = HERE / "public-reproduction-expected.json"
PRIVATE = re.compile(r"(?i)\b[a-z]:[\\/]+users[\\/]|file:///|session-state|appdata[\\/]|/home/[a-z]")
INPUTS = ("signoff_pack.py", "interiors_model.py", "cost_model.py", "verify_public.py", "requirements-wardrobe.txt",
          "storage-current.json", "cost-evidence.json", "cost-evidence.md", "final/CLEANUP-MANIFEST.md",
          "reproduction-inputs/wardrobe-interiors-original.json")
NOT_REPRODUCED = ("rollup-receipt.json", "file-hashes.json", "wardrobe-signoff-pack.pdf")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pdf_signature(path):
    with pymupdf.open(path) as document:
        return {"pages": len(document),
                "text_sha256": [hashlib.sha256(p.get_text().encode()).hexdigest() for p in document],
                "render_72dpi_sha256": [hashlib.sha256(p.get_pixmap(dpi=72).samples).hexdigest() for p in document]}


def record_expected():
    """Pin the published outputs as the public reference (run once on the verified package)."""
    outputs = {p.name: sha(p) for p in sorted(OUT.iterdir()) if p.is_file() and p.name not in NOT_REPRODUCED}
    expected = {"schema": "wardrobe-public-reproduction-expected/1",
                "published_file_hashes_sha256": sha(OUT / "file-hashes.json"),
                "published_pdf_sha256": sha(OUT / "wardrobe-signoff-pack.pdf"),
                "pdf": pdf_signature(OUT / "wardrobe-signoff-pack.pdf"),
                "byte_identical_outputs_sha256": outputs}
    EXPECTED.write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"expected": str(EXPECTED.name), "sha256": sha(EXPECTED), "outputs": len(outputs)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shared-md", type=Path)
    parser.add_argument("--receipt-out", type=Path, default=HERE / "public-reproduction-receipt.json")
    parser.add_argument("--record-expected", action="store_true")
    args = parser.parse_args()
    if args.record_expected:
        return record_expected()
    expected = json.loads(EXPECTED.read_bytes())
    data = json.loads((OUT / "storage-current.json").read_bytes())
    assert (HERE / "storage-current.json").read_bytes() == (OUT / "storage-current.json").read_bytes()
    master_sha = data["source_master_sha256"]
    generation_sha = data.get("interior_generation_basis_sha256", master_sha)

    # Recorded decisions and holds (as stated in the snapshot; provenance not re-proven here).
    assert data["construction_release"] is False
    assert data["confirmed_brief"]["materials_selected"] == "OPT-E"
    assert set(data["confirmed_brief"]["selected_cabinets"]) == {"ST-R04a-WR01", "ST-R08-UC01"}
    assert data["cost_comparison"]["selection"]["option"] == "OPT-E"
    assert data["R04"]["status"] == "homeowner_approved_in_principle_relationship_placeholders_not_fabrication_design"
    assert data["R05"]["route_gap_m"] == 0.3876

    cost = data["cost_comparison"]
    assert cost == json.loads((OUT / "cost_model.json").read_bytes())
    for option in cost["options"].values():
        assert option["four_flats_incl_required_common_inr"] == [4 * x for x in option["per_flat_incl_required_common_inr"]]
        assert option["per_flat_incl_provisional_pullouts_inr"] == [
            option["per_flat_incl_required_common_inr"][0] + 3000, option["per_flat_incl_required_common_inr"][1] + 7500]
    assert cost["options"]["OPT-E"]["per_flat_incl_required_common_inr"] == [263020, 463190]
    assert cost["options"]["OPT-E"]["four_flats_incl_required_common_inr"] == [1052080, 1852760]
    assert cost["common_totals_per_flat"]["required_inr"] == [
        sum(row["inr"][n] for row in cost["common_per_flat"]) for n in (0, 1)]
    assert verify_costs() == 21
    for name in ("cost-units.csv", "cost-flats.csv", "cost-common.csv"):
        with (OUT / name).open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            rows = list(reader)
            assert rows and len(reader.fieldnames) == len(set(reader.fieldnames))
            assert all(row["source_master_sha256"] == master_sha for row in rows)

    model = json.loads((OUT / "wardrobe-interiors.json").read_bytes())
    assert model == data["provisional_interiors"] == interiors(data)
    assert model["source_master_sha256"] == generation_sha
    assert model["status"] == "provisional_design_not_homeowner_approved_or_fabrication_released"
    reference = data.get("integration_receipt", {}).get("interior_reference_receipt")
    if reference:
        assert sha(OUT / "wardrobe-interiors.json") == reference["original_interior_source_sha256"]
    p = model["parameter_basis"]
    assert (p["long_rail_to_base_mm"], p["double_rail_ffl_mm"]) == (1650, [1800, 950])
    assert p["top_shelf_ffl_mm"] - p["panel_mm"] - p["double_rail_ffl_mm"][0] >= 70
    assert model["hardware_delta"]["per_flat_inr"] == [3000, 7500]
    changed = copy.deepcopy(data)
    changed["R04"]["south_wardrobe_zones_m"][0][2] += 0.150
    changed["R04"]["window_bay_m"][0] += 0.150
    assert round(interiors(changed)["rooms"]["R04"]["sections"][0]["bays"][0]["clear_width_mm"]
                 - model["rooms"]["R04"]["sections"][0]["bays"][0]["clear_width_mm"], 1) == 50
    for mutate in ("width", "height"):
        bad = copy.deepcopy(data)
        if mutate == "width":
            z = bad["R04"]["south_wardrobe_zones_m"][0]
            z[2] = z[0] + 0.05
        else:
            next(i for i in bad["items"] if i["id"] == "ST-R05-WR01")["height_range_m"][1] = 1.8
        try:
            interiors(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Impossible {mutate} accepted")

    md = (OUT / "wardrobe-signoff-pack.md").read_text(encoding="utf-8")
    html = (OUT / "wardrobe-signoff-pack.html").read_text(encoding="utf-8")
    shared = args.shared_md.read_text(encoding="utf-8") if args.shared_md else None
    for text in (md, html) + ((shared,) if shared is not None else ()):
        assert master_sha in text and generation_sha in text
        assert all(t in text for t in ("HS-WARDROBE-OPT-E", "HS-MBR-SPLIT-WARDROBE", "HS-R04A-CABINET", "HS-R08-UNDERCOUNTER"))
    assert "Contractor hold" in md and "INR 263,020-463,190" in md
    refs = re.findall(r"!\[[^]]*\]\(([^)]+)\)", md)
    assert len(refs) == 10 and all("/" not in r and "\\" not in r and (OUT / r).is_file() for r in refs)
    if shared is not None:
        assert re.findall(r"!\[[^]]*\]\(([^)]+)\)", shared) == ["../../storage-design/final/" + r for r in refs]
    for png in OUT.glob("*.png"):
        b = png.read_bytes()
        assert b[:8] == b"\x89PNG\r\n\x1a\n" and min(struct.unpack(">II", b[16:24])) > 500
    for svg in OUT.glob("*.svg"):
        ElementTree.parse(svg)

    # Reproduction against the pinned public reference.
    actual = {p.name: sha(p) for p in sorted(OUT.iterdir()) if p.is_file() and p.name not in NOT_REPRODUCED}
    assert actual == expected["byte_identical_outputs_sha256"], sorted(
        k for k in set(actual) | set(expected["byte_identical_outputs_sha256"])
        if actual.get(k) != expected["byte_identical_outputs_sha256"].get(k))
    pdf = pdf_signature(OUT / "wardrobe-signoff-pack.pdf")
    assert pdf == expected["pdf"], "PDF text/render differs from published package"
    with pymupdf.open(OUT / "wardrobe-signoff-pack.pdf") as document:
        text = " ".join(page.get_text() for page in document)
        assert "NOT FOR FABRICATION" in text and master_sha in text

    # Privacy scan of every public input and every regenerated text output.
    scanned = [HERE / n for n in INPUTS] + [p for p in OUT.iterdir() if p.suffix in (".md", ".html", ".json", ".csv", ".svg")]
    if args.shared_md:
        scanned.append(args.shared_md)
    scanned += [p for p in HERE.parent.glob("wardrobe-*.*") if p.suffix in (".md", ".json")]
    leaks = [p.name for p in scanned
             if p.name != "verify_public.py" and PRIVATE.search(p.read_text(encoding="utf-8", errors="ignore"))]
    assert not leaks, leaks
    absent = [n for n in ("current-review-master.json", "interior-generation-master.json", "original-signoff-master.json",
                          "pre-cabinets-master.json", "interior-reference-receipt.json", "original-signoff-receipt.json",
                          "cabinet-selection-receipt.json") if not (HERE / "reproduction-inputs" / n).exists()]

    receipt = {
        "schema": "wardrobe-public-reproduction-receipt/1",
        "status": "PASS_public_snapshot_reproduction_not_provenance_or_fabrication_approval",
        "recorded_current_review_master_sha256": master_sha,
        "recorded_interior_generation_basis_sha256": generation_sha,
        "inputs_sha256": {n: sha(HERE / n) for n in INPUTS},
        "expected_reference_sha256": sha(EXPECTED),
        "byte_identical_outputs": len(actual),
        "pdf_pages_text_and_render_identical": pdf["pages"],
        "not_reproduced": {"wardrobe-signoff-pack.pdf": "trailer ID regenerates; text and 72-dpi render compared",
                           "rollup-receipt.json": "written only by verify_rollup.py with private master chain",
                           "file-hashes.json": "contains the regenerated PDF hash"},
        "verified": ["snapshot-internal cost arithmetic and 21 option/unit calculations",
                     "interiors model rebuild equals immutable interior source; parametric failure guards",
                     "31 published outputs byte-identical; PDF text/render identical",
                     "relative image links; PNG/SVG validity; recorded decisions/holds present",
                     "no local absolute paths (drive-user, file URI, session/AppData, /home) in public inputs or outputs"],
        "not_verified": ["that the snapshot matches any canonical master (master hashes are recorded strings only)",
                         "homeowner sign-off and cabinet/interior receipt chains",
                         "unchanged geometry versus earlier masters",
                         "byte-exact historical 2ce3fcb4 delivery"],
        "private_inputs_absent": absent,
        "construction_release": False,
        "holds": "all measurement, fit, support/load and fabrication holds retained; review-only",
    }
    args.receipt_out.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "receipt_sha256": sha(args.receipt_out),
                      "byte_identical_outputs": len(actual), "private_inputs_absent": len(absent)}, indent=2))


if __name__ == "__main__":
    main()
