"""Portable wardrobe review pack. Import from master once, then rebuild from storage-current.json.

python signoff_pack.py --master <house-design.json> --receipt <original-integration.json>
    --basis-master <original-integrated-master.json> --cabinet-receipt <selection-receipt.json>
    --pre-cabinets-master <selection-previous-master.json> --shared-md <wardrobe-signoff-pack.md>
python signoff_pack.py

For a reference-only later master, also supply --interior-reference-receipt,
--interior-basis-master and --interior-source. The original model remains byte-equal.

No master writes, layout selection, price research or construction release.
"""
import argparse
import copy
import csv
import hashlib
import html
import json
import re
from pathlib import Path

import markdown
import pymupdf

from interiors_model import dimension, draw_interior_sheets, interiors

HERE = Path(__file__).resolve().parent
OUT = HERE / "final"
SOURCE = HERE / "storage-current.json"
ROOMS = ("R04", "R05", "R04a", "R08", "R09")
EXCLUDED = ("ST-R04-WR01", "ST-R04-LF01", "ST-R04-BED01",
            "ST-R04-NS01", "ST-R04-NS02", "ST-R05-NS01")
ORDER = ("OPT-E", "OPT-E-H", "OPT-F", "OPT-A", "OPT-B1", "OPT-C", "OPT-D")
TAX = "Tax-unnormalised allowances; not verified pre-GST totals or supplier quotes."
QUANTITY_HOLD = ("R04 quantities use a single 2.75 m reference run (2.70 m of wardrobe leaves), "
                 "not the split south-wall zones. Re-quantify after W03, curtain pockets, lofts "
                 "and shutters are measured/designed. R05 loft drawing has six proposed leaves "
                 "but the equal-scope cost model allows eight; reconcile before ordering.")


def read(path):
    return json.loads(Path(path).read_bytes())


def save_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def money(values):
    return "INR " + " - ".join(f"{v:,}" for v in values)


def clean_provenance(value):
    """Keep facts, not revision receipts or discarded source-path dependencies."""
    if isinstance(value, dict):
        return {k: clean_provenance(v) for k, v in value.items()
                if not any(t in k.lower() for t in ("sha256", "archive", "previous_", "superseded_assumptions"))
                and k not in ("generated_utc", "generator", "supersedes", "confirmation_request",
                              "source_request", "recorded_utc", "warning_review_request")}
    if isinstance(value, list):
        return [clean_provenance(v) for v in value]
    return value


def current_cost(original, master_sha):
    c = clean_provenance(copy.deepcopy(original))
    c["source_master_sha256"] = master_sha
    c["basis"]["R04_quantity_hold"] = QUANTITY_HOLD
    c["basis"]["common_fit_hold"] = "Tenant beds excluded (HD-05); fixed bedside joinery omitted (HD-14)."
    c["basis"]["scope"] = "Equal reference quantities across materials; R04 and R05 loft quantities require reconciliation."
    c["basis"]["allowance_tax_basis"] = TAX
    c["basis"]["common_scope"] = ("Ancillary items repeated in each flat, not building common areas; "
                                  "selected UC01 is included subject to site fit.")
    c["selection_cost_status"] = ("Both selected cabinets are included using previous allowances; "
                                  "these are not measured quantities or current installed quotes.")
    c["selection"] = {"option": "OPT-E", "decision_ref": "HS-WARDROBE-OPT-E",
                      "scope": "BWP plywood carcass and laminate shutters selected; detail and construction release pending."}
    c["options"]["OPT-E"]["name"] = ("HOMEOWNER-SELECTED: BWP plywood carcass and laminate shutters; "
                                      "stone base and vent gap remain proposed details")
    c["options"]["OPT-E-H"]["name"] = "Unselected variant: OPT-E with HDHMR 18 mm laminate shutters"
    for qualitative in (c["qualitative"]["OPT-E-H"], c["options"]["OPT-E-H"]["qualitative"]):
        qualitative["termite"] = "As OPT-E; HDHMR resistance is a product-specific claim (F9); verify certification."
    rows = [r for r in c["common_per_flat"] if r.get("category") in ("required", "optional_UC01")]
    uc_rows = [r for r in rows if r["category"] == "optional_UC01"]
    if len(uc_rows) != 1:
        raise ValueError("Expected exactly one utility under-counter allowance")
    uc = uc_rows[0]
    opt = uc["inr"]
    uc.update(item="ST-R08-UC01 selected under-counter shutters (carcass and shelves unpriced)",
              category="required", optional=False, fit_status="homeowner_selected_site_fit_unverified")
    for row in rows:
        if row["item"].startswith("ST-R09-SH01"):
            row["item"] = "ST-R09-SH01 aluminium shoe fronts + stone top (carcass and shelves unpriced)"
    c["common_per_flat"] = rows
    req = [sum(r["inr"][n] for r in rows) for n in (0, 1)]
    c["common_totals_per_flat"] = {"required_inr": req, "selected_UC01_component_inr": opt}
    for unit in c["units"]:
        if unit["room_id"] == "R04a":
            unit["conditional"] = False
            unit["scope_status"] = "homeowner_selected_site_fit_unverified"
    c["excluded_scope"] = {"beds": "Tenant-supplied, HD-05", "fixed_bedsides": "Omitted, HD-14"}
    c.pop("removed_scope", None)
    for oid, o in c["options"].items():
        o["per_unit"]["ST-R04a-WR01+LF01"]["conditional"] = False
        o["per_unit"]["ST-R04a-WR01+LF01"]["scope_status"] = "homeowner_selected_site_fit_unverified"
        old_base = o["base_wardrobes_lofts_per_flat_inr"]
        old_total = o["per_flat_incl_required_common_inr"]
        dressing = o["conditional_R04a_add_per_flat_inr"]
        o["reference_R04_R05_wardrobes_lofts_per_flat_inr"] = old_base
        o["reference_before_selected_cabinets_per_flat_inr"] = old_total
        o["selected_R04a_component_per_flat_inr"] = dressing
        o["selected_UC01_component_per_flat_inr"] = opt
        o["base_wardrobes_lofts_per_flat_inr"] = [old_base[n] + dressing[n] for n in (0, 1)]
        selected = [old_total[n] + dressing[n] + opt[n] for n in (0, 1)]
        o["per_flat_incl_required_common_inr"] = selected
        o["four_flats_incl_required_common_inr"] = [4 * n for n in selected]
        o["provisional_pullout_delta_per_flat_inr"] = [3000, 7500]
        o["per_flat_incl_provisional_pullouts_inr"] = [selected[n] + [3000, 7500][n] for n in (0, 1)]
        o["four_flats_incl_provisional_pullouts_inr"] = [4 * n for n in o["per_flat_incl_provisional_pullouts_inr"]]
        for k in ("per_flat_incl_common_inr", "four_flats_incl_common_inr", "optional_bedside_delta_per_flat_inr",
                  "conditional_R04a_add_per_flat_inr", "conditional_R04a_add_four_flats_inr",
                  "optional_UC01_delta_per_flat_inr", "per_flat_with_optional_UC01_inr"):
            o.pop(k, None)
        o["totals_note"] = ("Both selections are included using the R04a cabinet and R08 shutter allowances; "
                            "R08 carcass/partition/shelf and shoe carcass/shelf supports are unpriced. "
                            "Site fit remains unverified, pull-outs are separate and beds/bedsides excluded.")
        if oid in c["budget_comparison"]["options"]:
            comparison = c["budget_comparison"]["options"][oid]
            comparison["per_flat_inr"] = selected
            comparison["midpoint_inr"] = sum(selected) / 2
            comparison["low_vs_floor_inr"] = selected[0] - 250000
            comparison["high_vs_ceiling_inr"] = selected[1] - 350000
            comparison["verdict"] = ("Numeric screen only; source taxes are not normalised and the R04 split is not re-quantified.")
            for k in ("with_optional_bedside_inr", "with_conditional_R04a_inr"):
                comparison.pop(k, None)
            comparison["with_provisional_pullouts_inr"] = o["per_flat_incl_provisional_pullouts_inr"]
    c["budget_comparison"]["compared_figure"] = ("R04, R05 and selected R04a wardrobes/lofts + required ancillary items, "
                                                "including selected R08 UC01, repeated in each flat.")
    c["budget_comparison"]["caveat"] = QUANTITY_HOLD
    c["rounding_rule"] = ("Round each cost line to INR 10, sum displayed lines into units and required per-flat totals. "
                          "Four flats = exactly 4 x the per-flat endpoint. The unverified pull-out delta is separate.")
    return c


def reference_binding(current, current_sha, receipt_path, basis_path, source_path):
    """Prove a reference-only integration without changing its original design basis."""
    receipt, basis, source = read(receipt_path), read(basis_path), read(source_path)
    basis_sha, source_sha = digest(basis_path), digest(source_path)
    if (receipt["before_master_sha256"] != basis_sha or receipt["after_master_sha256"] != current_sha
            or receipt["source_master_sha256"] != basis_sha
            or receipt["source_file_sha256"] != source_sha or receipt["copied_fragment_sha256"] != source_sha
            or source["source_master_sha256"] != basis_sha):
        raise ValueError("Interior reference receipt, master basis or immutable source hash does not match")
    reference = current["storage"]["wardrobe_interiors_review"]
    if (reference != receipt["reference"] or reference["sha256"] != source_sha
            or reference["source_master_sha256"] != basis_sha
            or any(reference[key] is not False for key in
                   ("homeowner_interior_approval", "construction_release", "product_approval", "exact_chain_proven"))):
        raise ValueError("Interior reference changed its source or released an approval hold")
    for key in ("architecture", "decisions", "bathrooms", "lighting", "visualization_geometry", "open_items"):
        if current[key] != basis[key]:
            raise ValueError("Reference integration changed a protected dependency: " + key)
    storage = copy.deepcopy(current["storage"])
    storage.pop("wardrobe_interiors_review")
    if storage != basis["storage"]:
        raise ValueError("Reference integration changed existing storage data")
    return basis, basis_sha, {
        "filename": Path(receipt_path).name, "sha256": digest(receipt_path),
        "before_master_sha256": basis_sha, "after_master_sha256": current_sha,
        "original_interior_source_sha256": source_sha,
        "original_interior_source_filename": Path(source_path).name,
        "compatibility": "reference_only_all_existing_storage_geometry_decisions_and_holds_unchanged",
    }


