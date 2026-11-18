# Remaining-room simulation: sensitivity revision

**Exploratory only:** generic provisional photometry, assumed surfaces and geometry; not measured, product-specific or a construction release. This supplements the previous `simulation-report.md` and supersedes only its statement that small-room sensitivity was not run.

Master SHA-256 `b6f6bf1a127c7e39086deb9fd1d2c0dff79a495381e1a4b9457f6a9a468f23ac` and the prior review package are unchanged. All fittings, approvals, and existing holds remain unchanged; nothing was published or pushed.

## Scope and method

Each of six enclosures was run with the baseline and eight named sensitivity variants: 54 enclosure/case calculations. All use Radiance rcontrib, ab 8 / ad 512, MF 0.8, maintained lux, with the original 0.25 ft grids and recorded task masks. The prior report covers living, dining, kitchen and bedrooms.

- `rho_low` and `rho_high`: assumed reflectances; `beam_minus10` / `beam_plus10`: generic point-source beam angles changed by 10 degrees; `ceil_minus0.1` / `ceil_plus0.1`: hypothetical ceiling and associated ceiling-mounted source heights changed by 0.1 m. These are calculation variants, not design changes.
- `pocket_narrow` / `pocket_wide`: **identical-scene controls**, not a physical pocket study. These enclosures contain no modelled tray/cove pocket, including the bathroom perimeter strip. Actual pocket sensitivity remains unknown.
- Kitchen-slot variants are specific to the kitchen and were already covered by the previous report; they are not applicable here. Lumen +/-20% and MF 0.7/0.9 scale linearly relative to the MF 0.8 output.

## Baseline and sampling

Values are HIGH at 100%, averaged over the task mask: mean / minimum in lux / U0. Floor planes are evaluated 0.0005 m above the nominal floor. Small task masks in dressing and lobby warrant special caution.

| Room | Plane (m) | Grid shape | Room / task points | HIGH mean / min / U0 | LOW mean / min / U0 |
|---|---:|---|---:|---|---|
| Utility (UTL) | 0.90 | 16 x 58 | 928 / 132 | 211.1 / 172.2 / 0.82 | - |
| Dressing (DRS) | 0.75 | 25 x 14 | 350 / 12 | 197.9 / 190.2 / 0.96 | - |
| Lobby (LOB) | 0.75 | 22 x 14 | 308 / 8 | 264.2 / 255.7 / 0.97 | - |
| Attached bath (TL1) | 0.00 | 22 x 35 | 770 / 168 | 257.3 / 167.0 / 0.65 | 186.9 / 150.4 / 0.80 |
| Common bath (TL2) | 0.00 | 22 x 35 | 770 / 168 | 257.4 / 167.3 / 0.65 | 185.8 / 147.0 / 0.79 |
| Balcony (BAL) | 0.00 | 32 x 42 | 1344 / 522 | 75.3 / 49.0 / 0.65 | 54.7 / 33.9 / 0.62 |

## Sensitivity results

Paired changes use the same ad-512 baseline; percentages are change in task-mask mean. `-` means no modelled LOW lane. The U0 columns show HIGH uniformity, baseline to variant. Differences comparable to the identical-scene spread below should not be interpreted as a reliable effect.

