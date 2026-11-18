> Public-copy note: manufacturer PDFs are not redistributed. Links open official sources; mentions of retained archives describe the privately inspected source evidence. Source and delivered hashes differ where paths or links were adapted; see repository-copy-receipt.json.

# Location-linked lighting bill of materials

**Master SHA-256:** `b6f6bf1a127c7e39086deb9fd1d2c0dff79a495381e1a4b9457f6a9a468f23ac`. These are **modeled quantities for one flat**, not purchase quantities or approved construction dimensions. Four floors are intended to repeat the scheme, but site geometry, returns, cuts, product lead lengths and wastage must be measured independently. No verified current installed quote exists.

The complete `schedules/location-linked-bom.csv` lists **108 fixture records**, the separate profile allowances, **12 24 V supply classes**, **31 wall controls**, **three modeled PWM repeaters**, **eight conceptual switch modules**, and one 48 V track driver. It includes circuit/board, model specification, CCT, CRI/R9/IP targets and available indicative solver coordinates or strip paths. A supply, dimmer, switch, profile or repeater appears separately from its fixture; omit a separate profile where an approved integrated product already includes the required diffuser and heat-sinking. Do not treat these entries as certified matched products.

**Cautions:** P01's 480 W-class hatch location is unknown. Other positions are design placeholders, not field measurements. Strip lengths are installed-run model lengths, **not** reel or cut-order quantities. The four curtain strips are 8.88 m / 71.04 W combined, unmeasured and excluded from lux calculations. Prices, GST, delivery, labour, mounting hardware, spare stock, electrical cabling, connectors, boxes, DB/protection, accessories and waste need itemised quotes and professional survey.

## Fixture groups by location

Descriptions, individual modeled watts/lumens/beams, minimum CRI/R9, IP targets, CCT and design notes are in `schedules/fixture-class-specifications.csv` and `schedules/fixtures.csv`; a class is a search target, not a manufacturer SKU. The fixture IDs below point to their individual coordinates or paths in the location bill.