def import_master(path, receipt_path, basis_path, cabinet_receipt_path, pre_cabinets_path,
                  interior_receipt_path=None, interior_basis_path=None, interior_source_path=None):
    raw = Path(path).read_bytes()
    master = json.loads(raw)
    current_sha = hashlib.sha256(raw).hexdigest()
    interior_reference = None
    if any((interior_receipt_path, interior_basis_path, interior_source_path)):
        if not all((interior_receipt_path, interior_basis_path, interior_source_path)):
            raise ValueError("Interior rebind requires its receipt, exact previous master and immutable source")
        master, master_sha, interior_reference = reference_binding(
            master, current_sha, interior_receipt_path, interior_basis_path, interior_source_path)
    else:
        master_sha = current_sha
    generation_sha = master_sha
    s, d, v = master["storage"], master["decisions"], master["visualization_geometry"]
    assert d["bedrooms"]["fixed_bedside_joinery"]["status"] == "homeowner_selected_omission"
    assert d["r05_clearance"]["geometry_changed"] is False
    receipt = read(receipt_path)
    basis_sha = receipt["after_master_sha256"]
    if digest(basis_path) != basis_sha:
        raise ValueError("The original sign-off basis does not match its integration receipt")
    basis = read(basis_path)
    cabinet_receipt = read(cabinet_receipt_path)
    pre_cabinets = read(pre_cabinets_path)
    if digest(pre_cabinets_path) != cabinet_receipt["before_master_sha256"]:
        raise ValueError("The pre-cabinet master does not match the selection receipt")
    if cabinet_receipt["after_master_sha256"] != master_sha:
        raise ValueError("The current master does not match the cabinet-selection receipt")
    paths = (("storage",), ("architecture", "rooms"), ("architecture", "openings"),
             ("visualization_geometry", "master_layout"), ("visualization_geometry", "children_layout"),
             ("decisions", "bedrooms"), ("decisions", "r05_clearance"), ("decisions", "ceiling_heights"),
             ("decisions", "orientation"))
    for keys in paths:
        old, new = basis, pre_cabinets
        for key in keys:
            old, new = old[key], new[key]
        if old != new:
            raise ValueError("Pre-selection master changes an original storage dependency: " + ".".join(keys))
    for keys in paths[1:]:
        old, new = pre_cabinets, master
        for key in keys:
            old, new = old[key], new[key]
        if old != new:
            raise ValueError("Cabinet selection changes a storage geometry dependency: " + ".".join(keys))
    old_approvals = {approval["id"]: approval for approval in basis["decisions"]["homeowner_signoffs"]}
    new_approvals = {approval["id"]: approval for approval in master["decisions"]["homeowner_signoffs"]}
    for decision in ("HS-WARDROBE-OPT-E", "HS-MBR-SPLIT-WARDROBE"):
        if old_approvals[decision] != new_approvals[decision]:
            raise ValueError("Later master changes storage approval " + decision)

    selected_ids = {"ST-R04a-WR01": "HS-R04A-CABINET", "ST-R08-UC01": "HS-R08-UNDERCOUNTER"}
    selection = s["homeowner_selections"]["included_optional_storage"]
    if (selection != cabinet_receipt["selected_cabinets"]
            or selection["status"] != "homeowner_selected_subject_to_site_holds"
            or selection["construction_release"] is not False
            or {item["id"] for item in selection["items"]} != set(selected_ids)):
        raise ValueError("Both held cabinet selections must match the integration receipt")
    before_storage, normalised = pre_cabinets["storage"], copy.deepcopy(s)
    for item in normalised["items"]:
        if item["id"] not in selected_ids:
            continue
        previous = next(i for i in before_storage["items"] if i["id"] == item["id"])
        if (item["approval_status"] != "homeowner_selected_conditional_review_only"
                or item["homeowner_selection"]["status"] != "selected_subject_to_site_holds"
                or item["homeowner_selection"]["construction_release"] is not False):
            raise ValueError("Selected cabinet lacks its item-level hold: " + item["id"])
        item["approval_status"] = previous["approval_status"]
        item.pop("homeowner_selection")
        applicability = normalised["item_applicability"].pop(item["id"])
        if (applicability["status"] != "homeowner_selected_conditional_review"
                or applicability["decision_refs"] != [selected_ids[item["id"]]]
                or applicability["use_for_current_clearance"] is not False):
            raise ValueError("Selected cabinet applicability is not held: " + item["id"])
    normalised["homeowner_selections"].pop("included_optional_storage")
    normalised["cost_comparison"].pop("selection_cost_status")
    readiness = next(item for item in normalised["readiness"]["ready_for_homeowner_decision"] if item["id"] == "DEC-ST-05")
    readiness.pop("resolution")
    readiness.pop("status")
    if normalised != before_storage:
        raise ValueError("Cabinet selection changed storage beyond the recorded selections")
    for decision in selected_ids.values():
        if (new_approvals[decision]["status"] != "homeowner_selected_review_with_holds"
                or new_approvals[decision]["construction_release"] is not False):
            raise ValueError("Cabinet approval is missing or releases construction: " + decision)
    compatibility = "original_approvals_unchanged_then_exact_recorded_cabinet_selection_only"
    approvals = {approval["id"]: approval for approval in d["homeowner_signoffs"]}
    if (approvals["HS-WARDROBE-OPT-E"]["status"] != "homeowner_signed_off"
            or approvals["HS-MBR-SPLIT-WARDROBE"]["status"] != "homeowner_signed_off_in_principle"
            or approvals["HS-MBR-SPLIT-WARDROBE"]["open_item"] != "OI-MBR-03"):
        raise ValueError("Expected integrated storage approvals are missing or changed")
    if not any("OPT-E BWP plywood carcass" in value for value in receipt["integrated_decisions"]):
        raise ValueError("Integration receipt does not record OPT-E selection")
    if not any("R04 split wardrobe approved in principle" in value for value in receipt["integrated_decisions"]):
        raise ValueError("Integration receipt does not record R04 split in-principle approval")
    master_sha = current_sha
    heights = clean_provenance(d["ceiling_heights"])
    items = []
    for item in s["items"]:
        if item["id"] in EXCLUDED or item["id"] == "ST-R05-BED01":
            continue
        i = {k: copy.deepcopy(item[k]) for k in (
            "id", "room_id", "kind", "bounds_m", "bounds_uv_m", "height_range_m", "dimension_confidence",
            "length_m", "leaves", "leaf_width_m", "hinges_per_leaf", "plinth_m",
            "gross_volume_m3", "capacity", "segments") if k in item}
        i["approval_status"] = "joinery_details_proposed_not_fabrication_approved"
        if item["id"] in selected_ids:
            i["scope_status"] = "homeowner_selected_subject_to_site_holds"
            i["scope_decision_ref"] = selected_ids[item["id"]]
        if i["room_id"] == "R05":
            i["placement_status"] = "retained_by_homeowner_HD-15; dimensions_not_site_verified"
        i["height_status"] = "unmeasured_reference_envelope; loft_geometry_not_ceiling_reconciled"
        items.append(i)
    ml = v["master_layout"]
    band = ml["relationship_zones_m"]["wardrobe_wall_band"]["rect"]
    bay = ml["relationship_zones_m"]["window_bay"]["rect"]
    zones = [[band[0], band[1], bay[0], band[3]], [bay[2], band[1], band[2], band[3]]]
    r04 = {
        "room_rect_m": ml["frame"]["room_rect_m"], "south_wardrobe_zones_m": zones,
        "window_bay_m": bay, "W03_span_m": ml["openings"]["W03"]["proposed_span_m"],
        "W04_span_m": ml["openings"]["W04"]["span_m"], "D02_span_m": ml["openings"]["D02"]["span_m"],
        "status": "homeowner_approved_in_principle_relationship_placeholders_not_fabrication_design",
        "decision_ref": "HS-MBR-SPLIT-WARDROBE",
        "relationships": "SOUTH wardrobes/W03; WEST headboard/W04 north end; EAST TV/door",
        "compartments": "Provisional adult bays and heights are in wardrobe-interiors.json; they remain unapproved and unmeasured.",
        "reference_cost_capacity": {"run_m": 2.75, "leaves": 6, "shelves": 12, "drawers": 4,
                                    "long_hang_m": 1.72, "short_hang_m": 0.86, "loft_gross_m3": 1.444},
        "site_holds": ["OI-MBR-03", "OI-BED-01", "W03/W04 jambs and heads", "loft/pocket support section"]}
    r05 = {
        "frame": v["children_layout"]["frame"],
        "door_opening_v_m": s["context_constraints_R05"]["door_D03"]["opening_v_m"],
        "return_bounds_uv_m": s["context_constraints_R05"]["study_return"]["bounds_uv_m"],
        "curtain_track_u_m": v["children_layout"]["curtain_and_window"]["curtain_span_u_m"],
        "curtain_plane_v_m": s["context_constraints_R05"]["curtain_W05_placeholder"]["plane_v_m"],
        "window_placeholder_u_m": s["context_constraints_R05"]["curtain_W05_placeholder"]["window_placeholder_u_m"],
        "bed_envelope_uv_m": next(i["bounds_uv_m"] for i in s["items"] if i["id"] == "ST-R05-BED01"),
        "bed_scope": "Tenant-supplied planning envelope, not joinery and not a universal size limit",
        "route_gap_m": 0.3876, "route_target_m": 0.60,
        "route_status": "HD-15 retains layout; held site check, not comfortable route or statutory target",
        "loft_presence_continuity": "Homeowner-confirmed; support, dimensions and material unverified",
        "loft_leaf_discrepancy": {"proposed_drawing": 6, "cost_allowance": 8, "resolution": "unselected; no reprice"}}
    room_data = []
    for room in master["architecture"]["rooms"]:
        if room["id"] not in ROOMS:
            continue
        room_data.append({"id": room["id"], "name": room["name"],
                          "dimensions": clean_provenance(room["dimensions"]),
                          "basis": "Homeowner-confirmed nominal measurements where flagged; not independently verified",
                          "note": room["note"]})
    openings = [clean_provenance(o) for o in master["architecture"]["openings"]
                if o["id"] in ("D02", "D03", "D06", "W03", "W04", "W05")]
    for o in openings:
        o["authority"] = "Opening existence/source facts only; current placement uses R04/R05 relationship data."
        for k in ("approximate_segment_m", "approximate_segment_ft", "coordinate_order"):
            o.pop(k, None)
    data = {
        "schema": "wardrobe-signoff-review/1", "source_master_sha256": master_sha,
        "status": "review_deliverable_not_construction_release", "construction_release": False,
        "export_policy": "Current review projection with integrated homeowner decisions. Not a replacement master fragment.",
        "integration_receipt": {"filename": Path(receipt_path).name, "sha256": digest(receipt_path),
                                "integrated_master_sha256": basis_sha, "current_master_sha256": master_sha,
                                "compatibility": compatibility,
                                "decisions": ["HS-WARDROBE-OPT-E", "HS-MBR-SPLIT-WARDROBE"],
                                "cabinet_selection_receipt": {
                                    "filename": Path(cabinet_receipt_path).name,
                                    "sha256": digest(cabinet_receipt_path),
                                    "before_master_sha256": cabinet_receipt["before_master_sha256"],
                                    "after_master_sha256": cabinet_receipt["after_master_sha256"],
                                    "decisions": list(selected_ids.values())}},
        "confirmed_brief": {"flats": 4, "household": "3-4 tenants: couple plus one or two children",
                            "beds": "tenant-supplied HD-05", "fixed_bedsides": "omitted HD-14",
                            "budget_target_pre_gst_inr": [250000, 350000],
                            "materials_selected": "OPT-E", "material_decision": "HS-WARDROBE-OPT-E",
                            "R04_split": "approved in principle, dimensions unmeasured; OI-MBR-03",
                            "selected_cabinets": ["ST-R04a-WR01", "ST-R08-UC01"],
                            "selected_cabinet_fit": "Selected in scope; geometry, access and site fit remain unverified.",
                            "R05_layout": "retained HD-15",
                            "curtains": "ceiling-recessed two-track sheer + blackout; dimensions unmeasured",
                            "orientation": "north at sheet-bottom; west at sheet-right"},
        "effective_heights": heights, "rooms": room_data, "opening_facts": openings,
        "items": items, "R04": r04, "R05": r05,
        "quantity_model_inputs": {"R04": [2.70, 6, 12, 4, 6, 0.45, 2, 2.574, 2.75, 6, 1],
                                  "R05": [2.00, 4, 12, 2, 4, 0.50, 1, 1.4325, 3.81, 8, 1],
                                  "R04a": [1.55, 4, 22, 1, 4, 0.3875, 1, 0, 1.67, 4, 1]},
        "quantity_hold": QUANTITY_HOLD,
        "field_holds": [
            {"id": "H-LOFT", "status": "open", "check": "Measure loft soffit/top/depth/support in every room and flat; reconcile ceiling pockets and confirm load."},
            {"id": "OI-MBR-03", "status": "open", "check": "Measure and design R04 split joinery around W03; no old furniture coordinates are active."},
            {"id": "OI-BED-01", "status": "open", "check": "Check actual tenant queen/king frames, access, curtain stacks and switch/socket reach."},
            {"id": "CC-R05-12", "status": "layout_retained_HD-15_site_check", "check": "387.6 mm calculated corner gap; do not call it a comfortable route."},
            {"id": "FH-ST-03", "status": "open", "check": "Dressing clear width >=1.05 m plus actual door and cabinet operation."},
            {"id": "FH-ST-12", "status": "open", "check": "Utility cabinet: measure actual dimensions, plumbing, services and maintenance access."},
            {"id": "FH-ST-04/05/06/07/08/10", "status": "open", "check": "Door/window sizes and swings; plumb/levels; moisture; utility conflict; electrical and AC interfaces."}],
        "cost_comparison": current_cost(s["cost_comparison"], master_sha)}
    if interior_reference:
        data["interior_generation_basis_sha256"] = generation_sha
        data["integration_receipt"]["interior_reference_receipt"] = interior_reference
        data["integration_receipt"]["compatibility"] += "_then_guarded_reference_only_integration"
    save_json(SOURCE, data)
    return data


