# Current lighting review package

**REVIEW ONLY - NOT FOR CONSTRUCTION.** One typical Hyderabad 2BHK floor; confirm conditions independently on all four floors.

Master SHA-256: `79ece2aef1acd63ee401702149a91e29a6ed660123c4d9d3640ab5304ed89822`. The package is generated from that master; `manifest.json` binds each file. Historical optical input: `ca19a7b5cf2c0c92cf3120c95c812567fbdaa3325a7e18b3a132105e66aa604e`. The new heatmap `e935075c00174584056d8f4fb5aaac799146341c7d5923d1d45bd714a9a0e7c6` contains a targeted CBR-only reanalysis; every other room grid is unchanged from the verified original. Generic optics and provisional geometry are not measured or product-validated.

- `lighting-workbench.html`: offline plan, individual fitting inspector and saved analytic room maps. The controls select stored results, not live recalculation.
- `lighting-plan-main`, `lighting-plan-mood`, `lighting-plan-task`: A4 portrait PDF sets (page 1 overview with a zoom key; pages 2-7 are 2 x 3 zoom tiles with fitting IDs at 7.5 pt and a fixed-CCT suffix). Fitting types are distinguished by colour, line pattern and marker, legible in grayscale; a black ring marks placement/site holds. SVG/PNG give the overview, `-zoom-N.png` the tiles. Lighting-zone outlines and the four curtain lengths remain approximate.
- `lighting-review-schedules.pdf`: review quantities, fitting/control/supply and generic product tables.
- `heatmaps-summary.pdf`, `heatmaps/*.png`, `heatmaps.json`: CBR-reanalysed and otherwise inherited numerical model, no curtain lux credit. CBR estimates include held fittings and are not currently available viewer light.
- `lighting-specification.md`, `fixture-ledger.csv`, `curtain-strips.csv`, `switchboard-schedule.csv`, `circuit-ledger.csv`, `supply-ledger-selected-s1.csv`, `voltage-drop-selected-s1.csv`, `generic-product-search.csv`: current review schedules.
- `compliance-analytic-reference.csv`, `criteria-historical-reference.md`, `bom-historical-estimate.json`: prior calculations, research and cost allowances; not current product, cost or statutory approval.

Four curtain strips are homeowner-selected but held for pocket measurement/mock-up; W03 is excluded. CBR-H1-H6, the retained cove and relocated LINE strips are modelled ON for review; the cove and LINE installation remain held (H-CBR-CEIL). The CBR fan, loft/shutter, profile and electrical clearances are unmeasured; the wardrobe and glare diagnostics need review. P01 is one 480 W-class reference supply; P03 is removed. P01 distribution/protection, LT-4/LT-5 inrush and living voltage drop are OPEN. P16/C39/C40 remain MARGINAL. Product approval, exact-chain proof and construction release are false; a licensed electrician and manufacturers must resolve the electrical design.