| Room | Class | Qty | Fixed CCT | Strip m | Fixture IDs |
| --- | --- | --- | --- | --- | --- |
| BAL | CYLSV | 2 | 3000K | - | BAL-H1, BAL-H2 |
| BAL | PLINTH | 1 | 2700K | 2.93 | BAL-L1 |
| BAL | UPDNV | 2 | 2700K | - | BAL-L2, BAL-L3 |
| CBR | COVE_FW | 2 | 2700K | 7.77 | CBR-L1, CURT-CBR |
| CBR | DL6 | 6 | 3000K | - | CBR-H1, CBR-H2, CBR-H3, CBR-H4, CBR-H5, CBR-H6 |
| CBR | LIN | 4 | 2700K | 5.36 | CBR-X1, CBR-X2, CBR-X3, CBR-X4 |
| CBR | READ | 2 | 3000K | - | CBR-R1, CBR-R2 |
| CBR | TASK_HO | 1 | 4000K | 1.14 | CBR-S1 |
| DIN | COVE_FW | 2 | 2700K | 8.66 | DIN-L2, CURT-DIN |
| DIN | DL10 | 3 | 3000K | - | DIN-H1, DIN-H2, DIN-H3 |
| DIN | DL8V | 1 | 3000K | - | DIN-H6 |
| DIN | LIN | 1 | 2700K | 3.37 | DIN-X1 |
| DIN | PEND | 1 | 2700K | - | DIN-L1 |
| DIN | TRK6 | 3 | 3000K | - | FW-T1, FW-T2, FW-T3 |
| DIN | TRKLIN | 1 | 3000K | - | FW-T4 |
| DRS | DL7V | 2 | 4000K | - | DRS-H1, DRS-H2 |
| KIT | COVE_FW | 1 | 2700K | 8.82 | KIT-L1 |
| KIT | DL10 | 5 | 4000K | - | KIT-H1, KIT-H2, KIT-H3, KIT-H4, KIT-H7 |
| KIT | DL7 | 3 | 4000K | - | KIT-H5, KIT-H6, KIT-H8 |
| KIT | LIN | 1 | 4000K | 1.16 | KIT-T4 |
| KIT | TASK | 2 | 4000K | 1.16 | KIT-T2, KIT-T3 |
| KIT | TASK_LO | 1 | 4000K | 1.68 | KIT-T1 |
| LIV | BACK | 2 | 2700K | 5.3 | LIV-L2, LIV-P1 |
| LIV | COVE_FW | 2 | 2700K | 13.98 | LIV-L1, CURT-LIV |
| LIV | DL8 | 7 | 3000K | - | LIV-H1, LIV-H2, LIV-H3, LIV-H4, LIV-H5, LIV-H6, LIV-H7 |
| LIV | DL8A | 3 | 3000K | - | LIV-H8, LIV-H9, LIV-H10 |
| LIV | LIN | 2 | 2700K | 4.08 | LIV-X1, LIV-X2 |
| LIV | PIN6V | 1 | 2700K | - | LIV-P2 |
| LOB | DL7V | 2 | 3000K | - | LOB-H1, LOB-H2 |
| LOB | FACE10V | 1 | 4000K | - | LOB-F1 |
| LOB | STEP | 1 | 2700K | - | LOB-N1 |
| MBR | BACK | 1 | 2700K | 1.28 | MBR-L2 |
| MBR | COVE_FW | 2 | 2700K | 8.96 | MBR-L1, CURT-MBR-S |
| MBR | DL6 | 8 | 3000K | - | MBR-H1, MBR-H2, MBR-H3, MBR-H4, MBR-H5, MBR-H6, MBR-H7, MBR-H8 |
| MBR | LIN | 2 | 2700K | 3.86 | MBR-X1, MBR-X2 |
| MBR | READ | 2 | 3000K | - | MBR-R1, MBR-R2 |
| MBR | STEP | 1 | 2700K | - | MBR-N1 |
| TL1 | BCOVE | 1 | 2700K | 6.64 | TL1-L1 |
| TL1 | BDIF9V | 3 | 4000K | - | TL1-G1, TL1-G2, TL1-G3 |
| TL1 | BSPOT8V | 2 | 4000K | - | TL1-M1, TL1-M2 |
| TL1 | FACEV | 2 | 4000K | - | TL1-F1, TL1-F2 |
| TL1 | NICHE | 1 | 2700K | 0.75 | TL1-L2 |
| TL1 | VANITY | 1 | 2700K | 0.55 | TL1-L3 |
| TL2 | BCOVE | 1 | 2700K | 6.64 | TL2-L1 |
| TL2 | BDIF9V | 3 | 4000K | - | TL2-G1, TL2-G2, TL2-G3 |
| TL2 | BSPOT8V | 2 | 4000K | - | TL2-M1, TL2-M2 |
| TL2 | FACEV | 2 | 4000K | - | TL2-F1, TL2-F2 |
| TL2 | NICHE | 1 | 2700K | 0.75 | TL2-L2 |
| TL2 | VANITY | 1 | 2700K | 0.55 | TL2-L3 |
| UTL | BULKD | 3 | 4000K | - | UTL-H1, UTL-H2, UTL-H3 |
| UTL | TASKW | 1 | 4000K | 1.1 | UTL-T1 |

## Switchboards and other equipment

| Board | Knobs / mains dimmers | On/off modules | Integral fitting IDs |
| --- | --- | --- | --- |
| SB-01 | 5 / 2 | 0 | - |
| SB-02 | 2 / 3 | 1 | - |
| SB-03 | 2 / 2 | 0 | - |
| SB-04 | 1 / 1 | 0 | - |
| SB-05 | 1 / 1 | 1 | C24 |
| SB-05L | 0 / 0 | 1 | C25 |
| SB-05R | 0 / 0 | 1 | C26 |
| SB-06 | 1 / 0 | 0 | - |
| SB-06B | 3 / 0 | 0 | - |
| SB-07 | 1 / 0 | 1 | C33 |
| SB-07B | 3 / 0 | 0 | - |
| SB-08 | 2 / 1 | 1 | - |
| SB-08RL | 0 / 0 | 1 | C41 |
| SB-08RR | 0 / 0 | 1 | C41b |

Wall controls in the table are **21 single-colour knobs and ten mains-dimmer groups**. The six integral reader/PIR controls are inside fittings, not six more wall modules. Supplementary modules are conceptual two-way/intermediate switch points; exact plate layouts and back-box sizes remain open. Board and fixture placement requires site measurement.

The supply, circuit and control mappings are in `supply-schedule.csv`, `circuit-schedule.csv` and `wall-control-schedule.csv`; P01 is one 480 W-class reference supply, P03 is removed, and the 48 V track driver is separate. All source/driver/dimmer/repeater compatibility, distribution protection, thermal checks, wet-zone suitability, C39/C40 and curtain-pocket holds remain open.

For generic/imported or branded procurement search use `wholesale-rfq.md`; for exact manufacturer evidence use `source-index.md`. **No product or construction approval is implied.**
