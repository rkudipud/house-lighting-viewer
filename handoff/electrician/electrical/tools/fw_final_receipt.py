"""Create a non-self-referential receipt and SHA-256 inventory for the review pack."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HOUSE = Path(r"handoff/source-basis")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master", type=Path, default=HOUSE / "house-design.json")
    parser.add_argument("--out", type=Path, default=ROOT / "final-handoff")
    args = parser.parse_args()
    out, master = args.out.resolve(), args.master.resolve()
    ledger = load(out / "schedules" / "electrical-ledger.json")
    validation = load(out / "validation.json")
    if sha(master) != ledger["master_sha256"] or validation["master_sha256"] != ledger["master_sha256"]:
        raise ValueError("Current master, ledger and validation must have the same SHA")
    if validation["status"] != "PASS" or not all(v is False for v in ledger["release_flags"].values()):
        raise ValueError("Validation failed or a release flag changed")
    generator = out / "tools" / Path(__file__).name
    if Path(__file__).resolve() != generator.resolve():
        shutil.copy2(Path(__file__), generator)
    excluded = {"receipt.json", "SHA256SUMS.txt"}
    files = sorted((p for p in out.rglob("*") if p.is_file() and p.name not in excluded),
                   key=lambda p: str(p.relative_to(out)).casefold())
    inventory = {str(p.relative_to(out)): sha(p) for p in files}
    evidence = out / "source-evidence"
    receipt = {
        "schema": "electrical-handoff-receipt/1",
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "REVIEW_AND_QUOTATION_ONLY",
        "master_sha256": ledger["master_sha256"],
        "latest_master_receipt_sha256": sha(evidence / "wardrobe-interiors-reference-receipt.json"),
        "living_supply_decision_receipt_sha256": sha(evidence / "living-supply-and-cabinet-selections-receipt.json"),
        "one_supply_option_sha256": sha(evidence / "living-low-one-supply-option.json"),
        "historical_photometry": ledger["historical_photometry"],
        "totals_per_flat": ledger["totals_per_flat"],
        "release_flags": ledger["release_flags"],
        "validation_sha256": sha(out / "validation.json"),
        "validation_scope": validation["scope"],
        "validation_checks_passed": validation["checks_passed"],
        "open_holds": [
            "Exact strip, dimmer, controller, repeater and full chain are not proven or approved.",
            "Living P01 branch/fault protection, 20 A vs T1-K input, hatch, thermal, drop and LT-4/LT-5 inrush are open.",
            "P16 feed and C39/C40 drop margins, wet zones, protection and site routes require professional design.",
            "All curtain pocket dimensions and sightlines are unmeasured; the MBR pocket has no linked site photo.",
            "CBR C37 procurement, pooja geometry, product availability, warranty and current installed prices remain open.",
            "The provisional wardrobe reference adds no selected or costed wardrobe lighting.",
        ],
        "inventory_note": "SHA-256 inventory excludes this receipt and SHA256SUMS.txt to avoid self-reference.",
        "files_sha256": inventory,
    }
    receipt_path = out / "receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    listed = sorted([*files, receipt_path], key=lambda p: str(p.relative_to(out)).casefold())
    sums = "".join(f"{sha(p)}  {p.relative_to(out)}\n" for p in listed)
    sums_path = out / "SHA256SUMS.txt"
    sums_path.write_text(sums, encoding="utf-8")
    if sha(master) != ledger["master_sha256"]:
        raise ValueError("Master changed while the receipt was written; this receipt is stale")
    print(json.dumps({
        "master_sha256": ledger["master_sha256"],
        "receipt_sha256": sha(receipt_path),
        "sha256sums_sha256": sha(sums_path),
        "listed_files": len(listed),
    }, indent=2))


if __name__ == "__main__":
    main()