def export_costs(data):
    c = data["cost_comparison"]
    save_json(HERE / "cost_model.json", c)
    tax = TAX
    rows = []
    units = {u["id"]: u for u in c["units"]}
    for oid in ORDER:
        for uid, p in c["options"][oid]["per_unit"].items():
            u = units[uid]
            rows.append([oid, uid, u["room_id"], "homeowner_selected_fit_hold" if u["room_id"] == "R04a" else "base",
                         *p["inr"], u["front_elevation_sqft"], p["installed_weight_kg_excl_contents"],
                         tax, data["source_master_sha256"]])
    tables = {
        "cost-units.csv": (["option", "reference_unit", "room_id", "scope", "inr_low", "inr_high",
                            "front_sqft", "empty_weight_kg", "tax_basis", "source_master_sha256"], rows),
        "cost-flats.csv": (["option", "wardrobes_including_R04a_low", "wardrobes_including_R04a_high",
                            "selected_scope_per_flat_low", "selected_scope_per_flat_high",
                            "selected_scope_four_flats_low", "selected_scope_four_flats_high",
                            "selected_UC01_component_low", "selected_UC01_component_high",
                            "selected_R04a_component_low", "selected_R04a_component_high",
                            "provisional_pullout_delta_low", "provisional_pullout_delta_high",
                            "with_provisional_pullouts_per_flat_low", "with_provisional_pullouts_per_flat_high",
                            "with_provisional_pullouts_four_flats_low", "with_provisional_pullouts_four_flats_high",
                            "tax_basis", "scope", "source_master_sha256"],
                           [[oid, *c["options"][oid]["base_wardrobes_lofts_per_flat_inr"],
                             *c["options"][oid]["per_flat_incl_required_common_inr"],
                             *c["options"][oid]["four_flats_incl_required_common_inr"],
                             *c["options"][oid]["selected_UC01_component_per_flat_inr"],
                             *c["options"][oid]["selected_R04a_component_per_flat_inr"],
                             *c["options"][oid]["provisional_pullout_delta_per_flat_inr"],
                             *c["options"][oid]["per_flat_incl_provisional_pullouts_inr"],
                             *c["options"][oid]["four_flats_incl_provisional_pullouts_inr"], tax,
                             "Both selections included; R08 front-only allowance, carcass/shelves unpriced; fit held; pull-outs provisional",
                             data["source_master_sha256"]] for oid in ORDER]),
        "cost-common.csv": (["item", "category", "inr_low", "inr_high", "four_flats_low", "four_flats_high",
                             "evidence", "tax_basis", "scope", "source_master_sha256"],
                            [[r["item"], r["category"], *r["inr"], *[4 * n for n in r["inr"]], r["basis"],
                              tax, "Ancillary items repeated per flat, not building common areas",
                              data["source_master_sha256"]] for r in c["common_per_flat"]])}
    for name, (header, values) in tables.items():
        with (HERE / name).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(header)
            writer.writerows(values)
        (OUT / name).write_bytes((HERE / name).read_bytes())
    (OUT / "cost_model.json").write_bytes((HERE / "cost_model.json").read_bytes())