| Room | Variant | HIGH mean change | HIGH U0 base -> variant | LOW mean change | LOW U0 base -> variant |
|---|---|---:|---|---:|---|
| UTL | rho_low | -20.78% | 0.82 -> 0.80 | - | - |
| UTL | rho_high | 27.96% | 0.82 -> 0.85 | - | - |
| UTL | beam_minus10 | 6.31% | 0.82 -> 0.82 | - | - |
| UTL | beam_plus10 | -5.15% | 0.82 -> 0.83 | - | - |
| UTL | ceil_minus0.1 | 5.72% | 0.82 -> 0.82 | - | - |
| UTL | ceil_plus0.1 | -5.24% | 0.82 -> 0.82 | - | - |
| DRS | rho_low | -14.89% | 0.96 -> 0.95 | - | - |
| DRS | rho_high | 20.85% | 0.96 -> 0.96 | - | - |
| DRS | beam_minus10 | 20.90% | 0.96 -> 0.95 | - | - |
| DRS | beam_plus10 | -14.16% | 0.96 -> 0.96 | - | - |
| DRS | ceil_minus0.1 | 6.41% | 0.96 -> 0.96 | - | - |
| DRS | ceil_plus0.1 | -6.03% | 0.96 -> 0.97 | - | - |
| LOB | rho_low | -13.65% | 0.97 -> 0.96 | - | - |
| LOB | rho_high | 18.52% | 0.97 -> 0.97 | - | - |
| LOB | beam_minus10 | 22.43% | 0.97 -> 0.96 | - | - |
| LOB | beam_plus10 | -15.09% | 0.97 -> 0.97 | - | - |
| LOB | ceil_minus0.1 | 7.64% | 0.97 -> 0.97 | - | - |
| LOB | ceil_plus0.1 | -6.87% | 0.97 -> 0.97 | - | - |
| TL1 | rho_low | -12.52% | 0.65 -> 0.62 | -24.80% | 0.80 -> 0.77 |
| TL1 | rho_high | 18.53% | 0.65 -> 0.69 | 35.85% | 0.80 -> 0.80 |
| TL1 | beam_minus10 | 18.77% | 0.65 -> 0.58 | -0.31% | 0.80 -> 0.82 |
| TL1 | beam_plus10 | -13.21% | 0.65 -> 0.70 | -0.28% | 0.80 -> 0.82 |
| TL1 | ceil_minus0.1 | 5.00% | 0.65 -> 0.63 | 3.33% | 0.80 -> 0.78 |
| TL1 | ceil_plus0.1 | -4.66% | 0.65 -> 0.67 | -3.83% | 0.80 -> 0.80 |
| TL2 | rho_low | -12.55% | 0.65 -> 0.62 | -24.32% | 0.79 -> 0.77 |
| TL2 | rho_high | 18.50% | 0.65 -> 0.69 | 36.55% | 0.79 -> 0.84 |
| TL2 | beam_minus10 | 18.72% | 0.65 -> 0.58 | -0.10% | 0.79 -> 0.81 |
| TL2 | beam_plus10 | -13.25% | 0.65 -> 0.70 | 0.28% | 0.79 -> 0.81 |
| TL2 | ceil_minus0.1 | 4.97% | 0.65 -> 0.63 | 3.63% | 0.79 -> 0.78 |
| TL2 | ceil_plus0.1 | -4.73% | 0.65 -> 0.67 | -3.39% | 0.79 -> 0.81 |
| BAL | rho_low | -11.56% | 0.65 -> 0.61 | -40.45% | 0.62 -> 0.56 |
| BAL | rho_high | 17.53% | 0.65 -> 0.70 | 53.48% | 0.62 -> 0.71 |
| BAL | beam_minus10 | 15.74% | 0.65 -> 0.57 | -8.88% | 0.62 -> 0.70 |
| BAL | beam_plus10 | -11.73% | 0.65 -> 0.70 | 5.39% | 0.62 -> 0.66 |
| BAL | ceil_minus0.1 | 3.69% | 0.65 -> 0.63 | 2.75% | 0.62 -> 0.65 |
| BAL | ceil_plus0.1 | -3.54% | 0.65 -> 0.66 | -1.70% | 0.62 -> 0.64 |

## Identical-scene repeat diagnostic

The baseline and the two no-op pocket cases compile to byte-identical scenes. The table gives the range across their three simulated means, as a percentage of the baseline mean. This is a small run-to-run diagnostic, **not** a confidence interval or a measurement of real pocket geometry.

| Room | HIGH range | LOW range |
|---|---:|---:|
| UTL | 0.07% | - |
| DRS | 0.09% | - |
| LOB | 0.03% | - |
| TL1 | 0.02% | 0.35% |
| TL2 | 0.03% | 0.62% |
| BAL | 0.02% | 0.74% |

## Utility and lobby task-plane diagnostics

Utility values are HIGH+TASK at 100% on the 0.9 m room grid, not a separately surveyed counter patch. Lobby values are vertical HIGH+MIRROR at the original three face points; they are not a full face-uniformity assessment.

