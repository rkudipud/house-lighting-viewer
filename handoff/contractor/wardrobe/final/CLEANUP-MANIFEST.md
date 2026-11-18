# Wardrobe data cleanup manifest

Cleanup scope: this session's `files/storage-design` folder only. The cleanup below was performed against the previous master SHA-256 `e0bf1af22850905405eec2e8c07940f9e8d5a6ac04baecc03547a3fdcc733b72`; it is a historical cleanup record, not the current pack's source identifier.

## Removed

| Removed path | Reason | Verified replacement |
|---|---|---|
| `storage-fragment.json` | Prior interim fragment; its storage data is retained in the coordinator-owned canonical master. Its applicability details were superseded by current master decisions. | `storage-current.json` is the current homeowner-review projection; the canonical master remains authoritative. |
| `storage-sheets.html`, `storage-sheets.pdf` | Interim sheets used superseded storage views. | `wardrobe-signoff-pack.md`, `wardrobe-signoff-pack.pdf`, and the five current room PNG/SVG pairs. |
| `rebase-validation.json`, `validate_rebase.py` | Receipt and validator tied to the earlier 88cb5c3c basis and archive inputs; no longer validate the current master. | Current master provenance, `file-hashes.json`, and the checks recorded for this final package. |
| Root `cost-common.csv`, `cost-flats.csv`, `cost-units.csv`, `cost_model.json` | Duplicate generated exports, byte-equal to their final-folder copies. | `final/cost-common.csv`, `final/cost-flats.csv`, `final/cost-units.csv`, `final/cost_model.json`. |
| `__pycache__/cost_model.cpython-315.pyc` | Re-creatable Python bytecode cache; not a source or evidence file. | `cost_model.py`. |

No `archive/` directory was present to clean. No source attachment, transcript image, other session folder, canonical master, or current source/evidence file was deleted or modified.

## Retained

Current source inputs and readable artifacts remain available: `storage-current.json`, `cost-evidence.json/.md`, `cost-comparison.md`, `signoff_pack.py`, `storage_model.py`, `cost_model.py`, `cost_report.py`, `drawings.py`, and the root wardrobe brief, material verdict, and site-data files. `renders/p16.png`, `renders/p17.png`, and `renders/p18.png` are retained as source-page evidence.

The final folder contains the homeowner-review pack, the current storage JSON, cost model and separate CSVs, source cost evidence, five room PNG/SVG pairs, a current `file-hashes.json`, and this manifest. The later integrated sign-off selects OPT-E and approves the master split in principle; measurements and details remain unresolved and this package is not construction or fabrication approval.

## Provisional-interior pass

Removed only the `storage-design/interior-draft/` directory: ten draft PNG/SVG interior sheets, each with a current replacement in `final/`, and three temporary PDF-review PNGs. Also removed the recreatable Python caches `__pycache__/cost_model.cpython-315.pyc`, `__pycache__/interiors_model.cpython-315.pyc` and `__pycache__/signoff_pack.cpython-315.pyc`, then their empty directory.

Retained `interiors_model.py` and the final parametric `wardrobe-interiors.json`. The final package now contains five placement and five provisional-interior PNG/SVG pairs. Both selected cabinets remain subject to site fit; the utility carcass and shelves require a separate quote.