class Sheet:
    def __init__(self, title, subtitle):
        self.parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="950" viewBox="0 0 1400 950">',
                      '<rect width="1400" height="950" fill="white"/>',
                      '<style>text{font-family:Arial,sans-serif;fill:#172b39} .dim{fill:#785718}</style>']
        self.text(45, 49, title, 27, bold=True)
        self.text(45, 80, subtitle, 16)
        self.line(45, 97, 1355, 97)
        self.text(45, 918, "HOMEOWNER REVIEW ONLY | dimensions in metres | NOT FOR FABRICATION | all joinery sizes unmeasured proposals", 17, color="#a13e2c")

    def rect(self, x, y, w, h, fill="#edf3f3", stroke="#264d60", dash=False):
        self.parts.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" fill="{fill}" stroke="{stroke}" stroke-width="2"'
                          + (' stroke-dasharray="8 5"' if dash else '') + '/>')

    def line(self, x0, y0, x1, y1, color="#264d60", dash=False):
        self.parts.append(f'<line x1="{x0:.2f}" y1="{y0:.2f}" x2="{x1:.2f}" y2="{y1:.2f}" stroke="{color}" stroke-width="2"'
                          + (' stroke-dasharray="8 5"' if dash else '') + '/>')

    def text(self, x, y, text, size=16, anchor="start", bold=False, color="#172b39"):
        self.parts.append(f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" text-anchor="{anchor}"'
                          f' style="fill:{color};font-weight:{"bold" if bold else "normal"}">{html.escape(str(text))}</text>')

    def notes(self, lines, y=775):
        for n, line in enumerate(lines):
            self.text(45, y + 24 * n, line, 16)

    def dim(self, x0, y, x1, label):
        self.line(x0, y, x1, y, "#92712c")
        for x in (x0, x1):
            self.line(x, y - 6, x, y + 6, "#92712c")
        self.text((x0 + x1) / 2, y - 10, label, 15, anchor="middle")

    def finish(self, name, data):
        self.text(45, 943, "Master " + data["source_master_sha256"], 12)
        svg = "\n".join(self.parts + ["</svg>"])
        p = OUT / (name + ".svg")
        p.write_text(svg, encoding="utf-8")
        with pymupdf.open(stream=svg.encode(), filetype="svg") as doc:
            doc[0].get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5)).save(OUT / (name + ".png"))
        return name


def item_rect(sheet, bounds, origin, scale, fill="#edf3f3", dash=False):
    a, b, c, d = bounds
    sheet.rect(origin[0] + a * scale, origin[1] + b * scale, (c - a) * scale, (d - b) * scale, fill, dash=dash)


def draw_rooms(data):
    results = []
    r4, r5 = data["R04"], data["R05"]
    band = data["effective_heights"]["derived_levels_m"]["perimeter_band_underside"]
    soffit = data["effective_heights"]["derived_levels_m"]["slab_underside_soffit"]
    items = {i["id"]: i for i in data["items"]}
    s = Sheet("R04 MASTER | relationship plan + south-wall elevation", "Split approved in principle; W03 widths are unmeasured. Interior bays are provisional; see the interior sheet.")
    origin, scale = (100, 170), 100
    x0, z0, x1, z1 = r4["room_rect_m"]
    w, h = x1 - x0, z1 - z0
    s.rect(*origin, w * scale, h * scale, "white")
    s.text(100, 135, "PLAN - SOUTH UP", 19, bold=True)
    for n, rect in enumerate(r4["south_wardrobe_zones_m"]):
        a, b, c, d = rect
        s.rect(origin[0] + (a - x0) * scale, origin[1], (c - a) * scale, (d - b) * scale, "#fff3d3", dash=True)
        s.text(origin[0] + (a - x0 + (c - a) / 2) * scale, 205, "zone " + str(n + 1), 16, "middle")
    wa, wb = r4["W03_span_m"]
    s.line(100 + (wa - x0) * scale, 170, 100 + (wb - x0) * scale, 170, "#3d86a0")
    s.text(100 + w * scale / 2, 155, "SOUTH | W03 roughly centred", 16, "middle")
    s.text(120, 420, "No bed footprint selected", 18)
    s.text(120, 447, "EAST: TV / D02", 16)
    s.text(120, 474, "WEST: headboard / W04", 16)
    w4a, w4b = r4["W04_span_m"]
    s.line(100 + w * scale, 170 + (w4a - z0) * scale, 100 + w * scale, 170 + (w4b - z0) * scale, "#3d86a0")
    da, db = r4["D02_span_m"]
    s.line(100, 170 + (da - z0) * scale, 100, 170 + (min(db, z1) - z0) * scale, "#bc7755")
    s.dim(100, 685, 100 + w * scale, f"{w:.3f} nominal; north is down")
    s.text(100, 715, f"Room length {h:.4f} nominal; not a new survey.", 16)
    ex, ey, es = 720, 680, 150
    s.text(ex, 135, "SOUTH-WALL ELEVATION - SCHEMATIC", 19, bold=True)
    s.rect(ex, ey - soffit * es, w * es, soffit * es, "white")
    for a, b, c, d in r4["south_wardrobe_zones_m"]:
        xx, ww = ex + (a - x0) * es, (c - a) * es
        s.rect(xx, ey - 2.10 * es, ww, 2.10 * es, "#fff3d3", dash=True)
        s.text(xx + ww / 2, ey - 1.05 * es, "COMPARTMENTS", 16, "middle")
        s.text(xx + ww / 2, ey - 0.86 * es, "SEE INTERIOR", 16, "middle")
        s.dim(xx, 738, xx + ww, f"{c-a:.3f} placeholder")
    s.rect(ex + (wa - x0) * es, ey - 2.10 * es, (wb - wa) * es, 1.3 * es, "#f2f8ff", dash=True)
    s.text(ex + w * es / 2, ey - 1.35 * es, "W03", 18, "middle")
    s.text(ex + w * es / 2, 265, "LOFT / POCKET SECTION UNMEASURED", 16, "middle")
    s.line(ex, ey - band * es, ex + w * es, ey - band * es, "#bd8051", True)
    s.text(ex + 8, ey - band * es - 10, f"Band {band:.4f} derived, not a loft cap", 15)
    s.notes(["Each 1.448 m zone and 0.913 m W03 bay are placeholders; no jamb offset was measured.",
             "Window sill/head are illustrative only. No loft height, support detail or shutter arrangement is selected.",
             "2.228 m west-wall run before W04; less an assumed 0.30 m stack = 1.928 m. Fit remains unresolved.",
             "Retained R04 single-run quantities are comparison data only; do not fabricate from this image."], 790)
    results.append(s.finish("R04-master-plan-elevation", data))

    s = Sheet("R05 CHILDREN | retained plan + south-wall elevation", "HD-15 retains the layout; wardrobe compartments and shutters remain proposals for sign-off.")
    ox, oy, ps = 100, 160, 105
    U, V = r5["frame"]["u_span_m"], r5["frame"]["v_span_m"]
    s.rect(ox, oy, V * ps, U * ps, "white")
    s.text(100, 132, "PLAN - SOUTH UP; v right, u down", 19, bold=True)
    ret = r5["return_bounds_uv_m"]
    item_rect(s, [ret[1], ret[0], ret[3], ret[2]], (ox, oy), ps, "#dce1e1")
    for iid, fill in (("ST-R05-WR01", "#daeae5"), ("ST-R05-DK01", "#edf3f3"), ("ST-R05-TV01", "#edf3f3")):
        u0, v0, u1, v1 = items[iid]["bounds_uv_m"]
        item_rect(s, [v0, u0, v1, u1], (ox, oy), ps, fill)
    u0, v0, u1, v1 = r5["bed_envelope_uv_m"]
    item_rect(s, [v0, u0, v1, u1], (ox, oy), ps, "#faf1e3", True)
    s.text(ox + (v0 + v1) * ps / 2, oy + (u0 + u1) * ps / 2, "TENANT BED", 16, "middle")
    s.text(ox + (v0 + v1) * ps / 2, oy + (u0 + u1) * ps / 2 + 24, "1.680 x 2.130", 16, "middle")
    s.text(ox + 288, oy + 32, "4-leaf wardrobe", 16, "middle")
    s.text(ox + 25, oy + 230, "TV", 16)
    s.text(ox + 120, oy + 400, "DESK", 16, "middle")
    s.rect(ox, oy, V * ps, .6 * ps, "none", "#a172a5", True)
    da, db = r5["door_opening_v_m"]
    s.line(ox + da * ps, oy, ox + db * ps, oy, "#bc7755")
    s.line(ox + da * ps, oy, ox + da * ps, oy + (db-da) * ps, "#bc7755")
    s.text(ox + 50, oy + 94, "D03", 16)
    desk = items["ST-R05-DK01"]["bounds_uv_m"]
    s.line(ox + v0 * ps, oy + u1 * ps, ox + desk[3] * ps, oy + desk[0] * ps, "#c0392b")
    s.text(100, 693, "0.388 m corner gap: site hold, NOT comfortable passage", 16, color="#a13e2c")
    s.dim(ox, 733, ox + V * ps, f"{V:.3f} nominal; length {U:.3f}")
    ua, ub = r5["curtain_track_u_m"]
    s.line(ox + r5["curtain_plane_v_m"] * ps, oy + ua * ps,
           ox + r5["curtain_plane_v_m"] * ps, oy + ub * ps, "#a172a5")
    s.text(520, 618, "W05 /", 14)
    s.text(520, 639, "curtain", 14)
    ex, ey, es = 700, 675, 155
    s.text(ex, 132, "SOUTH WALL - SHUTTER PROPOSAL", 19, bold=True)
    s.rect(ex, ey - soffit * es, V * es, soffit * es, "white")
    s.line(ex, ey - band * es, ex + V * es, ey - band * es, "#bd8051", True)
    s.text(ex + 8, ey - soffit * es - 10, f"Band {band:.4f}; slab {soffit:.4f} derived", 15)
    wr0 = items["ST-R05-WR01"]["bounds_uv_m"][1]
    wr_width = items["ST-R05-WR01"]["bounds_uv_m"][3] - wr0
    for n in range(4):
        s.rect(ex + (wr0 + wr_width * n / 4) * es, ey - 2.1 * es, wr_width * es / 4, 2.0 * es, "#daeae5")
        s.text(ex + (wr0 + wr_width * (n + .5) / 4) * es, ey - .8*es, f"C{n+1}", 15, "middle")
    s.rect(ex + wr0 * es, ey - .1 * es, 2.025 * es, .1 * es, "#b6bcbc")
    s.rect(ex + da * es, ey - 2.13 * es, (db-da) * es, 2.13 * es, "#faf1e3", dash=True)
    s.text(ex + (da+db)/2 * es, ey - es, "D03", 16, "middle")
    loft_top = items["ST-R05-LF01"]["height_range_m"][1]
    s.rect(ex, ey - loft_top * es, V * es, (loft_top-2.13) * es, "none", "#a172a5", True)
    for t in (wr0/2, wr0, wr0+wr_width/4, wr0+wr_width/2, wr0+3*wr_width/4):
        s.line(ex+t*es, ey-loft_top*es, ex+t*es, ey-2.13*es, "#a172a5", True)
    s.text(ex+V*es/2, ey-2.53*es, "ONE CONTINUOUS LOFT - LEVELS TBD", 16, "middle")
    s.dim(ex, 733, ex+V*es, "3.810 total; A 1.785 + B 2.025 (not duplicate slabs)")
    s.notes(["Loft top 3.08 / soffit 2.13 are UNMEASURED references crossing the new band; this is NOT a resolved section.",
             "Reference gross volume 2.00 m3 = 0.937 + 1.063. Not updated for the new ceiling and not usable luggage capacity.",
             "Drawing proposal = 2 + 4 loft leaves; cost allowance = 8 leaves. Resolve hardware/quantity mismatch before ordering.",
             "No fixed bedsides (HD-14). W05/curtain plan extent remains an unmeasured placeholder; king fit is placement-specific."], 790)
    results.append(s.finish("R05-children-plan-elevation", data))

    configs = (
        ("R04a", "DRESSING", "ST-R04a-WR01", "ST-R04a-LF01", "R04a-dressing-plan-elevation"),
        ("R08", "UTILITY", "ST-R08-UC01", "ST-R08-LF01", "R08-utility-plan-elevation"),
        ("R09", "ENTRY SHOE STORAGE", "ST-R09-SH01", None, "R09-entry-plan-elevation"))
    for room, name, iid, lid, filename in configs:
        s = Sheet(f"{room} {name} | unit plan + elevation", "Cabinet envelopes only; not a room floorplan or approval of wall/door locations.")
        i = items[iid]
        x0, z0, x1, z1 = i["bounds_m"]
        if room in ("R04a", "R08"):
            length, depth = z1-z0, x1-x0
        else:
            length, depth = x1-x0, z1-z0
        sc, px, py = 270, 100, 285
        s.text(100, 145, "UNIT PLAN", 19, bold=True)
        s.rect(px, py, length*sc, depth*sc, "#edf3f3", dash=room != "R09")
        s.dim(px, py-30, px+length*sc, f"{length:.3f} proposed")
        s.text(px, py+depth*sc+35, f"Depth {depth:.3f} proposed", 17)
        s.text(710, 145, "FRONT ELEVATION", 19, bold=True)
        ex, ey, es = 710, 690, 155
        lo, hi = i["height_range_m"]
        s.rect(ex, ey-hi*es, length*es, (hi-lo)*es, "#edf3f3", dash=room != "R09")
        if lid:
            loft = items[lid]
            llo, lhi = loft["height_range_m"]
            lb = loft["bounds_m"]
            loft_length = lb[3]-lb[1]
            s.rect(ex, ey-lhi*es, loft_length*es, (lhi-llo)*es, "none", "#a172a5", True)
            s.text(ex+loft_length*es/2, ey-(llo+lhi)/2*es, "LOFT TBD", 16, "middle")
            s.text(100, 525, f"Reference loft vertical range {llo:.2f}-{lhi:.2f}: UNMEASURED.", 17)
        if room == "R04a":
            for n in range(1,4):
                s.line(ex+length*es*n/4, ey-hi*es, ex+length*es*n/4, ey-lo*es)
            s.text(100, 565, "22 shelf allowance + 1 drawer; mirror leaf proposed.", 17)
            s.notes(["SELECTED: project target site clear width >= 1.05 m before a 0.30 m cabinet gives a nominal 0.75 m residual lane.",
                     "Door/hinge sweep, usable dressing route and pocket/light access still require checking; no clear route is certified.",
                     "Loft plan length 1.670 m, depth 0.340 m; reference gross 0.497 m3 is not verified usable capacity.",
                     "R04a is included in selected-scope costs; exact fit, internal layout and mirror detail remain provisional."], 785)
        elif room == "R08":
            s.text(100, 565, "Under-counter SELECTED; loft shutters are required ancillary.", 17)
            s.notes(["LF01: 1.112 x 0.551 m plan; y=1.90-2.95 m reference. UC01: same plan, height 0.80 m proposed.",
                     "LD01 hooks / ladder / mop strip: 0.560 x 0.150 m, y=0.10-1.55 m; locate after D06 swing check.",
                     "The kitchen-to-south utility wall stays straight: no new enclosing return is drawn or authorised.",
                     "Utility measured-label / inferred-model scope mismatch remains open; cabinet and loft support not surveyed."], 785)
        else:
            s.text(ex+length*es/2, ey-.45*es, "LOUVRED", 16, "middle")
            s.text(100, 525, "Powder-coated aluminium, drained stone top, legs.", 17)
            s.notes(["SH01: 1.200 x 0.350 x 0.900 m proposed; up to about 16 pairs only if the actual pairs fit.",
                     "Confirm door/gate and stair/arrival egress on site. No reduction of required escape width is approved.",
                     "No fabrication location is implied by this isolated unit view; exposure, fixings and anti-tip restraint require checking.",
                     "Shoe cabinet is included in required ancillary cost; it is repeated in every flat, not a building-common item."], 785)
        s.dim(ex, 733, ex+length*es, f"{length:.3f}; height {hi-lo:.2f}")
        results.append(s.finish(filename, data))
    return results