| Variant | Utility mean (lx) | Lobby vertical mean / min (lx) |
|---|---:|---|
| base | 289.2 | 399.5 / 397.0 |
| rho_low | 234.1 | 341.4 / 339.6 |
| rho_high | 364.2 | 479.7 / 474.0 |
| beam_minus10 | 302.6 | 402.3 / 398.7 |
| beam_plus10 | 278.5 | 396.2 / 392.2 |
| ceil_minus0.1 | 301.8 | 409.8 / 406.7 |
| ceil_plus0.1 | 277.9 | 390.3 / 388.2 |

## Existing scene levels on the baseline grid

Task-mask mean lux from the six canonical scene level combinations. Zero means no included lane in that room; adjacent-room spill is not modelled in these closed enclosures. These are relative dimming combinations, not spectral or CCT calculations.

| Room | Off | Mood | Relax | Work | Full | Night |
|---|---:|---:|---:|---:|---:|---:|
| UTL | 0.0 | 0.0 | 63.3 | 277.5 | 289.2 | 0.0 |
| DRS | 0.0 | 0.0 | 59.4 | 197.9 | 197.9 | 0.0 |
| LOB | 0.0 | 0.0 | 79.3 | 349.3 | 349.3 | 0.6 |
| TL1 | 0.0 | 61.0 | 148.7 | 599.6 | 640.4 | 0.0 |
| TL2 | 0.0 | 60.5 | 148.3 | 599.3 | 639.4 | 0.0 |
| BAL | 0.0 | 32.8 | 50.0 | 75.3 | 130.0 | 0.0 |

## Verification and limitations

The previous A1-A4 engine benchmark results are inherited, not rerun. The new independent audit compares same-settings local versus remote baseline means for every fixture and plane and the room HIGH/LOW lanes; acceptance is within the greater of 6% of the local mean or 0.30 lx. The remote engine and generic optics hashes match the earlier parity run.

| Room | HIGH baseline difference | LOW baseline difference |
|---|---:|---:|
| UTL | -0.01% | - |
| DRS | 0.20% | - |
| LOB | -0.04% | - |
| TL1 | -0.01% | 0.43% |
| TL2 | 0.02% | -0.13% |
| BAL | 0.00% | 0.47% |

- **PASS**: Previous receipt, source files, outputs, master and delivered review unchanged.
- **PASS**: All nine variants, units, optical parameters and remote engine hashes.
- **PASS**: All result vectors finite, non-negative and aligned with original grids and workplanes.
- **PASS**: Unchanged fixture identities and plan polygons.
- **PASS**: Ceiling perturbations and flat/no-tray scene construction.
- **PASS**: Baseline scene matches previous local scene; pocket cases are identical-scene controls.
- **PASS**: Identical-settings local/remote parity on room lanes and every fixture/plane.

**Holds and limitations:**
- Utility and balcony are open-air in the brief but enclosed in this provisional model. Absolute lux and reflectance responses may be overstated; no exterior validation.
- Bathroom HIGH/LOW results are floor-plane values. No bathroom face-plane, mirror glare, IP zoning, or electrical safety approval is established by these runs.
- No IES/LDT files, selected products, measured finish reflectances, surveyed surfaces, real luminaire cut-off, glossy reflections, daylight, flicker, thermal or UGR calculations are supplied.
- Pooja, KIT-L1, curtain-strip, balcony and all other prior holds remain in force. Construction release, product approval and exact-chain proof remain false.
- The same flat is assumed on each floor; floor-specific survey variations were not modelled.

## Evidence

- `analysis-remaining.json`: complete scene, lane, task, parity and audit results.
- `runs\sens512small-*\sim-results.json`: per-fitting lux vectors and workplane coordinates.
- `runs\sens512small-*\radiance\*.rad`: generated room scenes used for the runs.
- `simulation-receipt-remaining.json`: file hashes and inherited master/review hashes.
- `independent-verification.json`: independent raw-statistic recomputation and report hashes.
- Previous full report and receipt remain one directory above this revision.


Public-copy note: operational job/log/cleanup artifacts and compiled scenes are omitted. Analysis and verification scripts are archived source snapshots, not a portable verification of the private master/receipt chain. Source/public hashes and omissions are recorded in `repository-copy-receipt.json`.
