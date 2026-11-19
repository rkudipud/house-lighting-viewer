> Public-copy note: manufacturer PDFs are not redistributed. Links open official sources; mentions of retained archives describe the privately inspected source evidence. Source and delivered hashes differ where paths or links were adapted; see `final-review-source-copy.json`.

# Electrical and lighting-control review package

**Review and quotation only. Not approved for purchase, wiring or construction.**
The homeowner's selected fixed CCT, S1 curtain strips, CBR H1-H6 review release
and one-supply living LOW concept are included. Product, exact-chain, site,
professional and construction releases remain open.

The current review includes the fixed-CCT selection and children's ceiling proposal.
No new wardrobe lighting is selected or costed.

## Read first

* `electrical-review.pdf` - room circuits, control and supply schedules,
  conceptual wiring blocks, site photos, open checks and budget qualifications.
* `control-options.pdf` - local dimming choices, switchboard intent and limits.
* `bill-of-materials.pdf` - modeled items by room; the full location-linked
  list is `schedules\location-linked-bom.csv`.
* `wholesale-rfq.pdf` - project search targets and exact-chain questions for
  generic/imported products or branded suppliers.
* `source-index.pdf` - official manufacturer references, archived evidence
  and unresolved conflicts.
* `figures\` - four conceptual diagrams in SVG and 2x PNG, plus two source
  site photographs. The MBR selected pocket has no individually linked photo
  in the master and must be checked on site.
* `schedules\` - circuit, fixture, CCT, switchboard, control, supply, drop,
  dimmer, curtain and location-linked BOM tables, plus `electrical-ledger.json`.
* Official manufacturer links replace third-party PDFs in the public copy;
  `source-evidence\` retains decision receipts and historical verification. `receipt.json` records the basis and
  holds; `validation.json` records artifact-consistency checks;
  `SHA256SUMS.txt` inventories every file except itself.

All counts are per flat unless identified otherwise. The 108 fixtures / 51
circuits include four unmeasured curtain strips totaling 8.88 m / 71.04 W;
those strips receive no photometric credit. The historical 82/82 photometry
result applies to its original verified input. The children's room has a
separate provisional generic-optics reanalysis; other rooms retain historical
estimates. No result is a measured field value.

P01 is one 480 W-class 24 V planning supply serving a modeled 181.52 W of
living LOW strips; P03 is removed. HLG-480H-24 is only a reference. Actual
strip/controller/repeater compatibility, 20 A versus controller-input
protection, 480 W hatch fit, voltage drop and LT-4/LT-5 inrush remain held.
P16/C39/C40, pocket dimensions, wet zones, local availability, warranty and
all site/professional checks remain open. The 1050 mm fan at the nominal room
centre is a planning choice, not a selected product or airflow approval. The
CBR cove and LINE are ON in the design simulation, but their installation and
operation remain held. No current installed price is verified.

## Provenance and regeneration

`source-evidence\prior-control-plan.json` and
`source-evidence\prior-control-plan-receipt.json` are preserved **only as
historical source evidence**. They predate the one-supply selection; use this
package's current schedules instead. The historical receipt preserves hashes
of its superseded review documents, which were removed after replacement; it
is retained for source provenance, not as a complete archived output set.
Similarly, `build-context.json` was
written before final render and validation; `receipt.json` and
`validation.json` record the completed review checks.

`tools\` contains the generating, rendering and validation scripts and text
templates. The retained sibling `fixed-white\` directory contains the
historical source plan, original figures, generating templates and scripts.
The builder accepts explicit `--house-root`, `--lighting-root`, `--fixed-root`,
`--manufacturer-sources`, `--dimmer-sources`, `--master` and `--out` paths;
its default paths refer to the current session environment. Preserve the
master's previous snapshots, signed receipts and original lighting fragment
when moving the build to another repository. The omitted third-party source PDFs
must be obtained from their official publishers. Rebinding after any
master change requires inspecting its receipt and changes, not merely replacing
the hash.

`validation.json` checks source linkage, arithmetic, schedule coverage and
document/image integrity. It is not a new photometric result, electrical
safety assessment, compatibility approval or installation authorization.
The renderer's `mode: final` describes PDF rendering only, not project release.