def compose_md(data, model, images, interior_images):
    c = data["cost_comparison"]
    r4 = data["R04"]
    z = r4["south_wardrobe_zones_m"]
    sizes = [r[2]-r[0] for r in z]
    r04_section = model["rooms"]["R04"]["sections"][0]
    p = model["parameter_basis"]
    top_rail, lower_rail = p["double_rail_ffl_mm"]
    upper_drop = p["double_upper_rail_to_lower_mm"]
    lower_drop = p["double_lower_rail_to_base_mm"]
    hook_clear = p["top_shelf_ffl_mm"] - p["panel_mm"] - top_rail
    lines = [
        "# Wardrobe and storage - homeowner sign-off pack",
        "",
        "**Ready for review, NOT for fabrication.** This pack records confirmed choices, material recommendations and remaining decisions; it does not approve joinery shop drawings.",
        "",
        f"**Source master SHA-256:** `{data['source_master_sha256']}`. Four identical rental flats in Hyderabad. This is a coordination handoff, not permission to fabricate.",
        "",
        "## 1. Already confirmed - do not ask again",
        "",
        "| Topic | Current rule |",
        "|---|---|",
        "| Household / floors | Four flats; typical family of 3-4, a couple plus one or two children (HD-04). |",
        "| Beds | Tenant-supplied, excluded from joinery and all costs (HD-05). |",
        "| Fixed bedside cabinets | Omitted in BOTH bedrooms (HD-14). Not an optional add-on awaiting approval. Movable tenant tables remain possible. |",
        "| Budget | INR 250,000-350,000 per flat, before GST, excluding beds (HD-06). Allowance rates are NOT tax-normalised. |",
        "| Material | OPT-E BWP plywood carcass and laminate shutters selected (HS-WARDROBE-OPT-E). Base, gap and hardware details are proposed pending professional checks. |",
        "| R04 relationship | Split wardrobe around roughly-centred W03 approved in principle (HS-MBR-SPLIT-WARDROBE); SOUTH wardrobe, WEST headboard/W04 and EAST TV/door. Exact widths are unmeasured; the interiors below are provisional. |",
        "| R05 layout | Retained unchanged (HD-15); approximately 387.6 mm bed/study corner gap is a SITE HOLD, not a comfortable passage. |",
        "| Dressing and utility | Homeowner selected the R04a shallow dressing cabinet (HS-R04A-CABINET) AND R08 under-counter cabinet (HS-R08-UNDERCOUNTER). Their dimensions, access and site fit remain held. |",
        "| Curtains | Ceiling-recessed two-track sheer + blackout (HD-08/14). Pocket, support, stack and LED access need measured sections. |",
        "| Lofts | Presence above wardrobes and in utility is homeowner-reported. R05 door-to-wardrobe continuity is confirmed; RCC material, dimensions and load capacity are NOT verified. |",
        "| Orientation | South-up plans: north down, west right. Confirmed nominal bedroom dimensions are not newly surveyed here. |",
        "",
        "## 2. Homeowner choices still open",
        "",
        "| Decision | Recommendation / choices | Homeowner response |",
        "|---|---|---|",
        "| Proposed interiors | Review the provisional bay, hanging, drawer and pull-out layouts in section 3a and request any changes. The layouts are not yet approved for fabrication. | __________ |",
        "| Bedroom shutter arrangement | Review after site measurement. In the children's room four hinged fronts are a provisional reference; six narrower fronts remain unselected. | __________ |",
        "| Final quote | Approve or revise scope only after measured quantities and itemised, tax-normalised quotations are available. | __________ |",
        "",
        "These outstanding choices do not reopen the selected OPT-E or the R04 split approval. No selection waives field holds or constitutes structural/electrical/fabrication approval.",
        "",
        "### Site measurements and professional checks - not homeowner preference questions",
        "",
        "Measure each flat's W03/W04/W05, doors and swings, finished floor and ceiling levels, wardrobe wall runs, curtain pockets and loft dimensions. Confirm R04 wardrobe/loft support, structural load and fixings, moisture, services and shutter access before shop drawings. The split and 1.448 m zones are not cut sizes.",
        "",
        "In the children's bedroom, the current plan keeps the wardrobe beside the door, the bed facing the TV, and the continuous loft over the door and wardrobe. The calculated 388 mm is the closest corner-to-corner gap between the proposed bed and the study return near its foot, not a clear walkway: measure the tenant's actual bed and free passage on site. HD-15 keeps the layout; no furniture relocation is authorised.",
        "",
        "**Contractor hold:** do not cut boards, install anchors, alter walls or order sized shutters from this pack. The joiner must issue measured shop drawings and a tax-normalised quotation; the site designer and qualified structural/electrical professionals must resolve affected support, curtain and service interfaces before work is released.",
        "",
        "## 3. Room schedule and quantity limits",
        "",
        "| Room | Current proposal / relationship | Dimensions and status |",
        "|---|---|---|",
        f"| R04 master | Two SOUTH wardrobe zones around W03 | {sizes[0]:.3f} m + {sizes[1]:.3f} m placeholder zones, 0.630 m depth; W03 bay 0.913 m unmeasured. These are NOT replacement cabinet dimensions. |",
        "| R04a dressing | Selected four-bay shallow cabinet, 22 shelf allowance + 1 drawer | Cabinet 1.550 x 0.300 m, y=0.10-2.10 m. Loft 1.670 x 0.340 m. Site clear-width target >=1.05 m and door/route operation must still be verified. |",
        "| R05 wardrobe | Four provisional bays: long hang; two SHORT hang rows; folded clothes/drawers; linen | Envelope 2.025 x 0.630 x 2.100 m including 0.100 m plinth. Interiors are designed provisionally but not fabrication-approved; 12 shelf positions are shown. |",
        "| R05 continuous loft | ONE run: A above entry/switch strip, B above wardrobe; no duplicate slab | 3.810 x 0.600 m; A length 1.785 m + B length 2.025 m. Drawing has 2+4=6 leaves, cost allowance has 8. Do not treat either as final. |",
        "| R05 TV / desk / overhead | Retained proposed ancillary joinery | TV 1.200 x 0.380 m, y=0.40-0.65. Desk 1.200 x 0.550 m, y=0.60-0.75. Overhead 1.200 x 0.350 m, y=1.35-2.10. No desk resizing selected. |",
        "| R08 utility | Aluminium loft shutters, hooks/ladder rail; selected louvred under-counter | Loft/UC01 plan 1.112 x 0.551 m. Loft y=1.90-2.95; UC01 height 0.80. Hook strip 0.560 x 0.150 m, y=0.10-1.55. Site/model scope conflict held. |",
        "| R09 entry | Aluminium shoe cabinet, louvres, legs, stone drip top | 1.200 x 0.350 x 0.900 m; up to about 16 pairs only if actual pairs fit. Confirm arrival/gate/door and egress clearance. |",
        "",
        "**All joinery dimensions above are proposed or inferred, not field-verified fabrication dimensions.** The only retained nominal bedroom measurements are R04 3.810 x 4.6863 m and R05 3.810 x 4.572 m, homeowner-confirmed but not independently checked.",
        "",
        "**R04 capacity is NOT transferred to the split design.** Its reference single-run cost scope carries six leaves, 12 shelves, four drawers, 1.72 m long-hang and 0.86 m short-hang rail, and 1.444 m3 gross loft allowance. The provisional interior bays below are a separate design, not proof that the old quantity allowance is sufficient.",
        "",
        "**Loft volumes are reference arithmetic only:** R05 0.937 + 1.063 = 2.000 m3 gross; R04a 0.497 m3; utility 0.597 m3. They use unmeasured reference envelopes, exclude usable-access deductions, are not revised for the current ceiling and do not establish suitcase counts or permitted loads. Bulky storage belongs in verified lofts, not the clothes compartments.",
        "",
        "## 3a. Provisional interior design",
        "",
        "The interior design is now laid out, not deferred. Every bay and height remains a working proposal for homeowner review and site measurement; the elevations are not fabrication drawings. Dimensions are millimetres from finished floor level (FFL); the inch equivalents are rounded.",
        "",
        f"**Hanging and reach:** estimated clear bedroom depth is {dimension(r04_section['estimated_clear_depth_mm'])} "
        f"after assumed wall, shutter and back allowances within the {dimension(r04_section['depth_envelope_mm'])} envelope. "
        f"Long rail at {dimension(p['long_rail_ffl_mm'])} FFL gives {dimension(p['long_rail_to_base_mm'])} rail-to-plinth; "
        f"subtract hanger/hook and clearance to get actual garment length. Top shelf is at {dimension(p['top_shelf_ffl_mm'])}. "
        f"Test actual adult hangers: the R04 placeholder clear bays are only about {dimension(r04_section['bays'][0]['clear_width_mm'])} wide.",
        "",
        f"**Double hanging is deliberately for short clothes:** rails at {dimension(top_rail)} and {dimension(lower_rail)} FFL "
        f"leave {dimension(upper_drop)} between rails and {dimension(lower_drop)} from the lower rail to the plinth, "
        f"before hanger/garment clearance. The upper rail has about {round(hook_clear)} mm to the assumed {p['panel_mm']} mm-thick "
        "shelf underside: verify the hanger hook and fittings. Two full 1,000 mm drops do not fit below the 1,900 mm shelf "
        "in this 2,100 mm-high reference unit; measure clothes or redesign rather than assuming they do.",
        "",
        "**Drawers and trays:** bedroom drawer fronts are 300-660 mm (1 ft 0 in-2 ft 2 in) FFL; proposed accessory trays are 700-820 mm (2 ft 4 in-2 ft 8 in). The dressing drawer is 700-880 mm (2 ft 4 in-2 ft 11 in). Rail, drawer and shelf heights are working ergonomic targets, not codes or product specifications. Confirm reach, weight, opening clearance and hardware suitability.",
        "",
        "| Room / bay | Clear width | Intended use | Approximate internal levels, mm FFL |",
        "|---|---|---|---|",
    ]
    for room_id in ("R04", "R05", "R04a", "R08", "R09"):
        for sec in model["rooms"][room_id]["sections"]:
            for b in sec["bays"]:
                levels = []
                if b["shelf_heights_ffl_mm"]:
                    levels.append("shelves " + ", ".join(str(n) for n in b["shelf_heights_ffl_mm"]))
                if b["rail_heights_ffl_mm"]:
                    levels.append("rails " + ", ".join(str(n) for n in b["rail_heights_ffl_mm"]))
                if b["drawers_ffl_mm"]:
                    levels.append("drawer fronts " + ", ".join(f"{a}-{z}" for a, z in b["drawers_ffl_mm"]))
                if b["pullouts_ffl_mm"]:
                    levels.append("pull-out " + ", ".join(f"{a}-{z}" for a, z in b["pullouts_ffl_mm"]))
                lines.append(f"| {room_id} / {b['id']} | {dimension(b['clear_width_mm'])} | "
                             f"{b['contents']} | {'; '.join(levels) or 'open; verify services'} |")
    lines += [
        "",
        "**Lofts:** use for light seasonal bedding and luggage only after the actual supports, access and loading have been professionally checked. R04's loft/W03/ceiling-recessed curtain pocket may conflict; no clash or support detail has been established. R05's continuous door-to-wardrobe loft remains, with six proposed versus eight costed leaves unresolved. No entry loft is assumed. The shallow dressing cabinet is for shelves/drawers, not standard adult hanging; utility shelving is subordinate to plumbing access.",
        "",
        "### Interior hardware and incremental allowance",
        "",
        "Existing reference allowances for R04 + R05 + R04a contain 92 hinges (36 + 32 + 24), seven drawer-channel pairs (4 + 2 + 1), four locks, 46 shelf positions and 4.0065 m of rail. These are comparison allowances, not a final hardware schedule; the old R04 single-run geometry and the R05 loft leaf-count discrepancy must be re-quantified. The low-end runner source is **not soft-close**; a soft-close upgrade, if wanted, is unpriced. Specify suitable rated, replaceable hinges and runners after leaf size/weight and substrate are checked.",
        "",
        "**New provisional pull-outs:** two saree/accessory trays in R04 plus one accessory tray in R05 = three tray-and-slide sets per flat. An **UNVERIFIED** INR 1,000-2,500 each gives +INR 3,000-7,500 per flat or +INR 12,000-30,000 for four flats. This is separate from the selected-scope total, not a quote or approved purchase; do not charge again if a supplier includes it. Changes to R04 panels/shutters/rails, utility carcass/partition/base/shelf, shoe cabinet carcass/shelf supports, soft-close upgrades, anchors and final installation remain unpriced until measured quotations. Four lockable drawers are proposed; none is a security safe.",
        "",
        "No wardrobe light has been newly selected or costed. Any later switched light, driver and wiring must be coordinated with the electrical plan and the required ceiling-recessed curtain pocket.",
        "",
        "## 4. Materials, durability and exact allowance comparison",
        "",
        "OPT-E BWP plywood carcass and laminate shutters are homeowner-selected (HS-WARDROBE-OPT-E). The stone base, ventilated gap and replaceable internals are proposed OPT-E details, subject to measured drawings, support and moisture checks; the selection is not fabrication release. OPT-F is an unselected alternative using an aluminium/ACP carcass with plywood fronts. Thin granite is better limited to base/sills/ledges than full carcasses.",
        "",
        "**Plinth correction:** 0.100 m is the total proposed assembly from FFL, including the stone, bedding and supporting kerb; do not add a 20 mm slab on a 100 mm kerb and still call it 100 mm. The section remains to be detailed. A 25 mm vent gap + 0.580 m carcass + 25 mm shutter allowance totals the 0.630 m planning envelope.",
        "",
        "Use certificate-verified plywood grade (IS 710 marine or the explicitly certified applicable IS 303 grade; do not equate BWR with marine BWP). Laminate cost basis is 1 mm outside and 0.8 mm liner inside, not 1 mm on both faces. HDHMR performance is manufacturer-specific; obtain relevant product certification rather than making a blanket 'no BIS standard exists' claim.",
        "",
        "Four hinges per 2.0 m leaf and two per reference 0.85 m loft leaf are costing guides, NOT a load rating. Verify actual leaf mass, width, screw substrate, hinge/runner load and cycle ratings with the chosen Hettich/Hafele/Ebco/Godrej system. No universal one-hour repair or service life is promised.",
        "",
        "## 4a. Seven options - identical reference scope",
        "",
        "**All money below is INR; tax-unnormalised indicative allowances, not verified pre-GST totals.** Required ancillary items including selected UC01 total INR 52,780-101,040 per flat; the selected R04a cabinet is included in the wardrobe column. 'Common' in data keys means ancillary items repeated in each flat, NOT building common areas. Weight remains the old base R04+R05 wardrobes/loft shutters only, empty; it excludes the selected R04a cabinet, contents and ancillary items.",
        "",
        "| Option | System / decision status | Wardrobes incl R04a / flat | Selected scope / flat | Selected scope / four flats | Old R04+R05 empty kg / flat |",
        "|---|---|---|---|---|---|"]
    descriptions = {
        "OPT-E": "HOMEOWNER-SELECTED: BWP ply + laminate; stone base/off-wall gap proposed",
        "OPT-E-H": "Variant: OPT-E with HDHMR shutters; edge/product verification",
        "OPT-F": "UNSELECTED alternative: aluminium/ACP box + BWP laminate fronts",
        "OPT-A": "All plywood; floor-contact plinth is its weak point",
        "OPT-B1": "Aluminium/ACP including shutters; dent/repair trade-off",
        "OPT-C": "12 mm granite carcass + ply fronts; specialist not recommended, NOT homeowner-rejected",
        "OPT-D": "Granite back/base + ply; no wall chasing, not recommended"}
    for oid in ORDER:
        o = c["options"][oid]
        lines.append(f"| {oid} | {descriptions[oid]} | {money(o['base_wardrobes_lofts_per_flat_inr'])} | "
                     f"{money(o['per_flat_incl_required_common_inr'])} | {money(o['four_flats_incl_required_common_inr'])} | {o['base_weight_per_flat_kg']} |")
    lines += [
        "",
        "**OPT-E selected scope:** INR 263,020-463,190 per flat, or INR 1,052,080-1,852,760 for four flats, includes the selected R04a cabinet and the R08 shutter allowance, but not a demonstrated R08 carcass or the provisional trays. Its midpoint is INR 363,105; the high end is numerically INR 113,190 above the INR 350,000 target. **OPT-F unselected alternative:** INR 261,520-514,120 per flat. These are not comparable pre-GST quotes: tax treatment and the R04 split quantities remain unresolved.",
        "",
        "**Required ancillary scope:** shoe cabinet front + stone top 9,130-14,510; utility loft shutters 9,450-14,490; selected under-counter shutters 7,200-11,040; hooks/ladder/mop rail 1,000-3,000; R05 TV console 8,000-18,000; R05 desk + overhead 18,000-40,000. The utility under-counter allowance covers fronts only, not a demonstrated carcass, partition, base or shelf. The shoe allowance covers front and top, not demonstrated internal shelves/supports. Quote missing components separately; these are not complete installed cabinet quotes or confirmation that all positions are final.",
        "",
        "**Both selections are included in scope, with incomplete allowances:** R08 UC01 front shutters contribute INR 7,200-11,040 per flat; R04a contributes INR 45,910-79,320 under OPT-E. R08 carcass, partition, base and shelf are not priced; fit remains unverified. Fixed bedside units are omitted and have no add-on line. The three provisional pull-outs, if accepted and not otherwise included, would bring OPT-E to INR 266,020-470,690 per flat or INR 1,064,080-1,882,760 for four flats; their rate is unverified.",
        "",
        "**Quantity caveat:** " + QUANTITY_HOLD,
        "",
        "R04 10% quantity sensitivity under OPT-E is +/-INR 8,920-15,394 per flat; it is not a reliable bound on the final split design. Each four-flat number equals 4 x the displayed per-flat endpoint. No division by 1.18 or other assumed GST rate is used.",
        "",
        "**Weight and support:** granite density 2,700 kg/m3 gives 32.4 / 40.5 / 54.0 kg/m2 at 12 / 15 / 20 mm; 18 mm ply at assumed 650 kg/m3 gives 11.7 kg/m2. Reference R04 empty-footprint loads are 2.60 kN/m2 OPT-E, 1.47 OPT-F and 3.70 OPT-C. These are not slab design checks, allowable capacities or direct comparisons with residential imposed-load limits.",
        "",
        "Granite is inert but brittle, difficult to modify and does not waterproof a damp wall. Repair leakage first, dry and verify the wall, provide inspection/ventilation and termite protection, seal board edges and use maintainable mechanical hardware. A 230 mm wall thickness alone does not select a safe anchor. Stone/loft load paths and fixings require competent site/structural review.",
        "",
        "Masonry/RCC cupboards and stone shelves are not costed or selected; irreversible work requires final layouts and engineer-designed support. Porcelain/sintered slabs retain brittle-edge/fixing disadvantages and are not recommended as a carcass. No stone spans, grooving, wall chasing or overhead stone support is approved.",
        "",
        "**Evidence:** 38 retained source records in `cost-evidence.json` / `.md`; sourced article/listing/forum rates remain distinguished from UNVERIFIED/ASSUMED allowances in `cost_model.json`. No dealer quotation was obtained; 12 mm stock availability was not confirmed. Beds, omitted bedsides, leak repair, loft structural work, electrical work, turnkey margin and upper-floor lifting are excluded.",
        "",
        "## 5. Ceiling, curtain and fabrication holds",
        "",
        "- HD-11 uses homeowner-stated 11 ft floor-to-floor, assumed 5 in slab and 1.5 in finish: 3.3528 - 0.1270 - 0.0381 = **3.1877 m slab underside**; minus 0.2286 m drop = **2.9591 m band underside**. These are DERIVED, not field measurements.",
        "- HD-14 confirms a separate gypsum/POP raised centre panel with provision for profiles/wiring. Its actual panel level and cavity depth are unknown; 3.1877 m is not a measured gypsum surface.",
        "- No bedroom loft is automatically clipped to the new band. Reference y=2.13-3.08 m loft envelopes and their volumes need measured sections, support/load checks and shutter/ceiling reconciliation (H-LOFT, FH-ST-01/02).",
        "- W03 has a possible pocket/loft support conflict, not proven absence of ceiling. Recessed two-track curtains remain required. Measure clear pocket/track spacing, stack, soffit and driver-access arrangement; no underside-mounted substitute selected.",
        "- The +/-0.30 m curtain stack, 0.55 m loft sweep offset and R05 fan u>=2.0 m are working assumptions, not manufacturer/code requirements. The previous 2.70 m cap is not a current selected height.",
        "- R04 west-wall fit: 3.0824424 - 0.8546376 = 2.2278048 m before W04. Less an assumed 0.30 m stack gives 1.9278048 m: a 1.680 m queen frame has 0.2478048 m width-only surplus; a 1.985 m king has 0.0571952 m deficit. Actual centreline, headboard, shutter sweep and access remain unresolved (OI-BED-01).",
        "- R05 387.6 mm is the straight corner distance sqrt(0.312^2 + 0.230^2), not a certified unobstructed route. HD-15 retains the layout for site confirmation; no desk alternative is selected. The 600 mm comparison is a project usability target, not a statutory minimum.",
        "- Before fabrication: measure W03/W04/W05, D02/D03/D06 swings, finished levels, plumb, utility/dressing width, wall moisture, concealed services, anchors, loft support and load; coordinate lights/PSUs/fan/AC and switches against actual shutters and tenant frames.",
        "",
        "## 6. Ergonomics and care",
        "",
        "Working recommendations, not sourced statutory dimensions: adjustable shelves on 32 mm centres and frequently used shelves around 0.70-1.60 m. Section 3a gives the actual provisional rail, shelf and drawer levels; adjust them to measured garments, clearances and user reach. No 1,000 mm double-hang drop is claimed for the current 2,100 mm reference height.",
        "",
        "Keep light/empty luggage high only after support review; use a stable rated step platform. Do not store damp clothes. Vacuum/wipe monthly; inspect moisture/termite paths at monsoon onset and after leaks; check hinges, runners and restraints every 6-12 months and between tenants. Keep matching spare hardware.",
        "",
        "## 7. Current files and cleanup boundary",
        "",
        "`wardrobe-signoff-pack.md/.pdf/.html`, `storage-current.json`, `wardrobe-interiors.json`, `cost_model.json`, three separate CSVs, `cost-evidence.md/.json`, and five room-plan plus five interior PNG/SVG sheets are the joinery coordination deliverables. `rollup-receipt.json` records validation and source provenance; `file-hashes.json` records final file hashes. `CLEANUP-MANIFEST.md` records actual removals only.",
        "",
        "In the parent folder, `signoff_pack.py`, `interiors_model.py`, `cost_model.py` and the entry-point wrappers rebuild the pack from the current snapshot. The root `wardrobe-brief.md`, `wardrobe-material-verdict.md` and `wardrobe-site-data.md/.json` remain readable.",
        "",
        "The coordinator master and Library/transcript-images are outside this cleanup boundary. No promise of purging canonical item payloads or creating a new master cabinet layout is made here. Obsolete footprints are absent from this review export; the cost model retains reference quantities without their retired coordinates.",
        "",
        "## 8. Room plan/elevation sheets",
        ""]
    for name in images:
        lines += [f"### {name.split('-')[0]}", "", f"![{name.replace('-', ' ')}]({name}.png)", ""]
    lines += ["## 9. Provisional interior elevations", ""]
    for name in interior_images:
        lines += [f"### {name.split('-')[0]}", "", f"![{name.replace('-', ' ')}]({name}.png)", ""]
    if "interior_generation_basis_sha256" in data:
        reference = data["integration_receipt"]["interior_reference_receipt"]
        at = lines.index("## 1. Already confirmed - do not ask again")
        lines[at:at] = [
            f"**Original interior-generation basis:** `{data['interior_generation_basis_sha256']}`; "
            f"immutable interior JSON SHA-256 `{reference['original_interior_source_sha256']}`. "
            "The current master adds a guarded source reference only; existing geometry, decisions and holds are unchanged. "
            "The original interior source has not been relabelled as generated from the newer master.",
            "",
        ]
    return "\n".join(lines) + "\n"


def publish_pdf(md, images):
    body = markdown.markdown(md, extensions=["tables"])
    css = """
    body { font-family: sans-serif; font-size: 10pt; line-height: 1.28; color: #172b39; }
    h1 { font-size: 23pt; color: #244b50; } h2 { font-size: 16pt; margin-top: 18pt; }
    h3 { font-size: 13pt; } p { margin: 7pt 0; } table { border-collapse: collapse; width: 100%; font-size: 8pt; }
    td,th { border: 0.5pt solid #bcc9ca; padding: 5pt; vertical-align: top; }
    th { background: #eaf0ef; } img { width: 100%; } code { font-size: 8pt; }
    """
    (OUT / "wardrobe-signoff-pack.html").write_text(
        "<!doctype html><html><meta charset='utf-8'><title>Wardrobe sign-off</title>"
        f"<style>{css}</style><body>{body}</body></html>", encoding="utf-8")
    narrative = markdown.markdown(md.split("## 8. Room plan/elevation sheets")[0], extensions=["tables"])
    story = pymupdf.Story(html=narrative, user_css=css)
    rect = pymupdf.paper_rect("a4-l")
    writer = pymupdf.DocumentWriter(str(OUT / "wardrobe-signoff-pack.pdf"))
    more = True
    while more:
        device = writer.begin_page(rect)
        more, filled = story.place(rect + (30, 28, -30, -30))
        story.draw(device)
        writer.end_page()
    writer.close()
    pdf_path = OUT / "wardrobe-signoff-pack.pdf"
    with pymupdf.open(pdf_path) as document:
        for name in images:
            with pymupdf.open(OUT / (name + ".svg")) as svg:
                with pymupdf.open(stream=svg.convert_to_pdf(), filetype="pdf") as vector:
                    page = document.new_page(width=rect.width, height=rect.height)
                    page.show_pdf_page(page.rect, vector, 0)
        for n, page in enumerate(document):
            page.insert_text((page.rect.width - 75, page.rect.height - 10), f"{n+1} / {len(document)}",
                             fontsize=8, color=(.25, .3, .3))
        result = document.tobytes(garbage=4, deflate=True)
    pdf_path.write_bytes(result)


def supporting_docs(data, md):
    source = f"Source master `{data['source_master_sha256']}`; current export `storage-design\\storage-current.json`."
    (HERE.parent / "wardrobe-brief.md").write_text(
        "# Wardrobe brief - current\n\n" + source + "\n\n## 1." + md.split("## 1.", 1)[1].split("## 4.", 1)[0]
        + "\nFull sign-off, cost evidence and room images: `storage-design\\final\\wardrobe-signoff-pack.md`.\n", encoding="utf-8")
    material = md[md.index("## 4."):md.index("## 5.")]
    (HERE.parent / "wardrobe-material-verdict.md").write_text(
        "# Wardrobe material verdict - current\n\n" + source + "\n\n" + material +
        "\nOPT-E is homeowner-selected; room plans are review-only and field/fabrication holds remain in the final coordination pack.\n", encoding="utf-8")
    (HERE / "cost-comparison.md").write_text(
        "# Wardrobe cost comparison - current\n\n" + source + "\n\n" + material, encoding="utf-8")
    site = {k: data[k] for k in ("source_master_sha256", "construction_release", "rooms", "opening_facts", "effective_heights", "R04", "R05", "field_holds")}
    save_json(HERE.parent / "wardrobe-site-data.json", site)
    site_md = ["# Wardrobe site data - current", "", source, "",
               "Nominal dimensions confirmed by homeowner; no independent site survey performed by this pack. All joinery and opening offsets remain unmeasured.", "",
               "| Room | Nominal dimensions (m) | Status |", "|---|---|---|"]
    for r in data["rooms"]:
        site_md.append(f"| {r['id']} | {' x '.join(str(d['value_m']) for d in r['dimensions']) or 'unknown'} | {r['basis']} |")
    site_md += ["", md[md.index("## 5."):md.index("## 6.")]]
    (HERE.parent / "wardrobe-site-data.md").write_text("\n".join(site_md), encoding="utf-8")


def build(shared_md=None):
    OUT.mkdir(exist_ok=True)
    data = read(SOURCE)
    model = interiors(data)
    immutable_source = None
    if "interior_generation_basis_sha256" in data:
        reference = data["integration_receipt"]["interior_reference_receipt"]
        source_path = HERE / "reproduction-inputs" / reference["original_interior_source_filename"]
        immutable_source = source_path.read_bytes()
        if (hashlib.sha256(immutable_source).hexdigest() != reference["original_interior_source_sha256"]
                or json.loads(immutable_source) != model):
            raise ValueError("Rebuilt interiors differ from the immutable canonical reference; issue a new reviewed source revision")
    data["provisional_interiors"] = model
    save_json(SOURCE, data)
    if immutable_source is not None:
        (OUT / "wardrobe-interiors.json").write_bytes(immutable_source)
    else:
        save_json(OUT / "wardrobe-interiors.json", model)
    (OUT / "storage-current.json").write_bytes(SOURCE.read_bytes())
    for name in ("cost-evidence.json", "cost-evidence.md"):
        (OUT / name).write_bytes((HERE / name).read_bytes())
    export_costs(data)
    images = draw_rooms(data)
    current_binding = data["source_master_sha256"] if "interior_generation_basis_sha256" in data else None
    interior_images = draw_interior_sheets(model, OUT, current_binding)
    md = compose_md(data, model, images, interior_images)
    (OUT / "wardrobe-signoff-pack.md").write_text(md, encoding="utf-8")
    publish_pdf(md, images + interior_images)
    supporting_docs(data, md)
    if shared_md:
        shared = md
        for name in images + interior_images:
            shared = shared.replace(f"![{name.replace('-', ' ')}]({name}.png)",
                                    f"![{name.replace('-', ' ')}](../../storage-design/final/{name}.png)")
        Path(shared_md).write_text(shared, encoding="utf-8")
    return data


def hashes():
    values = {p.name: digest(p) for p in sorted(OUT.iterdir())
              if p.is_file() and p.name != "file-hashes.json"}
    save_json(OUT / "file-hashes.json", values)
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master", type=Path)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--basis-master", type=Path)
    parser.add_argument("--cabinet-receipt", type=Path)
    parser.add_argument("--pre-cabinets-master", type=Path)
    parser.add_argument("--interior-reference-receipt", type=Path)
    parser.add_argument("--interior-basis-master", type=Path)
    parser.add_argument("--interior-source", type=Path)
    parser.add_argument("--shared-md", type=Path)
    args = parser.parse_args()
    if args.master:
        if not all((args.receipt, args.basis_master, args.cabinet_receipt, args.pre_cabinets_master)):
            parser.error("--master requires both receipts and their corresponding basis masters")
        import_master(args.master, args.receipt, args.basis_master, args.cabinet_receipt, args.pre_cabinets_master,
                      args.interior_reference_receipt, args.interior_basis_master, args.interior_source)
    elif any((args.receipt, args.basis_master, args.cabinet_receipt, args.pre_cabinets_master,
              args.interior_reference_receipt, args.interior_basis_master, args.interior_source)):
        parser.error("Receipt and basis arguments require --master")
    data = build(args.shared_md)
    hashes()
    print(json.dumps({"source_master_sha256": data["source_master_sha256"],
                      "output": str(OUT), "items": len(data["items"]), "status": "review_only"}))


if __name__ == "__main__":
    main()
